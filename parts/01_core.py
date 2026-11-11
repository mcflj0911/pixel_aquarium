import pygame
import random
import math
import sys
import os
from collections import deque
from array import array
import json
import time

is_muted = False
pygame.init()
info = pygame.display.Info()
ASSET_PATH = "doodads"
# Full-screen: the world is drawn at 1/WORLD_SCALE of the monitor's resolution and scaled up, so the tank fills the
# whole display (more water, bigger fish) while the frame stays cheap. By default the world is about 1.1 million pixels
# (about 1400x790 on a 1080p monitor); set the AQUARIUM_SCALE environment variable (e.g. 1.0 = native, 2.0 = chunky) to override.
WORLD_SCALE = float(os.environ.get("AQUARIUM_SCALE", 0)) or max(1.0, math.sqrt(info.current_w * info.current_h / 1.1e6))
display = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
DISPLAY_W, DISPLAY_H = display.get_size()   # what we actually got
SCREEN_WIDTH = int(math.ceil(DISPLAY_W / WORLD_SCALE))
SCREEN_HEIGHT = int(math.ceil(DISPLAY_H / WORLD_SCALE))
VS = SCREEN_HEIGHT / 600     # vertical stretch vs. the original 600px tank, used to spread fish through the extra height


def world_mouse(p):
    """Display pixels -> world pixels."""
    return (p[0] * SCREEN_WIDTH / DISPLAY_W, p[1] * SCREEN_HEIGHT / DISPLAY_H)
SAND_HEIGHT = 40
WATER_TOP = 80
ALGAE_SPAWN_RATE = 15
MAX_HUNGER = 100
DEBUG_EVENTS = False

CLR_WATER_TOP = (40, 100, 180)
CLR_WATER_BOTTOM = (10, 30, 80)
CLR_SAND = (163, 148, 125)
CLR_ALGAE = (60, 180, 60)
CLR_FOOD = (150, 100, 50)

STATE_WELCOME = 0
STATE_AQUARIUM = 1
current_state = STATE_WELCOME

LIGHT_MODES = [
    {"name": "LED RGB WHITE", "color": (255, 255, 255, 0)},
    {"name": "WARM WHITE",    "color": (255, 240, 200, 30)},
    {"name": "WARM",          "color": (255, 200, 100, 60)},
    {"name": "COOL",          "color": (150, 200, 255, 40)},
    {"name": "DEEP AMAZON",   "color": (100, 65, 20, 70)},
    {"name": "MOONLIGHT",     "color": (10, 20, 80, 110)},
    {"name": "PLANTED GROW",  "color": (255, 100, 255, 25)},
    {"name": "ACTINIC",       "color": (0, 0, 255, 50)},
    {"name": "SUNSET GOLD",   "color": (255, 140, 0, 45)},
    {"name": "MILD GREEN",    "color": (150, 255, 180, 35)},
    {"name": "RGB STROBE",    "color": (0, 0, 0, 0)},
    {"name": "BLACKWATER CREEK", "color": (70, 40, 10, 90)},
    {"name": "MANGROVE SHADOW", "color": (120, 130, 80, 55)},
    {"name": "ARCTIC CHILL", "color": (200, 230, 255, 35)},
    {"name": "SHALLOW WATER", "color": (0, 200, 255, 30)},
    {"name": "DAWN BREAK", "color": (255, 180, 150, 50)},
    {"name": "HIGH NOON", "color": (255, 255, 240, 15)},
    {"name": "TWILIGHT", "color": (60, 40, 100, 80)},
    {"name": "MIDNIGHT ABYSS", "color": (5, 5, 25, 160)},
    {"name": "THUNDERSTORM", "color": (80, 80, 100, 100)},
    {"name": "BIOLUME", "color": (0, 255, 180, 45)},
    {"name": "VINTAGE SEPIA", "color": (150, 100, 50, 65)},
    {"name": "NEON NIGHT", "color": (255, 20, 147, 40)}
]
current_light_idx = 0
light_notif_text = ""
light_notif_alpha = 0

def get_path(filename):
    return os.path.join(ASSET_PATH, filename)


# Sprites are drawn at SS times their size and smooth-scaled down, which gives soft anti-aliased edges
SS = 2


def tone(color, factor):
    """Brighten (factor > 1) or darken (factor < 1) the RGB part of a color."""
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


_HUE_CACHE = {}


def hue_shift(c, lvl):
    """Rotate a colour's hue by a whole number of steps (the guppy colour gene)."""
    if not lvl:
        return tuple(c[:3])
    key = (tuple(c[:3]), lvl)
    out = _HUE_CACHE.get(key)
    if out is None:
        import colorsys
        h, l, sat = colorsys.rgb_to_hls(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
        r, g, b = colorsys.hls_to_rgb((h + 0.06 * lvl) % 1.0, l, sat)
        out = _HUE_CACHE[key] = (int(r * 255), int(g * 255), int(b * 255))
    return out


def lerp_point(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def shaded_ellipse(surface, rect, top_col, bottom_col, steps=10):
    """Fill an ellipse with a top-to-bottom gradient by stacking shrinking ellipses."""
    x, y, w, h = rect
    for i in range(steps):
        t = i / (steps - 1)
        pygame.draw.ellipse(surface, mix(bottom_col, top_col, t),
                            (x + w * 0.04 * t, y, w * (1 - 0.08 * t), h * (1 - 0.8 * t)))


def shaded_polygon(surface, points, top_col, bottom_col):
    """Fill a polygon with a top-to-bottom gradient: a gradient strip clipped by the polygon's mask."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = int(min(xs)), int(min(ys))
    w, h = int(max(xs)) - x0 + 2, int(max(ys)) - y0 + 2
    local = [(px - x0, py - y0) for px, py in points]

    strip = pygame.Surface((w, h), pygame.SRCALPHA)
    for row in range(h):
        pygame.draw.line(strip, (*mix(top_col, bottom_col, row / (h - 1)), 255), (0, row), (w, row))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), local)
    strip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(strip, (x0, y0))


def fin_rays(surface, rect, count, color):
    """Draw rays from the fin's root (where it meets the body) across its far edge."""
    x, y, w, h = rect
    root = (x + w * 0.85, y + h * 0.5)
    for i in range(count):
        a = math.pi / 2 + math.pi * (i + 0.5) / count  # Far (left) half of the fin
        edge = (x + w * 0.5 + math.cos(a) * w * 0.5, y + h * 0.5 + math.sin(a) * h * 0.5)
        pygame.draw.aaline(surface, color, root, edge)


def fan_rays(surface, base, tip_a, tip_b, count, color):
    """Fan rays from a base point across the edge between two tips (tail fins)."""
    for k in range(count + 1):
        pygame.draw.aaline(surface, color, base, lerp_point(tip_a, tip_b, k / count))


def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                        + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1))


def smooth_closed(points, sub=5):
    """Catmull-Rom spline through a closed loop of points: turns a few corner points into an organic outline."""
    n = len(points)
    return [_cr(points[i - 1], points[i], points[(i + 1) % n], points[(i + 2) % n], k / sub)
            for i in range(n) for k in range(sub)]


def smooth_open(points, sub=5):
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        out += [_cr(pts[i - 1], pts[i], pts[i + 1], pts[i + 2], k / sub) for k in range(sub)]
    out.append(points[-1])
    return out


def body_outline(cx, cy, length, ht, hb, peak=0.5, pt=0.75, pn=0.55, ped=0.12, n=26):
    """A fish silhouette from tail (u=0) to nose (u=1): ht/hb are the half-heights above and below the axis at the
    deepest point (u=peak); pt/pn shape how quickly it swells behind and in front of it; ped is the tail-stalk width."""
    top, bot = [], []
    for k in range(n + 1):
        u = k / n
        if u < peak:
            f = math.sin(u / peak * math.pi / 2) ** pt
            f = max(f, ped * (1 - u / peak))
        else:
            f = math.sin((1 - u) / (1 - peak) * math.pi / 2) ** pn
        x = cx - length / 2 + u * length
        top.append((x, cy - ht * f))
        bot.append((x, cy + hb * f))
    return top + bot[::-1]


def clip_to_polygon(layer, pts):
    mask = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), pts)
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return layer


def paint_body(surf, pts, top, mid, belly, scale=None, shine=0.3, mid_at=0.45):
    """Fill a body outline with a three-stop gradient (dark back, body colour, pale belly), faint scales and a soft
    highlight along the back, so it reads as a rounded, glossy form."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = int(min(xs)) - 1, int(min(ys)) - 1
    w, h = int(max(xs)) - x0 + 3, int(max(ys)) - y0 + 3
    local = [(px - x0, py - y0) for px, py in pts]
    strip = pygame.Surface((w, h), pygame.SRCALPHA)
    for row in range(h):
        v = row / max(1, h - 1)
        col = mix(top, mid, v / mid_at) if v < mid_at else mix(mid, belly, (v - mid_at) / (1 - mid_at))
        pygame.draw.line(strip, (*col, 255), (0, row), (w, row))
    if scale:
        size, scol, sa = scale
        tex = pygame.Surface((w, h), pygame.SRCALPHA)
        for r in range(int(h / (size * 0.8)) + 1):
            off = size * 0.5 if r % 2 else 0
            for c in range(int(w / size) + 2):
                pygame.draw.arc(tex, (*scol, sa), (c * size + off - size, r * size * 0.8, size, size), math.pi / 2, math.pi * 1.5, 1)
        strip.blit(tex, (0, 0))
    hl = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (255, 255, 255, int(255 * shine * 0.45)), (w * 0.12, h * 0.07, w * 0.74, h * 0.26))
    pygame.draw.ellipse(hl, (255, 255, 255, int(255 * shine)), (w * 0.22, h * 0.12, w * 0.5, h * 0.12))
    strip.blit(hl, (0, 0))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), local)
    strip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(strip, (x0, y0))


def draw_fin(surf, pts, color, rays=0, root=None, alpha=215, edge=None, width=1, ray_col=None):
    """A translucent fin: pts is a closed outline whose first/last points sit on the body; rays fan from root to the
    free edge (the points in between)."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
    w, h = int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4
    local = [(px - x0, py - y0) for px, py in pts]
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(layer, (*color, alpha), local)
    free = local[1:-1]
    if rays and root is not None and len(free) > 1:
        rx, ry = root[0] - x0, root[1] - y0
        for k in range(rays):
            i = (k + 0.5) / rays * (len(free) - 1)
            a, b = free[int(i)], free[min(len(free) - 1, int(i) + 1)]
            tip = lerp_point(a, b, i - int(i))
            pygame.draw.line(layer, (*(ray_col or tone(color, 0.7)), 120), (rx, ry), tip, 1)
    if edge and len(free) > 1:
        pygame.draw.lines(layer, (*edge, 230), False, free, width)
    surf.blit(layer, (x0, y0))


def draw_eye(surf, ex, ey, r, iris=(235, 200, 90), ring=(20, 20, 20)):
    """Round eye: dark rim, coloured iris, black pupil, two highlights."""
    r = max(2.0, r)
    pygame.draw.circle(surf, ring, (ex, ey), int(r * 1.12))
    pygame.draw.circle(surf, iris, (ex, ey), int(r * 0.92))
    pygame.draw.circle(surf, tone(iris, 0.55), (ex, ey), int(r * 0.92), max(1, int(r * 0.18)))
    pygame.draw.circle(surf, (8, 8, 10), (ex, ey), max(1, int(r * 0.55)))
    pygame.draw.circle(surf, (255, 255, 255), (int(ex - r * 0.3), int(ey - r * 0.32)), max(1, int(r * 0.26)))
    pygame.draw.circle(surf, (255, 255, 255, 160), (int(ex + r * 0.28), int(ey + r * 0.3)), max(1, int(r * 0.12)))


def fin_shape(root_a, free, root_b, sub=5):
    """Outline for draw_fin: two points on the body and a smoothed free edge between them."""
    return [root_a] + smooth_open(free, sub) + [root_b]


def is_dark(color):
    return sum(color[:3]) < 260


_capture = None  # while a sprite is being cached, blit_fish hands over the finished surface instead of drawing it


def blit_fish(surface, fish_surf, center, facing, angle):
    """Scale a supersampled fish sprite down, mirror it to its heading, rotate it and blit it."""
    if _capture is not None:
        _capture.append(fish_surf)
        return
    sprite = pygame.transform.smoothscale(fish_surf, (fish_surf.get_width() // SS, fish_surf.get_height() // SS))
    if not facing:
        sprite = pygame.transform.flip(sprite, True, False)
    rotated = pygame.transform.rotate(sprite, angle if facing else -angle)
    surface.blit(rotated, rotated.get_rect(center=(int(center[0]), int(center[1]))))


def draw_ribbon(surface, p0, p1, w0, w1, color):
    """Fill the quad between two points whose widths taper from w0 to w1 (blades, grass)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length
    pts = [
        (p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2),
        (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
        (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2),
        (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2),
    ]
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.aalines(surface, color, True, pts)


LEAF_CACHE = {}


def render_leaf(length, width, top_col, bottom_col, vein_col):
    """Render an upright, shaded oval leaf with a midrib and side veins at SS times its size, then scale it down."""
    w, h = max(2, int(length * SS)), max(2, int(width * SS))
    leaf = pygame.Surface((w, h), pygame.SRCALPHA)
    shaded_ellipse(leaf, (0, 0, w, h), top_col, bottom_col)
    mid = h / 2
    pygame.draw.line(leaf, vein_col, (w * 0.06, mid), (w * 0.94, mid), SS)
    for k in range(1, 5):
        vx = w * (0.1 + 0.2 * k)
        pygame.draw.aaline(leaf, vein_col, (vx, mid), (vx + w * 0.1, h * 0.12))
        pygame.draw.aaline(leaf, vein_col, (vx, mid), (vx + w * 0.1, h * 0.88))
    return pygame.transform.smoothscale(leaf, (max(2, int(length)), max(2, int(width))))


def draw_leaf(surface, center, length, width, angle, top_col, bottom_col, vein_col):
    """Blit a leaf rotated by angle (degrees). Leaf sprites are cached: only the rotation changes per frame."""
    key = (round(length), round(width), *(c // 4 for col in (top_col, bottom_col, vein_col) for c in col[:3]))
    sprite = LEAF_CACHE.get(key)
    if sprite is None:
        sprite = render_leaf(round(length), round(width), top_col, bottom_col, vein_col)
        LEAF_CACHE[key] = sprite
    rotated = pygame.transform.rotate(sprite, angle)
    surface.blit(rotated, rotated.get_rect(center=(int(center[0]), int(center[1]))))

pygame.mixer.init()
