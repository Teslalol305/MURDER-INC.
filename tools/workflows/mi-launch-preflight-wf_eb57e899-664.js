export const meta = {
  name: 'mi-launch-preflight',
  description: 'Pre-flight review of MURDER INC. v2 on E3DS and the website: four lenses, adversarial verify, one decision doc',
  phases: [
    { title: 'Review', detail: 'E3DS contract, stream experience, GPU performance, website and launch' },
    { title: 'Verify', detail: 'one adversarial reviewer per lens tries to refute each finding' },
    { title: 'Decide', detail: 'release lead merges verified findings into docs/unreal/PREFLIGHT.md' },
  ],
}

const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'

const CONTEXT = `
PROJECT: MURDER INC., a first-person shooter rebuilt in Unreal Engine 5.9 (C++ project in /home/user/MURDER-INC./unreal/MurderInc), packaged for Linux with the Pixel Streaming 2 (PS2) plugin and streamed by Eagle 3D Streaming (E3DS) into the owner's website (the IPX.exchange "Game OS" page, built by the Cursor editor in another repository from instructions in docs/CURSOR_HANDOFF.md and docs/LAUNCH.md section 5). The owner is not technical; they do the E3DS Control Panel steps by hand. The owner's standard: a senior game developer should have foreseen deployment problems before the build; your job is to find the remaining ones NOW, before the owner hits them.

E3DS ACCOUNT: Core plan: 10 concurrent users (CCU), 300 streaming minutes a month, 10 GB storage. App name MurderInc (launcher MurderInc.sh at the zip root), project Project_MurderInc, configuration platform Linux.

HISTORY: Version 1 (sha256 8378eedd...) passed E3DS's upload check, but every real session ended at start with E3DS's email "Crashed ... But no crashlog was found" (a Shipping build writes no log). Version 2 (this release: sha256 82ed886a3fb508a96ce6ac0e7c4a4c3b61f0563872e9d9cdc25249817d92ee8a, 2,254,911,244 bytes, 9 parts, game commit e989cb8, launcher commit 3f5d85a) adds: a logging launcher tools/box/cloud/MurderInc.sh (writes MurderInc/Saved/Logs/MurderInc.log, passes stop signals on, exits with the game's exit code but 0 for a stop asked by the host, never runs the game as root, -MIDev runs the Development game carried in the zip, -MIForceSM6 skips Unreal's Vulkan SM6 check), SM5 fallback shaders, video-memory cuts ([MICloud] section of unreal/MurderInc/Config/DefaultGame.ini; BC6H interior cube maps via tools/box/cloud/cloud_assets.py), MICloud start-up diagnostics (unreal/MurderInc/Source/MurderInc/Cloud/MICloud.cpp), and "P Pause" on the home screen in cloud mode (Source/MurderInc/UI/SMIFrontEnd.cpp). Packaging: tools/box/cloud/package-cloud.sh. Read the top entry of docs/unreal/PROGRESS.md and docs/LAUNCH.md sections 2 to 13 for details. Another agent is editing docs/LAUNCH.md, docs/unreal/PROGRESS.md and docs/unreal/RESUME.md right now: read them, never edit them. The owner is about to upload version 2 as a new version of the app and test it.

E3DS DOCS: readable at https://docs.eagle3dstreaming.com/wiki/<page>/ (curl through the session proxy works; WebFetch may also work). Plain-text copies of about 27 key pages are in ${SP}/e3ds-docs/*.txt and the full page list is ${SP}/e3ds-docs/sitemap.xml (175 pages). Plans and prices: https://www.eagle3dstreaming.com/. Facts already read from those pages (verify before relying on them): Linux uploads are not stream-tested; Linux sessions start slowly, in four stages, and the whole ZIP is transferred to the machine for every session; the app name must equal the .sh name; the configuration's Platform must be Linux; E3DS appends to every launch: -AudioMixer -AllowPixelStreamingCommands -Windowed -ForceRes -log -Unattended -PixelStreamingURL=..., plus -ResX/-ResY (Resolution setting), -PixelStreamingEncoderCodec=, -PixelStreamingWebRTCMaxBitrate=, -PixelStreamingEncoderMinQP=/MaxQP=; machines are RTX 4080 / RTX 5070 with 12 to 16 GB of GPU memory and 32 GB RAM, one dedicated machine per viewer; an app should use 4 to 6 GB GPU memory and 50 to 70 % GPU; Browser Resolution "Dynamic" (the default) makes the page ask the app to render at the viewer's video-area size, and with -RenderOffScreen sizes such as 2560x1440, 3840x2160 and a phone's 1170x2532 are delivered at full size; logs: "Print UE log in browser console", "Auto-Download UE Crash Log - not working at present", "Email To Send Log Upon App Crash"; a Linux stream link is on connector_linux.eagle3dstreaming.com; Projects links always play the app's newest version; "Upload a new version" is on the app card; a version should not be deleted until the next one has proven itself.

GPU BOX (Linux; RTX PRO 6000 Blackwell 96 GB, driver 620.70; Unreal 5.9 installed build at /project/ue/UnrealEngine; staged version-2 build at /project/ue/cloud/build-Shipping/Linux; zip at /project/ue/cloud/MurderInc-E3DS.zip; logs of the version-2 check runs in /project/ue/cloud/repro/*/ (game.log, launcher logs, SUMMARY.txt, verify.log)). Reach it with the tool mcp__Higgsfield__gpu_rental_exec (load its schema first with ToolSearch query "select:mcp__Higgsfield__gpu_rental_exec"), session_id ec087d85-b777-4ece-be42-ccc063d225cf, at most 90 s per command. READ-ONLY: cat, grep, ls, zipinfo on logs, the staged build and the engine and plugin source are fine. Do NOT start the game, the editor, packaging, or anything that uses the GPU; do not write or delete anything under /project/ue. Another agent may be using the box.

RULES: Do not edit, create or delete any file in the repository and do not commit (one later agent writes the report). Never write download links, the owner's email address, the E3DS account or user name, or any person's name anywhere, including your output. Never ask for or handle passwords. Gameplay rules must not change. Cite evidence for every finding: an E3DS page URL with a short quote, a repo file:line, an engine source file:line, or a box log line. Say so when you could not verify something. Be concrete: a fix names the exact file and change, the exact E3DS setting, or the exact website change. Severity: blocker = version 2 will not stream or will crash for most sessions; high = most players get a clearly broken or bad experience, or the owner loses money or minutes; medium = noticeable for some players or some sessions; low = polish.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low'] },
          bites: { type: 'string', enum: ['v2-test', 'public-launch', 'later'] },
          evidence: { type: 'string' },
          impact: { type: 'string' },
          fix: { type: 'string' },
          fix_kind: { type: 'string', enum: ['owner-e3ds-setting', 'website', 'docs', 'game-code-or-config-needs-rebuild', 'launcher-needs-rezip', 'none'] },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['id', 'title', 'severity', 'bites', 'evidence', 'impact', 'fix', 'fix_kind', 'confidence'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' } },
    could_not_check: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_ok', 'could_not_check'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
          severity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low'] },
          reason: { type: 'string' },
          corrected_fix: { type: 'string' },
        },
        required: ['id', 'verdict', 'severity', 'reason', 'corrected_fix'],
      },
    },
  },
  required: ['verdicts'],
}

const DECISION = {
  type: 'object',
  properties: {
    owner_v2_test_settings: { type: 'array', items: { type: 'string' } },
    v3_must_fix: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          why: { type: 'string' },
          change: { type: 'string' },
          cost: { type: 'string' },
        },
        required: ['title', 'why', 'change', 'cost'],
      },
    },
    website_changes: { type: 'array', items: { type: 'string' } },
    before_public: { type: 'array', items: { type: 'string' } },
    doc_corrections: { type: 'array', items: { type: 'string' } },
    unknowns_until_e3ds_test: { type: 'array', items: { type: 'string' } },
    refuted: { type: 'array', items: { type: 'string' } },
    summary_for_owner: { type: 'string' },
    preflight_doc_path: { type: 'string' },
  },
  required: ['owner_v2_test_settings', 'v3_must_fix', 'website_changes', 'before_public', 'doc_corrections', 'unknowns_until_e3ds_test', 'refuted', 'summary_for_owner', 'preflight_doc_path'],
}

const LENSES = [
  {
    key: 'e3ds-contract',
    prompt: `YOUR LENS: will version 2 start, stream, stop and report correctly on E3DS's Linux machines, and what does each session's life look like? Check against E3DS's own documentation and our code:
- The launch contract: every argument E3DS appends (listed above) and what it does to our launcher (tools/box/cloud/MurderInc.sh) and game: -Windowed together with our -RenderOffScreen on Linux; -log and -Unattended in Shipping and in Development (effects on our MICloud code, the crash-report path and the exit guard); -PixelStreamingURL= with PS2 in 5.9 (read ParseLegacyCommandlineArgs in /project/ue/UnrealEngine/Engine/Plugins/Media/PixelStreaming2/Source/PixelStreaming2Settings/Private/PixelStreaming2PluginSettings.cpp and confirm it becomes ConnectionURL; look in the box run logs for a run that used -PixelStreamingURL and whether the streamer connected to the signalling server); -ResX/-ResY/-ForceRes; the legacy encoder arguments; -AllowPixelStreamingCommands and what PS2 5.9 needs instead, and what a viewer could do with console commands if they are allowed.
- How E3DS finds and runs the app (zip layout, app name = .sh name, Content one level below the top, executable bits, the user it runs as, the working directory), how it tells "App crashed" from a normal end (docs: your-own-launcher, minutes, ending-sessions, session-end-messages, monitoring-sessions), and whether our launcher's exit codes and log location match what E3DS's crash email reads (which file does it send, and does that work for Linux apps?).
- Session life: the four Linux stages and the start-up wait (the zip is transferred for every session: estimate the wait for our 2.25 GB zip from E3DS's numbers; what could be slimmed, such as the Development game or the SM5 shaders, and what we would lose), preallocated or warm machines, what the viewer sees at each stage and at the end (max session time, inactivity logout, connection dropped), the game pausing when the viewer leaves.
- Updates: apps-and-versions, update-without-uploading, create-a-patch, apply-a-patch, patch-launch-profiles: can later fixes ship as a small pak patch instead of a 2.25 GB upload, for Linux apps too? What can and cannot be patched (the launcher .sh, binaries, config)?
- Anything else in E3DS's docs that our build or our docs (docs/LAUNCH.md sections 2, 3, 8, 12, 13) get wrong. Known suspects to check: section 13 tells the owner to use -MIDev for "Auto Download UE Crash Log" (E3DS says that feature is not working at present); section 10 says "8 or 16 GB" (E3DS says 12 to 16 GB); the configuration field names (Platform values, Parameters To Pass To App / Launch options, Console Cmds To Pass To Unreal App).`,
  },
  {
    key: 'stream-experience',
    prompt: `YOUR LENS: what a player actually experiences in the browser with version 2, on E3DS's player page inside the owner's site, from the first click to the end of the session. Check:
- Resolution: Browser Resolution Dynamic versus Custom (docs: black-bars, stream page settings, loading-screen, fullscreen-button, command-line-parameters on -RenderOffScreen). Our launcher always adds -RenderOffScreen, so with Dynamic the game renders at the viewer's window size (4K monitors, Retina Macs, ultrawide screens, phones in portrait). Find how PS2 5.9 applies the browser's size request (engine source on the box under /project/ue/UnrealEngine/Engine/Plugins/Media/PixelStreaming2: the resolution command handler, r.SetRes, whether -AllowPixelStreamingCommands or another switch gates it, and whether E3DS's page sends device pixels or CSS pixels if you can tell) and what our game then does: GPU time, video memory (E3DS budget 4 to 6 GB), frame rate, and our HUD and menus (SMIFrontEnd.cpp, the HUD and loadout UI code) at sizes that are not 16:9. Give the safest owner setting for the version-2 test, and the right long-term fix in the game (for example: clamp the render size, or lower the screen percentage so TSR upscales, when the requested size is above 1920x1080; keep the UI readable), with the exact code location and the cvars.
- Input: mouse modes (E3DS Locked Mouse; docs features-api-mouse-mode, features-api-browser-mouse, controlling-the-stream), pointer lock and Esc, our P pause, keyboard focus inside an iframe, browser shortcuts that steal keys (Ctrl+W, Tab, Space scrolling the page, function keys), mouse sensitivity through the stream (relative movement in locked mode), right-click, game controllers (docs: game-controller-support) versus our gamepad code, touch and mobile (the game needs keyboard and mouse: what should the page do).
- Audio: does the game's sound reach the viewer (-AudioMixer, PS2 audio capture), browser autoplay rules, the first click.
- Session moments: the loading screen while a Linux machine starts (docs: iframe-loading-video, loading screen), the inactivity-logout countdown versus our pause screen (a paused player who reads for five minutes is logged out), max session time, "reload to play again", the CCU-limit queue message.
- Picture quality through H.264 at 1080p: HUD text size and contrast, detail that turns to mush at stream bitrates (docs: video quality, codec).`,
  },
  {
    key: 'gpu-performance',
    prompt: `YOUR LENS: GPU time, video memory and hitching of version 2 on E3DS's machines (RTX 4080 16 GB or RTX 5070 12 GB, one app per machine, the GPU shared with NVENC video encoding; E3DS asks for 4 to 6 GB GPU memory and 50 to 70 % GPU use). Our measurements come from an RTX PRO 6000 Blackwell (96 GB), a much faster card. Check:
- Measured numbers in the version-2 run logs on the box (/project/ue/cloud/repro/*/game.log, for example w-mem, v-vram5000, v-vram6000, v-e3ds-7600: Vulkan memory dumps, "MIDemo: frame" lines, the [MICloud] Features line, any stat output) and the cloud settings ([MICloud] in unreal/MurderInc/Config/DefaultGame.ini, MICloud.cpp, DefaultScalability.ini, DefaultEngine.ini). Estimate frame time and GPU memory on a 5070 and a 4080 at 1920x1080, 2560x1440 and 3840x2160 (Browser Resolution Dynamic), and say how sure you are and why.
- Shader and PSO hitching: every Linux session is a fresh machine with a freshly unpacked zip, so no pipeline cache survives between sessions. Check the project's PSO precaching settings (r.PSOPrecaching, r.PSOPrecache.*, a bundled PSO cache: look in the staged build for *.upipelinecache, *.stablepc.csv or shader pipeline cache files), whether the title and loadout screens give precaching time before play, and where the Vulkan pipeline cache goes under Saved/. Propose the cheapest effective measures.
- E3DS's optimisation advice (find the optimise / frame-rate / articles-optimization pages) versus our settings: t.MaxFPS 60, VSync, screen percentage and TSR, Lumen and shadow settings. Recommend specific, low-risk cvar changes for a version 3 with the expected gain, and say plainly what the player would lose visually for each (the owner cares a lot about next-gen visuals).`,
  },
  {
    key: 'website-and-launch',
    prompt: `YOUR LENS: the IPX Game OS page that embeds the stream (built by Cursor from docs/CURSOR_HANDOFF.md and docs/LAUNCH.md section 5) and everything the owner must set or know before making it public. Check against E3DS's docs (embed-stream-into-webpage, embed-stream-using-iframe, iframe-or-web-sdk, embed-with-the-web-sdk, embed-stream-using-e3ds-sdk, iframe-loading-video, device-ids-across-the-iframe, device-detection, login-in-front-of-a-stream, session-and-access, the features-api pages (fullscreen, live-connection-state, end-session, extend-session-time, mouse-mode, volume), branding-and-hosting, network-requirements) and the web platform's rules:
- The iframe: the exact allow attributes E3DS recommends; pointer lock and fullscreen inside a cross-origin iframe; the site's Content-Security-Policy frame-src (a Linux link is on connector_linux.eagle3dstreaming.com, and an underscore is not allowed in a CSP host-source: check what actually works, for example https://*.eagle3dstreaming.com, against the CSP Level 3 host-matching algorithm); Permissions-Policy headers on the site that could block fullscreen, autoplay or pointer lock; sandbox attributes; a Play button that loads the iframe only on click; keeping the inactivity countdown visible; reacting to the session ending (does E3DS post messages to the parent page?); mobile and touch visitors (keyboard and mouse needed); Safari and Firefox; focus.
- Access while testing (password) and how it looks in an iframe.
- Costs and capacity: Core plan 300 minutes a month and 10 CCU (verify current plans, prices and the price of extra minutes on www.eagle3dstreaming.com); how minutes are counted (docs: minutes); what 300 minutes means for a public page (sessions a month at 15 and at 30 minutes); the CCU-limit queue; settings that protect minutes (max session time, inactivity logout, the Play button, password, region).
- Write the corrected, complete text for the "Prompt to paste into Cursor" section of docs/CURSOR_HANDOFF.md for version 2. The owner downloads, joins and uploads the build themselves, so Cursor only builds and deploys the page; if it mentions the build at all: 9 parts, joined sha256 82ed886a3fb508a96ce6ac0e7c4a4c3b61f0563872e9d9cdc25249817d92ee8a, 2,254,911,244 bytes. Include every website fix above. Put that text in a finding's fix field (fix_kind website).`,
  },
]

const verifyPrompt = (lensKey, findings) => `You are an adversarial reviewer. Below are findings from a colleague's "${lensKey}" review of MURDER INC. version 2 on E3DS. For each finding of severity blocker, high or medium: try hard to REFUTE it from primary evidence (the E3DS page itself, the engine source on the box, repo files, box logs; read them yourself, do not trust the quotes). Default to "uncertain" when the evidence is thin, and say what would settle it. Re-rate severity honestly with the scale above. Check that each proposed fix is correct and minimal, and give the corrected fix (or repeat it if it is right). For low-severity findings, confirm them unless they are plainly wrong.

FINDINGS (JSON):
${JSON.stringify(findings, null, 1)}`

const results = await pipeline(
  LENSES,
  l => agent(CONTEXT + '\n' + l.prompt, { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }),
  (review, l) => {
    if (!review) return null
    if (!review.findings.length) return { lens: l.key, review, verdicts: [] }
    return agent(CONTEXT + '\n' + verifyPrompt(l.key, review.findings), { label: `verify:${l.key}`, phase: 'Verify', schema: VERDICTS })
      .then(v => ({ lens: l.key, review, verdicts: v ? v.verdicts : null }))
  },
)

const merged = results.filter(Boolean)
const missing = LENSES.map(l => l.key).filter(k => !merged.find(m => m.lens === k))
if (missing.length) log(`lenses with no result: ${missing.join(', ')}`)

phase('Decide')
const decision = await agent(CONTEXT + `
You are the release lead. Merge the verified findings of the four reviews below (each finding has the reviewer's verdict; a null verdicts list means the verification step failed, so treat those findings as unverified) into one decision document. Leave out refuted findings (list each in "refuted" with one line on why). Where reviewers disagree, decide and say why.

Write docs/unreal/PREFLIGHT.md (a NEW file; you may create only this file; plain English, short sentences; for the owner and the next engineer; no download links, no email addresses, no account names, no person's names) with these sections:
1. For the version 2 test (now): the exact E3DS settings to set, in Control Panel order, what to watch for during the test, and what to send back.
2. Version 3: the must-fix list. Only changes worth a rebuild, each with the exact file and change, the build cost, and what the player gains and loses.
3. The website (Cursor): the complete replacement text for the "Prompt to paste into Cursor" section of docs/CURSOR_HANDOFF.md.
4. Before going public: plan, minutes, capacity, settings, notes for the page.
5. Corrections our docs need (docs/LAUNCH.md section and the wrong sentence; do not edit LAUNCH.md yourself, another agent is editing it).
6. What we cannot know until the E3DS test, and how the test will tell us.
7. Checked and fine (one line each).
Do not commit. Return the structured summary; summary_for_owner is at most 8 short plain-English sentences.

REVIEWS (JSON):
${JSON.stringify(merged, null, 1)}`, { label: 'decide', phase: 'Decide', schema: DECISION })

return { decision, lenses: merged.map(m => ({ lens: m.lens, findings: m.review.findings.length, verdicts: m.verdicts ? m.verdicts.length : null })) }
