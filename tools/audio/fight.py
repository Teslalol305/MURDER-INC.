"""Writes Content/Data/audio_fight.json: a scripted 50-second Story fight as a bus event stream, in the format
MIAudio.Record writes (docs/unreal/AUDIO.md section 7), for MurderInc.Audio.Mixdown. Unreal units (cm) for the
player's events, web units (m, +Y up) for the enemy and flow payloads, as on the bus.

Usage: python3 tools/audio/fight.py
"""
import json
import math
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'unreal/MurderInc/Content/Data/audio_fight.json')
rng = random.Random(7)
ev = []


def add(t, type_, **kw):
    e = {'t': round(t, 4), 'type': type_}
    e.update(kw)
    ev.append(e)


def web(u):
    """Unreal cm -> web m (x, y up, z)."""
    return [round(u[0] / 100, 3), round(u[2] / 100, 3), round(u[1] / 100, 3)]


EYE = [1000.0, 1200.0, 170.0]   # the player on the avenue's south side, looking east (+X)
FWD = [1.0, 0.0, 0.0]


def observe(t, health=1.0, alive=True):
    add(t, 'observe', listener=EYE, forward=FWD, health=health, alive=alive)


def flow(t, name, text='', a=0, b=0, c=0):
    add(t, 'flow', name=name, text=text, a=a, b=b, c=c)


def enemy(t, kind, id_, etype, pos_u, dir_u=(0, 0, 0), **kw):
    # kinds: 0 spawn, 1 alert, 2 telegraph, 3 fire, 4 melee, 5 hit, 6 killed; etype 0 goon, 1 buzzard
    d = dict(kind=kind, id=id_, etype=etype, pos=web(pos_u), dir=[dir_u[0], dir_u[2], dir_u[1]], phase='', part='', damage=0,
             duration=0, byPlayer=False, weapon='')
    d.update(kw)
    add(t, 'enemy', **d)


def shots(t0, weapon, n, gap, target, surface='concrete', hit_every=0, kill_at=-1, kill_id=None, kill_type=0, head=False):
    for i in range(n):
        t = t0 + i * gap
        add(t, 'fire', weapon=weapon, muzzle=EYE, dir=FWD, ads=1.0, burst=i + 1, magLeft=30 - i)
        p = [target[0] + rng.uniform(-60, 60), target[1] + rng.uniform(-60, 60), target[2] + rng.uniform(-40, 60)]
        if hit_every and i % hit_every == hit_every - 1:
            add(t + 0.002, 'impact', point=p, normal=[-1, 0, 0], dir=FWD, surface='flesh', **{'from': 0})
            killed = i == kill_at
            add(t + 0.003, 'hitEnemy', part='head' if (head and killed) else 'body', killed=killed, damage=25, weapon=weapon)
            if killed:
                enemy(t + 0.004, 6, kill_id, kill_type, target, part='head' if head else 'body', byPlayer=True, weapon=weapon)
        else:
            add(t + 0.002, 'impact', point=p, normal=[-1, 0, 0], dir=FWD, surface=surface, **{'from': 0})


def enemy_burst(t0, id_, pos, n=3, gap=0.11):
    for i in range(n):
        t = t0 + i * gap
        d = [EYE[0] - pos[0], EYE[1] - pos[1] + rng.uniform(-150, 150), EYE[2] - pos[2] + rng.uniform(-60, 60)]
        L = math.sqrt(sum(x * x for x in d))
        d = [x / L for x in d]
        enemy(t, 3, id_, 0, pos, d)
        hit = [EYE[0] - 300 + rng.uniform(-200, 200), EYE[1] + rng.uniform(-250, 250), rng.uniform(0, 250)]
        add(t + 0.002, 'impact', point=hit, normal=[1, 0, 0], dir=d, surface=rng.choice(['concrete', 'brick', 'metal', 'car']), **{'from': 1})


for k in range(0, 520):
    observe(k * 0.1, 1.0)

flow(0.0, 'game:state', 'playing')
flow(0.05, 'hud:objective', 'Find the first master reel')
flow(0.4, 'hud:radio', 'Keys here. Three reels on the block. Bring them home.', 4.0)
add(0.5, 'music', i=0.15)
for i in range(8):
    add(0.8 + i * 0.52, 'step', pos=[EYE[0], EYE[1], 0], surface='asphalt', sprint=False)

G1, G2, G3, G4 = [3800, 1500, 100], [3300, 600, 100], [4200, 2100, 100], [2600, 1800, 100]
BZ = [2400, -600, 900]
enemy(4.0, 0, 0, 0, G1)
enemy(4.1, 0, 1, 0, G2)
enemy(4.6, 1, 0, 0, G1)
enemy(5.2, 0, 12, 1, BZ)
enemy(5.8, 1, 12, 1, BZ)
add(5.0, 'music', i=0.6)
enemy(6.6, 2, 0, 0, G1, duration=0.5)
enemy_burst(7.1, 0, G1)
enemy_burst(7.9, 0, G1)
shots(8.2, 'chopper', 9, 0.083, G1, hit_every=3, kill_at=8, kill_id=0)

add(10.0, 'reload', weapon='chopper', phase='start', empty=False)
add(10.5, 'reload', weapon='chopper', phase='magout', empty=False)
add(11.3, 'reload', weapon='chopper', phase='magin', empty=False)
add(11.8, 'reload', weapon='chopper', phase='bolt', empty=False)
add(12.2, 'reload', weapon='chopper', phase='done', empty=False)
enemy(12.6, 2, 12, 1, BZ, duration=0.46)
for i in range(3):
    d = [EYE[0] - BZ[0], EYE[1] - BZ[1], EYE[2] - BZ[2]]
    L = math.sqrt(sum(x * x for x in d))
    enemy(13.1 + i * 0.25, 3, 12, 1, BZ, [x / L for x in d])
add(13.4, 'playerHit', amount=12, health=88, kind=1)
observe(13.45, 0.88)
add(14.4, 'switch', **{'from': 'chopper', 'to': 'nine', 'phase': 'holster'})
add(14.75, 'switch', **{'from': 'chopper', 'to': 'nine', 'phase': 'draw'})
shots(15.0, 'nine', 3, 0.22, BZ, surface='metal', hit_every=1, kill_at=2, kill_id=12, kill_type=1)
enemy(15.5, 2, 1, 0, G2, duration=0.5)
shots(16.0, 'nine', 2, 0.25, G2, hit_every=1, kill_at=1, kill_id=1, head=True)

add(18.0, 'lit', index=3, pos=[3600, 900, 60], fuse=1.6)
enemy(18.2, 0, 2, 0, [3500, 800, 100])
add(19.6, 'blast', index=3, pos=[3600, 900, 60])
add(19.6, 'explosion', pos=[3600, 900, 60], radius=600, big=True)
enemy(19.61, 6, 2, 0, [3500, 800, 100], part='body', byPlayer=True, weapon='blast')
add(21.0, 'playerHit', amount=40, health=24, kind=0)
for k in range(211, 280):
    observe(k * 0.1, min(1.0, 0.24 + (k - 211) * 0.004))
enemy_burst(21.3, 3, G3, n=4)
for i in range(6):
    add(22.2 + i * 0.34, 'step', pos=[EYE[0], EYE[1], 0], surface='concrete', sprint=True)

for i in range(16):
    flow(24.0 + i * 0.1, 'hud:prompt', 'Hold E to take the reel', i / 15.0)
flow(25.7, 'hud:reels', '', 1, 3)
flow(25.7, 'objective:done', 'reel_1', 1, 3)
flow(25.71, 'audio:sting', 'reel')
flow(25.72, 'hud:radio', 'One down. Two to go.', 2.5)
flow(25.75, 'hud:objective', 'Find the second master reel')

enemy(29.0, 0, 3, 0, G4)
enemy(29.4, 1, 3, 0, G4)
enemy(30.0, 4, 3, 0, G4, phase='windup')
enemy(30.3, 4, 3, 0, G4, phase='strike')
add(30.5, 'swing', weapon='chopper')
add(30.62, 'melee', hit=True)
add(30.63, 'hitEnemy', part='body', killed=True, damage=60, weapon='melee')
enemy(30.64, 6, 3, 0, G4, part='body', byPlayer=True, weapon='melee')

add(33.0, 'music', i=1.0)
flow(33.0, 'objective:done', 'reel_3', 3, 3)
flow(33.01, 'audio:sting', 'all')
flow(33.02, 'objective:all')
flow(33.05, 'hud:objective', 'Get to the IPX truck')
enemy(34.0, 0, 4, 0, G3)
enemy(34.1, 0, 5, 0, G1)
shots(35.0, 'chopper', 12, 0.083, G3, hit_every=4, kill_at=11, kill_id=4)
shots(36.4, 'chopper', 10, 0.083, G1, hit_every=3, kill_at=8, kill_id=5)
add(37.6, 'dry', weapon='chopper')
for i in range(10):
    add(38.5 + i * 0.33, 'step', pos=[EYE[0], EYE[1], 0], surface='asphalt', sprint=True)
add(41.8, 'jump')
add(42.3, 'land', speed=520, surface='metal')
flow(43.0, 'extraction:reached')
flow(43.01, 'audio:sting', 'complete')
flow(43.02, 'game:state', 'complete')
add(43.1, 'music', i=0.15)
flow(47.5, 'menus:card', 'complete', 0, 0, 0)

ev.sort(key=lambda e: e['t'])
doc = {'about': 'A scripted 50-second Story fight for MurderInc.Audio.Mixdown (tools/audio/fight.py); the same format MIAudio.Record writes.', 'events': ev}
with open(OUT, 'w') as f:
    json.dump(doc, f, separators=(',', ':'))
print(f'{len(ev)} events, {ev[-1]["t"]} s -> {OUT}')
