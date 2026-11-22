"""Printed and painted faces of the structures family (assets/structures.py): sets Sign_<Key> read by mat.sign_face.

Drawn on the signs.py canvas (metres, y down from the top) and weathered with mi.texpaint noise through
assets/_gaps_art.face (sun fade, dust, grime toward the edges, rain streaks). Fictional content only: no real
transit authority, brand, artist or event. `build.py build structures --force` redraws them (about 40 s).
"""
import numpy as np

from assets import _gaps_art as GA
from assets import signs as S

face, txt, rect, greek = GA.face, GA.txt, GA.rect, GA.greek
paint = S.paint

KEYS = ["StationName", "StationClosed", "KioskNews", "KioskCandy", "KioskPosters", "RoadClosed", "DigDanger",
        "FlyPosters", "PostNoBills", "PriceCards", "ScaleDial", "GarageNumbers", "ShopPosters", "ExitBox", "OilStain",
        "LoadingZone"]

# atlas cells: name -> (u0, v0, u1, v1) in 0..1 of the face (v up from the bottom, as the UVs run)
FLY = {"gig": (0.0, 0.5, 0.25, 1.0), "party": (0.25, 0.5, 0.5, 1.0), "hoops": (0.5, 0.5, 0.75, 1.0),
       "drivers": (0.75, 0.5, 1.0, 1.0), "mixtape": (0.0, 0.0, 0.25, 0.5), "church": (0.25, 0.0, 0.5, 0.5),
       "torn": (0.5, 0.0, 0.75, 0.5), "ipx": (0.75, 0.0, 1.0, 0.5)}
FLY_M = (2.4, 1.8)                         # 8 bills of 0.6 x 0.9 m
PRICE_M = (0.6, 0.24)                      # 10 cards of 0.12 x 0.12
GARAGE_M = (2.8, 0.84)                     # 8 numbers of 0.7 x 0.42
SHOP_M = (1.8, 0.9)                        # 3 posters of 0.6 x 0.9
KPOST_M = (1.2, 0.9)                       # 2 kiosk posters of 0.6 x 0.9


def _n(rng, cv, s=0.02):
    return S.vnoise(rng, cv.H, cv.W, cv.k * s)


def station_name(cv, rng):
    """Porcelain-enamel plate: white on deep green, a border line, the stop name and the hours line."""
    rect(cv, 0, 0, 4.6, 0.82, "#0f3b2a")
    rect(cv, 0.035, 0.035, 4.565, 0.785, "#0f3b2a", r=0.03, outline=0.012)
    cv.put(cv.rect(0.035, 0.035, 4.565, 0.785, 0.03, 0.012), paint("#ece9dd"))
    txt(cv, "188 ST", 0.36, 1.25, 0.33, "#ece9dd", "heavy", cond=0.86, track=0.02)
    txt(cv, "HOLLIS AVE", 0.15, 3.35, 0.25, "#ece9dd", "bold", track=0.06)
    txt(cv, "ELEVATED  ·  CLOSED 1 AM – 5 AM", 0.075, 3.35, 0.53, "#ece9dd", "semi", track=0.04)
    rect(cv, 2.35, 0.14, 2.36, 0.68, "#ece9dd")
    chips = (_n(rng, cv, 0.006) > 1.55).astype(np.float32) * (np.minimum(np.minimum(cv.x, 4.6 - cv.x), np.minimum(cv.y, 0.82 - cv.y)) < 0.06)
    cv.put(chips, (0.03, 0.03, 0.035))                       # chipped enamel at the edges and bolt holes
    for x in (0.08, 4.52):
        for y in (0.08, 0.74):
            cv.put(cv.rect(x - 0.012, y - 0.012, x + 0.012, y + 0.012, 0.012), (0.12, 0.08, 0.05))


def station_closed(cv, rng):
    rect(cv, 0, 0, 1.5, 0.42, "#ece9dd")
    rect(cv, 0.02, 0.02, 1.48, 0.40, "#ece9dd", outline=0.01)
    cv.put(cv.rect(0.02, 0.02, 1.48, 0.40, 0.0, 0.01), paint("#101113"))
    txt(cv, "188 ST", 0.12, 0.75, 0.13, "#0f3b2a", "heavy", track=0.03)
    txt(cv, "STATION CLOSED", 0.085, 0.75, 0.29, "#b3261e", "heavy", track=0.05)


def kiosk_band(text, w):
    def draw(cv, rng):
        rect(cv, 0, 0, w, 0.26, "#24463a")
        txt(cv, text, 0.15, w / 2, 0.135, "#f4f2ec", "heavy", cond=0.82, track=0.04, max_w=w - 0.1)
    return draw


def kiosk_posters(cv, rng):
    # left: a cold-drink ad (no brand), right: lottery-style jackpot board with a fictional game name
    rect(cv, 0, 0, 0.6, 0.9, "#c81f2a")
    rect(cv, 0.04, 0.55, 0.56, 0.86, "#f4f2ec")
    txt(cv, "ICE", 0.14, 0.3, 0.14, "#f4f2ec", "heavy")
    txt(cv, "COLD", 0.14, 0.3, 0.36, "#f4f2ec", "heavy", max_w=0.5)
    txt(cv, "SODA · JUICE · WATER", 0.035, 0.3, 0.62, "#c81f2a", "bold")
    txt(cv, "75¢", 0.13, 0.3, 0.76, "#101113", "heavy")
    rect(cv, 0.6, 0, 1.2, 0.9, "#1b2f6b")
    txt(cv, "QUICK 6", 0.085, 0.9, 0.10, "#f6c21a", "heavyIt")
    txt(cv, "JACKPOT", 0.06, 0.9, 0.24, "#f4f2ec", "heavy")
    txt(cv, "$4", 0.17, 0.9, 0.42, "#f6c21a", "heavy")
    txt(cv, "MILLION", 0.05, 0.9, 0.58, "#f6c21a", "heavy")
    txt(cv, "PLAY HERE", 0.06, 0.9, 0.70, "#f4f2ec", "heavy")
    greek(cv, 0.66, 0.78, 1.14, 0.86, line=0.008, col="#9fb0d8", seed=3)


def road_closed(cv, rng):
    rect(cv, 0, 0, 3.4, 1.05, "#e8641b")
    rect(cv, 0.04, 0.04, 3.36, 1.01, "#e8641b", outline=0.02)
    cv.put(cv.rect(0.04, 0.04, 3.36, 1.01, 0.02, 0.02), paint("#101113"))
    txt(cv, "ROAD CLOSED", 0.36, 1.7, 0.40, "#101113", "heavy", cond=0.9, track=0.03, max_w=3.0)
    txt(cv, "EL STRUCTURE REPAIRS  ·  NO THRU TRAFFIC", 0.11, 1.7, 0.82, "#101113", "bold", max_w=3.1)


def dig_danger(cv, rng):
    rect(cv, 0, 0, 0.9, 0.6, "#f4f2ec")
    rect(cv, 0, 0, 0.9, 0.2, "#b3261e")
    cv.put(cv.rect(0.05, 0.03, 0.85, 0.17, 0.05), paint("#101113"))
    txt(cv, "DANGER", 0.11, 0.45, 0.10, "#f4f2ec", "heavy", track=0.06)
    txt(cv, "STEAM", 0.13, 0.45, 0.32, "#101113", "heavy", track=0.04)
    txt(cv, "KEEP OUT", 0.08, 0.45, 0.48, "#101113", "heavy", track=0.04)


def _bill(cv, x0, y0, w, h, kind, rng):
    """One fly-poster in the cell (x0, y0) (canvas metres, y down)."""
    cx = x0 + w / 2
    if kind == "gig":
        rect(cv, x0, y0, x0 + w, y0 + h, "#f2c21a")
        txt(cv, "LIVE", 0.12, cx, y0 + 0.12, "#101113", "heavy")
        txt(cv, "KING TONE", 0.085, cx, y0 + 0.28, "#b3261e", "heavy", cond=0.85, max_w=w - 0.04)
        txt(cv, "& THE 205 CREW", 0.04, cx, y0 + 0.38, "#101113", "bold")
        rect(cv, x0 + 0.06, y0 + 0.45, x0 + w - 0.06, y0 + 0.70, "#101113")
        txt(cv, "SAT JULY 29", 0.05, cx, y0 + 0.53, "#f2c21a", "heavy")
        txt(cv, "THE ROYAL BALLROOM", 0.03, cx, y0 + 0.62, "#f4f2ec", "bold")
        txt(cv, "DOORS 10 PM · $15", 0.035, cx, y0 + 0.79, "#101113", "bold")
    elif kind == "party":
        rect(cv, x0, y0, x0 + w, y0 + h, "#16a3c8")
        txt(cv, "BLOCK", 0.13, cx, y0 + 0.15, "#f4f2ec", "heavy")
        txt(cv, "PARTY", 0.13, cx, y0 + 0.31, "#f6c21a", "heavy")
        txt(cv, "205TH ST & 109 AVE", 0.035, cx, y0 + 0.45, "#101113", "bold")
        txt(cv, "DJ · FOOD · DOUBLE DUTCH", 0.03, cx, y0 + 0.55, "#101113", "semi")
        txt(cv, "AUG 5", 0.12, cx, y0 + 0.72, "#f4f2ec", "heavy")
    elif kind == "hoops":
        rect(cv, x0, y0, x0 + w, y0 + h, "#f4f2ec")
        rect(cv, x0, y0, x0 + w, y0 + 0.22, "#1b2f6b")
        txt(cv, "SUMMER HOOPS", 0.05, cx, y0 + 0.11, "#f4f2ec", "heavy", max_w=w - 0.06)
        def ball(d, k):
            d.ellipse([(cx - 0.13) * k, (y0 + 0.28) * k, (cx + 0.13) * k, (y0 + 0.54) * k], fill=255)
        cv.put(cv.draw(ball), paint("#d9521a"))
        txt(cv, "3 ON 3 TOURNAMENT", 0.04, cx, y0 + 0.62, "#1b2f6b", "heavy")
        txt(cv, "THE CAGE · EVERY SAT", 0.032, cx, y0 + 0.70, "#101113", "bold")
        greek(cv, x0 + 0.06, y0 + 0.75, x0 + w - 0.06, y0 + 0.86, line=0.008, seed=7)
    elif kind == "drivers":
        rect(cv, x0, y0, x0 + w, y0 + h, "#f4f2ec")
        txt(cv, "DRIVERS", 0.1, cx, y0 + 0.14, "#101113", "heavy")
        txt(cv, "WANTED", 0.1, cx, y0 + 0.27, "#b3261e", "heavy")
        txt(cv, "CAR SERVICE · 24 HRS", 0.033, cx, y0 + 0.40, "#101113", "bold")
        greek(cv, x0 + 0.06, y0 + 0.45, x0 + w - 0.06, y0 + 0.66, line=0.01, seed=11)
        for i in range(7):                                    # tear-off phone tabs, some gone
            if rng.random() < 0.6:
                xx = x0 + 0.03 + i * (w - 0.06) / 7
                rect(cv, xx + 0.004, y0 + 0.72, xx + (w - 0.06) / 7 - 0.004, y0 + h - 0.01, "#e9e7df")
                txt(cv, "555-0188", 0.014, xx + (w - 0.06) / 14, y0 + 0.80, "#101113", "bold")
    elif kind == "mixtape":
        rect(cv, x0, y0, x0 + w, y0 + h, "#101113")
        txt(cv, "MIC ROYAL", 0.085, cx, y0 + 0.16, "#d9a514", "heavy", cond=0.85, max_w=w - 0.04)
        txt(cv, "STREET LEVEL", 0.05, cx, y0 + 0.28, "#f4f2ec", "heavy")
        def disc(d, k):
            d.ellipse([(cx - 0.17) * k, (y0 + 0.34) * k, (cx + 0.17) * k, (y0 + 0.68) * k], fill=255)
        m = cv.draw(disc)
        cv.put(m, paint("#3b1420"))
        txt(cv, "IN STORES NOW", 0.04, cx, y0 + 0.78, "#d9a514", "heavy")
    elif kind == "church":
        rect(cv, x0, y0, x0 + w, y0 + h, "#ece6c8")
        txt(cv, "GOSPEL", 0.08, cx, y0 + 0.15, "#3b1420", "heavy")
        txt(cv, "REVIVAL", 0.08, cx, y0 + 0.26, "#3b1420", "heavy")
        txt(cv, "ALL WELCOME", 0.035, cx, y0 + 0.37, "#101113", "bold")
        greek(cv, x0 + 0.06, y0 + 0.43, x0 + w - 0.06, y0 + 0.78, line=0.009, seed=13)
    elif kind == "torn":                                      # the last layers of older bills, torn off
        rect(cv, x0, y0, x0 + w, y0 + h, "#d8d2c0")
        for i in range(5):
            yy = y0 + rng.uniform(0.0, h - 0.2)
            rect(cv, x0, yy, x0 + w, yy + rng.uniform(0.08, 0.25), ["#f2c21a", "#16a3c8", "#b3261e", "#f4f2ec", "#101113"][i])
        txt(cv, "TONE", 0.1, cx, y0 + 0.5, "#101113", "heavy")
    elif kind == "ipx":
        rect(cv, x0, y0, x0 + w, y0 + h, "#101113")
        txt(cv, "IPX", 0.2, cx, y0 + 0.3, "#f4f2ec", "xbIt")
        txt(cv, "IPX.EXCHANGE", 0.04, cx, y0 + 0.47, "#f6c21a", "bold")
        txt(cv, "THE FUTURE PAYS", 0.035, cx, y0 + 0.70, "#f4f2ec", "semi")


def fly_posters(cv, rng):
    cv.c[:] = paint("#d8d2c0")
    for name, (u0, v0, u1, v1) in FLY.items():
        x0, y0 = u0 * FLY_M[0], (1 - v1) * FLY_M[1]
        _bill(cv, x0, y0, (u1 - u0) * FLY_M[0], (v1 - v0) * FLY_M[1], name, rng)
    # paste wrinkles and tears: lighter creases, paper fibre showing at torn corners
    n = _n(rng, cv, 0.03)
    cv.put((n > 1.3).astype(np.float32) * 0.6, (0.75, 0.72, 0.64))
    tear = (S.vnoise(rng, cv.H, cv.W, cv.k * 0.08) > 1.15) & ((cv.y % 0.9) < 0.18)
    cv.put(tear.astype(np.float32) * 0.85, (0.80, 0.77, 0.70))


def post_no_bills(cv, rng):
    m, _, _ = cv.text("POST NO BILLS", "heavy", 0.16, 0.75, 0.12, track=0.08, cond=0.9)
    n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.006)
    bridges = (np.abs(((cv.x * 1000) % 37) - 18) < 1.2).astype(np.float32)      # stencil bridges
    cv.c[:] = paint("#e6e4dc")
    cv.a = np.clip(m * (0.7 + 0.35 * n) * (1 - bridges), 0, 1)


PRICES = ["3 FOR\n$1", "ORANGES\n5/$1", "APPLES\n69¢ LB", "LEMONS\n4/$1", "LIMES\n6/$1", "PLUMS\n99¢ LB",
          "MANGO\n2/$1", "PEPPERS\n$1.29", "EGGPLANT\n89¢", "SALE"]


def price_cards(cv, rng):
    cv.c[:] = paint("#f2efe4")
    for i, t in enumerate(PRICES):
        x0, y0 = (i % 5) * 0.12, (i // 5) * 0.12
        rect(cv, x0 + 0.004, y0 + 0.004, x0 + 0.116, y0 + 0.116, ["#f2efe4", "#f6e35a", "#ff9fbd", "#9fe08a"][i % 4])
        a, b = (t.split("\n") + [""])[:2]
        txt(cv, a, 0.018 if len(a) > 5 else 0.026, x0 + 0.06, y0 + 0.038, "#101113", "heavy", max_w=0.1)
        if b:
            txt(cv, b, 0.028, x0 + 0.06, y0 + 0.082, "#c81f2a", "heavy", max_w=0.1)


def scale_dial(cv, rng):
    rect(cv, 0, 0, 0.2, 0.2, "#e9e7df")
    def ticks(d, k):
        c = 0.1
        for i in range(40):
            a = -np.pi / 2 + i * 2 * np.pi / 40
            r0 = 0.078 if i % 5 else 0.07
            d.line([((c + r0 * np.cos(a)) * k, (c + r0 * np.sin(a)) * k), ((c + 0.088 * np.cos(a)) * k, (c + 0.088 * np.sin(a)) * k)],
                   fill=255, width=max(1, int(0.0018 * k)))
        d.line([(c * k, c * k), ((c + 0.07 * np.cos(-1.1)) * k, (c + 0.07 * np.sin(-1.1)) * k)], fill=255, width=max(1, int(0.003 * k)))
    cv.put(cv.draw(ticks), paint("#101113"))
    txt(cv, "LBS", 0.014, 0.1, 0.135, "#c81f2a", "heavy")


def garage_numbers(cv, rng):
    a = cv.blank()
    n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.008)
    for i in range(8):
        x0, y0 = (i % 4) * 0.7, (i // 4) * 0.42
        m, _, _ = cv.text(str(41 + i), "heavy", 0.30, x0 + 0.35, y0 + 0.21, cond=0.85)
        a = np.maximum(a, m)
    cv.c[:] = paint("#e6e4dc")
    cv.a = np.clip(a * (0.7 + 0.35 * n), 0, 1)


def shop_posters(cv, rng):
    # three paper posters for the office: a parts-store price list, a towing calendar, a cash-only notice
    rect(cv, 0, 0, 0.6, 0.9, "#f2efe4")
    rect(cv, 0, 0, 0.6, 0.16, "#b3261e")
    txt(cv, "HOLLIS AUTO PARTS", 0.045, 0.3, 0.08, "#f4f2ec", "heavy", max_w=0.56)
    for i, (a, b) in enumerate((("BRAKE PADS", "$19.99"), ("ROTORS", "$34.99"), ("MUFFLER", "$49.99"), ("BATTERY", "$59.99"),
                                ("OIL + FILTER", "$14.99"), ("WIPERS", "$7.99"))):
        y = 0.22 + i * 0.075
        txt(cv, a, 0.03, 0.04, y, "#101113", "bold", align="l")
        txt(cv, b, 0.032, 0.56, y, "#b3261e", "heavy", align="r")
    txt(cv, "FARMERS BLVD · (718) 555-0127", 0.022, 0.3, 0.84, "#101113", "semi")
    rect(cv, 0.6, 0, 1.2, 0.9, "#e9e7df")
    rect(cv, 0.6, 0, 1.2, 0.36, "#1b2f6b")
    txt(cv, "205 TOWING", 0.06, 0.9, 0.12, "#f6c21a", "heavy")
    txt(cv, "24 HR · FLATBED", 0.035, 0.9, 0.24, "#f4f2ec", "bold")
    for r in range(5):                                        # a month grid
        for c in range(7):
            x, y = 0.64 + c * 0.075, 0.42 + r * 0.085
            rect(cv, x, y, x + 0.07, y + 0.08, "#e9e7df", outline=0.002)
            cv.put(cv.rect(x, y, x + 0.07, y + 0.08, 0.0, 0.002), paint("#5a5a5a"))
            d = r * 7 + c - 3
            if 1 <= d <= 31:
                txt(cv, str(d), 0.016, x + 0.055, y + 0.016, "#101113", "bold", align="r")
    txt(cv, "JULY 2000", 0.03, 0.9, 0.39, "#101113", "heavy")
    rect(cv, 1.2, 0, 1.8, 0.9, "#f6e35a")
    txt(cv, "CASH", 0.12, 1.5, 0.22, "#101113", "heavy")
    txt(cv, "ONLY", 0.12, 1.5, 0.40, "#101113", "heavy")
    txt(cv, "NO CHECKS", 0.05, 1.5, 0.58, "#b3261e", "heavy")
    txt(cv, "NO CREDIT", 0.05, 1.5, 0.67, "#b3261e", "heavy")
    txt(cv, "- MGMT", 0.035, 1.6, 0.80, "#101113", "semi")


def exit_box(cv, rng):
    rect(cv, 0, 0, 0.7, 0.3, "#7a1410")
    m, _ = txt(cv, "EXIT", 0.15, 0.35, 0.15, "#fff1d0", "heavy", track=0.1)
    e = np.zeros((cv.H, cv.W, 3), np.float32) + S.to_lin(S.rgb("#7a1410")) * 0.5
    return e * (1 - m[..., None]) + S.to_lin(S.rgb("#fff1d0")) * m[..., None] * 1.8


def oil_stain(cv, rng):
    """1 x 1 m drip patch: a dark core, rings where it spread and dried, a halo of dust caught in it."""
    x, y = cv.x - 0.5, cv.y - 0.5
    n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.12)
    n2 = S.vnoise(rng, cv.H, cv.W, cv.k * 0.03)
    r = np.hypot(x * (1 + 0.25 * n), y * (1 - 0.2 * n)) + 0.03 * n2
    core = np.clip(1 - r / 0.38, 0, 1) ** 0.6
    ring = np.exp(-((r - 0.33) / 0.015) ** 2) * 0.5
    drops = (S.vnoise(rng, cv.H, cv.W, cv.k * 0.01) > 1.9).astype(np.float32) * (r < 0.48)
    cv.c[:] = paint("#0c0a08")
    cv.a = np.clip(0.9 * core + ring + 0.8 * drops, 0, 0.95)


def loading_zone(cv, rng):
    a, _, _ = cv.text("NO PARKING", "heavy", 0.17, 0.8, 0.16, track=0.06, cond=0.9)
    b, _, _ = cv.text("LOADING ZONE", "heavy", 0.17, 0.8, 0.42, track=0.06, cond=0.9)
    n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.006)
    cv.c[:] = paint("#e6e4dc")
    cv.a = np.clip(np.maximum(a, b) * (0.65 + 0.4 * n), 0, 1)


def have(key):
    return GA.have("Sign_" + key)


def draw_all(force=False):
    """Every face of the family (skips the ones that exist unless force)."""
    jobs = [
        ("StationName", 4.6, 0.82, 4096, "#0f3b2a", station_name, dict(rough=0.12, age=0.9, metal=None)),
        ("StationClosed", 1.5, 0.42, 1536, "#ece9dd", station_closed, dict(rough=0.15, age=1.0)),
        ("KioskNews", 2.4, 0.26, 2048, "#24463a", kiosk_band("NEWS  ·  MAGAZINES  ·  LOTTO", 2.4), dict(rough=0.4, age=1.3)),
        ("KioskCandy", 1.35, 0.26, 1536, "#24463a", kiosk_band("CANDY  ·  SODA", 1.35), dict(rough=0.4, age=1.3)),
        ("KioskPosters", KPOST_M[0], KPOST_M[1], 1536, "#c81f2a", kiosk_posters, dict(rough=0.35, age=1.4)),
        ("RoadClosed", 3.4, 1.05, 3072, "#e8641b", road_closed, dict(rough=0.3, age=1.1)),
        ("DigDanger", 0.9, 0.6, 1024, "#f4f2ec", dig_danger, dict(rough=0.35, age=1.0)),
        ("FlyPosters", FLY_M[0], FLY_M[1], 3072, "#d8d2c0", fly_posters, dict(rough=0.7, age=1.5)),
        ("PostNoBills", 1.5, 0.24, 1536, (0.9, 0.9, 0.88), post_no_bills, dict(rough=0.6, age=0, grime_amt=0, alpha=True)),
        ("PriceCards", PRICE_M[0], PRICE_M[1], 1280, "#f2efe4", price_cards, dict(rough=0.6, age=0.6, grime_amt=0.3)),
        ("ScaleDial", 0.2, 0.2, 512, "#e9e7df", scale_dial, dict(rough=0.1, age=0.6, grime_amt=0.4)),
        ("GarageNumbers", GARAGE_M[0], GARAGE_M[1], 2048, (0.9, 0.9, 0.88), garage_numbers, dict(rough=0.7, age=0, grime_amt=0, alpha=True)),
        ("ShopPosters", SHOP_M[0], SHOP_M[1], 2048, "#f2efe4", shop_posters, dict(rough=0.65, age=1.6)),
        ("ExitBox", 0.7, 0.3, 768, "#7a1410", exit_box, dict(rough=0.2, age=0.6, meta=dict(emissive_day=0.5))),
        ("OilStain", 1.0, 1.0, 1024, (0.05, 0.04, 0.03), oil_stain, dict(rough=0.15, age=0, grime_amt=0, alpha=True)),
        ("LoadingZone", 1.6, 0.6, 1536, (0.9, 0.9, 0.88), loading_zone, dict(rough=0.6, age=0, grime_amt=0, alpha=True)),
    ]
    for key, w, h, px, bg, fn, kw in jobs:
        if force or not have(key):
            kw = dict(kw)
            kw.setdefault("meta", {})
            kw["meta"] = dict(kw["meta"], drawn_by="assets/_structures_art.py")
            if kw.get("metal", 1) is None:
                kw.pop("metal")
            face(key, w, h, px, bg, fn, **kw)
            print("  face Sign_%s" % key, flush=True)
