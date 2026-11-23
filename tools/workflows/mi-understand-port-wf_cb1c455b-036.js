export const meta = {
  name: 'mi-understand-port',
  description: 'Read the Murder Inc. web game: write Unreal port specs, export tuning and level data, verify Unreal facts, draft the art bible',
  phases: [
    { title: 'Understand', detail: 'readers write per-subsystem port specs' },
    { title: 'Export', detail: 'dump tuning + level layout to JSON, capture reference shots' },
    { title: 'Scout', detail: 'verify Unreal Engine facts against Epic documentation' },
    { title: 'Art bible', detail: 'define the photoreal target look' },
    { title: 'Critique', detail: 'cross-check specs against source and exported data' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'

const COMMON = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter (three.js r160, everything procedural, about 53k lines in src/) that belongs to the user. It is being REBUILT in Unreal Engine 5 with photoreal, current-generation graphics; the art is authored in Blender. The web game stays as it is and is the ground truth for gameplay, tuning, level layout, copy and audio.',
  'Read first: docs/DESIGN.md (what the game is; section 8 "Direction v2" wins over sections 1, 2, 5, 6 where they differ: daylight is the default look), then the parts of docs/CONTRACT.md named in your task, and docs/DEV.md if you need to build or run anything.',
  'This container has no Unreal Editor (nothing Unreal can be compiled or run here) and no GPU. Blender 5.3 is available headless as a Python module: ' + PY + ' (import bpy). Node 22 and a pre-installed Playwright/Chromium are available (require("playwright") works from any directory; never run "playwright install").',
  'Rules: do not modify anything under src/, dist/, test/, or the existing files in tools/ and docs/. Write only the files assigned to you (new files and directories are fine where your task says so). Do not commit, push or create branches. Other agents work in parallel on other files in the same checkout. The machine has 4 shared CPU cores and 15 GB RAM: no long CPU-heavy jobs unless your task needs them.',
].join('\n')

const CONV = [
  'SHARED CONVENTIONS (fixed; other agents rely on them)',
  '- Coordinates. Web game (three.js): metres, +Y up, north = -Z, east = +X. Blender: metres, Z up, east = +X, north = +Y, so Blender(x, y, z) = (x_web, -z_web, y_web). Unreal: centimetres, Z up, X = east, Y = south, so Unreal(X, Y, Z) = (x_web, z_web, y_web) * 100 = (x_blender, -y_blender, z_blender) * 100. Swapping two axes converts the right-handed web space into Unreal left-handed space without mirroring. Give orientations as direction vectors or as an explicit Unreal yaw in degrees (yaw 0 faces +X/east, +90 faces +Y/south).',
  '- Forward axes. Props, vehicles and weapons: forward = +X (Blender and Unreal). Characters: face -Y in Blender (the Unreal mannequin convention, +Y in Unreal mesh space). Prop pivots: centre of the footprint on the ground. Wall/facade modules: pivot at the bottom-left corner of the outer face, running along +X, outer face looking toward -Y in Blender.',
  '- Names. Static meshes SM_<Family>_<Name>[_<Variant>], skeletal meshes SK_<Name>. Tiling texture sets TS_<Surface>_<Variant> (material slot name MI_<Surface>_<Variant>); unique sets are named after their asset (slot name M_<Asset>). Textures T_<Set>_BC (sRGB base colour), T_<Set>_N (tangent-space normal, OpenGL convention as Blender bakes it), T_<Set>_ORM (R = ambient occlusion, G = roughness, B = metallic, linear), optional T_<Set>_H (height) and T_<Set>_E (emissive).',
  '- Unreal project lives in unreal/MurderInc/ (project name MurderInc). Runtime data files exported from the web game live in unreal/MurderInc/Content/Data/*.json. Blender pipeline lives in art/blender/, generated art in art/out/ (git-ignored), preview renders in art/previews/. Port documentation lives in docs/unreal/.',
].join('\n')

const SPEC_RULES = [
  'HOW TO WRITE THE SPEC',
  '- Audience: engineers and artists who will rebuild this in Unreal Engine 5 and Blender WITHOUT reading the JavaScript. Be complete and exact: every constant with its value and unit, cited as path:line. Prefer tables. Give formulas as pseudo-code and state machines as explicit states, transitions and timers.',
  '- Read the listed source files completely; they are the ground truth. Where config values are overridden in code, report the effective value. Where docs/DESIGN.md and the code disagree, the code wins: note the difference. Never invent a value: if you cannot find something, say so under "Open questions".',
  '- Sections, in this order: 1 Overview (what this subsystem does for the player, in a paragraph); 2 Facts (tables of constants); 3 Behaviour (state machines, formulas, timing, edge cases, the order things happen in a frame where it matters); 4 Unreal mapping (unit-converted values in cm, cm/s and degrees, and the natural Unreal Engine 5 feature for each mechanic; describe, do not write code); 5 Art and audio implications (what must be modelled, textured, animated, simulated or recorded, with real dimensions); 6 Open questions and risks.',
  '- Do not paste large code blocks. Length: as long as completeness needs (typically 300 to 900 lines).',
].join('\n')

const ASSET_RULES = [
  'ASSET BRIEFS. Besides the spec, write the JSON file named in your task: an array of briefs, one per distinct thing that must be modelled in Blender, with this exact shape:',
  '{ "id": "snake_case_unique", "name": "SM_<Family>_<Name>", "family": "architecture|el|street|vehicle|prop|gameplay|weapon|character|sign|fx", "size_m": [width_x, depth_y, height_z] or null, "count": instances in the level (number or null), "description": "what it is and every part a modeller must build, with proportions", "materials": ["surface names"], "colours": ["#rrggbb with what it applies to"], "gameplay": "cover height / explosive / objective / none", "source": "path:line", "priority": 1 (the player sees it up close or it defines the block), 2 or 3 }',
  'Dimensions come from the code (bounding boxes, builder parameters), converted to metres in Blender axes. Describe the real-world object that the low-poly original stands for; the rebuild models the real thing.',
].join('\n')

const RETURN_RULES = 'When done, reply through the structured output: file (the spec path you wrote), summary (at most 120 words: what the spec covers and the three facts an implementer most needs), extra_files (other files you wrote), open_questions (at most 8, each one sentence).'

const SPEC_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    summary: { type: 'string' },
    extra_files: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['file', 'summary'],
}

const READERS = [
  {
    id: 'player', out: 'docs/unreal/spec/01-player.md', title: 'the player: movement, camera, input, health',
    files: 'src/player.js, src/input.js, src/physics.js (capsule movement, stepping, gravity, friction, raycasts, nav grid), src/config/player.js, src/core/settings.js, src/stubs/player.js and src/stubs/input.js (smallest correct API)',
    contract: '5.1 G.physics, 6.3 G.input, 6.4 G.player, 10 Foundation notes',
    focus: 'Movement (walk, sprint, crouch, jump, air control: speeds, accelerations, friction, gravity, step height, capsule size, slopes), stances and eye heights, camera (field of view, aim-down-sights zoom and timing, head bob, sway, landing dip, recoil kick application and recovery, screen shake), health, damage intake, regeneration per difficulty, death; the complete action list with default keyboard/mouse and gamepad bindings, look sensitivity model, dead zones and response curves, aim assist or friction if any, mouse-capture fallbacks; touch controls only as a short summary. Collision model used by physics (boxes, capsule) and what the player can and cannot climb.',
  },
  {
    id: 'weapons', out: 'docs/unreal/spec/02-weapons-combat.md', title: 'weapons, hit resolution, melee and explosives', assets: 'docs/unreal/spec/assets/weapons.json',
    files: 'src/weapon.js, every file in src/weapon/ (logic.js, handling.js, springs.js, build.js, chopper.js, nine.js, arms.js, viewmodel.js, material.js), src/combat.js, src/explosives.js, src/config/weapons.js, src/stubs/weapon.js, src/stubs/explosives.js',
    contract: '5.2 G.combat, 6.5 G.weapon, 6.7 G.explosives',
    focus: 'Per weapon (CHOPPER carbine, NINE pistol, melee): damage and falloff, rate of fire, magazine and reserve rules, reload stages and timings (tactical vs empty), draw/holster/swap times, spread model (base, movement, bloom per shot, recovery, aim-down-sights), recoil pattern and how it reaches the camera, fire modes, input buffering, the full weapon state machine. Hit resolution: hitscan rules, ranges, what stops a round, head multiplier, damage events, tracers (which shots, speed, colour), impact events. Melee timing/reach/cone. Explosives: propane tank and welding rack health, fuse, radius, damage falloff, chain rules, restoration in Hold the Block. Viewmodel: describe the CHOPPER, the NINE and the arms (gloves, watch, bracelet) part by part with dimensions as a modelling brief, sight alignment when aiming, and every procedural animation (sway, bob, fire kick, reload motions, inspect) with timings so it can be re-authored as real animation.',
  },
  {
    id: 'enemies', out: 'docs/unreal/spec/03-enemies.md', title: 'enemies: the Goon and the Buzzard', assets: 'docs/unreal/spec/assets/characters.json',
    files: 'src/enemies.js, every file in src/enemies/ (logic.js, goon.js, goon-anim.js, goon-model.js, rig.js, buzzard.js, buzzard-model.js, bolts.js, glow.js), src/config/enemies.js, src/stubs/enemies.js',
    contract: '6.6 G.enemies',
    focus: 'Per enemy and per difficulty (Hustler, Boss, Kingpin): health, damage, timings, spreads. The complete AI: perception (sight, hearing, alert propagation), the exposure/accuracy model, attack tokens, state machines (idle/patrol, alerted, move to fire position, cover use and crouching between bursts, burst fire, rush with the pipe, flinch, death), navigation (nav grid use, speeds, turning, avoidance), the Buzzard flight model (hover heights, strafing, telegraph, bolt speed and dodging, spin-down death and burst), spawn-in behaviour, pooling and caps, body persistence. Model briefs: the Goon (proportions, clothing variants, mask, crew colours, the SMG and the pipe) and the Buzzard (size, arms, rotors, eye light, slung gun) with dimensions. The full list of Goon animations/poses with durations (from goon-anim.js) so they can be authored or retargeted.',
  },
  {
    id: 'flow', out: 'docs/unreal/spec/04-flow.md', title: 'game flow, modes, waves, scoring and all copy',
    files: 'src/game.js, every file in src/game/, src/config/flow.js, src/config/text.js, src/config/quality.js, src/core/events.js, src/core/settings.js, src/main.js (boot order and main loop only), src/stubs/game.js',
    contract: '3 Boot and main loop, 4 The shared object G (all of it, especially 4.2 Events), 6.13 G.game, 7 Config files',
    focus: 'The state machine (title, intro, playing, paused, dead, complete) with every transition and timer. Story mode: reels, hold-to-grab, reinforcement waves per reel and difficulty, the reinforcement pump, pursuit after the third reel, extraction. Hold the Block: wave formulas, resupply, score, best score persistence. Spawn-point scoring and selection. Difficulty tiers. Run statistics and the rating ladder with thresholds. Radio lines with triggers and hold times, banners, objective lines, kill feed, every card. The music-intensity driver. The complete event list with payloads (name, when emitted, by whom). Every user-facing string, verbatim, in one table. User settings and their ranges/defaults.',
  },
  {
    id: 'level', out: 'docs/unreal/spec/05-level.md', title: 'the block: layout, architecture, the El, yards', assets: 'docs/unreal/spec/assets/level.json',
    files: 'src/level.js and every file in src/level/ (data.js, layout.js, buildings.js, el.js, street.js, yards.js, shop.js, ground.js, fences.js, kit.js), src/stubs/level.js',
    contract: '6.10 G.level, 10 Foundation notes, 11 Direction v2',
    focus: 'The exact layout in web coordinates AND Blender coordinates: play bounds, zones, every building (footprint, height, storeys, facade style, storefronts with their invented names, awnings, signs, fire escapes, roof items), the chop shop interior (walls, doors, lifts, mezzanine, stairs, skylights, work lights), the El (column rows and spacing, column and girder sections, deck height, ties, rails, station stairs, lamps), the avenue (lanes, kerbs, sidewalks, markings, manholes, hydrant, the roadblock), the alley, vacant lot, rear service lane, The Cage court, parking lot, perimeter sealing, ground surfaces per area. How collision is authored (boxes), spawn points (ground and air, per zone), cover points, objectives (reel positions), extraction zone, explosive placements, the start pose. Write it so a level builder can reconstruct the block, and so an artist knows every architectural module that is needed (module list with dimensions).',
  },
  {
    id: 'props', out: 'docs/unreal/spec/05b-props.md', title: 'props and vehicles', assets: 'docs/unreal/spec/assets/props.json',
    files: 'src/props.js and every file in src/props/ (kit.js, vehicles.js, street.js, clutter.js, gameplay.js, lot.js, shop.js, atlas.js, materials.js), src/config/catalog.js, src/stubs/props.js',
    contract: '6.2 G.props',
    focus: 'Every prop type in the catalogue: id, bounding dimensions, parts, colours/liveries, collision and cover height, variants, how many are placed and where (roughly). Vehicles in detail: sedan(s), yellow cab, SUV (and the player black SUV), panel van, Vulture van with open doors, box truck, the jack-knifed truck, the burned-out car, the raised and stripped cars in the shop, and the IPX armoured vault truck (livery, wordmark placement). Gameplay props: master reel case with tracker tag and boombox, propane tank, welding rack, resupply items. Street furniture, clutter, lot and shop props. For each, describe the real object to model (no real brands; liveries and plates are invented in the source: report them).',
  },
  {
    id: 'look', out: 'docs/unreal/spec/06-look-fx.md', title: 'surfaces, signage, lighting, atmosphere, post and effects', assets: 'docs/unreal/spec/assets/signs-fx.json',
    files: 'src/mats.js and every file in src/mats/, src/atmos.js and every file in src/atmos/, src/fx.js and every file in src/fx/, src/render.js, src/config/look.js, src/config/brand.js, src/stubs/mats.js, src/stubs/atmos.js, src/stubs/fx.js',
    contract: '5.3 G.render, 6.1 G.mats, 6.8 G.fx, 6.11 G.atmos, 11 Direction v2',
    focus: 'Surfaces: every generated material (what real surface it depicts, colours, real-world scale). Signage, posters, decals, graffiti, the mural, the billboard, licence plates: every text string verbatim with palette, size and where it goes; the brand tokens and the IPX wordmark construction. Lighting: the DAY rig (sun direction as a vector and as azimuth/elevation, colours, intensities, sky, ambient, fog/haze, exposure, tone mapping, bloom) and the NIGHT rig (same, plus lamp field, neon, window lights), translated into physical terms where possible. The far city/skyline, sky and clouds. Street life (birds, steam, traffic, anything animated), the El train (schedule, speed, length, light and sound cues, grit). Effects: every recipe (muzzle flash, tracers, shell casings, impacts per surface, blood-free hit puffs, explosions, fire jet, sparks, steam, dust, decals) with sizes, colours, lifetimes and counts, as briefs for Niagara. The post chain and quality presets.',
  },
  {
    id: 'ui-audio', out: 'docs/unreal/spec/07-ui-audio.md', title: 'HUD, menus and audio',
    files: 'src/hud.js, src/menus.js, every file in src/ui/, src/ui.css and src/base.css (layout, sizes, colours, type only), src/audio.js and every file in src/audio/, src/page.html, src/stubs/hud.js, src/stubs/menus.js, src/stubs/audio.js',
    contract: '6.9 G.audio, 6.12 G.hud and G.menus, 8 Page, CSS, branding, 11.3 HUD data for the minimap',
    focus: 'HUD: every element with position, size, colours, type, behaviour and timing (mission badge, minimap including how it is drawn and rotated, weapon bar, health bar, crosshair and spread gap, hit markers, damage arcs, interaction ring, kill feed, banners, radio subtitles, objective markers in the world). Menus and cards: title, intro, pause, death, debrief, settings and controls panels, navigation by keyboard/gamepad. Brand tokens in use. Audio: the complete list of sounds (name, what it is, trigger, 2D or 3D, loop or one-shot, variations, volume/pitch rules, attenuation), ambience beds, the music system (stems, tempo, key, intensity mapping, stings), reverb/space switching (street vs shop), ducking, the event-to-sound table. Then answer concretely: can every sound and every music stem be rendered offline to WAV files with the existing code (for example OfflineAudioContext in headless Chromium)? Which functions produce the buffers, what would a render script look like, and what would be lost?',
  },
]

function readerPrompt(r) {
  return [
    COMMON,
    '',
    'YOUR TASK: write the port spec ' + r.out + ' for ' + r.title + '.',
    'Source files to read completely: ' + r.files + '.',
    'docs/CONTRACT.md sections to read: ' + r.contract + '.',
    '',
    'WHAT THE SPEC MUST COVER',
    r.focus,
    '',
    SPEC_RULES,
    '',
    r.assets ? ASSET_RULES + '\nYour asset-brief file: ' + r.assets : '',
    '',
    CONV,
    '',
    RETURN_RULES,
  ].join('\n')
}

const EXPORT_PROMPT = [
  COMMON,
  '',
  'YOUR TASK: export the web game\'s real data for the Unreal rebuild, and capture reference pictures of the current game.',
  '',
  '1. Exporter. Create tools/ue-export/ (new directory) with a script that produces JSON files in unreal/MurderInc/Content/Data/. Use the real running game as the source so nothing is transcribed by hand: load a build in headless Chromium through the existing harness (tools/shot.cjs with a scenario file, see docs/DEV.md) or Playwright directly, wait until it is ready, and serialise from window.__G. dist/index.html is a committed production build; if you need a dev build run "npm install" then "node build.mjs --dev --out=dist/dev-export.html" (dist/dev-* is git-ignored). A full-build page needs about 3 GB of memory in software GL: run one at a time and close it when done.',
  '   Files to write (pretty-printed, stable key order, numbers rounded to 4 decimals, deterministic for seed 1994):',
  '   - config.json: every tuning table from G.config (player, weapons, enemies per difficulty, flow, explosives, quality presets, catalog), exactly as the game uses it.',
  '   - text.json: every user-facing string table.',
  '   - level.json: play bounds, zones, every static collider box (with what it belongs to when known), interior boxes, spawn points (ground/air, zone, facing), cover points, reel positions, extraction zone, start pose, explosive placements, El column positions and deck data, train path/schedule parameters, nav grid parameters. Each position in web metres {x,y,z} and Unreal centimetres {X,Y,Z}; each facing as a web direction vector and an Unreal yaw in degrees.',
  '   - props.json: every placed prop instance (catalogue id, variant, position, rotation, scale, zone) in both spaces, and the catalogue itself (dimensions per type).',
  '   - atmos.json: the day and night lighting rigs as numbers (sun/moon direction, colours, intensities, ambient, fog, exposure, bloom), sky parameters, lamp positions, neon/sign light positions and colours, window-light data where available.',
  '   If something listed is not reachable from window.__G, read how the module builds it and extract it from there (say which path you took); if it truly does not exist, omit it and say so.',
  '2. Self-check. tools/ue-export/verify.cjs: re-reads the JSON and checks it against the source of truth without the browser where possible (import the plain-data files in src/config/), checks the coordinate conversion on at least 5 landmarks (start pose, the three reels, the IPX truck: DESIGN.md gives approximate web coordinates), checks counts (spawn points, cover points, explosives) against what DESIGN.md requires, and exits non-zero on any mismatch. Run it and make it pass.',
  '3. Reference pictures of the CURRENT game, for before/after comparison and for the artists: 1280x720 PNGs in docs/unreal/reference/ (new directory): the title screen, the HUD in play at the start pose, five or six fixed-camera views by day (the avenue under the El from eye level looking east, the chop shop interior, the alley, the vacant lot with the mural, The Cage, the parking lot with the IPX truck), two of the same views by night, one close view of a Goon and one of a Buzzard, the CHOPPER and NINE viewmodels, and a top-down plan of the whole block (orthographic-looking, high camera). Use the cam / __setShot helpers in docs/DEV.md. Keep the whole directory under 12 MB.',
  '4. Document it in docs/unreal/spec/08-data-export.md: how to re-run, the schema of every file (field by field), the coordinate conversion with a worked example, what could not be exported.',
  '',
  CONV,
  '',
  'When done, reply through the structured output: file = docs/unreal/spec/08-data-export.md, summary (at most 120 words, include the counts you exported: colliders, props, spawn points, cover points, explosives), extra_files, open_questions.',
].join('\n')

const SCOUT_PROMPT = [
  COMMON,
  '',
  'YOUR TASK: establish the Unreal Engine facts the port depends on, from Epic\'s own documentation, and write docs/unreal/spec/00-unreal-scout.md. Nobody on this project can compile Unreal code here, so C++ and editor-Python will be written blind and compiled later: every API fact you verify now prevents a compile error later. Your own knowledge of Unreal may be out of date; prefer what the documentation says and mark each fact VERIFIED (with URL) or FROM MEMORY.',
  'Reachable hosts: dev.epicgames.com, www.unrealengine.com, forums.unrealengine.com (also docs.blender.org, en.wikipedia.org, PyPI, npm). Everything else is blocked by the network proxy; do not try to route around it and never disable TLS verification (read /root/.ccr/README.md if a tool has certificate or proxy trouble). The documentation site may need JavaScript: if curl returns only a shell, render pages with the pre-installed Playwright Chromium (pass the HTTPS proxy from the environment to the browser).',
  'Find out and record:',
  '1. The current Unreal Engine release (version number, date) and which version the project should target; whether the "ModelContextProtocol" and "AllToolsets" editor plugins (an MCP server inside the editor, console command ModelContextProtocol.StartServer, default http://127.0.0.1:8000/mcp) exist in it and from which version; how a .uproject marks a plugin reference as optional.',
  '2. Project settings (ini sections and keys) for a current-generation look: Lumen global illumination and reflections, hardware ray tracing, Nanite, virtual shadow maps, default RHI, mesh distance fields, auto exposure, anti-aliasing/TSR, virtual textures, Substrate materials (state and whether to enable), volumetric fog/clouds, sky atmosphere.',
  '3. Scripted content creation with the editor Python API (module "unreal"): importing glTF/GLB and FBX with Interchange or AssetImportTask (class and function names, how to set Nanite on imported meshes, how normal-map green-channel flipping is controlled), importing textures with the right sRGB/compression settings, creating materials and material instances (MaterialEditingLibrary), creating a level and spawning/placing actors (subsystems and function names), setting static-mesh collision, building navigation, saving assets; how to run a Python script headless from the command line (UnrealEditor-Cmd ... -run=pythonscript ...), including on Linux.',
  '4. C++ gameplay framework facts with exact header paths, module names for Build.cs and class/function names: ACharacter and UCharacterMovementComponent (the properties for walk/crouch/jump/gravity/braking), Enhanced Input set up entirely in C++, line traces and collision channels, damage (ApplyDamage / point damage), AIController with MoveTo and the navigation system, pawn sensing or AIPerception, timers, UMG widgets constructed in C++ and Slate, UGameUserSettings, SaveGame, Niagara spawning from C++, audio (SoundWave playback, attenuation, submixes), reading a JSON file at runtime (FFileHelper, FJsonSerializer) and staging non-asset files for packaging, automation tests (how to write and run them headless), and how to build a project from the command line on Windows and on Linux.',
  '5. Art pipeline facts: Blender to Unreal axis and scale conventions for glTF and FBX (what happens to Blender +X, +Y, +Z and to metres), Nanite support for imported static meshes and its limits (masked/translucent materials, skeletal meshes), recommended texture packing, tangent-space normal convention, lightmap UV needs with Lumen, what Fab/Megascans/City Sample content is free to use in Unreal projects and how it is added.',
  'Format: one section per topic; under each, short verified statements with the URL; a final "Could not verify" list. Include exact names (ini keys, class names, header paths, Python function names) verbatim: they will be copied into code.',
  '',
  CONV,
  '',
  'When done, reply through the structured output: file = docs/unreal/spec/00-unreal-scout.md, summary (at most 120 words: target engine version and the most important verified facts), open_questions (the most important things you could not verify).',
].join('\n')

const BIBLE_PROMPT = [
  COMMON,
  '',
  'YOUR TASK: write docs/unreal/ART_BIBLE.md, the art direction for the Unreal rebuild. The user\'s brief is: "much better graphics and textures, realistic next-gen graphics". The web game is stylised low-poly with canvas-painted textures (docs/DESIGN.md sections 4, 5, 8); the rebuild keeps the same place, layout, fiction and identity (Hollis, Queens; Jamaica Ave under an elevated train line; IPX; a hot summer afternoon about 4:15 PM by default, with 02:14 AM night as the alternate look) and replaces the look with photoreal, physically based rendering in Unreal Engine 5 (Lumen, Nanite, virtual shadow maps).',
  'Read docs/DESIGN.md fully, skim src/config/look.js and src/config/brand.js for the existing palette and brand tokens, and the storefront/sign names in DESIGN section 4.',
  'The bible must be concrete enough that ten different artists produce assets that belong in the same photograph:',
  '1. Target in one page: what "photoreal" means here, described through real-world reference: outer-borough New York commercial avenue under a riveted steel elevated line (structure type, typical column bents, lattice bracing, plate girders, open timber-tie deck), 2 to 5 storey brick tenements with fire escapes and cornices, one-storey taxpayer storefront strips with roll-down gates, awnings and box signs, a cinder-block auto body shop, a chain-link ball court, an attended parking lot. Period: present day. What to avoid (game-y cleanliness, uniform noise, pure colours, repetition).',
  '2. Lighting: DAY and NIGHT described physically (sun elevation/azimuth and why, illuminance, sky, exposure targets, shadow character under the El, bounce colour from brick and asphalt; at night sodium/LED street lighting, neon and box-sign emissive levels in nits, window light, wet reflections) and as Unreal settings to aim for. Mood words and a shot list of 8 hero views that must look like photographs.',
  '3. Material bible: every surface family (asphalt, concrete, brick types, painted and raw steel, cast iron, galvanised chain-link, glass, roll-gate steel, awning vinyl/canvas, plastics, rubber, timber, tar roofing, signage acrylic, vehicle paint/glass/chrome/tyres, fabric for clothing, gun metal and polymer) with physically based ranges (albedo, roughness, metallic), real-world pattern scale, characteristic wear (where dirt, rust, leaks, gum, oil, soot and chips gather and why), and which are TILING sets versus UNIQUE baked sets. Vertex-colour mask convention for wear on tiling surfaces: R = cavity dirt/grime, G = edge wear/chips, B = downward leak/rust streaks, A = ground splash-back/wetness.',
  '4. Modelling bar: bevel policy (2 to 10 mm on props, 5 to 20 mm on architecture), what detail is geometry versus normal map (geometry when larger than about 5 mm because Nanite renders it), real dimensions for the recurring things (brick 194 x 57 x 92 mm with 10 mm joints, kerb 150 mm, door 2.03 m, storefront bay widths, storey heights, El column spacing 10 m, track gauge 1.435 m, chain-link mesh 50 mm), texel density (1024 px/m first-person weapons and hands; 512 px/m cover props; tiling sets 2048 px over 2 m), triangle guidance.',
  '5. Signage and branding: how the invented storefront names, the IPX wordmark ("IPX" and "IPX.EXCHANGE" only, no slogan), the mural and the billboard should be built as real sign types (channel letters, lightbox, painted fascia, vinyl awning, neon tube) so they hold up in daylight and at night. No real brands, no real people other than the unseen player character.',
  '6. Characters and vehicles strategy: the Goon (masked, hoodie or puffer, black and oxblood, pale mask), the Buzzard drone, first-person arms (black gloves, gold watch, gold bracelet), vehicles (generic invented makes: sedans, yellow cab, SUV, panel van, box truck, armoured IPX vault truck). Give the quality bar and the honest options for reaching it: authored in Blender, Unreal-native sources (MetaHuman, mannequins, City Sample vehicles from Fab) and what each costs; recommend one per category.',
  '7. Effects and atmosphere bar (muzzle flash, tracers, impacts, explosions, steam, dust, heat haze, the passing train, pigeons, litter) and audio note.',
  '8. Asset priority list (what defines the block and must be built first) and a definition of done per asset (checklist an art director can tick).',
  '9. Performance targets and scalability (what to aim for on a mid-range current GPU, what scales down).',
  '',
  CONV,
  '',
  'When done, reply through the structured output: file = docs/unreal/ART_BIBLE.md, summary (at most 120 words), open_questions (decisions the user or the art lead must make).',
].join('\n')

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    summary: { type: 'string' },
    corrections: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' } },
    gaps: { type: 'array', items: { type: 'string' } },
    asset_count: { type: 'number' },
  },
  required: ['file', 'summary', 'corrections', 'gaps'],
}

function criticPrompt(done) {
  const list = done.map(d => '- ' + d.file + ': ' + d.summary + (d.open_questions && d.open_questions.length ? '\n  open: ' + d.open_questions.join(' | ') : '')).join('\n')
  return [
    COMMON,
    '',
    'YOUR TASK: you are the reviewer of the port specification that other agents just wrote. Find what is wrong or missing and fix it in place. Be adversarial: assume each spec contains transcription errors until you have checked.',
    'What was written:',
    list,
    'Also present: unreal/MurderInc/Content/Data/*.json (exported data), docs/unreal/spec/assets/*.json (asset briefs), docs/unreal/ART_BIBLE.md.',
    '',
    'Do, in this order:',
    '1. For every spec in docs/unreal/spec/: sample at least 40 constants and 5 behavioural claims and check each against the cited source line. Fix every error directly in the spec (keep a list). Check that each required section exists and that the Unreal unit conversions are right (metres to centimetres, radians to degrees, web axes to Unreal axes per the conventions below).',
    '2. Cross-check: the same number or rule stated in two specs must agree (difficulty tables, weapon stats, wave sizes, positions). Check at least 30 values of the exported JSON against src/config and against the specs, and the positions of the start pose, the three reels and the IPX truck against docs/DESIGN.md section 4. Report contradictions and resolve them from the source.',
    '3. Gaps: list anything a port team would still have to open the JavaScript for. Fill the important ones yourself.',
    '4. Merge docs/unreal/spec/assets/*.json into docs/unreal/spec/assets.json: one array, unique ids, schema-valid, sorted by family then priority; remove duplicates that describe the same object; make sure nothing in docs/DESIGN.md section 4 is missing (add briefs for missing things with source "DESIGN.md").',
    '5. Write docs/unreal/spec/README.md: an index with a paragraph per spec, the corrections you made, the open questions that matter most (deduplicated, ordered by risk), and a count of assets by family and priority.',
    '',
    CONV,
    '',
    'Reply through the structured output: file = docs/unreal/spec/README.md, summary (at most 150 words), corrections (what you fixed), contradictions (what disagreed and how you resolved it), gaps (what is still missing), asset_count.',
  ].join('\n')
}

// Each workflow run is capped at two concurrent agents on this machine, so the work is split into
// groups that are launched as separate runs: args = { group: 'export-scout' | 'readers-a' ... | 'bible' | 'critic' }.
const group = (args && args.group) || 'all'
const NOTE = '\n\nNOTE: an earlier run of this same task was interrupted. Files it left behind (for example under tools/ue-export/, unreal/ or docs/unreal/) may be incomplete: review them, reuse what is sound and replace what is not.'
const byId = {}
READERS.forEach(r => { byId[r.id] = r })
const reader = id => () => agent(readerPrompt(byId[id]), { label: 'spec:' + id, phase: 'Understand', schema: SPEC_SCHEMA })
const GROUPS = {
  'export-scout': [
    () => agent(EXPORT_PROMPT + NOTE, { label: 'export:data', phase: 'Export', schema: SPEC_SCHEMA }),
    () => agent(SCOUT_PROMPT + NOTE, { label: 'scout:unreal', phase: 'Scout', schema: SPEC_SCHEMA }),
  ],
  'readers-a': [reader('player'), reader('weapons')],
  'readers-b': [reader('enemies'), reader('flow')],
  'readers-c': [reader('level'), reader('props')],
  'readers-d': [reader('look'), reader('ui-audio')],
  'bible': [() => agent(BIBLE_PROMPT, { label: 'art:bible', phase: 'Art bible', schema: SPEC_SCHEMA })],
}
if (group === 'critic') {
  phase('Critique')
  const written = READERS.map(r => ({ file: r.out, summary: r.title }))
    .concat([{ file: 'docs/unreal/spec/08-data-export.md', summary: 'the data export (tools/ue-export, unreal/MurderInc/Content/Data)' }, { file: 'docs/unreal/spec/00-unreal-scout.md', summary: 'verified Unreal Engine facts' }, { file: 'docs/unreal/ART_BIBLE.md', summary: 'the art direction' }])
  const critique = await agent(criticPrompt(written), { label: 'critic:specs', phase: 'Critique', schema: CRITIC_SCHEMA })
  return { critique }
}
const jobs = group === 'all' ? Object.keys(GROUPS).flatMap(k => GROUPS[k]) : GROUPS[group]
if (!jobs) throw new Error('unknown group ' + group)
phase('Understand')
const results = await parallel(jobs)
const done = results.filter(Boolean)
log(group + ': ' + done.length + ' of ' + jobs.length + ' agents finished')
return { group, finished: done.length, failed: jobs.length - done.length, specs: done }
