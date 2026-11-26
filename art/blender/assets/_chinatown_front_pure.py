"""Pure-arithmetic helpers of the Canal kit that the placements need without Blender (rooftop frame legs, lantern hooks)."""
import numpy as np

from assets import _chinatown_level as lv


def rooftop_legs():
    """The rooftop frame's legs as lane D placed them (market.letters.leg colliders): (east end x, [leg centre x], face y)."""
    legs = [lv.cbox(i) for i in lv.parts("market.letters.leg")]
    xs = sorted(float((lo[0] + hi[0]) / 2) for lo, hi in legs)
    x_e = max(float(hi[0]) for lo, hi in legs)
    yc = float(np.mean([(lo[1] + hi[1]) / 2 for lo, hi in legs]))
    return x_e, xs, yc


def lantern_hooks(L=14.0, sag=0.55, n=16):
    """The 16 lanterns' pivots along SM_Prop_CT_LanternString_14m (same arithmetic as _chinatown_kit.m_lantern_string)."""
    out = []
    for i in range(n):
        x = L * (i + 0.5) / n
        z = -sag * (1 - ((x - L / 2) / (L / 2)) ** 2)
        out.append((round(x, 3), 0.0, round(z - 0.12 - 0.65, 3)))
    return out
