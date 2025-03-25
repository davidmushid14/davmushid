from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import Babel, gettext as _
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de Stripe
import stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")

app = Flask(__name__)
app.secret_key = 'cfbf976df4f2e295000890d09fcce409934b96d0251391627a874c3d65c47bf4'

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration de Flask-Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
babel = Babel(app)

def get_locale():
    lang = request.args.get('lang') or request.accept_languages.best_match(['fr', 'en', 'zh', 'ar'])
    return lang

babel.locale_selector_func = get_locale

@app.context_processor
def inject_locale():
    return {'current_locale': get_locale()}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'index'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

API_KEY = 'votre_clé_API'
BASE_URL = 'https://api.tiktok.com/accounts/search'

@app.route('/')
def index():
    welcome_message = _("Bienvenue sur notre site !")
    return render_template('index.html', welcome_message=welcome_message)

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(_("Cet utilisateur existe déjà."), "error")
            return redirect(url_for('index'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash(_("Cet email est déjà utilisé."), "error")
            return redirect(url_for('index'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
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
        user = User.query.filter_by(username=username).first()

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
        plan = request.form.get('plan', 'basic')
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
    return response.json() if response.status_code == 200 else []

@app.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        data = request.get_json()
        if not data or 'amount' not in data:
            return jsonify(error="Amount is required"), 400

        # Méthodes de paiement de base
        payment_methods = ['card', 'paypal']
        
        # Créer le PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=data['amount'],
            currency='usd',
            payment_method_types=payment_methods,
        )

        return jsonify({'clientSecret': intent['client_secret']})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        plan = request.form['plan']
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