# The in-game half of the browser features, tested on the box without WebRTC (stream-test.sh xtest <out> [config]):
# the packaged game in a window on a private virtual screen (Xvfb :99, drawn on the GPU through desktop-run
# --vulkan), started as under Pixel Streaming (-MICloud), driven with XTEST input (what a stream's input becomes):
# the click card, the first click, the set-up flow into a run, mouse look, P to pause and resume.
# Pictures with PIL from the virtual screen. Run with /opt/venv/bin/python3 -I as root.
import json, os, re, subprocess, sys, time
from PIL import ImageGrab

OUT = sys.argv[1]; CFG = sys.argv[2] if len(sys.argv) > 2 else 'Development'
RUN = '/project/ue/cloud/run'; LOG = f'{RUN}/cloud.log'; DISP = ':99'
os.makedirs(OUT, exist_ok=True)
R = {}
def note(k, v): R[k] = v; print(k, json.dumps(v)); json.dump(R, open(f'{OUT}/results.json', 'w'), indent=1)
def text(): return open(LOG).read() if os.path.exists(LOG) else ''
def probes(): return [dict((k, float(v)) for k, v in re.findall(r'(\w+)=(-?[\d.]+)', l)) for l in text().splitlines() if 'MICloudProbe' in l]
def last(): p = probes(); return p[-1] if p else {}
def wait(fn, s):
    t = time.time()
    while time.time() - t < s:
        v = fn()
        if v: return v
        time.sleep(0.25)
def xdo(*a): subprocess.run(['xdotool', *a], env=dict(os.environ, DISPLAY=DISP), check=False)
def grab(n): ImageGrab.grab(xdisplay=DISP).convert('RGB').save(f'{OUT}/{n}.jpg', quality=88)
def yaw_after():
    n = len(probes()); wait(lambda: len(probes()) >= n + 2, 5); return last().get('yaw', 0)

if subprocess.run(['pgrep', '-x', 'Xvfb'], capture_output=True).returncode != 0:
    subprocess.Popen(['Xvfb', DISP, '-screen', '0', '1920x1080x24', '-ac', '-nolisten', 'tcp'], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(2)
if os.path.exists(LOG): os.remove(LOG)
L = f'/project/ue/cloud/build-{CFG}/Linux'
cmd = (f'cd {RUN} && HOME=/home/ue4 DISPLAY={DISP} XDG_RUNTIME_DIR=/tmp/studio/xdg setsid nohup desktop-run --vulkan {L}/MurderInc.sh '
       f'-vulkan -unattended -nosplash -ResX=1920 -ResY=1080 -windowed -MICloud -MICloudProbe=0.5 -MICloudLog={LOG} '
       f'-stdout -FullStdOutLogOutput </dev/null > {RUN}/xgame.log 2>&1 & echo $! > {RUN}/xgame.pid')
t0 = time.time(); subprocess.run(['su', 'ue4', '-c', cmd])
ok = wait(lambda: last().get('fps', 0) > 20, 180)
note('start', {'seconds_to_running': round(time.time() - t0, 1), 'ok': bool(ok)})
time.sleep(6)
note('card_up', last().get('click') == 1); grab('x1-click-to-play')
xdo('mousemove', '960', '700'); xdo('click', '1'); time.sleep(1.5)
note('first_click', {'dismissed': 'Click to play: dismissed' in text(), 'card_up_after': last().get('click') == 1})
xdo('key', 'Return'); time.sleep(2); grab('x2-setup')
xdo('key', 'ctrl+Return'); time.sleep(2); xdo('key', 'Return')
playing = wait(lambda: last().get('state') == 2, 60)
note('setup_to_run', {'playing': bool(playing), 'state': last().get('state')})
time.sleep(4)
look = []
for dx in (100, -100, 300):
    y0 = yaw_after(); xdo('mousemove_relative', '--', str(dx), '0'); y1 = yaw_after()
    d = ((y1 - y0 + 540) % 360) - 180; look.append({'counts': dx, 'degrees': round(d, 3), 'deg_per_count': round(d / dx, 5)})
note('mouse_look_xtest', look)
grab('x3-play')
xdo('key', 'p'); paused = wait(lambda: last().get('state') == 3, 4); time.sleep(0.8); grab('x4-paused')
time.sleep(1.5); xdo('key', 'p'); resumed = wait(lambda: last().get('state') == 2, 4)
note('pause_p', {'paused': bool(paused), 'resumed': bool(resumed)})
note('memory', {'peak_rss_mb': max((p.get('peakRssMB', 0) for p in probes()), default=0)})
pid = open(f'{RUN}/xgame.pid').read().strip()
for p in subprocess.run(['pgrep', '-x', 'MurderInc'], capture_output=True, text=True).stdout.split() + \
         subprocess.run(['pgrep', '-x', 'MurderInc-Linux'], capture_output=True, text=True).stdout.split():
    if 'cloud/build-' in open(f'/proc/{p}/cmdline').read(): os.kill(int(p), 15)
