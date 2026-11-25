"""Keep the GPU busy from a second process, so that the game next to it gets only a share of the card: the load for
the lag tests (lag-test.sh) that the game's own dynamic resolution cannot undo. The driver gives each process that
has work a turn on the card, so one hog that never stops leaves the game about half of the GPU, two hogs a third,
and so on (measured: lag-test.sh calib, docs/unreal/PROGRESS.md "Version 3, release A"). Stop it with a kill.

    /opt/venv/bin/python3 -I gpu_hog.py [work ms] [idle ms] [size]

work ms   how long one burst of GPU work lasts (default 4)
idle ms   the pause after each burst (default 0: the hog never lets go of the card)
size      the side of the square matrices it multiplies (default 2048)
It prints one line when it is running ("hog running ...") and one line every 10 s with the bursts it made.
"""
import sys
import time

import torch

work = float(sys.argv[1]) / 1000 if len(sys.argv) > 1 else 0.004
idle = float(sys.argv[2]) / 1000 if len(sys.argv) > 2 else 0.0
size = int(sys.argv[3]) if len(sys.argv) > 3 else 2048

a = torch.rand(size, size, device='cuda')
b = torch.rand(size, size, device='cuda')
for _ in range(20):  # the first products load the libraries: not part of the measurement
    c = a @ b
torch.cuda.synchronize()
# How many products fit in one burst when the card is free (measured once, before the game starts).
n, t0 = 0, time.perf_counter()
while time.perf_counter() - t0 < 0.5:
    c = a @ b
    torch.cuda.synchronize()
    n += 1
per = 0.5 / max(n, 1)
count = max(1, round(work / per))
print(f'hog running: bursts of {count} products of {size}x{size} (about {count * per * 1000:.1f} ms on a free card), '
      f'{idle * 1000:.0f} ms idle between them', flush=True)
bursts, last = 0, time.perf_counter()
while True:
    for _ in range(count):
        c = a @ b
    torch.cuda.synchronize()  # the burst ends when the card has done it: here the driver lets the game in
    bursts += 1
    if idle > 0:
        time.sleep(idle)
    now = time.perf_counter()
    if now - last >= 10:
        print(f'{bursts} bursts in {now - last:.1f} s ({(now - last) / bursts * 1000:.1f} ms each, idle included)', flush=True)
        bursts, last = 0, now
