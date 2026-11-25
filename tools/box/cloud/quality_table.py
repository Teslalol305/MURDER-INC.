#!/usr/bin/env python3
"""Release 3c, the quality ladder, step L1: what does each setting buy, in GPU time, and what does it cost in looks?

The Development game plays a script of its demo director (Source/MurderInc/Flow/MIDemoDirector.cpp) in a Story run at a fixed
render scale (r.ScreenPercentage 50, dynamic resolution off) with the frame-rate target fixed at 60, standing in a scene. One
variant at a time it sets a few console variables, waits for the picture to settle, measures the GPU's time for a few seconds,
puts the variables back, and measures again (the baseline next to it). A viewer (rtcinput.py) saves a frame every few seconds,
so that each variant can be LOOKED at as the stream delivers it. The game's own log (the probe lines every 0.2 s, the demo's
"line N" markers, both with the engine's time stamps) is matched to the script by time.

  quality_table.py names                        every console variable the variants touch, one per line
  quality_table.py gen-probe <dir>              <dir>/play.txt: reads every one of them back (the baselines)
  quality_table.py baseline <game.log> <out>    the values the probe run printed, as JSON
  quality_table.py gen <dir> <baseline.json> [scenes=street,garage] [only=<label,label>]
                                                <dir>/play.txt (the game's script), view.txt (the viewer's), labels.json
  quality_table.py gen-steps <dir> <n> [scenes=]   the ladder walked: step 1 to n and back, with MI.Cloud.QualityStep (the new game)
  quality_table.py frames <dir> [label,label]   the received frame at the end of each variant's measuring window and the baseline's
  quality_table.py sum <dir> [csv]              the table: for every variant, the GPU time next to the baseline's, the saving,
                                                the longest frame in the first 1.5 s after the change, and the frame to look at

How the runs are started (tools/box/cloud/lag-test.sh, the Development game of a test folder, E3DS's own shader platform):
  lag-test.sh run q-street game=dev demo=<dir>/play.txt view=<dir>/view.txt join=3 probe=0.2 secs=<n> profile=1 -- -sm5 -MIFps=60
"""
import collections
import datetime
import json
import os
import re
import statistics
import sys

# ---- what is measured ----------------------------------------------------------------------------------------------------
# (label, [(variable, value), ...], what it is). The first three of each family are the scalability group at 2 and 1 (the
# levels the ladder of version 3 meant to use) and then the single variables that group sets, one at a time.
V = []


def add(label, cvars, note=''):
    V.append((label, cvars, note))


for grp, name in (('shadow', 'sg.ShadowQuality'), ('gi', 'sg.GlobalIlluminationQuality'), ('refl', 'sg.ReflectionQuality'),
                  ('post', 'sg.PostProcessQuality'), ('fx', 'sg.EffectsQuality'), ('viewdist', 'sg.ViewDistanceQuality'),
                  ('shading', 'sg.ShadingQuality')):
    for lv in (2, 1):
        add('%s %d' % (grp, lv), [(name, str(lv))], 'scalability group, level %d' % lv)
# Lumen (E3DS's card has no Nanite and no hardware ray tracing: software Lumen)
add('lumen probes /32', [('r.Lumen.ScreenProbeGather.DownsampleFactor', '32')], 'one screen probe per 32 pixels, not 16')
add('lumen octa 6', [('r.Lumen.ScreenProbeGather.TracingOctahedronResolution', '6')], 'fewer rays per probe (8 -> 6)')
add('lumen octa 4', [('r.Lumen.ScreenProbeGather.TracingOctahedronResolution', '4')], 'fewer rays per probe (8 -> 4)')
add('lumen adaptive 0', [('r.Lumen.ScreenProbeGather.NumAdaptiveProbes', '0')], 'no extra probes at edges')
add('lumen AO off', [('r.Lumen.ScreenProbeGather.ShortRangeAO', '0')], 'no short-range ambient occlusion')
add('lumen AO half', [('r.Lumen.ScreenProbeGather.ShortRangeAO.DownsampleFactor', '2')], 'ambient occlusion at half resolution')
add('lumen screen traces off', [('r.Lumen.ScreenProbeGather.ScreenTraces', '0')], 'no screen-space traces for the probes')
add('lumen stochastic', [('r.Lumen.ScreenProbeGather.StochasticInterpolation', '1')], 'stochastic probe interpolation')
add('lumen mesh SDFs off', [('r.Lumen.TraceMeshSDFs', '0')], 'only the global distance field is traced')
add('lumen reflections off', [('r.Lumen.Reflections.Allow', '0')], 'no Lumen reflections (screen-space reflections stay)')
add('lumen reflections /4', [('r.Lumen.Reflections.DownsampleFactor', '4')], 'reflections at a quarter of the pixels (cloud profile: half)')
add('lumen reflections rough 0.15', [('r.Lumen.Reflections.MaxRoughnessToTrace', '0.15')], 'only the glossiest surfaces reflect (cloud profile: 0.4)')
add('lumen surface light x2', [('r.LumenScene.DirectLighting.UpdateFactor', '128'), ('r.LumenScene.Radiosity.UpdateFactor', '256')], 'the surface cache updates half as often')
add('lumen radiosity off', [('r.LumenScene.Radiosity', '0')], 'no bounce light in the surface cache')
add('lumen max trace 5000', [('r.Lumen.MaxTraceDistance', '5000')], 'rays stop at 50 m')
add('lumen max trace 2500', [('r.Lumen.MaxTraceDistance', '2500')], 'rays stop at 25 m')
add('lumen translucency 128', [('r.Lumen.TranslucencyVolume.GridPixelSize', '128')], 'a coarser lighting volume for translucent surfaces')
add('lumen off', [('r.DynamicGlobalIlluminationMethod', '0')], 'no global illumination at all (the bound, not a step)')
# fog, anti-aliasing
add('fog off', [('r.VolumetricFog', '0')], 'no volumetric fog')
add('fog grid 24', [('r.VolumetricFog.GridPixelSize', '24')], 'a coarser fog grid (16 -> 24)')
add('fog grid 32 z32', [('r.VolumetricFog.GridPixelSize', '32'), ('r.VolumetricFog.GridSizeZ', '32')], 'the coarsest fog grid the viewer allowlist lets through')
add('aa TAA', [('r.AntiAliasingMethod', '2')], 'temporal anti-aliasing instead of Temporal Super Resolution')
add('aa FXAA', [('r.AntiAliasingMethod', '1')], 'FXAA instead of Temporal Super Resolution')
add('tsr update 2', [('r.TSR.History.UpdateQuality', '2')], 'cheaper history update')
add('tsr update 1', [('r.TSR.History.UpdateQuality', '1')], 'cheapest history update')
add('tsr reject 1', [('r.TSR.RejectionAntiAliasingQuality', '1')], 'cheaper rejection anti-aliasing')
add('tsr flicker off', [('r.TSR.ShadingRejection.Flickering', '0')], 'no flicker detection')
add('tsr history 50', [('r.TSR.History.ScreenPercentage', '50')], 'the history at the drawn size, not the output size')
# virtual shadow maps
add('vsm pages 1024', [('r.Shadow.Virtual.MaxPhysicalPages', '1024')], 'half the shadow page pool (cloud profile: 2048)')
add('vsm pages 512', [('r.Shadow.Virtual.MaxPhysicalPages', '512')], 'a quarter of the shadow page pool')
add('vsm lod +1', [('r.Shadow.Virtual.ResolutionLodBiasDirectional', '1.0'), ('r.Shadow.Virtual.ResolutionLodBiasDirectionalMoving', '1.0')], 'sun shadows at half resolution')
add('vsm lod +2', [('r.Shadow.Virtual.ResolutionLodBiasDirectional', '2.0'), ('r.Shadow.Virtual.ResolutionLodBiasDirectionalMoving', '2.0')], 'sun shadows at a quarter of the resolution')
add('vsm local lod +1', [('r.Shadow.Virtual.ResolutionLodBiasLocal', '1.0'), ('r.Shadow.Virtual.ResolutionLodBiasLocalMoving', '2.0')], 'lamp shadows at half resolution')
add('vsm smrt 4/2', [('r.Shadow.Virtual.SMRT.RayCountDirectional', '4'), ('r.Shadow.Virtual.SMRT.SamplesPerRayDirectional', '2'), ('r.Shadow.Virtual.SMRT.RayCountLocal', '2')], 'fewer shadow rays (softer penumbra, more noise)')
add('vsm smrt 2/1', [('r.Shadow.Virtual.SMRT.RayCountDirectional', '2'), ('r.Shadow.Virtual.SMRT.SamplesPerRayDirectional', '1'), ('r.Shadow.Virtual.SMRT.RayCountLocal', '1')], 'the fewest shadow rays')
add('vsm off', [('r.Shadow.Virtual.Enable', '0')], 'cascaded shadow maps instead (the bound, not a step)')
# post effects
add('dof off', [('r.DepthOfFieldQuality', '0')], 'no depth of field')
add('bloom 1', [('r.BloomQuality', '1')], 'the cheapest bloom')
add('ssr off', [('r.SSR.Quality', '0')], 'no screen-space reflections')
add('lightshafts off', [('r.LightShaftQuality', '0')], 'no light shafts')
add('tonemapper 2', [('r.Tonemapper.Quality', '2')], 'a simpler tone mapper')
add('clouds off', [('r.VolumetricCloud', '0')], 'no volumetric clouds')
add('sky samples 32', [('r.SkyAtmosphere.SampleCountMax', '32'), ('r.SkyAtmosphere.FastSkyLUT.SampleCountMax', '32')], 'a cheaper sky')
add('niagara 1', [('fx.Niagara.QualityLevel', '1')], 'cheaper particles')
add('translucency lighting', [('r.TranslucencyLightingVolume.Dim', '32')], 'a smaller translucency lighting volume')

# Round 2 (after the first round's GPU profile of the street scene, 'ProfileGPU': 3.8 ms on the graphics queue, of which volumetric cloud
# shadow 0.55 ms, shadow depths 0.50 ms (one 8192 x 2048 atlas of cascaded and local shadow maps: the SM5 game has no Nanite, and its
# shadows are not the virtual ones), cloud reconstruction and the sky capture 0.4 ms, post processing 0.42 ms; and 1.2 ms on the compute
# queue, Lumen's scene lighting and screen probe gather).
add('cloud shadow off', [('r.VolumetricCloud.ShadowMap', '0')], 'clouds cast no shadows on the ground')
add('cloud shadow 1024', [('r.VolumetricCloud.ShadowMap.MaxResolution', '1024')], 'the cloud shadow map at 1024 (default 2048?)')
add('cloud shadow rays 16', [('r.VolumetricCloud.ShadowMap.RaySampleMaxCount', '16')], 'fewer samples for the cloud shadow map')
add('cloud view rays 128', [('r.VolumetricCloud.ViewRaySampleMaxCount', '128')], 'fewer samples along the view ray through the clouds')
add('cloud skyAO off', [('r.VolumetricCloud.SkyAO', '0')], 'no sky occlusion from the clouds')
add('cloud distant skylight off', [('r.VolumetricCloud.EnableDistantSkyLightSampling', '0')], 'no distant sky light sampling in the clouds')
add('cloud lights off', [('r.VolumetricCloud.EnableLocalLightsSampling', '0'), ('r.VolumetricCloud.EnableAtmosphericLightsSampling', '0')], 'the clouds are not lit by lamps')
add('shadow res 1024', [('r.Shadow.MaxResolution', '1024'), ('r.Shadow.MaxCSMResolution', '1024')], 'shadow maps at 1024 (cloud profile: 2048)')
add('shadow csm 2', [('r.Shadow.CSM.MaxCascades', '2')], 'two sun shadow cascades (default 10 at level 3)')
add('shadow csm 3', [('r.Shadow.CSM.MaxCascades', '3')], 'three sun shadow cascades')
add('shadow dist 0.7', [('r.Shadow.DistanceScale', '0.7')], 'shadows fade out sooner')
add('shadow radius 0.06', [('r.Shadow.RadiusThreshold', '0.06')], 'small things cast no shadow')
add('shadow filter 3', [('r.ShadowQuality', '3')], 'fewer shadow filter taps')
add('shadow preshadow 0.5', [('r.Shadow.PreShadowResolutionFactor', '0.5')], 'half-size per-object shadows')
add('dfshadow off', [('r.DistanceFieldShadowing', '0')], 'no distance field shadows')
add('capsule off', [('r.CapsuleShadows', '0')], 'no capsule shadows')
add('skylight capture slice', [('r.SkyLight.RealTimeReflectionCapture.TimeSlice', '1')], 'the real-time sky capture in slices')
add('skylight capture off', [('r.SkyLight.RealTimeReflectionCapture', '0')], 'no real-time sky capture (the sky light keeps its last capture)')
add('res 1600x900', [('r.SetRes', '1600x900')], 'the OUTPUT size 1600 x 900 (the video is smaller; the browser stretches it)')
add('res 1280x720', [('r.SetRes', '1280x720')], 'the OUTPUT size 1280 x 720')
EXTRA_BASE = {'r.SetRes': '1920x1080'}

NAMES = []
for _l, cv, _n in V:
    for n, _v in cv:
        if n not in NAMES:
            NAMES.append(n)
NAMES += ['r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod', 'r.AntiAliasingMethod', 'r.ScreenPercentage', 'sg.TextureQuality',
          'r.Nanite', 'r.Shadow.Virtual.Enable', 'r.RayTracing', 'r.Lumen.HardwareRayTracing', 't.MaxFPS', 'r.DynamicRes.OperationMode']
NAMES = [n for n in dict.fromkeys(NAMES) if n != 'r.SetRes']

# ---- the scenes -----------------------------------------------------------------------------------------------------------
# Each scene is the demo director's lines that bring the player there and look at something that costs the GPU. (x, y in cm.)
SCENES = {
    # the first room of a Story run, standing where it begins
    'start': ['wait 1'],
    # the avenue under the elevated line, looking down it: sun, shadows of the El, shop windows, vehicles
    'street': ['spring 1.3 110 1.7', 'route 1 -3725 875 -3475 875 -3175 675 -2775 525 -2775 425', 'wait 1.5', 'face point -1500 150 300', 'wait 2.5'],
    # indoors by the last reel: lamps and a small room
    'garage': ['goto -490 130', 'lookat -400 100 60 1.5', 'wait 2'],
}

SETTLE, MEASURE, RESTORE_SETTLE, BASE = 3.5, 4.0, 2.5, 3.0
if os.environ.get('Q_MEASURE'):
    MEASURE = float(os.environ['Q_MEASURE'])
HITCH_WINDOW = 1.5
FRAME_EVERY = 3.0


def fmt_cmd(c):
    return 'con %s %s' % (c[0], c[1])


def gen_probe(out):
    os.makedirs(out, exist_ok=True)
    lines = ['wait 4', 'con MIStart mission skip', 'waitstate playing 40', 'god 1', 'wait 3']
    lines += ['con %s' % n for n in NAMES]
    lines += ['wait 2', 'quit']
    open(os.path.join(out, 'play.txt'), 'w').write('\n'.join(lines) + '\n')


def parse_ts(line):
    m = re.match(r'\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\]', line)
    if not m:
        return None
    y, mo, d, h, mi, s, ms = (int(x) for x in m.groups())
    return datetime.datetime(y, mo, d, h, mi, s, ms * 1000, tzinfo=datetime.timezone.utc).timestamp()


def baseline(log, out):
    vals = {}
    for line in open(log, errors='replace'):
        m = re.match(r'\[[^\]]*\]\[[^\]]*\](\S+) = "([^"]*)"', line)
        if m and m.group(1) in NAMES:
            vals[m.group(1)] = m.group(2)
    json.dump(vals, open(out, 'w'), indent=1, sort_keys=True)
    missing = [n for n in NAMES if n not in vals]
    print('%d of %d variables read back' % (len(vals), len(NAMES)))
    if missing:
        print('NOT FOUND (no such variable, or not printed): ' + ', '.join(missing))


def gen(out, base_file, scenes, only):
    base = json.load(open(base_file))
    for k, v in EXTRA_BASE.items():
        base.setdefault(k, v)
    os.makedirs(out, exist_ok=True)
    lines = ['wait 4', 'con MIStart mission skip', 'waitstate playing 40', 'god 1',
             'con r.DynamicRes.OperationMode 0', 'con r.ScreenPercentage 50', 'wait 6']
    labels = {}   # script line number -> (role, scene, variant)

    def put(text, role=None, scene=None, variant=None):
        lines.append(text)
        if role:
            labels[len(lines)] = [role, scene, variant]

    todo = [v for v in V if not only or v[0] in only]
    for scene in scenes:
        for ln in SCENES[scene]:
            put(ln)
        put('wait 3')
        put('wait %g' % BASE, 'base', scene, '')                # the scene's own baseline, before anything
        put('wait 0.1')
        for label, cvars, note in todo:
            missing = [c for c, _ in cvars if c not in base]
            if missing:
                continue                                            # no such variable in this build: nothing to measure
            for c in cvars:
                put(fmt_cmd(c), 'set', scene, label)
            put('wait %g' % SETTLE)
            put('wait %g' % MEASURE, 'measure', scene, label)
            put('wait 0.1')
            for c, _v in cvars:
                put('con %s %s' % (c, base[c]), 'restore', scene, label)
            put('wait %g' % RESTORE_SETTLE)
            put('wait %g' % BASE, 'base', scene, label)
            put('wait 0.1')
    put('wait 1')
    put('quit')
    open(os.path.join(out, 'play.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump({'labels': labels, 'variants': {l: {'cvars': c, 'note': nt} for l, c, nt in V}, 'baseline': base,
               'frame_every': FRAME_EVERY}, open(os.path.join(out, 'labels.json'), 'w'), indent=1)
    total = sum(float(re.match(r'wait ([\d.]+)', l).group(1)) for l in lines if l.startswith('wait '))
    # the viewer: click the card, then a frame every FRAME_EVERY seconds for as long as the game's script runs
    view = ['wait 3', 'click']
    count = int(total / FRAME_EVERY) + 4
    for i in range(count):
        view.append('frame f%04d.jpg' % i)
        view.append('wait %g' % (FRAME_EVERY - 0.2))
    open(os.path.join(out, 'view.txt'), 'w').write('\n'.join(view) + '\n')
    print('%d variants x %d scene(s): the script runs about %.0f s (%d lines)' % (len(todo), len(scenes), total, len(lines)))


def gen_steps(out, nsteps, scenes):
    """The ladder itself, walked: step 0 (the scene alone), then up one step at a time to the last, then down again, with the new
    binary's MI.Cloud.QualityStep (the step is pinned; the variables are applied exactly as the ladder applies them in play).
    Each step is measured for MEASURE seconds after SETTLE seconds. 'saves' in the table is against step 0 (the scene alone, before
    and after the walk); the hitch is the longest frame in the 1.5 s after the change."""
    os.makedirs(out, exist_ok=True)
    lines = ['wait 4', 'con MIStart mission skip', 'waitstate playing 40', 'god 1',
             'con r.DynamicRes.OperationMode 0', 'con r.ScreenPercentage 50', 'con MI.Cloud.QualityStep 0', 'wait 6']
    labels = {}

    def put(text, role=None, scene=None, variant=None):
        lines.append(text)
        if role:
            labels[len(lines)] = [role, scene, variant]

    seq = list(range(1, nsteps + 1)) + list(range(nsteps - 1, -1, -1))
    for scene in scenes:
        for ln in SCENES[scene]:
            put(ln)
        put('wait 3')
        put('wait %g' % MEASURE, 'base', scene, '')
        put('wait 0.1')
        for i, k in enumerate(seq):
            label = ('step %d' % k) if i < nsteps else ('back to %d' % k)
            if k == 0:
                put('con MI.Cloud.QualityStep 0', 'set', scene, 'back to 0')
                put('wait %g' % SETTLE)
                put('wait %g' % MEASURE, 'base', scene, 'back to 0')
                put('wait 0.1')
                continue
            put('con MI.Cloud.QualityStep %d' % k, 'set', scene, label)
            put('wait %g' % SETTLE)
            put('wait %g' % MEASURE, 'measure', scene, label)
            put('wait 0.1')
    put('wait 1')
    put('quit')
    open(os.path.join(out, 'play.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump({'labels': labels, 'variants': {}, 'baseline': {}, 'frame_every': FRAME_EVERY}, open(os.path.join(out, 'labels.json'), 'w'), indent=1)
    total = sum(float(re.match(r'wait ([\d.]+)', l).group(1)) for l in lines if l.startswith('wait '))
    view = ['wait 3', 'click']
    for i in range(int(total / FRAME_EVERY) + 4):
        view.append('frame f%04d.jpg' % i)
        view.append('wait %g' % (FRAME_EVERY - 0.2))
    open(os.path.join(out, 'view.txt'), 'w').write('\n'.join(view) + '\n')
    print('%d steps walked up and down in %d scene(s): about %.0f s' % (nsteps, len(scenes), total))


# What sets the lighting level's hitch: the variables of sg.GlobalIlluminationQuality 3 -> 1 (BaseScalability.ini), one group at a time,
# each set and put back REPS times (a change in play is one of these, in either direction).
HITCH = [
    ('gi group 1', [('sg.GlobalIlluminationQuality', '1', '3')]),
    ('gi atlas 2048', [('r.LumenScene.SurfaceCache.AtlasSize', '2048', '4096')]),
    ('gi cards', [('r.LumenScene.SurfaceCache.CardTexelDensityScale', '50', '100'), ('r.LumenScene.SurfaceCache.CardMaxResolution', '256', '512'),
                  ('r.LumenScene.SurfaceCache.CardClipSphereCulling.Radius', '2500', '0')]),
    ('gi final gather 0', [('r.Lumen.FinalGatherMethod', '0', '1')]),
    ('gi AO 1', [('r.AOQuality', '1', '2')]),
    ('gi surface light', [('r.LumenScene.DirectLighting.UpdateFactor', '128', '32'), ('r.LumenScene.Radiosity.UpdateFactor', '128', '64'),
                          ('r.LumenScene.DirectLighting.MaxLightsPerTile', '4', '8')]),
    ('shadow group 1', [('sg.ShadowQuality', '1', '3')]),
    ('shadow csm 3 + radius', [('r.Shadow.CSM.MaxCascades', '3', '10'), ('r.Shadow.RadiusThreshold', '0.06', '0.01')]),
    ('clouds off', [('r.VolumetricCloud', '0', '1')]),
    ('radiosity off', [('r.LumenScene.Radiosity', '0', '1')]),
    ('lumen reflections off', [('r.Lumen.Reflections.Allow', '0', '1')]),
]


def gen_hitch(out, reps, scenes):
    os.makedirs(out, exist_ok=True)
    lines = ['wait 4', 'con MIStart mission skip', 'waitstate playing 40', 'god 1',
             'con r.DynamicRes.OperationMode 0', 'con r.ScreenPercentage 50', 'con MI.Cloud.QualityStep 0', 'wait 6']
    labels = {}

    def put(text, role=None, scene=None, variant=None):
        lines.append(text)
        if role:
            labels[len(lines)] = [role, scene, variant]

    for scene in scenes:
        for ln in SCENES[scene]:
            put(ln)
        put('wait 3')
        for label, cv in HITCH:
            for r in range(reps):
                for c, v, _b in cv:
                    put('con %s %s' % (c, v), 'set', scene, label)
                put('wait 3')
                for c, _v, b in cv:
                    put('con %s %s' % (c, b), 'restore', scene, label)
                put('wait 3')
    put('wait 1')
    put('quit')
    open(os.path.join(out, 'play.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump({'labels': labels, 'variants': {}, 'baseline': {}}, open(os.path.join(out, 'labels.json'), 'w'), indent=1)
    view = ['wait 3', 'click', 'wait 20']
    print('%d variants x %d reps x %d scene(s)' % (len(HITCH), reps, len(scenes)))
    open(os.path.join(out, 'view.txt'), 'w').write('\n'.join(view) + '\n')


def sum_hitch(d):
    L = json.load(open(os.path.join(d, 'labels.json')))
    labels = {int(k): v for k, v in L['labels'].items()}
    P, M = probes(os.path.join(d, 'game.log')), markers(os.path.join(d, 'game.log'))
    byline = {}
    for t, ln, txt in M:
        byline.setdefault(ln, t)
    res = collections.OrderedDict()
    for ln in sorted(labels):
        role, scene, var = labels[ln]
        t0 = byline.get(ln)
        if t0 is None:
            continue
        ps = [p for p in P if t0 <= p[0] < t0 + HITCH_WINDOW]
        res.setdefault((scene, var), {'set': [], 'restore': []})[role].append(max([p[2] for p in ps] or [0.0]))
    print('%-8s %-26s %-32s %s' % ('scene', 'variant', 'set (ms, each repeat)', 'put back (ms, each repeat)'))
    for (scene, var), r in res.items():
        print('%-8s %-26s %-32s %s' % (scene, var, ' '.join('%4.0f' % x for x in r['set']), ' '.join('%4.0f' % x for x in r['restore'])))


def probes(log):
    out = []
    for line in open(log, errors='replace'):
        if 'MICloudProbe fps=' not in line:
            continue
        t = parse_ts(line)
        kv = dict(re.findall(r'(\w+)=(-?[\d.]+)', line))
        if t is None or 'gpuMs' not in kv:
            continue
        out.append((t, float(kv['gpuMs']), float(kv['worstMs']), float(kv.get('fps', 0)), float(kv.get('dr', 0)), kv))
    return out


def markers(log):
    out = []
    for line in open(log, errors='replace'):
        m = re.search(r'MIDemo: frame \d+ t [\d.]+: line (\d+): (.*)', line)
        if m:
            out.append((parse_ts(line), int(m.group(1)), m.group(2).strip()))
    return out


def summarize(d, csv=False):
    L = json.load(open(os.path.join(d, 'labels.json')))
    labels = {int(k): v for k, v in L['labels'].items()}
    log = os.path.join(d, 'game.log')
    P, M = probes(log), markers(log)
    byline = {}
    for t, ln, txt in M:
        byline.setdefault(ln, t)
    ends = sorted(byline.items())

    def window(ln):   # [start of line ln, start of the next line)
        t0 = byline.get(ln)
        nxt = [t for l, t in ends if l > ln]
        return (t0, nxt[0]) if t0 and nxt else (None, None)

    meas, hitch, bases, order = {}, {}, [], []
    for ln in sorted(labels):
        role, scene, var = labels[ln]
        t0, t1 = window(ln)
        if t0 is None:
            continue
        if role in ('measure', 'base'):
            ps = [p for p in P if t0 <= p[0] < t1]
            if not ps:
                continue
            if role == 'measure':
                meas[(scene, var)] = (t0, ps)
                order.append((scene, var))
            else:
                bases.append((t0, scene, var, ps))
        else:
            ps = [p for p in P if t0 <= p[0] < t0 + HITCH_WINDOW]
            hitch.setdefault((scene, var), {})[role] = max([p[2] for p in ps] or [0.0])
    mean = lambda ps: statistics.mean(p[1] for p in ps)
    out, scenes = [], []
    for scene, _v in order:
        if scene not in scenes:
            scenes.append(scene)
    for scene in scenes:
        alone = [b for b in bases if b[1] == scene and b[2] == '']
        if alone:
            print('\n== scene %s: the scene alone, before the first variant: %.2f ms (median %.2f, %d probe lines) ==' % (
                scene, mean(alone[0][3]), statistics.median(p[1] for p in alone[0][3]), len(alone[0][3])))
        else:
            print('\n== scene %s ==' % scene)
        print('%-30s %7s %7s %7s %7s %7s %6s  %s' % ('variant', 'GPU ms', 'base ms', 'saves', 'saves %', 'hitch', 'dr', 'what'))
        for s, v in [x for x in order if x[0] == scene]:
            t0, ps = meas[(s, v)]
            mine = mean(ps)
            before = [b for b in bases if b[1] == s and b[0] < t0]
            after = [b for b in bases if b[1] == s and b[0] > t0]
            bs = ([mean(before[-1][3])] if before else []) + ([mean(after[0][3])] if after else [])
            base = statistics.mean(bs) if bs else float('nan')
            saves = base - mine
            pct = 100.0 * saves / base if bs else float('nan')
            h = hitch.get((s, v), {})
            hmax = max(h.get('set', 0.0), h.get('restore', 0.0))
            dr = statistics.mean(p[4] for p in ps)
            print('%-30s %7.2f %7.2f %7.2f %6.1f%% %6.0fms %5.2f  %s' % (v, mine, base, saves, pct, hmax, dr, L['variants'].get(v, {}).get('note', '')))
            out.append([s, v, mine, base, saves, pct, hmax, h.get('set', 0.0), h.get('restore', 0.0)])
    if csv:
        with open(os.path.join(d, 'table.csv'), 'w') as f:
            f.write('scene,variant,gpu_ms,base_ms,saves_ms,saves_pct,hitch_ms,hitch_set_ms,hitch_restore_ms\n')
            for row in out:
                f.write(','.join('%.3f' % x if isinstance(x, float) else str(x) for x in row) + '\n')
    return 0


def frames(d, wanted):
    """For each variant (all, or the labels in wanted) the received frame saved at the end of its measuring window, and the frame at
    the end of the baseline window before it. Prints 'scene|variant|measure frame|baseline frame'."""
    L = json.load(open(os.path.join(d, 'labels.json')))
    labels = {int(k): v for k, v in L['labels'].items()}
    M = markers(os.path.join(d, 'game.log'))
    byline = {}
    for t, ln, txt in M:
        byline.setdefault(ln, t)
    ends = sorted(byline.items())
    view = open(os.path.join(d, 'view.log'), errors='replace').read().splitlines()
    t0 = None
    saved = []   # (epoch, file)
    for line in view:
        m = re.match(r'\s*([\d.]+)\s+streamers .*wall clock ([\d.]+)', line)
        if m:
            t0 = float(m.group(2)) - float(m.group(1))
        m = re.match(r'\s*([\d.]+)\s+saved (\S+)', line)
        if m and t0 is not None:
            saved.append((t0 + float(m.group(1)), m.group(2)))

    def near(t):
        return min(saved, key=lambda x: abs(x[0] - t))[1] if saved else None

    def end_of(ln):
        t = byline.get(ln)
        nxt = [x for l, x in ends if l > ln]
        return (nxt[0] - 0.25) if t and nxt else None

    out, last_base = [], {}
    for ln in sorted(labels):
        role, scene, var = labels[ln]
        e = end_of(ln)
        if e is None:
            continue
        if role == 'base':
            last_base[scene] = near(e)
        elif role == 'measure' and (not wanted or var in wanted):
            out.append((scene, var, near(e), last_base.get(scene)))
    for r in out:
        print('|'.join(str(x) for x in r))


def main(a):
    if not a:
        print(__doc__)
        return 2
    c = a[0]
    if c == 'names':
        print('\n'.join(NAMES))
    elif c == 'gen-probe':
        gen_probe(a[1])
    elif c == 'baseline':
        baseline(a[1], a[2])
    elif c == 'gen':
        kv = dict(x.split('=', 1) for x in a[3:] if '=' in x)
        gen(a[1], a[2], kv.get('scenes', 'street,garage').split(','), set(kv['only'].split(',')) if 'only' in kv else None)
    elif c == 'gen-hitch':
        kv = dict(x.split('=', 1) for x in a[2:] if '=' in x)
        gen_hitch(a[1], int(kv.get('reps', 4)), kv.get('scenes', 'street,garage').split(','))
    elif c == 'sum-hitch':
        sum_hitch(a[1])
    elif c == 'gen-steps':
        kv = dict(x.split('=', 1) for x in a[3:] if '=' in x)
        gen_steps(a[1], int(a[2]), kv.get('scenes', 'street,garage').split(','))
    elif c == 'frames':
        frames(a[1], set(a[2].split(',')) if len(a) > 2 else None)
    elif c == 'sum':
        return summarize(a[1], 'csv' in a[2:])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
