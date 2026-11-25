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
  quality_table.py sum <dir> [csv]              the table: for every variant, the GPU time next to the baseline's, the saving,
                                                the longest frame in the first 1.5 s after the change, and the frame to look at

How the runs are started (tools/box/cloud/lag-test.sh, the Development game of a test folder, E3DS's own shader platform):
  lag-test.sh run q-street game=dev demo=<dir>/play.txt view=<dir>/view.txt join=3 probe=0.2 secs=<n> profile=1 -- -sm5 -MIFps=60
"""
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

NAMES = []
for _l, cv, _n in V:
    for n, _v in cv:
        if n not in NAMES:
            NAMES.append(n)
NAMES += ['r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod', 'r.AntiAliasingMethod', 'r.ScreenPercentage', 'sg.TextureQuality',
          'r.Nanite', 'r.Shadow.Virtual.Enable', 'r.RayTracing', 'r.Lumen.HardwareRayTracing', 't.MaxFPS', 'r.DynamicRes.OperationMode']
NAMES = list(dict.fromkeys(NAMES))

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
    return datetime.datetime(y, mo, d, h, mi, s, ms * 1000).timestamp()


def baseline(log, out):
    vals = {}
    for line in open(log, errors='replace'):
        m = re.search(r'LogConsoleResponse: .*?(\S+) = "([^"]*)"', line) or re.search(r'(?:Display|Log): (\S+) = "([^"]*)"', line)
        if m and m.group(1) in NAMES:
            vals[m.group(1)] = m.group(2)
    json.dump(vals, open(out, 'w'), indent=1, sort_keys=True)
    missing = [n for n in NAMES if n not in vals]
    print('%d of %d variables read back' % (len(vals), len(NAMES)))
    if missing:
        print('NOT FOUND (no such variable, or not printed): ' + ', '.join(missing))


def gen(out, base_file, scenes, only):
    base = json.load(open(base_file))
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
    count = int(total / FRAME_EVERY) + 30
    for i in range(count):
        view.append('frame f%04d.jpg' % i)
        view.append('wait %g' % (FRAME_EVERY - 0.2))
    open(os.path.join(out, 'view.txt'), 'w').write('\n'.join(view) + '\n')
    print('%d variants x %d scene(s): the script runs about %.0f s (%d lines)' % (len(todo), len(scenes), total, len(lines)))


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
    elif c == 'sum':
        return summarize(a[1], 'csv' in a[2:])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
