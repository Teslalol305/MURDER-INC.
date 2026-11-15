// Stub atmosphere (CONTRACT 6.11): a night-sky colour, light haze, cool ambient, the single
// shadow-casting key light with its shadow camera fitted to the level bounds, and a tiny generated
// environment map so metal and car paint have something to reflect. No sky dome, no lamps, no train.
// Defaults come from src/config/look.js.

import * as THREE from 'three';

const LIGHT_DISTANCE = 140; // how far behind the block the key light sits

export function createAtmos(G) {
  const look = G.config.look;
  const scene = G.scene;

  scene.background = new THREE.Color(look.sky.zenith);
  scene.fog = new THREE.FogExp2(look.fog.color, look.fog.density);
  scene.add(new THREE.HemisphereLight(look.ambient.sky, look.ambient.ground, look.ambient.intensity));

  const sun = new THREE.DirectionalLight(look.sun.color, look.sun.intensity);
  sun.name = 'key';
  sun.castShadow = true;
  sun.shadow.bias = look.sun.shadowBias;
  sun.shadow.normalBias = look.sun.shadowNormalBias;
  sun.shadow.radius = look.sun.shadowRadius;
  if (G.quality.shadow > 0) sun.shadow.mapSize.set(G.quality.shadow, G.quality.shadow);
  scene.add(sun, sun.target);

  /** Aims the light at the middle of the block and wraps its shadow frustum tightly around the bounds. */
  function fitShadow(bounds) {
    const dir = new THREE.Vector3().fromArray(look.sun.direction).normalize();
    const centre = new THREE.Vector3((bounds.minX + bounds.maxX) / 2, 0, (bounds.minZ + bounds.maxZ) / 2);
    sun.target.position.copy(centre);
    sun.position.copy(centre).addScaledVector(dir, -LIGHT_DISTANCE);
    sun.updateMatrixWorld();
    sun.target.updateMatrixWorld();

    // Corners of the block's volume in the light's view space give the frustum.
    const view = new THREE.Matrix4().lookAt(sun.position, centre, sun.up).setPosition(sun.position).invert();
    const box = new THREE.Box3();
    const corner = new THREE.Vector3();
    for (const x of [bounds.minX, bounds.maxX]) {
      for (const y of [0, look.sun.shadowHeight]) {
        for (const z of [bounds.minZ, bounds.maxZ]) box.expandByPoint(corner.set(x, y, z).applyMatrix4(view));
      }
    }
    const cam = sun.shadow.camera;
    cam.left = box.min.x - 1;
    cam.right = box.max.x + 1;
    cam.bottom = box.min.y - 1;
    cam.top = box.max.y + 1;
    cam.near = Math.max(0.5, -box.max.z - 2); // the camera looks down its −Z
    cam.far = -box.min.z + 2;
    cam.updateProjectionMatrix();
  }

  /**
   * Image-based light from a throwaway scene: a sky-to-street gradient with a few bright "lamps".
   * Without an environment every metallic material renders black.
   */
  function buildEnvironment() {
    const env = new THREE.Scene();
    const dome = new THREE.SphereGeometry(40, 24, 12);
    const top = new THREE.Color(look.sky.zenith).multiplyScalar(2);
    const rim = new THREE.Color(look.sky.glow).multiplyScalar(1.6);
    const floor = new THREE.Color(look.ambient.ground).multiplyScalar(0.35);
    const colors = new Float32Array(dome.attributes.position.count * 3);
    const tint = new THREE.Color();
    for (let i = 0; i < colors.length / 3; i++) {
      const h = dome.attributes.position.getY(i) / 40; // −1 … 1
      if (h >= 0) tint.lerpColors(rim, top, Math.min(1, h * 2.5));
      else tint.lerpColors(rim, floor, Math.min(1, -h * 6));
      tint.toArray(colors, i * 3);
    }
    dome.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const sky = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide });
    env.add(new THREE.Mesh(dome, sky));

    const lamp = new THREE.MeshBasicMaterial({ color: new THREE.Color(look.palette.sodium).multiplyScalar(18) });
    const bulb = new THREE.BoxGeometry(5, 0.5, 5);
    for (const [x, y, z] of [[14, 22, 6], [-16, 20, -10], [-4, 24, 18], [20, 18, -18]]) {
      const mesh = new THREE.Mesh(bulb, lamp);
      mesh.position.set(x, y, z);
      env.add(mesh);
    }

    const pmrem = new THREE.PMREMGenerator(G.renderer);
    G.render.setEnvironment(pmrem.fromScene(env, 0.03).texture);
    pmrem.dispose();
    for (const item of [dome, bulb, sky, lamp]) item.dispose();
  }

  fitShadow((G.level && G.level.bounds) || { minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  buildEnvironment();

  return {
    sun,
    setInterior() {},
    update() {},
    // No train in the stub: it never runs.
    train: { active: false, phase: null, dir: 1, x: 0, lo: 0, hi: 0, y: 0, z: 0, speed: 0, length: 0 },
    passTrain() {},
  };
}
