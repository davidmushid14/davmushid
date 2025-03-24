function getQueryParams() {
    let params = {};
    let queryString = window.location.search.substring(1);
    let regex = /([^&=]+)=([^&]*)/g;
    let match;
    while (match = regex.exec(queryString)) {
        params[decodeURIComponent(match[1])] = decodeURIComponent(match[2]);
    }
    return params;
}

let queryParams = getQueryParams();
let authorizationCode = queryParams['code'];
let state = queryParams['state'];

if (authorizationCode) {
    document.getElementById('code').innerText = `Authorization Code: ${authorizationCode}`;
} else {
    document.getElementById('code').innerText = 'Authorization code not found.';
}
// Animation Shader Collab
let camera, scene, renderer, clock;
let uniforms;

function init() {
  const container = document.getElementById("shadercollab");

  clock = new THREE.Clock();
  camera = new THREE.Camera();
  camera.position.z = 1;

  scene = new THREE.Scene();
  const geometry = new THREE.PlaneBufferGeometry(2, 2);

  uniforms = {
    u_time: { type: "f", value: 1.0 },
    u_resolution: { type: "v2", value: new THREE.Vector2() }
  };

  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: document.getElementById("vertex").textContent,
    fragmentShader: document.getElementById("fragment").textContent
  });

  const mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);

  renderer = new THREE.WebGLRenderer();
  renderer.setPixelRatio(window.devicePixelRatio);
  container.appendChild(renderer.domElement);

  onWindowResize();
  window.addEventListener("resize", onWindowResize);
}

function onWindowResize() {
  renderer.setSize(window.innerWidth / 2, window.innerHeight);
  uniforms.u_resolution.value.x = renderer.domElement.width;
  uniforms.u_resolution.value.y = renderer.domElement.height;
}

function render() {
  uniforms.u_time.value = clock.getElapsedTime();
  renderer.render(scene, camera);
}

function animate() {
  render();
  requestAnimationFrame(animate);
}

init();
animate();

   
