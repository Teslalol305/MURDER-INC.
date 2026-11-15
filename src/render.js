// Renderer (`G.render`), CONTRACT 5.3.
//
// Two scenes, one HDR post chain:
//
//   world scene  ─┐                                   ┌─ bloom (added into the scene target)
//                 ├─ HDR half-float target (MSAA) ────┼─ grade   (exposure, vignette, hit / low-health /
//   viewmodel  ───┘  depth cleared in between         │           ADS feedback, flash, fade, grain, CA)
//                                                     └─ output  (tone mapping + sRGB, upscale to canvas)
//
// - The viewmodel scene is drawn after the world into the same target with the depth buffer cleared, so
//   the weapon never clips into walls. `vmCamera` copies the world camera's world transform every frame
//   and is itself part of `vmScene`: parent the weapon rig to `G.vmCamera` to work in view space, or
//   place it in `G.vmScene` in world space. Render owns the viewmodel lights (world-space key + ambient).
// - The internal resolution is the canvas size × quality.scale × a dynamic factor, capped by
//   quality.pixelBudget; the output pass stretches the result over the canvas.
// - If the post chain cannot be built or one of its shaders fails, rendering switches for good to a plain
//   forward path: straight to the canvas with built-in tone mapping. The game stays playable, the post
//   effects are simply gone.
//
// Rules for other modules: never create lights after boot (use `render.lights`), and write gameplay
// feedback to `render.post` (0…1 values) rather than touching the passes.

import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { Pass } from 'three/examples/jsm/postprocessing/Pass.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import * as LOOK from './config/look.js';
import * as PLAYER from './config/player.js';
import * as QUALITY from './config/quality.js';
import { clamp, paramOn } from './core/util.js';

const POOL_LIGHTS = 6;
const MAX_HELD_LIGHTS = 4; // acquire() leaves at least two lights for flashes
const COMPILE_TIMEOUT_MS = 6000;

const TONE_MAPPING = {
  aces: THREE.ACESFilmicToneMapping,
  agx: THREE.AgXToneMapping,
  reinhard: THREE.ReinhardToneMapping,
  cineon: THREE.CineonToneMapping,
  linear: THREE.LinearToneMapping,
};

const glsl = (n) => Number(n).toFixed(4);

/**
 * The grade: everything between the HDR scene and the tone mapper, in one full-screen pass.
 * Works on scene-referred linear colour; the output pass that follows tone maps and encodes it.
 */
function gradeShader(feedback) {
  return {
    name: 'GradeShader',
    uniforms: {
      tDiffuse: { value: null },
      uTime: { value: 0 },
      uExposure: { value: 1 },
      uSaturation: { value: 1 },
      uVignette: { value: 0 },
      uGrain: { value: 0 },
      uAberration: { value: 0 },
      uDamage: { value: 0 },
      uLowHealth: { value: 0 },
      uAds: { value: 0 },
      uFlash: { value: 0 },
      uFade: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D tDiffuse;
      uniform float uTime;
      uniform float uExposure;
      uniform float uSaturation;
      uniform float uVignette;
      uniform float uGrain;
      uniform float uAberration;
      uniform float uDamage;
      uniform float uLowHealth;
      uniform float uAds;
      uniform float uFlash;
      uniform float uFade;
      varying vec2 vUv;

      const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
      const vec3 HIT_TINT = vec3(${feedback.damageTint.map(glsl).join(', ')});

      float hash(vec2 p) {
        vec3 q = fract(vec3(p.xyx) * 0.1031);
        q += dot(q, q.yzx + 33.33);
        return fract((q.x + q.y) * q.z);
      }

      void main() {
        vec2 c = vUv - 0.5;
        float d = length(c) * 1.41421356;         // 0 in the middle, 1 in the corners
        float edge = smoothstep(0.3, 1.0, d);     // vignette falloff
        float rim = smoothstep(0.5, 1.08, d);     // hit / low-health red: hugs the screen border

        // Chromatic aberration: red and blue split apart toward the corners.
        vec2 split = c * d * d * uAberration * 2.0;
        vec3 col = vec3(
          texture2D(tDiffuse, vUv + split).r,
          texture2D(tDiffuse, vUv).g,
          texture2D(tDiffuse, vUv - split).b);

        col *= uExposure;

        // Saturation: drains at low health and for a moment on every hit.
        float luma = dot(col, LUMA);
        float sat = uSaturation
          * (1.0 - ${glsl(feedback.lowHealthDesaturate)} * uLowHealth)
          * (1.0 - ${glsl(feedback.damageDesaturate)} * uDamage);
        col = max(mix(vec3(luma), col, sat), 0.0);

        // Vignette: the lens, tunnel vision when hurt, focus when aiming.
        float vig = uVignette
          + ${glsl(feedback.lowHealthVignette)} * uLowHealth
          + ${glsl(feedback.adsVignette)} * uAds;
        col *= 1.0 - min(vig, 1.0) * edge;

        // Red on the screen edges: a flash on every hit, a slow pulsing rim at low health.
        float pulse = 0.75 + 0.25 * sin(${glsl(feedback.lowHealthPulse)} * uTime);
        float red = uDamage * rim * ${glsl(feedback.damageEdge)}
          + uLowHealth * rim * rim * ${glsl(feedback.lowHealthRim)} * pulse;
        col = mix(col, HIT_TINT, min(red, 1.0));

        // White-out: squared so small values only lift the frame and 1 is a full flash.
        col = mix(col, vec3(${glsl(feedback.flashWhite)}), uFlash * uFlash);
        col *= 1.0 - uFade;

        // Film grain, a touch stronger in the highlights; it also dithers the dark gradients.
        float grain = hash(gl_FragCoord.xy + fract(uTime) * vec2(371.0, 913.0)) - 0.5;
        col += grain * uGrain * (0.08 + 0.9 * dot(col, LUMA)) * (1.0 - uFade);

        gl_FragColor = vec4(max(col, 0.0), 1.0);
      }`,
  };
}

/**
 * Dynamic resolution as a small state machine (exported for tests). Feed it one timestamp per drawn
 * frame: it averages frame times over a window and moves a render scale between DR.min and 1 in
 * DR.step steps to hold the frame rate. When the smallest scale is still too slow twice in a row it
 * asks the host to drop a quality preset.
 *
 * @param {object} DR    config/quality.js `dynamicResolution`
 * @param {object} host  { changed(scale)  the scale moved,
 *                         canDrop()       may the preset be lowered right now?,
 *                         drop()          lower it }
 */
export function createGovernor(DR, host) {
  let scale = 1;
  let last = null; // timestamp of the previous sample
  let frames = 0;
  let total = 0; // ms in the current window
  let settleUntil = 0;
  let upWait = DR.upWait; // doubles every time the scale has to come down
  let upAt = 0;
  let floored = 0; // consecutive slow windows at the minimum scale

  /** Throws the current window away and measures nothing for `seconds`. */
  function settle(now, seconds) {
    frames = 0;
    total = 0;
    floored = 0;
    settleUntil = now + seconds * 1000;
  }

  function sample(now) {
    const ms = last === null ? 0 : now - last;
    last = now;
    // Hitches and hidden tabs are not slow frames.
    if (now < settleUntil || ms <= 0 || ms > DR.ignoreAbove) return;
    frames++;
    total += ms;
    if (frames < DR.windowFrames && total < DR.windowMs) return; // the window is still open

    const average = total / frames;
    frames = 0;
    total = 0;
    const atFloor = scale <= DR.min + 1e-6;
    let next = scale;

    if (average > DR.slow && !atFloor) {
      next = average > DR.slowest ? DR.min : scale - DR.step * (average > DR.slower ? 2 : 1);
      upWait = Math.min(DR.upWaitMax, upWait * 2);
      upAt = now + upWait * 1000;
    } else if (average < DR.fast && scale < 1 && now >= upAt) {
      next = scale + DR.step;
      upAt = now + DR.upWait * 1000;
    }

    floored = atFloor && average > DR.dropAbove ? floored + 1 : 0;
    if (floored >= 2) {
      floored = 0;
      if (host.canDrop()) {
        host.drop();
        next = DR.dropScale;
      }
    }

    const steps = Math.round(1 / DR.step);
    next = clamp(Math.round(next * steps) / steps, DR.min, 1); // exact tenths, no float drift
    if (next !== scale) {
      scale = next;
      settle(now, DR.settleAfterChange);
      host.changed(scale);
    }
  }

  return {
    sample,
    settle,
    /** Back to full resolution (the player picked a preset by hand). */
    reset(now) {
      scale = 1;
      upWait = DR.upWait;
      upAt = 0;
      settle(now, DR.settleAfterChange);
    },
    get scale() {
      return scale;
    },
  };
}

/**
 * The viewmodel pass: drawn over the world in the same target with a fresh depth buffer, so the weapon
 * never clips into walls. (A stock RenderPass with clearDepth clears whatever target happens to be
 * bound when it starts; this one binds its target first.)
 */
class ViewmodelPass extends RenderPass {
  render(renderer, writeBuffer, readBuffer) {
    const autoClear = renderer.autoClear;
    renderer.autoClear = false; // keep the world's colour
    renderer.setRenderTarget(this.renderToScreen ? null : readBuffer);
    renderer.clearDepth();
    renderer.render(this.scene, this.camera);
    renderer.autoClear = autoClear;
  }
}

/** A pass that only runs a callback: marks the point where scene rendering ends and post begins. */
class TapPass extends Pass {
  constructor(callback) {
    super();
    this.needsSwap = false;
    this.callback = callback;
  }

  render() {
    this.callback();
  }
}

export function createRender(G) {
  const params = G.params;
  const canvas = document.getElementById('view');
  if (!canvas) throw new Error('the page has no canvas#view');

  const shotMode = paramOn(params, 'shot');
  const stepMode = paramOn(params, 'step');
  const { presets, ladder, dynamicResolution: DR } = QUALITY;

  // ---------------------------------------------------------------------------------------------
  // Renderer, scenes, cameras
  // ---------------------------------------------------------------------------------------------

  let usePost = params.post !== '0';
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: !usePost, // with the post chain, anti-aliasing happens in the HDR target instead
      alpha: false,
      stencil: false,
      depth: true,
      powerPreference: 'high-performance',
    });
  } catch {
    throw new Error('this browser could not create a WebGL context (hardware acceleration may be off)');
  }
  const gl = renderer.getContext();
  const caps = renderer.capabilities;

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = TONE_MAPPING[LOOK.grade.toneMapping] ?? THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.setClearColor(LOOK.clearColor, 1);
  renderer.info.autoReset = false; // stats cover the whole frame, not just the last pass
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.shadowMap.autoUpdate = false; // refreshed every quality.shadowEvery frames

  const scene = new THREE.Scene();
  scene.name = 'world';
  const camera = new THREE.PerspectiveCamera(G.settings.get('fov'), 1, 0.08, 700);
  camera.rotation.order = 'YXZ';
  scene.add(camera);

  const vmScene = new THREE.Scene();
  vmScene.name = 'viewmodel';
  const vmCamera = new THREE.PerspectiveCamera(PLAYER.fov.viewmodel, 1, 0.01, 10);
  vmCamera.rotation.order = 'YXZ';
  vmScene.add(vmCamera);

  // Viewmodel lighting lives in world space so highlights slide over the weapon as the player turns.
  {
    const v = LOOK.viewmodel;
    vmScene.add(new THREE.HemisphereLight(v.ambientSky, v.ambientGround, v.ambientIntensity));
    const key = new THREE.DirectionalLight(v.keyColor, v.keyIntensity);
    key.position.fromArray(v.keyDirection).normalize().multiplyScalar(-10);
    vmScene.add(key);
  }

  // ---------------------------------------------------------------------------------------------
  // Quality
  // ---------------------------------------------------------------------------------------------

  function gpuName() {
    try {
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      return String(gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || '');
    } catch {
      return '';
    }
  }
  const gpu = gpuName();

  function detectQuality() {
    return QUALITY.autoDetect({
      userAgent: navigator.userAgent,
      touchPoints: navigator.maxTouchPoints || 0,
      screenMin: Math.min(window.screen?.width ?? Infinity, window.screen?.height ?? Infinity),
      gpu,
    });
  }

  const forcedQuality = presets[params.q] ? params.q : shotMode ? 'test' : null;
  // True while the preset was chosen for the player; only then may it be lowered automatically.
  let autoQuality = !forcedQuality && G.settings.get('quality') === 'auto';
  const initialQuality = forcedQuality ?? (autoQuality ? detectQuality() : G.settings.get('quality'));

  /** The live preset row. Its identity never changes: setQuality() copies new values into it. */
  const quality = { ...(presets[initialQuality] ?? presets[QUALITY.fallback]) };
  G.quality = quality;

  // ---------------------------------------------------------------------------------------------
  // Gameplay-facing state
  // ---------------------------------------------------------------------------------------------

  const post = { damage: 0, lowHealth: 0, ads: 0, flash: 0, fade: 0, saturation: 1 };
  const look = { ...LOOK.grade };

  // ---------------------------------------------------------------------------------------------
  // Pooled point lights
  // ---------------------------------------------------------------------------------------------

  const slots = [];
  for (let i = 0; i < POOL_LIGHTS; i++) {
    const light = new THREE.PointLight(0xffc880, 0, 10, 2);
    light.name = `pool-light-${i}`;
    scene.add(light);
    const slot = { light, ttl: 0, life: 1, peak: 0, held: false, handle: null };
    slot.handle = {
      light,
      release() {
        if (!slot.held) return;
        slot.held = false;
        light.intensity = 0;
      },
    };
    slots.push(slot);
  }

  /** Idle slot, or the flashing one closest to done. Never a held one. */
  function freeSlot() {
    let best = null;
    for (let i = 0; i < slots.length; i++) {
      const s = slots[i];
      if (s.held) continue;
      if (s.ttl <= 0) return s;
      if (!best || s.ttl < best.ttl) best = s;
    }
    return best;
  }

  const lights = {
    /** Short flash at `pos` that fades linearly to nothing over `ttl` seconds. */
    flash(pos, color = 0xffc880, intensity = 30, range = 10, ttl = 0.06) {
      const s = freeSlot();
      if (!s) return;
      s.light.position.copy(pos);
      s.light.color.set(color);
      s.light.distance = range;
      s.light.intensity = intensity;
      s.peak = intensity;
      s.life = s.ttl = Math.max(ttl, 1e-3);
    },
    /**
     * Borrows a light until release(). The caller drives position, colour, intensity and distance.
     * Returns null when four are already out (two always stay available for flashes).
     */
    acquire() {
      let held = 0;
      for (let i = 0; i < slots.length; i++) if (slots[i].held) held++;
      if (held >= MAX_HELD_LIGHTS) return null;
      const s = freeSlot();
      if (!s) return null;
      s.held = true;
      s.ttl = 0;
      s.light.intensity = 0;
      return s.handle;
    },
  };

  function updateLights(dt) {
    for (let i = 0; i < slots.length; i++) {
      const s = slots[i];
      if (s.held || s.ttl <= 0) continue;
      s.ttl -= dt;
      s.light.intensity = s.ttl > 0 ? (s.peak * s.ttl) / s.life : 0;
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Post chain
  // ---------------------------------------------------------------------------------------------

  let composer = null;
  let sceneTarget = null; // HDR + MSAA + depth: both scenes render here
  let gradeTarget = null; // HDR, no depth: the grade writes here
  let bloomPass = null;
  let gradePass = null;
  let phase = 'idle'; // 'scene' | 'post' while a frame is being drawn: tells shader errors apart
  let postBroken = false;
  let sceneCalls = 0;
  let sceneTriangles = 0;

  // Size state. `css*` is the canvas in CSS pixels, `inner*` the internal render resolution.
  let cssW = 1;
  let cssH = 1;
  let dpr = 1;
  let innerW = 1;
  let innerH = 1;
  let sizeDirty = true;

  const msaaSamples = () => Math.min(quality.msaa | 0, caps.maxSamples | 0);

  renderer.debug.onShaderError = (ctx, program, vs, fs) => {
    const log = [ctx.getProgramInfoLog(program), ctx.getShaderInfoLog(vs), ctx.getShaderInfoLog(fs)]
      .filter(Boolean)
      .join(' | ')
      .slice(0, 300);
    if (phase === 'post') {
      postBroken = true;
      console.warn(`[render] a post shader failed to compile: ${log}`);
    } else {
      console.error(`[render] a material shader failed to compile: ${log}`);
    }
  };

  function buildPost() {
    const hdr = caps.isWebGL2 && (renderer.extensions.has('EXT_color_buffer_float') || renderer.extensions.has('EXT_color_buffer_half_float'));
    if (!hdr) throw new Error('float render targets are not supported');

    sceneTarget = new THREE.WebGLRenderTarget(1, 1, {
      type: THREE.HalfFloatType,
      samples: msaaSamples(),
      depthBuffer: true,
      stencilBuffer: false,
    });
    sceneTarget.texture.name = 'scene.hdr';
    gradeTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false, stencilBuffer: false });
    gradeTarget.texture.name = 'grade.hdr';

    // EffectComposer clones its target for the second buffer; only the buffer the scenes render into
    // needs MSAA and depth, so swap the clone for the scene target (see bindBuffers()).
    composer = new EffectComposer(renderer, gradeTarget);
    composer.renderTarget2.dispose();
    composer.renderTarget2 = sceneTarget;
    composer.setPixelRatio(1); // sizes are given in internal pixels
    bindBuffers();

    const worldPass = new RenderPass(scene, camera);
    const vmPass = new ViewmodelPass(vmScene, vmCamera);
    const tap = new TapPass(() => {
      sceneCalls = renderer.info.render.calls;
      sceneTriangles = renderer.info.render.triangles;
      phase = 'post';
    });
    bloomPass = new UnrealBloomPass(new THREE.Vector2(256, 256), look.bloomStrength, look.bloomRadius, look.bloomThreshold);
    gradePass = new ShaderPass(gradeShader(LOOK.feedback));

    composer.addPass(worldPass);
    composer.addPass(vmPass);
    composer.addPass(tap);
    composer.addPass(bloomPass);
    composer.addPass(gradePass);
    composer.addPass(new OutputPass());
  }

  /** Scenes always render into the MSAA target and the grade into the lean one, whatever swapped last frame. */
  function bindBuffers() {
    composer.readBuffer = sceneTarget;
    composer.writeBuffer = gradeTarget;
  }

  function disposePost() {
    if (composer) {
      for (const pass of composer.passes) pass.dispose();
      composer.dispose(); // also frees both render targets
    } else {
      sceneTarget?.dispose();
      gradeTarget?.dispose();
    }
    composer = sceneTarget = gradeTarget = bloomPass = gradePass = null;
  }

  function switchToForward(reason) {
    if (!usePost) return;
    usePost = false;
    disposePost();
    sizeDirty = true;
    console.warn(`[render] post chain unavailable (${reason}): using the plain forward path`);
  }

  function drawPost(dt) {
    const g = gradePass.uniforms;
    g.uTime.value = G.time.t % 600;
    g.uExposure.value = api.exposure * look.exposure;
    g.uSaturation.value = post.saturation * look.saturation;
    g.uVignette.value = look.vignette;
    g.uGrain.value = look.grain;
    g.uAberration.value = look.aberration;
    g.uDamage.value = clamp(post.damage, 0, 1);
    g.uLowHealth.value = clamp(post.lowHealth, 0, 1);
    g.uAds.value = clamp(post.ads, 0, 1);
    g.uFlash.value = clamp(post.flash, 0, 1);
    g.uFade.value = clamp(post.fade, 0, 1);

    bloomPass.enabled = quality.bloom && params.bloom !== '0' && look.bloomStrength > 0;
    bloomPass.strength = look.bloomStrength;
    bloomPass.radius = look.bloomRadius;
    bloomPass.threshold = look.bloomThreshold;
    bloomPass.highPassUniforms.smoothWidth.value = look.bloomKnee;

    renderer.toneMappingExposure = 1; // exposure is applied in the grade, before the tone mapper
    bindBuffers();
    phase = 'scene';
    composer.render(dt);
    phase = 'idle';
  }

  /** No post: both scenes straight to the canvas with built-in tone mapping. Fade rides on the exposure. */
  function drawForward() {
    renderer.toneMappingExposure = api.exposure * look.exposure * (1 - clamp(post.fade, 0, 1)) * (1 + 3 * clamp(post.flash, 0, 1));
    renderer.setRenderTarget(null);
    renderer.render(scene, camera); // clears first (autoClear)
    sceneCalls = renderer.info.render.calls;
    sceneTriangles = renderer.info.render.triangles;
    renderer.autoClear = false; // the viewmodel goes on top: fresh depth, same colour
    renderer.clearDepth();
    renderer.render(vmScene, vmCamera);
    renderer.autoClear = true;
  }

  // ---------------------------------------------------------------------------------------------
  // Size and dynamic resolution
  // ---------------------------------------------------------------------------------------------

  const dynamic = !shotMode && !stepMode && params.dynres !== '0';
  const governor = createGovernor(DR, {
    changed() {
      sizeDirty = true;
    },
    // Only a preset that was chosen for the player may be lowered behind their back.
    canDrop: () => autoQuality && ladder.indexOf(quality.name) > 0,
    drop() {
      setQuality(ladder[ladder.indexOf(quality.name) - 1]);
      G.events.emit('quality:auto', { name: quality.name });
    },
  });
  governor.settle(performance.now(), DR.settle);

  function applySize() {
    sizeDirty = false;
    cssW = Math.max(1, canvas.clientWidth || window.innerWidth || 1);
    cssH = Math.max(1, canvas.clientHeight || window.innerHeight || 1);
    dpr = Math.min(window.devicePixelRatio || 1, quality.maxDpr);

    const scale = quality.scale * (usePost ? governor.scale : 1);
    let w = cssW * dpr * scale;
    let h = cssH * dpr * scale;
    const budget = quality.pixelBudget / (w * h);
    if (budget < 1) {
      w *= Math.sqrt(budget);
      h *= Math.sqrt(budget);
    }
    innerW = Math.max(1, Math.round(w));
    innerH = Math.max(1, Math.round(h));

    if (usePost) {
      renderer.setPixelRatio(dpr);
      renderer.setSize(cssW, cssH, false);
      composer.setSize(innerW, innerH);
    } else {
      // The canvas itself carries the internal resolution; CSS stretches it.
      renderer.setPixelRatio(innerW / cssW);
      renderer.setSize(cssW, cssH, false);
    }
    camera.aspect = vmCamera.aspect = cssW / cssH;
  }

  // ---------------------------------------------------------------------------------------------
  // Shadows and quality switching
  // ---------------------------------------------------------------------------------------------

  /** Pushes quality.shadow to the renderer and to every shadow-casting light in the world scene. */
  function applyShadows() {
    const size = Math.min(quality.shadow | 0, caps.maxTextureSize);
    const enabled = size > 0;
    const toggled = renderer.shadowMap.enabled !== enabled;
    renderer.shadowMap.enabled = enabled;
    scene.traverse((obj) => {
      if (obj.isLight && obj.castShadow && obj.shadow && enabled && obj.shadow.mapSize.x !== size) {
        obj.shadow.mapSize.set(size, size);
        if (obj.shadow.map) {
          obj.shadow.map.dispose();
          obj.shadow.map = null; // reallocated at the new size on the next shadow pass
        }
      }
      // Turning shadows on or off changes shader defines: every material has to rebuild its program.
      if (toggled && obj.material) {
        for (const m of Array.isArray(obj.material) ? obj.material : [obj.material]) m.needsUpdate = true;
      }
    });
    renderer.shadowMap.needsUpdate = true;
  }

  function setQuality(nameOrRow) {
    const row = typeof nameOrRow === 'string' ? presets[nameOrRow] ?? presets[QUALITY.fallback] : nameOrRow;
    if (!row) return;
    Object.assign(quality, row);
    if (sceneTarget && sceneTarget.samples !== msaaSamples()) {
      sceneTarget.samples = msaaSamples();
      sceneTarget.dispose(); // GL storage is rebuilt with the new sample count on next use
    }
    applyShadows();
    governor.settle(performance.now(), DR.settleAfterChange);
    sizeDirty = true;
  }

  G.events.on('settings:change', ({ key, value }) => {
    if (key !== 'quality' || forcedQuality) return;
    autoQuality = value === 'auto';
    governor.reset(performance.now());
    setQuality(autoQuality ? detectQuality() : value);
  });

  // ---------------------------------------------------------------------------------------------
  // Frame
  // ---------------------------------------------------------------------------------------------

  let frameNo = 0;
  let contextLost = false;
  let lastDpr = window.devicePixelRatio || 1;

  /**
   * Draws one frame. `draw = false` only advances time-based state (light fades): the test harness
   * uses it to fast-forward the simulation without paying for rendering.
   */
  function frame(dt, draw = true) {
    updateLights(dt);
    if (!draw || contextLost) return;

    if (dynamic && usePost) governor.sample(performance.now());
    const ratio = window.devicePixelRatio || 1;
    if (ratio !== lastDpr) {
      lastDpr = ratio;
      sizeDirty = true;
    }
    if (sizeDirty) applySize();

    // Modules set fov / aspect freely; keep both projections and the viewmodel camera in step.
    camera.updateProjectionMatrix();
    vmCamera.updateProjectionMatrix();
    camera.updateWorldMatrix(true, false);
    camera.matrixWorld.decompose(vmCamera.position, vmCamera.quaternion, vmCamera.scale);

    if (renderer.shadowMap.enabled && frameNo % (shotMode ? 1 : Math.max(1, quality.shadowEvery | 0)) === 0) {
      renderer.shadowMap.needsUpdate = true;
    }
    frameNo++;
    renderer.info.reset();

    if (usePost) {
      try {
        drawPost(dt);
      } catch (err) {
        phase = 'idle';
        switchToForward(err && err.message ? err.message : String(err));
      }
      if (postBroken) switchToForward('shader error');
      if (usePost) return;
      applySize();
      renderer.info.reset();
    }
    drawForward();
  }

  function resize() {
    applySize();
  }

  function setEnvironment(texture) {
    scene.environment = texture || null;
    vmScene.environment = texture || null;
  }

  function stats() {
    const info = renderer.info;
    return {
      calls: sceneCalls, // world + shadow + viewmodel draw calls of the last frame
      triangles: sceneTriangles,
      frameCalls: info.render.calls, // including the post passes
      geometries: info.memory.geometries,
      textures: info.memory.textures,
      programs: info.programs ? info.programs.length : 0,
      width: innerW,
      height: innerH,
      canvasWidth: canvas.width,
      canvasHeight: canvas.height,
      scale: governor.scale,
      quality: quality.name,
      post: usePost,
      msaa: usePost ? msaaSamples() : 0,
      shadow: renderer.shadowMap.enabled ? Math.min(quality.shadow | 0, caps.maxTextureSize) : 0,
      gpu,
    };
  }

  /**
   * Called once by boot when the world is complete: sizes the shadow maps, compiles every material
   * for both scenes and draws a first frame (shadow pass included) behind the boot screen.
   */
  async function onLevelReady() {
    applyShadows();
    if (sizeDirty) applySize();
    try {
      // Programs differ between the HDR target and the canvas: compile for where the frame will go.
      renderer.setRenderTarget(usePost ? sceneTarget : null);
      const pending = Promise.all([renderer.compileAsync(scene, camera), renderer.compileAsync(vmScene, vmCamera)]);
      renderer.setRenderTarget(null);
      // A material that never reports ready must not hold the boot screen forever.
      await Promise.race([pending, new Promise((resolve) => setTimeout(resolve, COMPILE_TIMEOUT_MS))]);
    } catch (err) {
      renderer.setRenderTarget(null);
      console.warn('[render] shader pre-compile failed:', err);
    }
    try {
      frame(0);
    } catch (err) {
      console.error('[render] first frame failed:', err); // the loop will report it again, once
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Start-up
  // ---------------------------------------------------------------------------------------------

  const api = {
    renderer,
    scene,
    camera,
    vmScene,
    vmCamera,
    post,
    look,
    exposure: 1,
    lights,
    quality,
    setQuality,
    setEnvironment,
    frame,
    resize,
    stats,
    onLevelReady,
  };

  if (usePost) {
    try {
      buildPost();
    } catch (err) {
      switchToForward(err.message);
    }
  }
  applySize();

  // Self-test: push one empty frame through the whole chain so a broken pass shows up now, not mid-game.
  if (usePost) {
    try {
      for (let i = 0; i < 8 && gl.getError() !== gl.NO_ERROR; i++); // drain errors that are not ours
      phase = 'post';
      bindBuffers();
      composer.render(0);
      phase = 'idle';
      const error = gl.getError();
      if (postBroken) switchToForward('shader error');
      else if (error !== gl.NO_ERROR) switchToForward(`GL error 0x${error.toString(16)}`);
    } catch (err) {
      phase = 'idle';
      switchToForward(err.message);
    }
    if (!usePost) applySize();
  }

  const markSizeDirty = () => {
    sizeDirty = true;
  };
  window.addEventListener('resize', markSizeDirty);
  window.addEventListener('orientationchange', markSizeDirty);
  if (typeof ResizeObserver === 'function') new ResizeObserver(markSizeDirty).observe(canvas);

  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault(); // allows the context to come back
    contextLost = true;
  });
  canvas.addEventListener('webglcontextrestored', () => {
    contextLost = false;
    sizeDirty = true;
    renderer.shadowMap.needsUpdate = true;
  });

  G.renderer = renderer;
  G.scene = scene;
  G.camera = camera;
  G.vmScene = vmScene;
  G.vmCamera = vmCamera;

  return api;
}
