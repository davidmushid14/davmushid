from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import Babel, gettext as _
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import requests

app = Flask(__name__)
app.secret_key = 'cfbf976df4f2e295000890d09fcce409934b96d0251391627a874c3d65c47bf4'  # Clé secrète pour Flask

# Configuration de Stripe
stripe.api_key = 'sk_test_51R0140L11Yg2rs4elCsCL1IXDv4dp39o1qp3bgBUnO4kmB3rzgS97oysiH5gMiR8X1uD8l2VataNJh1U3pWqb4ni00MhXiVSdb'  # Remplace par ta clé secrète Stripe
stripe_public_key = 'pk_test_51R0140L11Yg2rs4e4ePnXNBfbJ82uPMi5MCNPgqOEFDl5CGdrQxGJCZa3xSCImkW5CCDsUdjWxyXiNpWU86IAbRI00ajzxV46S'  # Remplace par ta clé publique Stripe

# Configuration de la base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration de Flask-Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # Français par défaut
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'  # Dossier des fichiers de traduction
babel = Babel(app)

# Fonction pour obtenir la langue actuelle
def get_locale():
    lang = request.args.get('lang') or request.accept_languages.best_match(['fr', 'en', 'zh', 'ar'])
    print(f"Langue sélectionnée : {lang}")  # Pour voir la langue choisie dans la console
    return lang

babel.locale_selector_func = get_locale

# Ajouter get_locale au contexte global des templates
@app.context_processor
def inject_locale():
    return {'current_locale': get_locale()}

# Initialisation de SQLAlchemy
db = SQLAlchemy(app)

# Initialisation de Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'index'  # Redirige vers la page d'accueil si l'utilisateur n'est pas connecté

# Modèle Utilisateur
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# Chargement de l'utilisateur pour Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Création de la base de données
with app.app_context():
    db.create_all()

API_KEY = 'votre_clé_API'
BASE_URL = 'https://api.tiktok.com/accounts/search'

@app.route('/')
def index():
    welcome_message = _("Bienvenue sur notre site !")  # Texte à traduire
    return render_template('index.html', welcome_message=welcome_message)

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Vérification si l'utilisateur existe déjà
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(_("Cet utilisateur existe déjà."), "error")
            return redirect(url_for('index'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash(_("Cet email est déjà utilisé."), "error")
            return redirect(url_for('index'))

        # Hachage du mot de passe avec pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Création d'un nouvel utilisateur
        new_user = User(username=username, email=email, password=hashed_password)

        # Ajout à la base de données
        db.session.add(new_user)
        db.session.commit()

        flash(_("Inscription réussie ! Vous pouvez maintenant vous connecter."), "success")
        return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Recherche de l'utilisateur dans la base de données
        user = User.query.filter_by(username=username).first()

        # Vérification du mot de passe
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(_("Connexion réussie !"), "success")
            return redirect(url_for('dashboard'))
        else:
            flash(_("Utilisateur non trouvé ou mot de passe incorrect."), "error")
            return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_("Vous avez été déconnecté."), "success")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        selected_country = request.form['country']
        selected_category = request.form['category']
        selected_followers = request.form['followers']

        accounts = get_tiktok_accounts(selected_country, selected_category, selected_followers)

        # Vérifier le plan choisi (Basic ou Premium)
        plan = request.form.get('plan', 'basic')  # Par défaut, le plan est Basic
        if plan == 'basic':
            return render_template('basic.html', accounts=accounts)
        else:
            return render_template('search.html', accounts=accounts)
    return render_template('search.html')

def get_tiktok_accounts(country, category, followers_range):
    params = {
        'api_key': API_KEY,
        'country': country,
        'category': category,
        'followers_range': followers_range
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return []

@app.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        data = request.get_json()
        amount = data['amount']

        # Créer un PaymentIntent avec l'API Stripe
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',  # Remplacez par la devise appropriée
            payment_method_types=['card', 'apple_pay', 'paypal'],  # Activer Apple Pay et PayPal
            metadata={'integration_check': 'accept_a_payment'},
        )

        return jsonify({
            'clientSecret': intent['client_secret']
        })
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        plan = request.form['plan']
        # Process payment here

        # Rediriger en fonction du plan choisi
        if plan == 'basic':
            return redirect(url_for('basic'))
        else:
            return redirect(url_for('search'))
    return render_template('payment.html', stripe_public_key=stripe_public_key)

@app.route('/basic')
@login_required
def basic():
    return render_template('basic.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/callback')
def callback():
    return render_template('callback.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
