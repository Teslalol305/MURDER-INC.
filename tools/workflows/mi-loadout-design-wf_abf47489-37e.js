export const meta = {
  name: 'mi-loadout-design',
  description: 'Design the new front end the user asked for: pick a character, pick a four-gun loadout with weapon attachments, pick the level and the game style; written as a spec with data schemas, checked by two independent critics',
  phases: [
    { title: 'Design', detail: 'docs/unreal/LOADOUT.md and the data files: roster, attachments, characters, levels, modes, screens' },
    { title: 'Critique', detail: 'two independent reviews: rules and code fit; content and player experience' },
    { title: 'Revise', detail: 'the design revised against the critiques' },
  ],
}
const CONTEXT = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter (three.js; "an IPX production starring Ja Rule"; Hollis, Queens) owned by the user, which is being REBUILT in Unreal Engine 5.9 with photoreal graphics. The web game (src/, docs/DESIGN.md) has one player character seen only as arms ("Rule"), two guns (the CHOPPER, an AK-pattern carbine, and the NINE, a 9 mm pistol) plus melee, one level (the block under the El) and two modes (Story: collect three master reels and extract; Hold the Block: waves). The Unreal port so far reproduces those rules exactly and proves it with golden-value tests: docs/unreal/GAMEPLAY.md (contracts as built), unreal/MurderInc/Source/MurderInc (Weapons, Player, Flow, Core/Data), unreal/MurderInc/Content/Data/*.json (config, text, level, presentation), docs/unreal/spec/02-weapons-combat.md, 03-enemies.md, 04-flow.md, 07-ui-audio.md. A gameplay agent is writing enemies and the game flow in C++ right now (do not edit Source/ or Content/Data files that exist; you write a design and NEW data files only).

THE USER'S NEW REQUEST (verbatim): "include all the guns and animations in the sprite pack i downloaded as load out options where a user can pick 4 guns to carry into the game from the home screen. the flow should be. Pick a charachter-pick load out and add weapon attachments then pick level and game style"

WHAT THE PACK IS: the user bought the "Tactical FPS Animation Pack - Assault Rifle" (Infima Games). It holds ONE rifle, an M4-style carbine, in three handguard lengths (Short, Default, Extended; each with the stock folded or open), with attachments: angled grip, vertical grip, laser, scope, folding front and rear iron sights, silencer, and a standard or a transparent magazine; first-person clips: fire (semi, auto, aimed, empty), fire-mode switch, reload (normal, quick, empty, empty-retain, each also aimed), magazine check, three jam clearances, inspect, grip change, melee (bash, two swings), quick grenade throw, heal with a syringe, equip, quick equip, holster, aim and crouch transitions, trigger discipline poses, locomotion and poses; matching third-person clips; weapon-part clips. An animation agent is importing it onto the UE5 mannequin skeleton and adapting the reloads to the CHOPPER (its mapping will be docs/unreal/ANIMATION.md). The pack may be used in the game but its files are never committed (public repository).
WHAT ELSE EXISTS AS ART: SK_Chopper and SK_Nine with moving parts (being rebuilt to a higher standard), the enemy's SM_Weapon_GoonSMG and pipe, the player's arms SK_RuleArms (in progress), three masked Goons (in progress), the Buzzard drone, eleven vehicles, the street.`

const DESIGN = CONTEXT + `

ROLE: lead game designer and UI architect for the port. YOUR TASK: write docs/unreal/LOADOUT.md, the design an engineer will implement next, plus the new data files it defines under unreal/MurderInc/Content/Data/ (new files only: loadout.json or several, as you decide), so that everything is data and adding a gun later is adding entries.
Decisions the project lead has already made (design to them; list anything you disagree with under open questions, with your recommendation):
- Flow from the home screen: character, then loadout with attachments, then level, then game style (and difficulty), then the briefing and play. Back is always possible; the last choices are remembered; a quick "play again with the same set-up" exists.
- The player carries FOUR guns (number keys, wheel, gamepad) plus melee. The roster today is four: the CHOPPER, the NINE, the pack's carbine (give it a name in the game's own voice: read text.json for the tone; no real makes or model names) and a player version of the Goon's submachine gun. The design must work for a roster larger than four (the user may buy more packs of the same series: each would bring one gun with the same clip set), with a clear screen for choosing four from many and ordering them.
- Attachments by slot (optic, muzzle, underbarrel, laser, magazine, handguard or barrel, stock) with a per-gun compatibility table; today's parts are the pack's, usable on the pack's carbine and, where a mount exists on our own models (the CHOPPER has a short top rail and a muzzle device; the NINE has an accessory rail), on those too. Every attachment has a modest, legible rule effect taken from data (for example: scope changes the aimed field of view and aim time; silencer shrinks the distance at which enemies hear a shot and the muzzle flash, and softens damage at range; grips trade recoil against handling; laser tightens hip fire; handguard length trades handling against recoil and range), with costs so there is no best build.
- PARITY: the default set-up (Rule, CHOPPER and NINE with no attachments, the block, Story or Hold the Block) must play exactly as the web game does, so the existing golden-value tests still hold; everything new is an addition on top.
- Characters: a data-driven roster. Today the only art is Rule's arms; propose three more crew members as variations the character artist can build on the same arms (glove, sleeve, skin, jewellery), cosmetic only unless you argue for small perks. Names and looks are placeholders for the user to replace; never a real person's likeness.
- Levels: one today (the block); the screen shows it and is built for more. Game styles: Story and Hold the Block, with what each needs from a level.
- The pack's extra clips: say which become features (inspect, magazine check, fire-mode switch between semi and auto, melee with the gun) and which are left out for now and why (jams, syringe heal, grenade), since the web game has regeneration and no grenades.
The document must contain: the flow as a state diagram with every screen (what it shows, a 3D preview of the character and of the gun on a turntable with attachments appearing as they are chosen, inputs for mouse, keyboard and gamepad, the texts with keys for text.json); the data schemas with a complete first version of the data (the four guns with all rule numbers: for the two new guns derive them from the CHOPPER's and the enemy SMG's numbers in config.json and say how; every attachment with effects; characters; levels; modes); how four carried guns change the rules as built (slots, swap timing, ammunition, HUD, the weapon wheel) with the exact classes of GAMEPLAY.md that change; the art and animation each gun, attachment and character needs (meshes, sockets for each attachment slot, clip per state, by reference to ANIMATION.md's naming), marked exists / in progress / missing; save data; tests (parity of the default set-up; one automation test per attachment effect; a scripted walk through the whole flow); and a short list of open questions for the user, each with a default that work proceeds on.
Aim for a document an engineer can implement from without asking questions, readable in 30 minutes. Commit your files: git add with explicit paths (docs/unreal/LOADOUT.md and your new data files), never git add -A, git commit, git push -u origin claude/tender-albattani-5q78qr; end the commit message with exactly these two lines and no model name elsewhere:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4

Reply through the structured output: summary (at most 200 words), files, roster (the four guns with their names), open_questions (each with its default).`
const D_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, roster: { type: 'array', items: { type: 'string' } }, open_questions: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'files', 'open_questions'] }

phase('Design')
const d = await agent(DESIGN, { label: 'loadout:design', phase: 'Design', schema: D_SCHEMA, effort: 'high', model: 'opus' })
if (!d) return { design: null }

const LENSES = [
  { key: 'rules', text: 'Lens: rules and code. Check the design against the code and contracts as they are (docs/unreal/GAMEPLAY.md, Source/MurderInc/Weapons, Player, Flow, Core/Data, the golden tests under Tests/ and Content/Data/golden): does the default set-up provably stay identical to the web game; do the data schemas load with the existing data subsystem pattern; are the derived numbers of the two new guns and every attachment effect well defined (units, where in the fire, spread, recoil, aim and hearing formulas of spec 02 and 03 each one applies, order of combination, clamps); is anything exploitable or strictly dominant; what in four-slot carrying conflicts with the weapon state machine, swap timing, ammunition and HUD as built; are the tests enough.' },
  { key: 'experience', text: 'Lens: player experience and content. Walk through the flow as a player with a mouse and as a player with a gamepad: number of steps to start a match the first time and the tenth time, clarity of choosing four from a roster of four today and of twelve later, attachment screens, previews, back and cancel, defaults, remembered choices, text tone against text.json. Then check feasibility against the art and animation that exist or are in progress (the pack inventory above, docs/unreal/ANIMATION.md if present, art/blender/PROGRESS.md): every gun, attachment mount, character variant and clip the design relies on, marked exists, in progress or missing; what the design promises that nothing can deliver yet; where our own guns lack a mount the design assumes.' },
]
const C_SCHEMA = { type: 'object', properties: { verdict: { type: 'string' }, problems: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, problem: { type: 'string' }, severity: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'problem', 'fix'] } } }, required: ['verdict', 'problems'] }
const crits = (await parallel(LENSES.map(l => () => agent(CONTEXT + `

ROLE: an independent reviewer who did not write the design. Read docs/unreal/LOADOUT.md and the new data files it names (` + (d.files || []).join(', ') + `). Do not edit anything. ` + l.text + `
Report real problems only, most serious first, each with where it is in the document or data, what is wrong, severity (blocker, major, minor) and a concrete fix. Reply through the structured output: verdict (at most 80 words), problems.`, { label: 'loadout:critic-' + l.key, phase: 'Critique', schema: C_SCHEMA, effort: 'high', model: 'opus' })))).filter(Boolean)

phase('Revise')
const problems = crits.flatMap(c => c.problems)
log(problems.length + ' problems from ' + crits.length + ' critics')
const r = await agent(CONTEXT + `

ROLE: the designer of docs/unreal/LOADOUT.md. Two independent reviewers found these problems:
` + JSON.stringify(problems, null, 1) + `
Revise the document and its data files: fix every blocker and major problem (or say precisely why one is not a problem), fix the minor ones that cost little, keep the document readable in 30 minutes. Re-check that every number in the data is consistent with the text. Commit and push your files as before (explicit paths, the same two trailer lines:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4).
Reply through the structured output: summary (at most 200 words), files, roster, open_questions (each with its default).`, { label: 'loadout:revise', phase: 'Revise', schema: D_SCHEMA, effort: 'high', model: 'opus' })
return { design: r || d, critic_verdicts: crits.map(c => c.verdict), problems_found: problems.length }
