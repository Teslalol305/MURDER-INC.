"""Midtown kit, part 3: the pipe-scaffold stair tower from the gantry down to the street (L5, midtown.md 5.3 and 4 S3).

The tower (world x -8..-3, z 14..20) is two flight columns (x -8..-5.6 and -5.4..-3.0) with a spine between, 8 flights of
5 risers of 0.346 over 2.5 m (tread 0.5), landings N (z 14..15.5) and S (z 18..20) at 14.0, 12.27, ... 0.15; its outer faces
are bay frames with OPAQUE netting (no alpha: thin-geometry and masked cost), the landings open east to the square.
Tubes are 6 cm (the design's flicker floor; real scaffold tube is 48 mm). Placements: assets/_midtown_place.py.
"""
import math

import numpy as np

from assets import _midtown_roof as R
from assets.facade import B, bx, sheet

X, Y, Z = np.eye(3)
TUBE = 0.03                                    # radius: 6 cm tubes
LIFT = 0.346 * 5                               # 1.73 m between landings


def coupler(b, p, slot="galv"):
    bx(b, (p[0] - 0.05, p[1] - 0.05, p[2] - 0.045), (p[0] + 0.05, p[1] + 0.05, p[2] + 0.045), slot, ch=0.012, pin=False)


def m_flight(ctx, M):
    """One flight: 10 art risers of 0.173 over 2.5 m (treads 0.25; the data's 5 collider steps are 0.346), 2.4 m wide, plate
    stringers, checker treads with nosings, tube handrails (1.0 m) and mid rails both sides. Pivot: the foot of the flight
    on its centre line at the lower landing (z = 0), rising along +X."""
    b = B(701, step=0.6)
    n, rise, run, W = 5, 0.346, 0.5, 2.4
    for s in (-1, 1):
        y = s * (W / 2 - 0.04)
        p0, p1 = np.array((-0.05, y, -0.10)), np.array((n * run, y, n * rise - 0.10))
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        up = np.cross(d, Y)
        up = up if up[2] > 0 else -up
        R.fc.bar(b, p0, p1, 0.06, 0.22, "galv", up=up, ch=0.004)
    # the art draws 10 risers of 0.173 over 0.25 m treads (a real scaffold stair) on the data's 5 collider steps of 0.346
    # (the roof stair does the same: 18 art risers over 8 collider steps); 5 steps of 0.35 read as a ladder of giant steps
    na, ra, ta = 2 * n, rise / 2, run / 2
    for i in range(na - 1):
        x0, z = i * ta, (i + 1) * ra
        bx(b, (x0 + 0.0, -W / 2 + 0.06, z - 0.008), (x0 + ta + 0.03, W / 2 - 0.06, z), "plate", ch=0.002, pin=False, axis="y")
        bx(b, (x0 + 0.0, -W / 2 + 0.06, z - 0.06), (x0 + 0.06, W / 2 - 0.06, z), "plate", pin=False, axis="y")      # nosing, 6 cm
    for s in (-1, 1):
        y = s * (W / 2 + 0.02)
        for (ha, hb) in ((1.0, 1.0), (0.5, 0.5)):
            R.tube(b, (-0.1, y, ha), (n * run + 0.1, y, n * rise + hb), "galv", TUBE)
        for xx in (0.05, n * run / 2, n * run - 0.05):
            z = rise * xx / run
            R.tube(b, (xx, y, z - 0.10), (xx, y, z + 1.0 + 0.02), "galv", TUBE)
            coupler(b, (xx, y, z + 1.0))
    return R.done(ctx, b, "SM_Scaf_Flight_2p4", M, ground=False, expect_size=(None, None, None),
                  notes="Scaffold stair flight (L5): 10 art risers of 0.173 over 2.5 m (the level's 5 collider steps of 0.346), 2.4 m wide, plate stringers, checker treads, 6 cm "
                        "tube rails 1.0 and 0.5. Pivot: foot of the flight, centre line, lower landing level, rising +X.")


def m_landing(ctx, M):
    """A landing 5.0 (across both flight columns, y) by 1.5 m (x): scaffold boards on tube transoms, a toe board on the
    outer side. Pivot: the west end (x = 0) on the centre line, deck top z = 0, running +X."""
    b = B(711, step=0.6)
    L, W = 1.5, 5.0
    for xx in (0.05, L / 2, L - 0.05):
        R.tube(b, (xx, -W / 2, -0.11), (xx, W / 2, -0.11), "galv", TUBE)
    for s in (-1, 1):
        R.tube(b, (-0.05, s * (W / 2 - 0.05), -0.17), (L + 0.05, s * (W / 2 - 0.05), -0.17), "galv", TUBE)
    nb = int(W / 0.225)
    for j in range(nb):
        y0 = -W / 2 + j * W / nb
        bx(b, (0.0, y0 + 0.004, -0.05), (L, y0 + W / nb - 0.004, 0.0), "boards", ch=0.004, pin=False, axis="y")
    for xx in (0.03, L - 0.03):
        bx(b, (xx - 0.03, -W / 2, -0.06), (xx + 0.03, W / 2, 0.0), "galv", pin=False, axis="y")
    bx(b, (L - 0.03, -W / 2, 0.0), (L, W / 2, 0.15), "boards", ch=0.003, pin=False, axis="y")
    return R.done(ctx, b, "SM_Scaf_Landing_2p4", M, ground=False, expect_size=(None, None, None),
                  notes="Scaffold landing 1.5 x 5.0 m (the N landing; the S landing is two of them, 2.0 m deep, or this one scaled "
                        "1.33 in x): boards on tube transoms, toe board on +X. Pivot: west end, centre line, deck top.")


def m_bay(ctx, M):
    """One bay of the tower's outer frame, 2.5 m wide by one lift (1.73 m): two standards, the ledger at the top, a
    guard rail at 1.0 and 0.5 over the lower level, a diagonal brace, couplers. Pivot: bottom-left on the frame's plane
    (y = 0), running +X; stack lifts at 1.73 m."""
    b = B(721, step=0.6)
    L, H = 2.5, LIFT
    for xx in (0.0, L):
        R.tube(b, (xx, 0, 0.0), (xx, 0, H), "galv", TUBE)
    for zz in (H, 1.0, 0.5):
        R.tube(b, (-0.05, 0, zz), (L + 0.05, 0, zz), "galv", TUBE)
        for xx in (0.0, L):
            coupler(b, (xx, 0, zz))
    R.tube(b, (0.05, -0.06, 0.08), (L - 0.05, -0.06, H - 0.08), "galv", TUBE)
    for p in ((0.05, -0.06, 0.08), (L - 0.05, -0.06, H - 0.08)):
        coupler(b, p)
    return R.done(ctx, b, "SM_Scaf_Bay_Frame", M, ground=False, expect_size=(None, None, None),
                  notes="Scaffold bay frame 2.5 m x one lift (1.73): standards, ledger, guard rails at 1.0 and 0.5, a diagonal, "
                        "couplers, 6 cm tubes. Pivot: bottom-left in the frame plane, +X; stack at 1.73 m.")


def m_netting(ctx, M):
    """Opaque woven netting over one bay (2.5 x 1.73 m), hanging a little slack between ties, on the outer side
    (y = -0.10). Pivot as the bay frame."""
    b = B(731, step=1.0)
    L, H = 2.5, LIFT
    nx, nz = 6, 4
    F = np.zeros((nz, nx, 3))
    for j in range(nz):
        for i in range(nx):
            x, z = i * L / (nx - 1), j * H / (nz - 1)
            sag = 0.04 * math.sin(math.pi * i / (nx - 1)) * (1 - abs(2 * j / (nz - 1) - 1)) + 0.01 * math.sin(3 * i + j)
            F[j, i] = (x, -0.10 - sag, z)
    sheet(b, F, 0.004, "fabricNet")
    for (xx, zz) in ((0.1, 0.1), (L - 0.1, 0.1), (0.1, H - 0.1), (L - 0.1, H - 0.1)):
        R.tube(b, (xx, -0.10, zz), (xx, -0.03, zz), "rubber", 0.03, n=6)
    return R.done(ctx, b, "SM_Scaf_Netting_Panel", M, ground=False, expect_size=(None, None, None),
                  notes="Scaffold netting panel 2.5 x 1.73 m, OPAQUE (MI_Fabric_ScaffoldNet, a tint of the canvas scan: no alpha), "
                        "slack between four ties, on the outer side of a bay frame. Pivot as SM_Scaf_Bay_Frame.")


def m_sign(ctx, M):
    """The contractor's board (KESSLER & ROTH SCAFFOLD, Board_KesslerRoth) 2.4 x 1.2 m: plywood back, the printed face,
    two tube clamps. Pivot: bottom-left of the face, face toward -Y."""
    b = B(741, step=1.0)
    W, H = 2.4, 1.2
    bx(b, (0.0, 0.0, 0.0), (W, 0.018, H), "boards", ch=0.003, axis="x")
    R.face_quad(b, 0.0, W, 0.0, H, -0.001, "signFace")
    fr = ((0.0, -0.001, 0.0), X, Z, (W, H))
    for zz in (0.25, H - 0.25):
        R.tube(b, (-0.3, 0.06, zz), (W + 0.3, 0.06, zz), "galv", TUBE)
        for xx in (0.2, W - 0.2):
            coupler(b, (xx, 0.06, zz))
    return R.done(ctx, b, "SM_Scaf_Sign", M, ground=False, faces=[("M_Sign_MT_Face", fr)], expect_size=(None, None, None),
                  notes="Scaffold contractor's board 2.4 x 1.2 m (face Board_KesslerRoth: an invented contractor, no phone number), "
                        "clamped to the tower's south face. Pivot: bottom-left, face -Y.")


PROPS = [m_flight, m_landing, m_bay, m_netting, m_sign]
