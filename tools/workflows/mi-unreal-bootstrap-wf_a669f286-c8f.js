export const meta = {
  name: 'mi-unreal-bootstrap',
  description: 'Create the Unreal 5.9 C++ project, get it compiling and booting headless on the rented GPU box, document the loop, design the gameplay architecture',
  phases: [
    { title: 'Bootstrap', detail: 'project skeleton, box scripts, first green compile, editor + MCP smoke test' },
    { title: 'Architecture', detail: 'gameplay module design from the port specs and the engine template' },
    { title: 'Verify', detail: 'fresh agent repeats sync, build and boot from the docs alone' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const SESSION = 'cd9d7408-b3de-43f6-ac4c-27e93d9df66c'
const BRANCH = 'claude/tender-albattani-5q78qr'

const COMMON = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter (three.js) owned by the user, which is being REBUILT in Unreal Engine 5.9 with photoreal graphics. The web game (src/) is the ground truth for gameplay and stays untouched. Read docs/DESIGN.md first (section 8 wins over 1, 2, 5, 6: daylight default). Port specs written by other agents are in docs/unreal/spec/ (01-player.md, 02-weapons-combat.md, 03-enemies.md, 04-flow.md exist now; 05-level, 05b-props, 06-look-fx, 07-ui-audio, 08-data-export, 00-unreal-scout and docs/unreal/ART_BIBLE.md are being written right now and may appear while you work). Data exported from the web game is in unreal/MurderInc/Content/Data/*.json (config, text, level, props, atmos).',
  'Other agents are working in the same checkout on other paths (docs/unreal/spec, art/, tools/ue-export): never edit or delete their files.',
].join('\n')

const BOX = [
  'THE UNREAL BOX',
  'A rented Linux GPU box (RTX PRO 6000, 16 cores, 64 GB RAM) runs Unreal Engine 5.9.0 (preview 2, changelist 60738873). It costs the user about 114 credits per hour while it runs: work efficiently, do not leave long jobs unwatched, do not start things you do not need.',
  'How to reach it: the MCP tool mcp__Higgsfield__gpu_rental_exec (load its schema first with ToolSearch, query "select:mcp__Higgsfield__gpu_rental_exec") with session_id ' + SESSION + '. Each call runs one bash command as root in a fresh shell and returns exit code, stdout and stderr (first 2,000 plus last 18,000 characters each). HARD LIMITS: a call must finish within 50 seconds (the MCP client gives up at 60 s; pass timeout_s 55 at most), so start anything longer with `setsid nohup ... > /project/ue/logs/<name>.log 2>&1 &` and poll its log in later calls (a poll may begin with `sleep 40`). Never use `pkill -f` or `pgrep -f` (they match your own shell and kill it): use `pkill -x NAME` / `pgrep -x NAME` with the process name cut to 15 characters (UnrealEditor, CrashReportClie, ShaderCompileWo, UnrealTraceServ). Do not call gpu_rent, gpu_rental_stop or any other rental tool: the user controls renting and stopping. If gpu_rental_exec reports that the box is not running, stop and report that.',
  'Layout: /project is persistent storage; everything else on the box is lost when it stops. /project/ue/UnrealEngine is the engine, owned by user ue4. UnrealEditor and the build tools must not run as root: use `su ue4 -c "..."`. /project/ue/bin/run-editor.sh <uproject> [args] starts the editor with the cache settings that work here (the stock Zen local cache cannot be reached on this box, so the script passes a file-system cache graph and disables Zen auto-launch: keep those arguments for every editor or commandlet start, including UnrealEditor-Cmd). /project/ue/bin/mcp.py talks to the editor\'s built-in MCP server: `python3 /project/ue/bin/mcp.py init | list | call <tool> \'<json args>\' [max_chars]`. The server exposes four meta-tools (list_toolsets, describe_toolsets, describe_tools, call_tool) and 111 toolsets, among them EditorToolset.ActorToolset, AssetToolset, LevelToolset, MaterialToolset, MaterialInstanceToolset, StaticMeshToolset, TextureToolset, EditorAppToolset, ConsoleToolset.ConsoleToolset, ConsoleToolset.LogsToolset, AutomationTestToolset, SceneCaptureToolset, NavMeshToolset, InputToolset, FileSystemToolset, BlueprintToolsets, UMGEditor.WidgetBlueprintEditorSubsystem, NiagaraToolsets, MetaSoundToolset, PerfToolset: read a toolset with describe_toolsets / describe_tools before calling it. /project/ue/logs holds logs. /project/ue/setup-box.sh re-creates the ue4 user and system packages after a restart of the box.',
  'Windows do not work on this box: the editor aborts when it opens a window on the box desktop (the Vulkan bridge "PrimusVK" throws "Layouts don\'t match at all"). Always run it headless, for example: su ue4 -c "setsid nohup /project/ue/bin/run-editor.sh <uproject> -RenderOffscreen -unattended -nosplash -NoSound > /project/ue/logs/editor.log 2>&1 &". It starts in about 40 seconds and its MCP server listens on http://127.0.0.1:8000/mcp. A headless editor on /project/ue/Blank/Blank.uproject may still be running from the setup test: stop it (pkill -x UnrealEditor) before you start another.',
  'Engine facts already verified on the box: plugins ModelContextProtocol (Engine/Plugins/Experimental/ModelContextProtocol) and AllToolsets (Engine/Plugins/Experimental/Toolsets/AllToolsets); the MCP settings section is [/Script/ModelContextProtocol.ModelContextProtocolSettings] with bAutoStartServer=True, and the switch -ModelContextProtocolStartServer also starts it; bundled toolchain Engine/Extras/ThirdPartyNotUE/SDKs/HostLinux/Linux_x64/v26_clang-20.1.8-rockylinux8 and bundled .NET 10; project templates in /project/ue/UnrealEngine/Templates, including TP_FirstPerson (C++), whose Source/TP_FirstPerson/Variant_Shooter (ShooterCharacter, ShooterWeapon, ShooterProjectile, ShooterPickup, ShooterWeaponHolder, ShooterNPC, ShooterAIController, ShooterNPCSpawner, ShooterStateTreeUtility, ShooterGameMode, ShooterPlayerController, ShooterUI, ShooterBulletCounterUI) is working Unreal 5.9 shooter code and the best reference for current API usage. The engine headers and source are on the box: grep them rather than trusting memory (your knowledge of Unreal may predate 5.9).',
  'Files reach the box only through git: the repository is public, so the box clones and pulls https://github.com/Teslalol305/MURDER-INC. (branch ' + BRANCH + ') without credentials, and you commit and push from the local checkout. The box cannot push. Text comes back only through command output: keep outputs small (grep, head, tail, cut -c).',
].join('\n')

const GIT = [
  'GIT RULES',
  'Work on branch ' + BRANCH + ' only; never force-push, never touch another branch, never open a pull request. Stage only your own paths with explicit `git add <paths>` (never `git add -A` or `git add .`: other agents have unfinished files in this checkout). If git reports index.lock or a non-fast-forward, wait a few seconds and retry; someone else committed. Push with `git push -u origin ' + BRANCH + '`. End every commit message with exactly these two lines and put no model name anywhere else (code, comments, docs):',
  'Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>',
  'Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4',
].join('\n')

const CONV = [
  'UNREAL CONVENTIONS (fixed; other agents rely on them)',
  '- Project unreal/MurderInc/, project and primary game module both named MurderInc, EngineAssociation "5.9". Class prefix MI (AMIGameMode, AMIPlayerCharacter, UMIWeaponComponent ...), log category LogMI. Source folders under Source/MurderInc/: Core (types, data loading, settings, subsystems), Player, Weapons, Enemies, Flow (game mode and state, mission and holdout directors), World (reel pickup, extraction zone, explosives, El train, spawn and cover points, level builder helpers), UI, Audio, Tests (automation tests named MurderInc.*).',
  '- Gameplay is C++ plus data: every tuning number comes from Content/Data/*.json, loaded once by a game-instance subsystem into structs (converted to Unreal units at load: metres to centimetres, radians to degrees). No tuning constants in code, and no gameplay logic in Blueprints, so that the game builds and tests headless from a clean checkout. Art is referenced through soft paths in data so it can be swapped.',
  '- Coordinates: web game metres, +Y up, north -Z, east +X; Unreal centimetres, Z up, X east, Y south: Unreal(X, Y, Z) = (x_web, z_web, y_web) * 100. Yaw 0 faces +X (east), +90 faces +Y (south).',
  '- Generated binary content (.uasset, .umap, imported meshes and textures) lives only on the box under the project\'s Content/ and is not committed; it must be reproducible by committed scripts. Committed: Source/, Config/, the .uproject, Content/Data/*.json, Content/Python/*.py, tools/box/*, docs/unreal/*.',
  '- Rendering target: current-generation, photoreal: Lumen global illumination and reflections, Nanite, virtual shadow maps, hardware ray tracing where the Vulkan driver supports it, temporal super resolution.',
].join('\n')

const BOOT_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    works: { type: 'array', items: { type: 'string' } },
    timings: { type: 'array', items: { type: 'string' } },
    pitfalls: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
    commits: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'works', 'open_issues'],
}

const BOOTSTRAP_PROMPT = [
  COMMON, '', BOX, '', GIT, '', CONV, '',
  'ROLE: senior Unreal engineer. YOUR TASK: bootstrap the Unreal project and the remote build loop, and prove them with a green compile and a running headless editor. Everything later (ten more agents writing gameplay, importing art, building the level) depends on this loop being reliable and documented.',
  '',
  'Deliver, in this order (commit and push after each milestone, then pull on the box):',
  '1. On the box, a clone of the repository at /project/ue/repo owned by ue4 (git clone --branch ' + BRANCH + ' --single-branch; keep it a pure mirror: all edits happen in the local checkout).',
  '2. Box scripts, committed under tools/box/ and run from /project/ue/repo/tools/box/ (bash, small, each prints a short status line; all long work detached with logs in /project/ue/logs): sync.sh (fetch the branch and hard-reset the mirror to it; untracked generated content must survive), build.sh (stops a running editor, then builds the editor target MurderIncEditor Linux Development as ue4 with the engine\'s Build.sh and -waitmutex, writing build.log and a one-word status file RUNNING / OK / FAILED), build-status.sh (status, elapsed time, then compiler errors only: file, line, message, at most 40), editor.sh start|stop|status (headless editor on the MurderInc project with the MCP server, using /project/ue/bin/run-editor.sh), test.sh (run the MurderInc.* automation tests headless and print pass/fail counts), shot.sh <out.png> [console camera/args] (capture a 1920x1080 picture of the running game or editor viewport to a file on the box and print its size and mean brightness so a black frame is detected), seed-content.sh (copy the first-person arms, weapon meshes, mannequins, animations and input assets from the engine template TP_FirstPerson into the project Content as placeholders; idempotent). Read the engine\'s own scripts and BuildConfiguration docs on the box to get the invocations right.',
  '3. The project unreal/MurderInc/ in the local checkout, written with the engine template as the reference for every API you touch (read TP_FirstPerson\'s .uproject, Target.cs, Build.cs, Config/*.ini and the Variant_Shooter sources on the box): MurderInc.uproject (the plugins the template\'s shooter needs, plus ModelContextProtocol and AllToolsets marked so the project still opens on an engine without them: check how FPluginReferenceDescriptor spells that in the engine source), Source/MurderInc.Target.cs, Source/MurderIncEditor.Target.cs, Source/MurderInc/MurderInc.Build.cs and module files, Config/DefaultEngine.ini, DefaultGame.ini, DefaultInput.ini, DefaultEditor.ini with the rendering target above (take every key from the engine\'s BaseEngine.ini / template config or the source, not from memory; note which features the Linux Vulkan path supports), a .gitignore for the project (Binaries, Intermediate, Saved, DerivedDataCache, and generated binary content), and Saved/Config/LinuxEditor/EditorPerProjectUserSettings.ini created on the box (not committed) so the MCP server auto-starts.',
  '4. A minimal playable slice in C++ that proves the stack end to end: the MurderInc module, LogMI, AMIGameMode, AMIPlayerController and AMIPlayerCharacter with a first-person camera, walk, sprint, crouch, jump and mouse look through Enhanced Input set up entirely in C++ (input actions and mapping context created in code, so no binary input assets are needed), a UMIDataSubsystem that loads Content/Data/config.json at start-up and logs a few values (stage the Data directory for packaging in DefaultGame.ini), and one automation test MurderInc.Core.DataLoads that checks real values from config.json. Use the movement numbers from docs/unreal/spec/01-player.md where the stock character movement component can express them; leave exact parity for later.',
  '5. A green build on the box (iterate on compiler errors until build-status.sh says OK), then the headless editor running on the project with MCP answering; through MCP or editor Python create and save a small test map /Game/Maps/L_Bootstrap (floor, a few boxes, a player start, sun, sky atmosphere, sky light, exponential height fog, post-process volume with Lumen), make it the default map, run test.sh (the test must pass), and capture one picture with shot.sh that is not black.',
  '6. docs/unreal/BOX.md: the exact loop (edit locally, commit, push, sync.sh, build.sh, poll build-status.sh, editor.sh, mcp.py, test.sh, shot.sh), measured timings (clean build, incremental build, editor start), every pitfall you hit and its fix, what is not committed and how it is regenerated, and what a restarted box needs (setup-box.sh, then what).',
  '',
  'Rules of engagement: compile early (get an empty module green before adding classes). When a build fails, read the first error, fix, rebuild; do not guess at APIs: grep the engine headers on the box. Keep every box command under 50 seconds. If something on the box is broken beyond your task (engine files missing, disk full, GPU absent), stop and report it.',
  '',
  'Reply through the structured output: summary (at most 200 words), works (what you verified, each with the evidence), timings, pitfalls, open_issues (what is not done or not verified), commits (hashes with one-line descriptions).',
].join('\n')

const ARCH_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    summary: { type: 'string' },
    work_packages: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, files: { type: 'string' }, depends_on: { type: 'string' } }, required: ['id', 'title'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['file', 'summary', 'work_packages'],
}

const ARCH_PROMPT = [
  COMMON, '', BOX, '', CONV, '',
  'ROLE: lead gameplay architect for the Unreal port. YOUR TASK: write docs/unreal/ARCHITECTURE.md, the design that about ten engineers (agents) will implement in parallel next, each owning one work package, without stepping on each other. Another agent is bootstrapping the project skeleton and the build loop right now (unreal/MurderInc/, tools/box/, docs/unreal/BOX.md): do not write project files yourself; write only docs/unreal/ARCHITECTURE.md.',
  'Inputs: the port specs in docs/unreal/spec/ (read every one that exists completely, and re-check the directory before you finish: more arrive while you work), docs/DESIGN.md, the exported data in unreal/MurderInc/Content/Data/ (read the key structure of every JSON file), and the engine itself on the box: read the TP_FirstPerson Variant_Shooter sources (cat them through gpu_rental_exec in pieces) to see how Unreal 5.9 structures a shooter (character, weapon holder interface, NPC, AI controller, state tree utilities, UI), and grep engine headers for every class you plan to build on. The box is read-only for you: do not build, start or stop anything there.',
  'The document must contain:',
  '1. Principles: C++ plus data, headless-testable, parity with the web game\'s rules (name the places where Unreal systems replace hand-rolled web code and how parity is kept: for example the custom velocity rule on top of character movement, hitscan from the eye, per-tick accumulators for fire control, a clock that only advances in intro and playing).',
  '2. Module and folder map with every class: name, base class (with its engine header path), responsibility, the spec sections it implements, the data it reads, the events it sends and receives. Cover: data subsystem and structs, game mode/state and the flow state machine, Story and Hold the Block directors, spawn scoring, difficulty, statistics and rating, player character and controller, movement component, camera layers (recoil, sway, bob, shake), health and regeneration, weapon system (CHOPPER, NINE, melee, state machine, spread, recoil, reload timelines), hit resolution and damage, explosives and chains, the Goon (movement on the nav mesh, perception, exposure and accuracy ramp, tokens, fire positions and cover, bursts, rush, death and bodies), the Buzzard (flight model, telegraphed bolts, crash), pooling and caps, reel pickup and extraction, the El train, the event bus, the HUD and menus (decide between UMG built in C++ and Slate, and say why), audio hooks, save data and settings, the level builder (how the block is assembled from level.json and props.json: first as a grey-box from the collider boxes so gameplay can be tested before art exists, then with real meshes mapped by catalogue id), automation tests with golden values taken from the web game.',
  '3. The shared contracts that parallel work depends on, written as actual C++ declarations to copy: the core enums and structs, the event bus (delegate signatures), interfaces (damageable, interactable, weapon holder), collision channels and trace conventions, gameplay tags if used, the data structs with their JSON field mapping, naming of sockets and of assets expected from art.',
  '4. Tick order and timing rules that preserve the web game\'s behaviour, and where fixed-step accumulation is required.',
  '5. Work packages: 8 to 12 packages that can be built in parallel after the contracts exist, each with an id, a title, the exact files it owns, what it depends on, how it is tested (automation tests and an in-editor smoke check through MCP), and its definition of done. Order them so a grey-box Story run (walk, shoot, Goons and Buzzards, three reels, extraction, death and win cards) is reachable as early as possible.',
  '6. Risks and decisions for the project lead, each with a recommendation.',
  'Be concrete and complete rather than brief; engineers will copy declarations from this file.',
  '',
  'Reply through the structured output: file = docs/unreal/ARCHITECTURE.md, summary (at most 150 words), work_packages (id, title, files, depends_on), open_questions (at most 8).',
].join('\n')

function verifyPrompt(boot) {
  return [
    COMMON, '', BOX, '', GIT, '', CONV, '',
    'ROLE: sceptical release engineer. Another agent says it bootstrapped the Unreal project and the remote build loop. Its report: ' + (boot ? boot.summary : '(no report)') + ' Claimed to work: ' + (boot && boot.works ? boot.works.join(' | ') : 'nothing listed') + '. Open issues it admits: ' + (boot && boot.open_issues ? boot.open_issues.join(' | ') : 'none') + '.',
    'YOUR TASK: prove or disprove it using only docs/unreal/BOX.md and the committed scripts, the way the next ten engineers will. Do not trust the report.',
    '1. Read docs/unreal/BOX.md and tools/box/*. On the box: run sync.sh; check the mirror is at the pushed commit; touch one source file\'s content locally in a harmless way (for example a log line), commit, push, sync, build with build.sh, poll with build-status.sh until it ends: record the incremental build time. Then make a deliberate compile error, push, build: does build-status.sh show the error clearly (file, line, message)? Revert it, push, build: green again?',
    '2. editor.sh start: does the editor reach "Engine is initialized" with the MurderInc project and without Error lines that matter (list the errors and warnings that do appear)? Does mcp.py answer, and can you read the level\'s actors through a toolset? Run test.sh: does the automation test pass, and does it fail when you break the expected value (check, then restore)? Run shot.sh: is the picture produced and not black?',
    '3. Review the committed project files for correctness against the engine (grep engine headers and BaseEngine.ini for every setting and API you doubt): the .uproject, Target.cs files, Build.cs dependencies, the config keys for Lumen, Nanite, virtual shadow maps and ray tracing on the Linux Vulkan path, the Enhanced Input set-up in C++, the data subsystem and JSON staging, the .gitignore.',
    '4. Fix what is cheap and clearly wrong (commit and push each fix with a clear message), update docs/unreal/BOX.md where it is inaccurate or missing a step, and leave the box with the editor stopped and the build green.',
    'Reply through the structured output: summary (at most 200 words: verdict first), works (what you verified yourself, each with evidence), timings, pitfalls (new ones you found), open_issues (what is still broken or unverified, most important first), commits.',
  ].join('\n')
}

phase('Bootstrap')
const both = await parallel([
  () => agent(BOOTSTRAP_PROMPT, { label: 'unreal:bootstrap', phase: 'Bootstrap', schema: BOOT_SCHEMA }),
  () => agent(ARCH_PROMPT, { label: 'unreal:architect', phase: 'Architecture', schema: ARCH_SCHEMA }),
])
const boot = both[0]
const arch = both[1]
log('bootstrap: ' + (boot ? boot.summary.slice(0, 160) : 'no result'))
phase('Verify')
const verify = await agent(verifyPrompt(boot), { label: 'unreal:verify-loop', phase: 'Verify', schema: BOOT_SCHEMA })
return { boot, arch, verify }
