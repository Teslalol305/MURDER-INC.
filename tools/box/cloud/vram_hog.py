"""Hold graphics memory so that only <free MiB> stay free on the card, to run the game as if on a smaller card
(E3DS's servers have 8 or 16 GB; the box has 96 GB). Diagnostic for e3ds-repro.sh; stop it with a kill.

    /opt/venv/bin/python3 -I vram_hog.py 7600      # leaves about an 8 GB card's usable memory free
"""
import sys
import time

import torch

leave = int(sys.argv[1]) * 1024 * 1024
free, total = torch.cuda.mem_get_info()
want = free - leave
blocks = []
chunk = 512 * 1024 * 1024
while want > 0:
    n = min(chunk, want)
    blocks.append(torch.empty(n, dtype=torch.uint8, device='cuda'))
    want -= n
torch.cuda.synchronize()
free2, _ = torch.cuda.mem_get_info()
print(f'held {sum(b.numel() for b in blocks) >> 20} MiB; free now {free2 >> 20} MiB of {total >> 20} MiB', flush=True)
while True:
    time.sleep(5)
