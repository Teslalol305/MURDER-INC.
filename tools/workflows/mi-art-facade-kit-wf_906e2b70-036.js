export const meta = {
  name: 'mi-art-facade-kit',
  description: 'Build the modular New York facade kit in Blender (storefronts, brick upper floors, cornices, fire escapes) and a sample block face under the El',
  phases: [
    { title: 'Facade kit', detail: 'modules on scanned tiling sets, sample building, look-dev renders, GLB export' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'

const PROMPT = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts and exported as GLB for Unreal. Setting: Hollis, Queens: Jamaica Avenue under a riveted steel elevated train line, a hot clear summer afternoon by default.',
  'The user pays for every token: work efficiently, read selectively, do not polish beyond the task. Final look development happens later in Unreal; Blender renders are sanity checks. What matters: correct, detailed, well-UV-mapped modular geometry with sensible material slots, exported and validated.',
  '',
  'START HERE: read art/blender/README.md and art/blender/PROGRESS.md (the pipeline: library art/blender/mi/, command line art/blender/build.py, families art/blender/assets/street.py and el.py, scan-backed materials from the catalogue art/scans/sets.json with textures in art/out/textures/, HDRI day rig) and look at art/previews/el_day_hero.jpg to see the current state: the El and the street are built, but the buildings behind them are blank placeholder walls. Your job is to replace that massing with real architecture. Follow the conventions in the README exactly (axes, pivots, names, tiling sets with world-scale UVs and vertex-colour wear masks, outputs).',
  'What to build is specified in docs/unreal/spec/05-level.md (the buildings and storefronts sections: footprints, heights, storeys, facade styles, storefront names, awnings, signs, fire escapes, roof items) and the architecture briefs in docs/unreal/spec/assets/level.json; the quality bar and real-world dimensions are in docs/unreal/ART_BIBLE.md (modelling bar and material sections). Read those parts, not the whole documents.',
  '',
  'ENVIRONMENT: Python with Blender 5.3.0 as a module: ' + PY + ' (import bpy). CPU only, 4 shared cores: Cycles on CPU with 3 threads, renders at most 1280x720 and 64 samples, at most about 8 renders in total. Check the running bpy module instead of trusting memory. No internet except art/scans/fetch.py for catalogued Poly Haven files. Write only under art/. Do not commit or push. Look at every image you render.',
  '',
  'YOUR TASK: the family art/blender/assets/facade.py, a modular kit from which every street-facing building of the block can be assembled by a level script, on the module widths and storey heights the level spec implies:',
  '- Ground floor: storefront bay with glazed shopfront, bulkhead and recessed door; roll-down security gate bay (gate closed, slats modelled, with guide rails, hood box and padlock hasp); narrow residential entrance bay with door, transom and stoop step; sign band / fascia that takes a sign texture later (leave a named material slot M_Sign_<Slot> with 0..1 UVs); fabric awning with frame (two widths); pier.',
  '- Upper floors: brick bay with double-hung window (frame, sashes, glass, stone or brick lintel, projecting sill), blank brick bay, corner return, air-conditioner unit as a separate prop.',
  '- Top and sides: cornice run and end (pressed-metal profile with brackets), parapet with coping, party-wall cap, flat roof panel, rooftop water tank on a steel frame, stair bulkhead.',
  '- Fire escape as its own modules: balcony with railing, drop ladder, stair flight between balconies, wall brackets.',
  '- Brick in at least three scanned variants per the catalogue (red, brown, painted), mortar at real scale, soot and rain streaks through the wear masks; glass as a proper glass slot; metal trim painted.',
  '- An assembly helper and one sample: assemble the block face named in the level spec that stands behind the El on the north or south side (pick the one with the most storefronts) from the modules, place it with the street and three El bays, and render: facade_day_hero.jpg (eye level from the opposite sidewalk), facade_day_street.jpg (looking along the avenue under the El with the buildings on one side), facade_storefront.jpg (one storefront close, at eye level), facade_wire.jpg (clay or wireframe). Two self-review rounds at most.',
  '- Export every module as GLB, update the manifest, run the export validation, add the family to the README and update art/blender/PROGRESS.md as you go (you may be cut off without warning: keep files runnable after each step).',
  '',
  'Reply through the structured output: summary (at most 150 words), files, previews, assets (exported SM_ names with triangle counts), known_weaknesses (honest, most visible first).',
].join('\n')

const SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' } },
    assets: { type: 'array', items: { type: 'string' } },
    known_weaknesses: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'previews', 'known_weaknesses'],
}

phase('Facade kit')
// Second start: the first run was cut off by the usage limit after ten minutes. The user asked for
// the background agents to run on Opus.
const STATE = '\n\nSTATE NOTE: an earlier run of this exact task was cut off by a usage limit after about ten minutes. It wrote its plan and a checklist into art/blender/PROGRESS.md (section "Facade kit") and may have left a partial art/blender/assets/facade.py. Review what is there and continue from it; do not start over.'
return await agent(PROMPT + STATE, { label: 'art:facade-kit', phase: 'Facade kit', schema: SCHEMA, effort: 'high', model: 'opus' })
