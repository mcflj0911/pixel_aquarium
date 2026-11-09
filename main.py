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


class Pebble:
    def __init__(self):
        # Using the same z and positioning logic from your main.py
        self.z = random.uniform(0.5, 1.6)
        self.pos_x = random.randint(0, SCREEN_WIDTH)
        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + \
                      math.sin(self.pos_x * 0.02) * 5 + \
                      math.cos(self.pos_x * 0.05) * 2

        # Procedural Generation instead of loading from disk
        width = int(random.randint(6, 12) * self.z)
        height = int(random.randint(4, 8) * self.z)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)

        # Pick a base stony color with slight variation
        gray_val = random.randint(100, 140)
        base_col = [gray_val, gray_val - 5, gray_val - 10]

        # Apply depth shading once at creation to save CPU cycles per frame
        shade = 0.4 + (self.z - 0.7) * (0.6 / 0.5)
        shade = max(0.3, min(1.0, shade))
        final_col = (int(base_col[0] * shade), int(base_col[1] * shade), int(base_col[2] * shade))

        # Draw the pebble shape
        pygame.draw.ellipse(self.image, final_col, (0, 0, width, height))

        # Add a tiny "highlight" speck for texture
        highlight_col = (min(255, final_col[0] + 30), min(255, final_col[1] + 30), min(255, final_col[2] + 30))
        pygame.draw.ellipse(self.image, highlight_col, (width // 4, height // 4, width // 3, height // 3))

    def draw(self, surface):
        # Using the sink logic to bed the pebble into the sand
        sink = int(8 * self.z)
        rect = self.image.get_rect(midbottom=(self.pos_x, int(self.base_y + sink)))

        # Blit the pre-shaded image directly
        surface.blit(self.image, rect)
def create_pebbles(count=60):
    return sorted((Pebble() for _ in range(count)), key=lambda p: p.z)


def shade_for_depth(image, z):
    """Bake depth shading into a sprite once; it only depends on the sprite's z."""
    shade = max(0.2, min(1.0, 0.3 + (z - 0.7) * (0.7 / 0.5)))
    v = int(255 * shade)
    image.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    return image


def render_rock(width, height, rng):
    """Draw a lumpy, faceted stone at SS times its size, then scale it down."""
    w, h = int(width * SS), int(height * SS)
    pts = []
    for k in range(20):
        a = math.tau * k / 20
        r = 1 + rng.uniform(-0.1, 0.1)
        flat = 0.7 if math.sin(a) > 0 else 1.0  # Flatter underside, rounder top
        pts.append((w / 2 + math.cos(a) * w / 2 * 0.92 * r,
                    h / 2 + math.sin(a) * h / 2 * 0.92 * r * flat))

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    grey = rng.randint(115, 145)
    stone = (grey, grey - 4, grey - 10)
    shaded_polygon(surf, pts, tone(stone, 1.3), tone(stone, 0.55))

    # A lighter facet on the upper left catches the light
    facet = [(w / 2 + (px - w / 2) * 0.5 - w * 0.1, h / 2 + (py - h / 2) * 0.45 - h * 0.12) for px, py in pts]
    pygame.draw.polygon(surf, tone(stone, 1.45), facet)

    # Fractures across the stone
    for _ in range(3):
        x1, y1 = rng.uniform(0.25, 0.75) * w, rng.uniform(0.35, 0.65) * h
        x2, y2 = x1 + rng.uniform(-0.2, 0.2) * w, y1 + rng.uniform(0.05, 0.15) * h
        pygame.draw.aaline(surf, tone(stone, 0.45), (x1, y1), (x2, y2))

    return pygame.transform.smoothscale(surf, (max(2, int(width)), max(2, int(height))))


def render_driftwood(width, height, rng):
    """A gnarled piece of mopani-style driftwood: a thick root-base with forking limbs, shaded bark and knots."""
    w, h = int(width * SS), int(height * SS)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    bark = (rng.randint(92, 118), rng.randint(66, 84), rng.randint(42, 58))

    def limb(x, y, ang, length, th, depth):
        pts, a, steps = [(x, y)], ang, 7
        for _ in range(steps):
            a += rng.uniform(-0.22, 0.22)
            x += math.cos(a) * length / steps
            y -= math.sin(a) * length / steps
            pts.append((x, y))
        ths = [th * (1 - 0.6 * k / steps) + 1 for k in range(len(pts))]
        for col, shrink, off in ((tone(bark, 0.48), 1.0, 0), (tone(bark, 0.88), 0.8, 0), (tone(bark, 1.28), 0.3, -th * 0.2)):
            for i in range(len(pts) - 1):
                pa, pb = pts[i], pts[i + 1]
                wd = max(1, int(ths[i] * shrink))
                pygame.draw.line(surf, col, (pa[0], pa[1] + off), (pb[0], pb[1] + off), wd)
                pygame.draw.circle(surf, col, (int(pb[0]), int(pb[1] + off)), max(1, wd // 2))
        for i in range(1, len(pts) - 1, 2):  # knots and grain
            pygame.draw.ellipse(surf, tone(bark, 0.4), (pts[i][0] - ths[i] * 0.2, pts[i][1] - ths[i] * 0.12, ths[i] * 0.4, ths[i] * 0.26))
        if depth > 0:
            for idx in (3, 5):
                if rng.random() < 0.85:
                    limb(pts[idx][0], pts[idx][1], a + rng.choice((-1, 1)) * rng.uniform(0.5, 1.0), length * rng.uniform(0.45, 0.65),
                         th * 0.6, depth - 1)

    bx = w * rng.uniform(0.35, 0.6)
    limb(bx, h - 3, math.pi / 2 + rng.uniform(-0.5, 0.5), h * 0.85, w * 0.075, 2)
    limb(bx + w * 0.08, h - 3, rng.uniform(0.15, 0.55), w * 0.42, w * 0.055, 1)
    limb(bx - w * 0.08, h - 3, math.pi - rng.uniform(0.15, 0.55), w * 0.4, w * 0.055, 1)
    return pygame.transform.smoothscale(surf, (max(2, int(width)), max(2, int(height))))


MOSS_CACHE = {}


class Rock:
    def __init__(self, x=None, z=None, y_offset=0):
        self.z = z if z is not None else random.uniform(0.7, 1.2)
        self.pos_x = x if x is not None else random.randint(0, SCREEN_WIDTH)

        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2
        self.y_offset = y_offset

        # Rocks are rendered once and cached as sprites
        width = random.uniform(55, 80) * self.z * (1.0 if y_offset == 0 else 0.8)
        height = width * random.uniform(0.5, 0.7)
        if y_offset < -20:
            height *= 0.7
        self.image = shade_for_depth(render_rock(width, height, random.Random(random.random())), self.z)
        if random.random() > 0.5:
            self.image = pygame.transform.flip(self.image, True, False)
        self.img0, self.sc, self.fl = self.image, 1.0, False

    kind = "ROCK"
    mday = 0        # the tank day this piece was put in: moss grows with its age

    def moss_level(self):
        if self.kind not in ("ROCK", "DRIFTWOOD"):
            return 0
        return min(4, max(0, eco.day - self.mday) // 7)

    def mossy(self, level):
        key = (id(self.image), level)
        img = MOSS_CACHE.get(key)
        if img is None:
            if len(MOSS_CACHE) > 80:
                MOSS_CACHE.clear()
            img = self.image.copy()
            w, h = img.get_size()
            rng = random.Random(int(self.pos_x * 7) + int(self.z * 100))
            wood = self.kind == "DRIFTWOOD"
            for _ in range(level * max(8, w * h // 260)):
                x, y = rng.randrange(w), rng.randrange(int(h * 0.7) + 1)
                if img.get_at((x, y))[3] > 200:
                    base = (76, 130, 62) if wood else (62, 112, 70)
                    c = (base[0] + rng.randint(-12, 14), base[1] + rng.randint(-12, 22), base[2] + rng.randint(-10, 10))
                    pygame.draw.circle(img, c, (x, y), rng.choice((1, 2, 2, 3)))
            img = MOSS_CACHE[key] = img
        return img

    def draw(self, surface):
        sink = int(35 * self.z) if self.y_offset >= 0 else 0
        lvl = self.moss_level()
        img = self.mossy(lvl) if lvl else self.image
        rect = img.get_rect(midbottom=(self.pos_x, int(self.base_y + self.y_offset + sink)))
        surface.blit(img, rect)


class Driftwood(Rock):
    def __init__(self, x=None, z=None, y_offset=0):
        self.z = z if z is not None else random.uniform(0.7, 1.1)
        self.pos_x = x if x is not None else random.randint(0, SCREEN_WIDTH)
        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2
        self.y_offset = y_offset
        rng = random.Random(random.random())
        width = rng.uniform(120, 190) * self.z
        self.image = shade_for_depth(render_driftwood(width, width * rng.uniform(0.55, 0.85), rng), self.z)
        if rng.random() < 0.5:
            self.image = pygame.transform.flip(self.image, True, False)
        self.img0, self.sc, self.fl = self.image, 1.0, False

    kind = "DRIFTWOOD"


class _Hard(Rock):
    """Shared plumbing for the built pieces: caves, clay pots, a wreck and a stone bridge are painted once and then behave like rocks."""

    def __init__(self, x=None, z=None, y_offset=0):
        self.z = z if z is not None else random.uniform(0.8, 1.1)
        self.pos_x = x if x is not None else random.randint(100, SCREEN_WIDTH - 100)
        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2
        self.y_offset = y_offset
        rng = random.Random(random.random())
        self.image = shade_for_depth(self.paint(rng, self.z), self.z)
        if rng.random() < 0.5:
            self.image = pygame.transform.flip(self.image, True, False)
        self.img0, self.sc, self.fl = self.image, 1.0, False


class Cave(_Hard):
    kind = "CAVE"

    def paint(self, rng, z):
        w = rng.uniform(120, 160) * z
        img = render_rock(w, w * rng.uniform(0.62, 0.78), rng)
        W, H = img.get_size()
        ow, oh = int(W * 0.44), int(H * 0.6)
        ox, oy = (W - ow) // 2 + int(rng.uniform(-0.08, 0.08) * W), H - oh
        pygame.draw.ellipse(img, (14, 12, 20), (ox - 3, oy - 3, ow + 6, oh * 2 + 6))
        pygame.draw.ellipse(img, (24, 22, 32), (ox, oy, ow, oh * 2))
        pygame.draw.ellipse(img, (10, 9, 14), (ox + ow * 0.12, oy + oh * 0.22, ow * 0.76, oh * 1.6))
        pygame.draw.ellipse(img, (56, 50, 60), (ox + ow * 0.1, H - max(3, oh * 0.18), ow * 0.8, max(3, oh * 0.3)))
        return img


class ClayPot(_Hard):
    kind = "POT"

    def paint(self, rng, z):
        u = SS
        w = rng.uniform(58, 76) * z
        h = w * 0.74
        W, H = int(w * u), int(h * u)
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        terra, dark, light = (190, 100, 62), (126, 60, 40), (224, 140, 92)
        pygame.draw.polygon(sf, terra, [(0.05 * W, 0.52 * H), (0.22 * W, 0.15 * H), (0.74 * W, 0.1 * H), (0.74 * W, 0.97 * H), (0.22 * W, 0.88 * H)])
        for fx in (0.3, 0.46, 0.62):
            pygame.draw.line(sf, dark, (fx * W, 0.14 * H), (fx * W, 0.93 * H), int(2 * u))
        pygame.draw.line(sf, light, (0.12 * W, 0.4 * H), (0.7 * W, 0.16 * H), int(3 * u))
        pygame.draw.ellipse(sf, light, (0.6 * W, 0.04 * H, 0.3 * W, 0.94 * H))
        pygame.draw.ellipse(sf, dark, (0.66 * W, 0.12 * H, 0.2 * W, 0.78 * H))
        pygame.draw.ellipse(sf, (36, 20, 18), (0.69 * W, 0.18 * H, 0.15 * W, 0.66 * H))
        return pygame.transform.smoothscale(sf, (max(2, W // u), max(2, H // u)))


class Shipwreck(_Hard):
    kind = "SHIP"

    def paint(self, rng, z):
        u = SS
        w = rng.uniform(170, 210) * z
        h = w * 0.64
        W, H = int(w * u), int(h * u)
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        wood, wood_d, wood_l = (92, 62, 42), (56, 38, 28), (138, 100, 66)
        pygame.draw.polygon(sf, wood, [(0.04 * W, 0.56 * H), (0.12 * W, 0.92 * H), (0.78 * W, 0.97 * H), (0.97 * W, 0.62 * H), (0.88 * W, 0.5 * H), (0.5 * W, 0.62 * H)])
        for k in range(1, 5):   # planks
            y = 0.56 * H + k * 0.085 * H
            pygame.draw.line(sf, wood_d, (0.08 * W + k * 0.012 * W, y), (0.9 * W - k * 0.03 * W, y - 0.02 * H), int(2 * u))
        for k in range(9):   # broken ribs standing up from the deck edge
            x = (0.14 + 0.085 * k) * W
            top = 0.52 * H - rng.uniform(0.08, 0.34) * H * (1 - 0.5 * abs(k - 4) / 4)
            pygame.draw.line(sf, wood_l if k % 2 else wood, (x, 0.58 * H), (x + rng.uniform(-6, 6) * u, top), int(4 * u))
        pygame.draw.line(sf, wood_d, (0.5 * W, 0.6 * H), (0.46 * W, 0.04 * H), int(6 * u))   # the mast
        pygame.draw.line(sf, wood_d, (0.36 * W, 0.2 * H), (0.58 * W, 0.17 * H), int(4 * u))
        sail = [(0.37 * W, 0.22 * H), (0.57 * W, 0.19 * H), (0.55 * W, 0.34 * H), (0.5 * W, 0.4 * H), (0.46 * W, 0.34 * H), (0.4 * W, 0.42 * H)]
        pygame.draw.polygon(sf, (206, 196, 172, 210), sail)
        for px, py in ((0.3, 0.76), (0.46, 0.8), (0.62, 0.78)):
            pygame.draw.circle(sf, (22, 40, 44), (int(px * W), int(py * H)), int(5 * u))
            pygame.draw.circle(sf, (120, 150, 140), (int(px * W), int(py * H)), int(5 * u), int(1.5 * u))
        return pygame.transform.smoothscale(sf, (max(2, W // u), max(2, H // u)))


class StoneBridge(_Hard):
    kind = "BRIDGE"

    def paint(self, rng, z):
        u = SS
        w = rng.uniform(180, 220) * z
        h = w * 0.56
        W, H = int(w * u), int(h * u)
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        stone, edge, lite = (126, 124, 134), (74, 72, 84), (164, 162, 172)
        pygame.draw.rect(sf, stone, (0.02 * W, 0.36 * H, 0.17 * W, 0.64 * H))
        pygame.draw.rect(sf, stone, (0.81 * W, 0.36 * H, 0.17 * W, 0.64 * H))
        cx, cy = 0.5 * W, 0.98 * H
        outer, inner = [], []
        for k in range(25):
            a = math.pi + math.pi * k / 24
            outer.append((cx + math.cos(a) * 0.49 * W, cy + math.sin(a) * 0.83 * H))
            inner.append((cx + math.cos(a) * 0.31 * W, cy + math.sin(a) * 0.58 * H))
        pygame.draw.polygon(sf, stone, outer + inner[::-1])
        for k in range(1, 24, 2):   # the arch stones
            pygame.draw.line(sf, edge, outer[k], inner[k], int(2 * u))
        for y in (0.5, 0.64, 0.8):
            pygame.draw.line(sf, edge, (0.02 * W, y * H), (0.19 * W, y * H), int(2 * u))
            pygame.draw.line(sf, edge, (0.81 * W, y * H), (0.98 * W, y * H), int(2 * u))
        pygame.draw.lines(sf, lite, False, outer[3:22], int(3 * u))
        pygame.draw.polygon(sf, edge, outer + inner[::-1], int(2 * u))
        return pygame.transform.smoothscale(sf, (max(2, W // u), max(2, H // u)))


ROCK_KINDS = {"ROCK": Rock, "DRIFTWOOD": Driftwood, "CAVE": Cave, "POT": ClayPot, "SHIP": Shipwreck, "BRIDGE": StoneBridge}


def rock_look(r):
    """Rebuild a piece's picture from its original sprite, its scale and its flip."""
    img = r.img0
    if abs(r.sc - 1.0) > 0.01:
        img = pygame.transform.smoothscale(img, (max(4, int(img.get_width() * r.sc)), max(4, int(img.get_height() * r.sc))))
    if r.fl:
        img = pygame.transform.flip(img, True, False)
    r.image = img


def create_hardscape():
    new_rocks = []
    # Define how many rock outcroppings we want
    num_clusters = round(random.randint(4, 6) * SCREEN_WIDTH / 1320)

    for _ in range(num_clusters):
        # Pick a center for this driftwood cluster
        cluster_x = random.randint(50, SCREEN_WIDTH - 50)
        cluster_z = random.uniform(0.7, 1.2)  # Keep depth consistent per cluster

        # Decide how many rocks are in this specific outcropping
        cluster_size = random.randint(3, 8)

        for i in range(cluster_size):
            # Rocks get more scattered as we move from the cluster center
            spread = 20 + (i * 10)
            x = cluster_x + random.randint(-spread, spread)

            # Stack rocks more aggressively in the center of clusters
            # i < 3 ensures the "core" of the pile is taller
            num_layers = random.randint(1, max(3, round(3 * VS))) if i < 3 else 1

            for layer in range(num_layers):
                # Vertical stacking with slight horizontal jitter for crags
                y_off = -(layer * 18)
                jitter_x = x + random.randint(-10, 10)

                new_rocks.append(Rock(x=jitter_x, z=cluster_z, y_offset=y_off))

    # Add a few "stray" rocks in the sandy channels for realism
    for _ in range(5):
        new_rocks.append(Rock())

    # Driftwood pieces on the sand, drawn with the rocks so they sort by depth too
    for _ in range(random.randint(3, 5)):
        new_rocks.append(Driftwood(x=random.randint(80, SCREEN_WIDTH - 80), z=random.uniform(0.72, 1.1)))

    # Standard depth sorting for proper rendering
    return sorted(new_rocks, key=lambda r: (r.z, -r.y_offset))

SHRIMP_COLORS = [(255, 50, 50, 200), (70, 120, 255, 200), (255, 205, 60, 200)]


class TinyShrimp:
    def __init__(self):
        self.pos = pygame.Vector2(random.randint(50, SCREEN_WIDTH - 50), random.randint(WATER_TOP + 50, SCREEN_HEIGHT - 100))
        self.vel = pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))
        self.acc = pygame.Vector2(0, 0)
        self.z = random.uniform(0.2, 0.4)
        self.max_speed = 3.5
        self.gene = 0   # 0 red, 1 blue, 2 yellow
        self.base_color = (255, 50, 50, 200)
        self.trail = []
        self.is_eating = False
        self.eating_timer = 0
        self.target_algae = None
        self.female = random.random() < 0.55
        self.age = random.randint(4000, 9000)
        self.adult_z = self.z
        self.berried = 0
        self.moult_t = random.randint(1500, 5000)

    def life_step(self):
        """Cherry shrimp life: shrimplets grow, berried females carry eggs, and everyone sheds a shell now and then."""
        self.age += 1
        if self.age < 3600:
            self.z = self.adult_z * (0.45 + 0.55 * self.age / 3600)
        if self.berried > 0:
            self.berried -= 1
            if self.berried == 0:
                n = random.randint(2, 4)
                made = 0
                for _ in range(n):
                    if len(shimps) >= 44:
                        break
                    kid = TinyShrimp()
                    kid.pos = pygame.Vector2(self.pos) + (random.uniform(-6, 6), random.uniform(-4, 4))
                    kid.age, kid.z = 0, kid.adult_z * 0.45
                    kid.female = random.random() < 0.55
                    g = random.choice((self.gene, random.choice(shimps).gene))
                    if random.random() < 0.08:
                        g = random.randint(0, 2)
                    kid.gene = g
                    kid.base_color = SHRIMP_COLORS[g]
                    shimps.append(kid)
                    made += 1
                if made:
                    stats["shrimplets"] += made
                    notify(f"{made} shrimplets hatched", log=False)
        elif (self.female and self.age > 5000 and eco is not None and eco.water > 55 and len(shimps) < 40
              and random.random() < 0.00004):
            self.berried = 1500
        self.moult_t -= 1
        if self.moult_t <= 0:
            self.moult_t = random.randint(3000, 7000)
            if len(moult_shells) < 30:
                moult_shells.append([self.pos.x, self.pos.y, self.vel.x >= 0, 900, self.z])
            self.vel += pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 0.2))
            stats["moults"] += 1

    def update(self, algae_list):
        self.life_step()
        self.trail.append(list(self.pos))
        if len(self.trail) > 40:
            self.trail.pop(0)

        if not self.target_algae and algae_list:
            nearby = [a for a in algae_list if self.pos.distance_to(pygame.Vector2(a)) < 120]
            if nearby:
                self.target_algae = nearby[0]

        if self.target_algae:
            direction = (pygame.Vector2(self.target_algae) - self.pos)
            if direction.length() > 2:
                self.pos += direction.normalize() * 0.3
            else:
                if self.target_algae in algae_list:
                    algae_list.remove(self.target_algae)
                self.target_algae = None
        else:
            self.pos += self.vel
            if random.random() < 0.01:
                self.vel = pygame.Vector2(random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))

        if self.pos.x < 10 or self.pos.x > SCREEN_WIDTH - 10: self.vel.x *= -1
        if self.pos.y < WATER_TOP + 10 or self.pos.y > SCREEN_HEIGHT - 30: self.vel.y *= -1

    def draw(self, surface):
        z, x, y = self.z, self.pos.x, self.pos.y
        facing = self.vel.x >= 0
        t = pygame.time.get_ticks() * 0.01

        s_size = 40 * z
        shrimp_surf = pygame.Surface((s_size * 2, s_size), pygame.SRCALPHA)
        cx, cy = s_size, s_size // 2

        leg_speed = 5 if self.is_eating else 1
        leg_wave = math.sin(t * leg_speed) * (4 * z)

        ant_wave = math.sin(t) * (5 * z)
        ant_col = (255, 255, 255, 120)
        pygame.draw.line(shrimp_surf, ant_col, (cx + 2 * z, cy - 2 * z), (cx + 15 * z, cy - 10 * z + ant_wave), 1)

        pygame.draw.ellipse(shrimp_surf, self.base_color, (cx - 5 * z, cy - 6 * z, 12 * z, 10 * z))
        for i in range(4):
            sx, sy = cx - (i * 5 * z), cy + (i * 2 * z)
            pygame.draw.circle(shrimp_surf, (*mix(self.base_color, (255, 255, 255), 0.12 + 0.08 * i), 180), (int(sx), int(sy)),
                               int((5 - i) * z))

        if self.berried > 0:   # a saddle of green eggs under the tail
            for i in range(5):
                pygame.draw.circle(shrimp_surf, (150, 210, 90, 230), (int(cx - (2 + i * 2.2) * z), int(cy + 5 * z)), max(1, int(1.4 * z)))
        tail_flick = math.sin(t * 2) * (3 * z)
        pygame.draw.polygon(shrimp_surf, self.base_color,
                            [(cx - 15 * z, cy + 6 * z), (cx - 22 * z, cy + 10 * z + tail_flick),
                             (cx - 22 * z, cy + 2 * z + tail_flick)])

        pygame.draw.circle(shrimp_surf, (10, 10, 10), (int(cx + 4 * z), int(cy - 2 * z)), max(1, int(1.5 * z)))

        if self.is_eating:
            pygame.draw.line(shrimp_surf, (255, 255, 255, 200), (cx + 2 * z, cy + 2 * z),
                             (cx + 6 * z + leg_wave, cy + 8 * z), 1)
            pygame.draw.line(shrimp_surf, (255, 255, 255, 200), (cx + 4 * z, cy + 2 * z),
                             (cx + 8 * z - leg_wave, cy + 8 * z), 1)

        for i in range(3):
            lx = cx - (i * 4 * z)
            pygame.draw.line(shrimp_surf, (255, 255, 255, 100), (lx, cy + 4 * z),
                             (lx - 2 * z, cy + 8 * z + (leg_wave if self.is_eating else 0)), 1)

        final = shrimp_surf if facing else pygame.transform.flip(shrimp_surf, True, False)
        surface.blit(final, final.get_rect(center=(int(x), int(y))))

class Daphnia:
    """A water flea: a hopping, translucent speck of live food that small fish chase."""

    def __init__(self):
        self.pos = pygame.Vector2(random.randint(50, SCREEN_WIDTH - 50), random.randint(WATER_TOP + 50, SCREEN_HEIGHT - 100))
        self.vel = pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))
        self.acc = pygame.Vector2(0, 0)
        self.z = random.uniform(0.25, 0.45)
        self.max_speed = 2.5
        self.base_color = (226, 186, 110)
        self.nutrition = 5
        self.is_alive = True
        self.phase = random.uniform(0, math.tau)

    def apply_force(self, force):
        self.acc += force

    def behavior(self):
        if random.random() < 0.012:  # a hop
            self.apply_force(pygame.Vector2(random.uniform(-2, 2), random.uniform(-2.4, 0.4)))
        self.apply_force(pygame.Vector2(0.01, 0.012))  # they sink between hops

    def update(self):
        self.vel += self.acc
        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)
        self.pos += self.vel
        self.acc *= 0
        self.vel *= 0.985

    def draw(self, surface):
        z, x, y = self.z, int(self.pos.x), int(self.pos.y)
        t = pygame.time.get_ticks() * 0.012 + self.phase
        r = max(2, int(5 * z * 2))
        beat = math.sin(t * 2.2) * 3 * z
        dirx = 1 if self.vel.x >= 0 else -1
        pygame.draw.line(surface, (240, 225, 190), (x + dirx * r * 0.5, y - r * 0.3), (x + dirx * (r + 4 * z * 2), y - r * 0.9 + beat), 1)
        pygame.draw.line(surface, (240, 225, 190), (x + dirx * r * 0.5, y - r * 0.1), (x + dirx * (r + 4 * z * 2), y - r * 0.2 - beat), 1)
        pygame.draw.ellipse(surface, self.base_color, (x - r, y - r * 0.8, r * 2, r * 1.6))
        pygame.draw.ellipse(surface, (250, 232, 190), (x - r * 0.8, y - r * 0.7, r * 1.2, r * 0.7))
        pygame.draw.circle(surface, (210, 60, 60), (x - dirx * int(r * 0.1), y), max(1, r // 4))
        pygame.draw.circle(surface, (10, 10, 12), (x + dirx * int(r * 0.6), y - int(r * 0.25)), max(1, r // 4))
        pygame.draw.ellipse(surface, (170, 130, 80), (x - r, y - r * 0.8, r * 2, r * 1.6), 1)


# ---- plants: a little physics (water flow, wakes, springy sway) and natural, shaded shapes ----
PLANT_CLOCK = 0
PLANT_BUCKETS = {}


def water_flow(x, t, cur):
    """Sideways push of the water at a position: slow swells that travel across the tank, a gusty envelope, and the
    event current on top."""
    gust = 1.0 + 0.5 * math.sin(t * 0.0021 + x * 0.0007)
    return (5.0 * math.sin(x * 0.0042 - t * 0.010) + 2.2 * math.sin(x * 0.011 + t * 0.017 + 2.0)) * gust + cur


def blade_normals(pts):
    n = len(pts)
    nrm = []
    hyp = math.hypot
    last = n - 1
    for i in range(n):
        a = pts[i - 1 if i else 0]
        b = pts[i + 1 if i < last else last]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = hyp(dx, dy) or 1.0
        nrm.append((-dy / ln, dx / ln))
    return nrm


def draw_blade(surface, pts, widths, cols, highlight=None):
    """A tapered ribbon along a centre line, painted in bands from base colour to tip colour so it reads as a gradient.
    cols is (base, mid, tip)."""
    n = len(pts)
    nrm = blade_normals(pts)
    left = [(p[0] + nx * w * 0.5, p[1] + ny * w * 0.5) for p, (nx, ny), w in zip(pts, nrm, widths)]
    right = [(p[0] - nx * w * 0.5, p[1] - ny * w * 0.5) for p, (nx, ny), w in zip(pts, nrm, widths)]
    cuts = (0, max(1, n // 3), max(2, 2 * n // 3), n - 1)
    for b in range(3):
        a, z = cuts[b], min(n - 1, cuts[b + 1] + 1)
        if z - a < 1:
            continue
        pygame.draw.polygon(surface, cols[b], left[a:z + 1] + right[a:z + 1][::-1])
    if highlight is not None and n > 2:
        pygame.draw.lines(surface, highlight, False, pts[1:-1], 1)


_POW16 = {}


def blade_centerline(px, py, length, n, tilt, curl, lean, flutter, phase, clock, droop=0.0):
    pts = []
    sin, cos = math.sin, math.cos
    st, ct = length * sin(tilt), length * cos(tilt)
    pw = _POW16.get(n)
    if pw is None:
        pw = _POW16[n] = [(i / n) ** 1.6 for i in range(n + 1)]
    lean_k = lean * length / 110.0
    flut_k = flutter * (length / 140.0)
    base_ph = clock * 0.05 + phase
    cl, dr = curl * length, droop * length * 0.45
    for i in range(n + 1):
        s = i / n
        s2 = s * s
        x = px + st * s + cl * s2 + lean_k * pw[i] + sin(base_ph + s * 3.2) * flut_k * s2
        y = py - ct * s + dr * s2
        pts.append((x, y))
    return pts


class Plant:
    lift = 0       # pixels above the sand it grows from (java fern on wood)
    hp = 1.0       # health 0.2..1: pale and yellow when starved, shaded or nibbled
    depth = 0      # 0 front, 1 middle, 2 back: a back plant is hazier and is drawn behind the rest
    nib = 0        # fresh nibble marks from plant-eating fish
    bloom = 0      # days of flowering left
    psize = 1.0    # how much bigger or smaller than the plant it was born as
    hang = False   # hangs from the surface instead of standing on the sand
    layer = "mid"   # pothos only: which depth layer it is drawn in (bg behind the fish, mid with the plants, fg in front)
    sc = 1.0       # pothos only: size of leaves and stems (bigger in front, smaller behind)
    shade = 1.0    # pothos only: brightness (distant vines sink into the water)

    def __init__(self, x, species_type):
        self.pos_x = x
        self.species = species_type
        self.tint = random.randint(-18, 18)
        self.phase = random.uniform(0, math.tau)
        self.lean = 0.0   # how far the water is currently pushing it (springy: overshoots, settles)
        self.vel = 0.0
        self.push = 0.0   # extra push this frame from fish swimming past
        self.segments = 10
        self.wake = 1.0   # how strongly passing fish stir it
        q = (self.phase * 7.31) % 1.0   # per-plant traits come from the existing phase, so a saved tank's random stream is untouched
        self.flower = (0.3 + 0.7 * ((q * 13.7) % 1.0)) if (q < 0.18 and species_type == "Vallisneria") else 0
        self.sori = q > 0.4
        hs = VS ** 0.75
        if species_type in ("Rotala", "Ludwigia", "Cabomba", "Hygrophila"):
            self.height = random.randint(170, 320) * hs if species_type in ("Rotala", "Cabomba") else random.randint(130, 250) * hs
            self.gain, self.stiff, self.damp = 0.85, 0.0055, 0.06
            self.hue = random.random()
            self.stems = [(random.uniform(-18, 18), random.uniform(-0.2, 0.2), random.uniform(0.6, 1.0) * self.height, random.uniform(0, math.tau))
                          for _ in range(random.randint(3, 5))]
        elif species_type == "Vallisneria":
            self.height = random.randint(130, 260) * hs
            self.gain, self.stiff, self.damp = 0.9, 0.006, 0.07
            self.blades = [(random.uniform(-9, 9), random.uniform(-0.22, 0.22), random.uniform(0.6, 1.0) * self.height,
                            random.uniform(5, 8), random.uniform(0, math.tau), random.uniform(-0.12, 0.12))
                           for _ in range(random.randint(6, 9))]
        elif species_type == "Hairgrass":
            self.height = random.randint(55, 100) * hs
            self.gain, self.stiff, self.damp = 1.1, 0.009, 0.09
            self.wake = 1.4
            self.blades = [(random.uniform(-12, 12), random.uniform(-0.5, 0.5), random.uniform(0.65, 1.0) * self.height,
                            random.uniform(3, 5), random.uniform(0, math.tau), random.uniform(0.4, 1.0))
                           for _ in range(random.randint(8, 11))]
        elif species_type == "TigerLotus":
            self.height = random.randint(80, 160) * hs
            self.gain, self.stiff, self.damp = 0.55, 0.008, 0.08
            self.stalks = [(random.uniform(-8, 8), random.uniform(-0.35, 0.35), random.uniform(0.6, 1.0) * self.height,
                            random.uniform(0.85, 1.2), random.uniform(0, math.tau)) for _ in range(random.randint(3, 5))]
        elif species_type == "Anubias":
            self.height = 50
            self.gain, self.stiff, self.damp = 0.15, 0.02, 0.15
            self.wake = 0.4
            self.leaves = sorted([(random.uniform(-1.25, 1.25), random.uniform(10, 24), random.uniform(24, 36),
                                   random.uniform(0, math.tau)) for _ in range(random.randint(6, 8))], key=lambda l: abs(l[0]), reverse=True)
        elif species_type == "DwarfGrass":   # a dense little carpet tuft
            self.height = random.randint(22, 40) * hs
            self.gain, self.stiff, self.damp = 1.2, 0.01, 0.1
            self.wake = 1.5
            self.blades = [(random.uniform(-17, 17), random.uniform(-0.45, 0.45), random.uniform(0.6, 1.0) * self.height,
                            random.uniform(2.2, 3.6), random.uniform(0, math.tau), random.uniform(0.3, 1.0))
                           for _ in range(random.randint(12, 17))]
        elif species_type == "Cryptocoryne":   # a low rosette of wavy leaves, bronze or green
            self.height = 42 * hs
            self.gain, self.stiff, self.damp = 0.3, 0.02, 0.15
            self.wake = 0.5
            self.bronze = random.random() < 0.5
            self.leaves = sorted([(random.uniform(-1.25, 1.25), random.uniform(8, 16), random.uniform(20, 31), random.uniform(0, math.tau))
                                  for _ in range(random.randint(7, 10))], key=lambda l: abs(l[0]), reverse=True)
        elif species_type == "Clover":   # Marsilea: short stalks topped with four-leaf clovers
            self.height = random.randint(26, 46) * hs
            self.gain, self.stiff, self.damp = 0.8, 0.008, 0.08
            self.stalks = [(random.uniform(-15, 15), random.uniform(-0.3, 0.3), random.uniform(0.55, 1.0) * self.height,
                            random.uniform(0.8, 1.2), random.uniform(0, math.tau)) for _ in range(random.randint(5, 8))]
        elif species_type == "MossBall":   # a round, fuzzy marimo moss ball resting on the sand
            self.height = 16
            self.gain, self.stiff, self.damp = 0.0, 0.02, 0.2
            self.wake = 0.0
            self.radius = random.uniform(9, 15) * hs
            self.dots = [(random.uniform(0, math.tau), random.uniform(0, 0.85), random.randrange(3)) for _ in range(28)]
        elif species_type == "JavaFern":   # tied to driftwood: a fountain of long, dark, ribbed leaves
            self.height = 70 * hs
            self.gain, self.stiff, self.damp = 0.35, 0.012, 0.12
            self.wake = 0.6
            self.leaves = [(random.uniform(-1.0, 1.0), random.uniform(34, 62) * hs, random.uniform(4.5, 7.0), random.uniform(0, math.tau))
                           for _ in range(random.randint(9, 13))]
        elif species_type == "Pothos":   # trailing vines hanging from the surface, with heart-shaped leaves
            self.height = 1
            self.hang = True
            self.gain, self.stiff, self.damp = 0.5, 0.01, 0.1
            self.wake = 0.0
            self.vines = [(random.uniform(-16, 16), random.uniform(-0.3, 0.3), (70 + random.uniform(150, 360)) * hs, random.uniform(0, math.tau))
                          for _ in range(random.randint(5, 7))]
        else:  # Amazon sword: a rosette of broad, arching leaves
            self.height = random.randint(130, 210) * hs
            self.gain, self.stiff, self.damp = 0.55, 0.008, 0.09
            self.leaves = [(random.uniform(-0.95, 0.95), random.uniform(0.7, 1.0) * self.height, random.uniform(12, 19), random.uniform(0, math.tau))
                           for _ in range(random.randint(9, 13))]

    def step(self, t, cur):
        target = water_flow(self.pos_x, t, cur) * self.gain + max(-14.0, min(14.0, self.push))
        self.push = 0.0
        self.vel += (target - self.lean) * self.stiff - self.vel * self.damp
        self.lean = max(-24.0, min(24.0, self.lean + self.vel))

    # ---- drawing ----
    def draw(self, surface, frame):
        if self.hang:
            getattr(self, "_draw_" + self.species.lower())(surface, -70, PLANT_CLOCK)   # rooted above the screen so the bare top of each stem is out of sight
            return
        base_y = ground_y(self.pos_x) - self.lift
        if random.random() < 0.002:
            bubbles.append(Bubble(self.pos_x, base_y))
        if not self.lift:
            pygame.draw.ellipse(surface, (52, 42, 28, 120), (self.pos_x - 15, base_y - 3, 30, 8))
        getattr(self, "_draw_" + self.species.lower())(surface, base_y, PLANT_CLOCK)
        if self.bloom:
            self._draw_bloom(surface, base_y, PLANT_CLOCK)
        if self.nib >= 2:   # nibbled: a few brown patches on the leaves
            r = random.Random(int(self.phase * 1000))
            for _ in range(min(7, self.nib + 1)):
                hh = max(30, self.height)
                pygame.draw.circle(surface, (150, 120, 62), (int(self.pos_x + r.uniform(-18, 18) + self.lean * 0.1), int(base_y - r.uniform(0.15, 0.8) * hh)), r.choice((2, 2, 3)))

    def _draw_bloom(self, surface, base_y, clock):
        x = self.pos_x + self.lean * 0.15
        sway = math.sin(clock * 0.03 + self.phase) * 2
        if self.species == "Anubias":   # a white spathe wrapped round a yellow spadix
            pygame.draw.line(surface, (110, 150, 90), (x + 4, base_y - 2), (x + 6 + sway, base_y - 34), 2)
            pygame.draw.ellipse(surface, (246, 244, 226), (x + 1 + sway, base_y - 52, 11, 22))
            pygame.draw.ellipse(surface, (236, 206, 84), (x + 4 + sway, base_y - 44, 4, 12))
        elif self.species == "Cryptocoryne":   # a tall, twisted, maroon spathe
            pts = [(x + math.sin(i * 0.8 + clock * 0.04) * 2, base_y - 4 - i * 5) for i in range(9)]
            pygame.draw.lines(surface, (150, 48, 84), False, pts, 4)
            pygame.draw.line(surface, (200, 96, 130), pts[-2], (pts[-1][0] + sway, pts[-1][1] - 8), 2)
        else:   # a sword plant sends up a flower stalk with small white flowers
            top = max(WATER_TOP + 30, base_y - self.height * 0.95)
            pts = [(x + 6 + self.lean * 0.3 * (1 - i / 8.0) + math.sin(clock * 0.03 + i) * 1.5, base_y - (base_y - top) * i / 8.0) for i in range(9)]
            pygame.draw.lines(surface, (110, 160, 90), False, pts, 2)
            for i in (3, 5, 7, 8):
                pygame.draw.circle(surface, (244, 246, 240), (int(pts[i][0]), int(pts[i][1])), 3)
                pygame.draw.circle(surface, (236, 210, 90), (int(pts[i][0]), int(pts[i][1])), 1)

    def _col(self, rgb, k=1.0):
        hp = self.hp
        key = (rgb, k, int(hp * 10), self.depth)
        try:
            return self._colc[key]
        except AttributeError:
            self._colc = {}
        except KeyError:
            pass
        t = self.tint
        c = (max(0, min(255, int((rgb[0] + t) * k))), max(0, min(255, int((rgb[1] + t * 0.6) * k))),
             max(0, min(255, int((rgb[2] + t * 0.3) * k))))
        if hp < 0.99:   # starved or shaded plants go pale and yellow
            c = mix(c, (160, 140, 62), min(0.8, (1.0 - hp) * 0.95))
        if self.depth:   # distance haze: the water takes the colour out of far plants
            c = mix(c, (30, 78, 118), (0.0, 0.22, 0.42)[self.depth])
        self._colc[key] = c
        return c

    def _stem_pts(self, dx, tilt, length, ph, clock, base_y, n, lively=1.5):
        pts = blade_centerline(self.pos_x + dx, base_y, length, n, tilt, 0.04, self.lean, lively + abs(self.lean) * 0.2, ph, clock)
        return [(x, max(WATER_TOP + 4, y)) for x, y in pts]

    def _draw_rotala(self, surface, base_y, clock):
        """Rotala: thin stems, dense whorls of narrow needle leaves, green below and pink-red in the sun-facing tips."""
        top_c = mix((160, 205, 96), (236, 104, 142), self.hue)
        for dx, tilt, length, ph in self.stems:
            n = 16
            pts = self._stem_pts(dx, tilt, length, ph, clock, base_y, n)
            pygame.draw.lines(surface, self._col((86, 120, 62)), False, pts, 1)
            for i in range(2, n + 1):
                s = i / n
                px, py = pts[i]
                ll = 13 * self.psize ** 0.5 * (1.0 - 0.5 * s) * (0.9 + 0.1 * math.sin(ph + i * 1.9))
                col = self._col(mix((60, 142, 66), top_c, s ** 1.2))
                sway = math.sin(clock * 0.04 + ph + i * 0.8) * 1.2
                for side in (-1, 1):
                    for rise in (0.2, 0.62):   # two needles per side, one flatter, one more upright
                        pygame.draw.line(surface, col, (px, py), (px + side * ll * (1 - rise * 0.6), py - ll * rise + sway), 1)
            tx, ty = pts[-1]
            pygame.draw.circle(surface, self._col(top_c, 1.1), (int(tx), int(ty)), 3)
            pygame.draw.circle(surface, self._col(top_c, 1.25), (int(tx), int(ty) - 3), 2)

    def _draw_ludwigia(self, surface, base_y, clock):
        """Ludwigia: a woody red-brown stem with broad oval leaves in opposite pairs, olive on top and wine red underneath."""
        top_c = mix((120, 150, 60), (178, 44, 52), self.hue)
        for dx, tilt, length, ph in self.stems:
            n = 9
            pts = self._stem_pts(dx, tilt, length, ph, clock, base_y, n, 1.2)
            pygame.draw.lines(surface, self._col((104, 66, 46)), False, pts, 3)
            for i in range(2, n + 1):
                s = i / n
                px, py = pts[i]
                ll = 25 * self.psize ** 0.5 * (1.0 - 0.5 * s) * (0.9 + 0.1 * math.sin(ph + i * 1.7))
                flap = math.sin(clock * 0.035 + ph + i * 0.9) * 7
                up = self._col(mix((84, 122, 46), top_c, s ** 1.2))
                under = self._col((150, 34, 44), 0.7 + 0.3 * s)
                for side in (-1, 1):
                    ang = 90 - side * (52 - 14 * s) + side * flap
                    r = math.radians(ang)
                    draw_leaf(surface, (px + math.cos(r) * ll * 0.5, py - math.sin(r) * ll * 0.5), ll, ll * 0.62, ang, up, under, self._col((196, 120, 96)))
            tx, ty = pts[-1]
            pygame.draw.circle(surface, self._col(top_c, 1.1), (int(tx), int(ty)), 3)

    def _draw_cabomba(self, surface, base_y, clock):
        """Cabomba: feathery fan leaves. Each node carries a half-round fan of fine forked threads, so the stem looks like a green plume."""
        for dx, tilt, length, ph in self.stems:
            n = 11
            pts = self._stem_pts(dx, tilt, length, ph, clock, base_y, n, 2.0)
            pygame.draw.lines(surface, self._col((70, 118, 80)), False, pts, 1)
            for i in range(1, n + 1):
                s = i / n
                px, py = pts[i]
                rr = 17 * self.psize ** 0.5 * (1.0 - 0.55 * s)
                col = self._col(mix((46, 120, 88), (150, 214, 130), s ** 1.3))
                tip_col = self._col(mix((84, 160, 112), (190, 236, 150), s ** 1.3))
                wob = math.sin(clock * 0.045 + ph + i * 0.7) * 0.12
                for k in range(7):
                    a = math.pi * (0.06 + 0.88 * k / 6) + wob   # 7 threads across the upper half circle
                    ex, ey = px + math.cos(a) * rr, py - math.sin(a) * rr * 0.75
                    mx, my = px + math.cos(a) * rr * 0.55, py - math.sin(a) * rr * 0.75 * 0.55
                    pygame.draw.line(surface, col, (px, py), (mx, my), 1)
                    for fork in (-0.28, 0.28):   # each thread forks near the end
                        fx, fy = px + math.cos(a + fork) * rr, py - math.sin(a + fork) * rr * 0.75
                        pygame.draw.line(surface, tip_col, (mx, my), (fx, fy), 1)
            tx, ty = pts[-1]
            pygame.draw.circle(surface, self._col((170, 226, 140)), (int(tx), int(ty)), 2)

    def _draw_hygrophila(self, surface, base_y, clock):
        """Hygrophila: a stout stem with big lance-shaped leaves that alternate left and right and arch down a little."""
        for dx, tilt, length, ph in self.stems:
            n = 8
            pts = self._stem_pts(dx, tilt, length, ph, clock, base_y, n, 1.0)
            pygame.draw.lines(surface, self._col((100, 110, 60)), False, pts, 3)
            for i in range(1, n + 1):
                s = i / n
                px, py = pts[i]
                ll = 34 * self.psize ** 0.5 * (1.0 - 0.45 * s) * (0.92 + 0.08 * math.sin(ph + i * 1.3))
                side = 1 if (i + int(ph * 3)) % 2 else -1
                bend = math.sin(clock * 0.03 + ph + i) * 6
                ang = 90 - side * (66 - 12 * s) + side * bend
                r = math.radians(ang)
                draw_leaf(surface, (px + math.cos(r) * ll * 0.5, py - math.sin(r) * ll * 0.5), ll, ll * 0.3, ang,
                          self._col(mix((84, 130, 52), (176, 196, 84), s)), self._col((54, 92, 40)), self._col((200, 224, 140)))
            tx, ty = pts[-1]
            for side in (-1, 1):   # the growing tip: two small upright leaves
                draw_leaf(surface, (tx + side * 3, ty - 6), 14, 5, 90 - side * 22, self._col((190, 210, 100)), self._col((110, 150, 60)), self._col((220, 236, 170)))

    def _draw_vallisneria(self, surface, base_y, clock):
        flut = 2.0 + abs(self.lean) * 0.25
        for dx, tilt, length, width, ph, curl in self.blades:
            pts = blade_centerline(self.pos_x + dx, base_y, length, 9, tilt, curl, self.lean, flut, ph, clock)
            pts = [(x, max(WATER_TOP + 4, y)) for x, y in pts]
            widths = [width * (1 - (i / 9) ** 4) * (0.85 + 0.15 * math.sin(i * 1.3 + ph)) + 0.6 for i in range(10)]
            draw_blade(surface, pts, widths, (self._col((20, 70, 34)), self._col((38, 118, 52)), self._col((100, 168, 76))),
                       self._col((130, 196, 110)))
        if self.flower:   # a female plant: a thin coiled stalk carries a small white three-petal flower up to the surface
            fx, fy = self.pos_x + 5, base_y
            top = max(WATER_TOP + 20, base_y - self.height * (0.75 + 0.3 * self.flower))
            pts = [(fx + math.sin(i * 0.9 + self.phase) * 3 + self.lean * 0.1 * (base_y - y) / 100.0, y)
                   for i, y in enumerate(range(int(base_y), int(top), -5))]
            if len(pts) > 2:
                pygame.draw.lines(surface, self._col((120, 170, 110)), False, pts, 1)
                ex, ey = pts[-1]
                for k in range(3):
                    a = k * math.tau / 3 + math.sin(clock * 0.03 + self.phase) * 0.2
                    pygame.draw.circle(surface, (236, 240, 236), (int(ex + math.cos(a) * 3), int(ey + math.sin(a) * 2)), 2)
                pygame.draw.circle(surface, (236, 210, 90), (int(ex), int(ey)), 1)

    def _draw_hairgrass(self, surface, base_y, clock):
        flut = 3.0 + abs(self.lean) * 0.35
        for dx, tilt, length, width, ph, droop in self.blades:
            pts = blade_centerline(self.pos_x + dx, base_y, length, 7, tilt, math.sin(ph) * 0.18, self.lean, flut, ph, clock, droop)
            widths = [max(0.8, width * (1 - i / 7) ** 0.7) for i in range(8)]
            draw_blade(surface, pts, widths, (self._col((40, 96, 44)), self._col((84, 150, 62)), self._col((150, 196, 100))), None)
            if width > 4.2:   # the broader blades end in a tiny pale seed head
                pygame.draw.circle(surface, self._col((214, 220, 150)), (int(pts[-1][0]), int(pts[-1][1])), 1)

    def _draw_tigerlotus(self, surface, base_y, clock):
        flut = 2.0 + abs(self.lean) * 0.2
        red = (176 + self.tint, 52, 66)
        for dx, tilt, length, size, ph in self.stalks:
            pts = blade_centerline(self.pos_x + dx, base_y, length, 6, tilt, 0.05, self.lean, flut, ph, clock)
            pygame.draw.lines(surface, (118, 40, 48), False, pts, 2)
            tx, ty = pts[-1]
            ang = (pts[-2][0] - pts[-1][0]) * 1.2 + math.sin(clock * 0.04 + ph) * 6
            draw_leaf(surface, (tx, ty - 6), 44 * size, 28 * size, ang, tone(red, 1.25), tone(red, 0.6), (96, 28, 40))
            mx, my = pts[3]
            draw_leaf(surface, (mx + (10 if dx > 0 else -10), my), 26 * size, 16 * size, 20 + math.sin(clock * 0.05 + ph) * 8,
                      tone(red, 1.0), tone(red, 0.55), (96, 28, 40))

    def _draw_anubias(self, surface, base_y, clock):
        pygame.draw.line(surface, (95, 75, 50), (self.pos_x - 14, base_y), (self.pos_x + 14, base_y), 3)
        for ang, petiole, length, ph in self.leaves:
            a = ang + self.lean * 0.01 + math.sin(clock * 0.02 + ph) * 0.04
            tip = (self.pos_x + math.sin(a) * petiole, base_y - 4 - math.cos(a) * petiole)
            pygame.draw.line(surface, (70, 110, 55), (self.pos_x, base_y - 2), tip, 2)
            c = (tip[0] + math.sin(a) * length * 0.5, tip[1] - math.cos(a) * length * 0.5)
            draw_leaf(surface, c, length, length * 0.62, 90 - math.degrees(a), (96, 156, 76), (28, 74, 34), (170, 214, 140))

    def _draw_dwarfgrass(self, surface, base_y, clock):
        flut = 2.0 + abs(self.lean) * 0.3
        for dx, tilt, length, width, ph, droop in self.blades:
            pts = blade_centerline(self.pos_x + dx, base_y, length, 5, tilt, math.sin(ph) * 0.15, self.lean, flut, ph, clock, droop * 0.5)
            widths = [max(0.8, width * (1 - i / 5) ** 0.7) for i in range(6)]
            draw_blade(surface, pts, widths, (self._col((52, 120, 52)), self._col((110, 186, 76)), self._col((176, 224, 112))), None)

    def _draw_cryptocoryne(self, surface, base_y, clock):
        x = self.pos_x
        pygame.draw.ellipse(surface, (58, 46, 30), (x - 9, base_y - 3, 18, 6))
        top, bot, vein = (((158, 116, 64), (72, 46, 28), (216, 178, 112)) if self.bronze else ((98, 152, 70), (34, 84, 40), (170, 208, 128)))
        for ang, petiole, length, ph in self.leaves:
            a = ang + self.lean * 0.008 + math.sin(clock * 0.02 + ph) * 0.05
            tip = (x + math.sin(a) * petiole, base_y - 3 - math.cos(a) * petiole)
            pygame.draw.line(surface, (88, 92, 52), (x, base_y - 2), tip, 2)
            c = (tip[0] + math.sin(a) * length * 0.5, tip[1] - math.cos(a) * length * 0.5)
            draw_leaf(surface, c, length, length * 0.5, 90 - math.degrees(a), self._col(top), self._col(bot), self._col(vein))

    def _draw_clover(self, surface, base_y, clock):
        flut = 1.5 + abs(self.lean) * 0.15
        for dx, tilt, length, size, ph in self.stalks:
            pts = blade_centerline(self.pos_x + dx, base_y, length, 4, tilt, 0.04, self.lean, flut, ph, clock)
            pygame.draw.lines(surface, self._col((74, 130, 58)), False, pts, 1)
            tx, ty = pts[-1]
            r = 5.5 * size
            spin = math.sin(clock * 0.03 + ph) * 0.4
            for k in range(4):
                a = spin + k * math.pi / 2 + math.pi / 4
                pygame.draw.circle(surface, self._col((84, 170, 76)), (int(tx + math.cos(a) * r * 0.9), int(ty + math.sin(a) * r * 0.72 - r * 0.2)), max(2, int(r * 0.75)))
            pygame.draw.circle(surface, self._col((146, 208, 112)), (int(tx), int(ty - r * 0.2)), max(1, int(r * 0.34)))

    def _draw_mossball(self, surface, base_y, clock):
        r = self.radius
        cx, cy = self.pos_x, base_y - r * 0.55
        pygame.draw.circle(surface, (36, 84, 38), (int(cx), int(cy)), int(r))
        shades = ((66, 136, 54), (94, 168, 66), (126, 194, 86))
        for a, d, k in self.dots:
            pygame.draw.circle(surface, self._col(shades[k]), (int(cx + math.cos(a) * d * r), int(cy + math.sin(a) * d * r * 0.9)), max(2, int(r * 0.27)))
        pygame.draw.circle(surface, (170, 216, 120), (int(cx - r * 0.3), int(cy - r * 0.35)), max(1, int(r * 0.16)))

    def _draw_javafern(self, surface, base_y, clock):
        flut = 1.8 + abs(self.lean) * 0.2
        for tilt, length, width, ph in sorted(self.leaves, key=lambda l: -abs(l[0])):
            pts = blade_centerline(self.pos_x, base_y, length, 7, tilt, tilt * 0.1, self.lean, flut, ph, clock, droop=0.35 * abs(tilt))
            widths = [width * math.sin(math.pi * (0.1 + 0.8 * i / 7)) ** 0.7 + 0.6 for i in range(8)]
            draw_blade(surface, pts, widths, (self._col((20, 66, 36)), self._col((40, 104, 50)), self._col((96, 150, 70))),
                       self._col((124, 172, 96)))
            if self.sori:   # mature fronds carry two rows of brown spore dots
                for i in range(3, 7):
                    qx, qy = pts[i]
                    for sgn in (-1, 1):
                        pygame.draw.circle(surface, (112, 82, 44), (int(qx + sgn * widths[i] * 0.22), int(qy)), 1)

    def _draw_pothos(self, surface, base_y, clock):
        top = base_y + 2
        k, sc = self.shade, self.sc
        ng = eco.night if eco is not None else 0.0   # leaves droop and close up a little after dark
        lf = 1.0 - 0.16 * ng
        stem, lt, lb, lv = self._col((70, 112, 48), k), self._col((112, 176, 76), k), self._col((40, 98, 44), k), self._col((170, 214, 120), k)
        for dx, tilt, length, ph in self.vines:
            pts = blade_centerline(self.pos_x + dx * sc, 0, length, 8, tilt, 0.05, self.lean, 1.2, ph, clock)
            pts = [(x, top - y) for x, y in pts]   # same springy curve, flipped to hang downward
            pygame.draw.lines(surface, stem, False, pts, max(2, int(2 * sc)))
            for i in range(1, 9):
                px, py = pts[i]
                for side in (-1, 1):
                    sz = (1.0 + 0.25 * math.sin(ph + i * 2.1 + side)) * sc
                    draw_leaf(surface, (px + side * 7 * sc, py + 3 + side), 17 * sz * lf, 12 * sz * lf,
                              90 + side * (38 - 20 * ng) + math.sin(clock * 0.03 + ph + i) * 8, lt, lb, lv)

    def _draw_sword(self, surface, base_y, clock):
        flut = 2.5 + abs(self.lean) * 0.3
        pygame.draw.ellipse(surface, (60, 48, 30), (self.pos_x - 10, base_y - 4, 20, 8))
        for tilt, length, width, ph in sorted(self.leaves, key=lambda l: -abs(l[0])):
            pts = blade_centerline(self.pos_x, base_y, length, 9, tilt, tilt * 0.12, self.lean, flut, ph, clock, droop=0.3 * abs(tilt))
            widths = [width * math.sin(math.pi * (0.06 + 0.86 * i / 9)) ** 0.8 + 0.8 for i in range(10)]
            draw_blade(surface, pts, widths, (self._col((26, 86, 40)), self._col((48, 138, 58)), self._col((112, 178, 80))), self._col((156, 208, 124)))
            vc = self._col((100, 168, 78))
            for i in (3, 5, 7):   # slanting side veins off the midrib
                vx, vy = pts[i]
                pygame.draw.line(surface, vc, (vx, vy), (vx - widths[i] * 0.42, vy - widths[i] * 0.22), 1)
                pygame.draw.line(surface, vc, (vx, vy), (vx + widths[i] * 0.42, vy - widths[i] * 0.22), 1)


def update_plants():
    """Every frame: advance each plant's springy sway in the water flow, then let swimming fish stir the ones they pass."""
    global PLANT_CLOCK
    PLANT_CLOCK += 1
    cur = eco.current * 170
    PLANT_BUCKETS.clear()
    for p in plants:
        p.step(PLANT_CLOCK, cur)
        PLANT_BUCKETS.setdefault(int(p.pos_x // 48), []).append(p)
    floor = SCREEN_HEIGHT - SAND_HEIGHT
    for f in fishes + predators:
        vx = getattr(f, "vel", None)
        if vx is None or abs(vx.x) < 0.5 or f.pos.y < floor - 480:
            continue
        reach = 50 + 45 * f.z
        bx = int(f.pos.x // 48)
        for b in (bx - 1, bx, bx + 1, bx + 2):
            for p in PLANT_BUCKETS.get(b, ()):
                dx = p.pos_x - f.pos.x
                if abs(dx) < reach and f.pos.y > floor - p.height - 30:
                    p.push += vx.x * 3.2 * (1 - abs(dx) / reach) * p.wake


def create_plants(count=None):
    """Lay out the planting in natural drifts: tall stem plants and vallisneria at the sides, mixed bushes in the middle
    band, a sparse open centre with swords and short grass, with irregular gaps between plants."""
    new_plants = []
    width = SCREEN_WIDTH
    x = random.randint(10, 30)
    while x < width - 5:
        d = abs(x - width / 2) / (width / 2)
        if d > 0.7:
            species = random.choices(["Vallisneria", "Rotala", "Ludwigia", "Hairgrass"], [4, 3, 2, 1])[0]
            step = random.randint(14, 34)
        elif d > 0.3:
            species = random.choices(["TigerLotus", "Anubias", "Vallisneria", "Rotala", "Ludwigia", "Sword"], [3, 3, 2, 2, 2, 2])[0]
            step = random.randint(16, 42)
        else:
            species = random.choice(["Hairgrass", "Sword", "Anubias", "Sword"]) if random.random() < 0.45 else None
            step = random.randint(20, 50)
        if species:
            new_plants.append(Plant(x, species))
        x += step
    while sum(1 for p in new_plants if p.species == "Sword") < 4:
        new_plants.append(Plant(random.randint(int(width * 0.25), int(width * 0.75)), "Sword"))
    # low ground cover everywhere, so the bottom of the tank never looks bare (a few gaps are left on purpose)
    x = random.randint(4, 18)
    while x < width - 4:
        if random.random() < 0.82:
            species = random.choices(["DwarfGrass", "Cryptocoryne", "Clover", "MossBall"], [5, 3, 3, 1])[0]
            new_plants.append(Plant(x + random.randint(-6, 6), species))
        x += random.randint(16, 34)
    new_plants.sort(key=PLANT_ORDER)   # tall plants first, the low cover is drawn in front of their bases
    return new_plants


PLANT_ORDER = lambda p: (-p.depth, p.height < 70, p.pos_x)


def mounted_plants():
    """Mid-height planting that needs the hardscape: java fern tied to the driftwood, and pothos vines hanging from the surface.
    Added after the original layout so a saved tank's seed still gives the same rocks and plants."""
    extra = []
    for r in rocks:
        if isinstance(r, Driftwood) and r.z < 0.95 and random.random() < 0.9:
            h = r.image.get_height()
            w = r.image.get_width()
            sink = int(35 * r.z)
            for _ in range(random.randint(1, 2)):
                fern = Plant(r.pos_x + random.uniform(-0.28, 0.28) * w, "JavaFern")
                fern.lift = max(6, int(h * 0.62) - sink)
                extra.append(fern)
    for edge in (-1, 1):   # pothos spills in from the top corners in three depths: behind the fish, with the plants, in front
        def pothos(off, layer, sc, shade, vines):
            p = Plant(off if edge < 0 else SCREEN_WIDTH - off, "Pothos")
            p.layer, p.sc, p.shade, p.vines = layer, sc, shade, p.vines[:vines]
            extra.append(p)
        for k in range(random.randint(3, 4)):   # background: smaller, dimmer, further in
            pothos(random.randint(0, 40) + k * random.randint(50, 75), "bg", 0.75, 0.62, 5)
        for k in range(random.randint(2, 3)):   # middle: the original strands
            pothos(8 + k * random.randint(60, 85) + random.randint(0, 20), "mid", 1.0, 1.0, 7)
        for k in range(random.randint(1, 2)):   # foreground: big, bold leaves right at the glass
            pothos(random.randint(-10, 30) + k * random.randint(90, 130), "fg", 1.5, 1.0, 3)
    return extra


class FoodPellet:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 1.2)
        self.bites = 3          # a pellet is nibbled a bit at a time, so fish compete and share it

    def update(self):
        dune_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5 + math.cos(self.pos.x * 0.05) * 2
        if self.pos.y < dune_y:
            self.pos += self.vel

    def draw(self, surface):
        n = 1 + max(1, getattr(self, "bites", 3))
        pygame.draw.rect(surface, CLR_FOOD, (int(self.pos.x), int(self.pos.y), n, n))

class Bubble:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = random.uniform(0.5, 1.2)

    def update(self):
        self.pos.y -= self.speed
        self.pos.x += math.sin(pygame.time.get_ticks() * 0.01) * 0.5 + eco.current * 6

    def draw(self, surface):
        pygame.draw.circle(surface, (220, 240, 255), (int(self.pos.x), int(self.pos.y)), 1)

GROW_FRAMES = 7200        # a fry reaches full size after this many frames
LIFESPAN = 54000          # a fish lives about this long (varies per fish)


class Fish:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.z = random.uniform(0.6, 1.1)
        self.z_speed = random.uniform(-0.002, 0.002)
        self.vel = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.acc = pygame.Vector2(0, 0)
        self.hunger = 0.0
        self.id = random.randint(1000, 9999)
        self.health = 100.0
        self.max_speed = 2
        self.alive = True

    def update_hunger(self):
        self.hunger = min(100, self.hunger + 0.02)

    def eat(self):
        self.hunger = max(0, self.hunger - 25)

    @property
    def dz(self):
        """Depth of the swimming lane. A fry is small, but it still swims in its adult lane."""
        return getattr(self, "adult_z", self.z)

    def life_frac(self):
        return getattr(self, "age", 0) / getattr(self, "lifespan", LIFESPAN)

    def vigor(self):
        """-1 (pale and old) .. 0 (dull juvenile / plain) .. 1 (prime of life: richer and brighter)."""
        if not hasattr(self, "age"):
            return 0.0
        if self.growth < 1.0:
            return -0.1
        life = self.life_frac()
        if life < 0.2:
            return 0.3 + 0.7 * life / 0.2
        if life < 0.55:
            return 1.0
        if life < 0.8:
            return 1.0 - (life - 0.55) / 0.25
        return -min(1.0, (life - 0.8) / 0.3)

    def life_stage(self):
        if not hasattr(self, "age"):
            return "adult"
        if self.growth < 0.5:
            return "fry"
        if self.growth < 1.0:
            return "juvenile"
        life = self.life_frac()
        return "elder" if life > 0.8 else "prime" if self.vigor() > 0.8 else "adult"

    @property
    def gene_key(self):
        return (int(round(clamp(getattr(self, "hl", 0.0), -2.0, 2.0))), 0)

    def get_depth_color(self, base_color):
        if hasattr(self, "hl"):
            base_color = hue_shift(base_color, self.gene_key[0])   # the colour line gene of non-guppy fish
        r, g, b = base_color[0], base_color[1], base_color[2]
        v = self.vigor()
        if v > 0.02:      # prime: richer colour, a touch brighter
            lum = 0.3 * r + 0.59 * g + 0.11 * b
            k = 1.0 + 0.22 * v
            br = 1.0 + 0.10 * v
            r, g, b = (lum + (r - lum) * k) * br, (lum + (g - lum) * k) * br, (lum + (b - lum) * k) * br
        elif v < -0.02:   # old (or a dull fry): washed out towards a pale grey
            lum = 0.3 * r + 0.59 * g + 0.11 * b
            t = -v * 0.55
            grey = lum * 0.6 + 120
            r, g, b = r * (1 - t) + grey * t, g * (1 - t) + grey * t, b * (1 - t) + grey * t
        dim = 0.4 + (self.dz * 0.6)
        return (max(0, min(255, int(r * dim))), max(0, min(255, int(g * dim))), max(0, min(255, int(b * dim))))

    def apply_force(self, force):
        self.acc += force

    def update(self, pellets, algae):
        self.z += self.z_speed
        if self.z < 0.6 or self.z > 1.1:
            self.z_speed *= -1

        ft = getattr(self, "flare_t", 0)
        if ft > 0:
            self.flare_t = ft - 1
        elif getattr(self, "flare", 0):
            self.flare = 0
        self.hunger += 0.05
        if self.hunger >= MAX_HUNGER:
            self.hunger = MAX_HUNGER
            self.health -= 0.1
            if self.health <= 0:
                self.alive = False

        target_pos, target_ref, is_alg = None, None, False
        food_cd = getattr(self, "food_cd", 0)
        if food_cd > 0:
            self.food_cd = food_cd - 1
        bottom_feeder = getattr(self, "bottom", False)

        def resting(p):
            return p.pos.y >= ground_y(p.pos.x) - 6

        if self.hunger > (15 if len(pellets) >= 4 else 30) and food_cd <= 0:   # a cloud of food excites even the not-quite-hungry
            # mid-water fish take food on the way down and only pick from the sand when they are starving;
            # bottom feeders (corydoras, plecos, loaches) go for what has already landed
            candidates = [(p.pos, p, False) for p in pellets if (bottom_feeder or not getattr(p, "bottom_only", False))
                          and (bottom_feeder or not resting(p) or self.hunger > 75)] + \
                         [(pygame.Vector2(a), a, True) for a in algae]
            if candidates:
                target_pos, target_ref, is_alg = min(
                    candidates, key=lambda c: self.pos.distance_to(c[0]) - (70 if (bottom_feeder and not c[2] and resting(c[1])) else 0))

        chasing = False
        excite = 0.0
        if target_ref is not None and not is_alg:
            near_food = [p for p in pellets if p.pos.distance_squared_to(target_ref.pos) < 90 * 90]
            if len(near_food) >= 3:   # a cloud of flakes: everyone heads for its middle, not for single flakes
                excite = min(1.0, len(near_food) / 6.0)
                cloud = sum((p.pos for p in near_food), pygame.Vector2()) / len(near_food)
        if target_pos and self.pos.distance_to(target_pos) < 250 + 150 * excite:
            chasing = True
            to_target = target_pos - self.pos
            if to_target.length_squared() > 0:
                self.apply_force(to_target.normalize() * (0.2 + 0.1 * self.hunger / 100 + 0.12 * excite))
            if excite and self.pos.distance_to(cloud) > 40:
                self.apply_force(unit(cloud - self.pos) * 0.1 * excite)
            if self.pos.distance_to(target_pos) < 10:
                if is_alg:
                    self.hunger = max(0, self.hunger - 20)
                    if target_ref in algae:
                        algae.remove(target_ref)
                else:
                    bites = getattr(target_ref, "bites", 1)
                    self.hunger = max(0, self.hunger - (40 if bites <= 1 else 22))
                    target_ref.bites = bites - 1
                    if target_ref.bites <= 0 and target_ref in pellets:
                        pellets.remove(target_ref)
                    else:
                        self.food_cd = 22   # take a bite, drift off, let the others in
                    self.vel *= 0.3
                    if hasattr(self, "mouth_open_timer"):
                        self.mouth_open_timer = 10
        if getattr(self, "darty", False):
            self.dart_glide(chasing)

        self.vel += self.acc
        cap = self.max_speed * ((1.4 + 0.3 * excite) if chasing else 1.0)   # a feeding frenzy makes them quicker
        if self.vel.length() > cap:
            self.vel.scale_to_length(cap)
        self.pos += self.vel
        self.acc *= 0

        if self.pos.x < 0 or self.pos.x > SCREEN_WIDTH:
            self.vel.x *= -1
        if self.pos.y < WATER_TOP or self.pos.y > SCREEN_HEIGHT - SAND_HEIGHT:
            self.vel.y *= -1

        if random.random() < 0.005:
            bubbles.append(Bubble(self.pos.x, self.pos.y))

    def draw_shadow(self, surface, width):
        dune_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5 + math.cos(self.pos.x * 0.05) * 2
        s_col = (20, 20, 20, 70) if self.health > 30 else (80, 20, 20, 90)
        pygame.draw.ellipse(surface, s_col, (self.pos.x, dune_y, width * self.z, 5))

# ---- freshwater species: one shared renderer, each species is a body shape, a palette and a few markings ----
from types import SimpleNamespace


def lane(frac):
    """A swimming depth as a fraction of the water column (0 = just under the surface, 1 = the sand)."""
    return WATER_TOP + 30 + frac * (SCREEN_HEIGHT - SAND_HEIGHT - WATER_TOP - 70)


def edge_y(outline, x, top=True):
    """Height of the body's top (or bottom) edge at a given x, so fins can be rooted exactly on the body."""
    n = len(outline) // 2
    pts = outline[:n] if top else outline[n:][::-1]
    for i in range(len(pts) - 1):
        if pts[i][0] <= x <= pts[i + 1][0]:
            t = (x - pts[i][0]) / max(1e-6, pts[i + 1][0] - pts[i][0])
            return pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
    return pts[0][1] if x < pts[0][0] else pts[-1][1]


def mkfin(shape, color, rays=0, root=None, alpha=225, edge=None, width=1, ray_col=None):
    return (shape, color, rays, root, alpha, edge, width, ray_col)


def flare_fin(fin, k):
    """Spread a fin outward from where it joins the body (threat or courtship display)."""
    shape = fin[0]
    if len(shape) < 3:
        return fin
    ax, ay = (shape[0][0] + shape[-1][0]) / 2, (shape[0][1] + shape[-1][1]) / 2
    spread = [shape[0]] + [(ax + (x - ax) * k, ay + (y - ay) * k) for x, y in shape[1:-1]] + [shape[-1]]
    return (spread,) + tuple(fin[1:])


def fin_on_top(g, u_front, u_back, h, sweep=0.0, peak=0.45, **kw):
    """Dorsal fin rooted on the back between two positions along the body (u: 0 = tail, 1 = nose)."""
    xf, xb = g.rx + u_front * g.L, g.rx + u_back * g.L
    xm = xf + (xb - xf) * peak
    h, sweep = h * g.z, sweep * g.z
    yf, yb, ym = (edge_y(g.outline, x, True) + g.z for x in (xf, xb, xm))
    free = [(xf + (xb - xf) * 0.1 + sweep * 0.3, yf - h * 0.7), (xm + sweep * 0.7, ym - h),
            (xb + (xf - xb) * 0.08 + sweep, yb - h * 0.4)]
    return mkfin(fin_shape((xf, yf), free, (xb, yb)), kw.pop("color", g.fin), root=(xm, ym + 4 * g.z), **kw)


def fin_on_belly(g, u_front, u_back, h, sweep=0.0, peak=0.45, **kw):
    """Anal fin rooted on the underside."""
    xf, xb = g.rx + u_front * g.L, g.rx + u_back * g.L
    xm = xf + (xb - xf) * peak
    h, sweep = h * g.z, sweep * g.z
    yf, yb, ym = (edge_y(g.outline, x, False) - g.z for x in (xf, xb, xm))
    free = [(xf + (xb - xf) * 0.1 + sweep * 0.3, yf + h * 0.7), (xm + sweep * 0.7, ym + h),
            (xb + (xf - xb) * 0.08 + sweep, yb + h * 0.4)]
    return mkfin(fin_shape((xf, yf), free, (xb, yb)), kw.pop("color", g.fin), root=(xm, ym - 4 * g.z), **kw)


def fin_tail(g, kind="fork", spread=26, length=26, notch=0.55, **kw):
    z, rx, cy, sw = g.z, g.rx, g.cy, g.sway
    sp, ln = spread * z, length * z
    ra, rb = (rx + 5 * z, cy - 4 * z), (rx + 5 * z, cy + 4 * z)
    if kind == "fork":
        free = [(rx - 0.25 * ln, cy - 0.55 * sp + sw * 0.4), (rx - ln, cy - sp + sw), (rx - ln * notch, cy + sw * 0.9),
                (rx - ln, cy + sp + sw), (rx - 0.25 * ln, cy + 0.55 * sp + sw * 0.4)]
    else:
        free = [(rx - 0.3 * ln, cy - 0.85 * sp + sw * 0.3), (rx - 0.92 * ln, cy - 0.5 * sp + sw * 0.8), (rx - ln, cy + sw),
                (rx - 0.92 * ln, cy + 0.5 * sp + sw * 0.8), (rx - 0.3 * ln, cy + 0.85 * sp + sw * 0.3)]
    return mkfin(fin_shape(ra, free, rb), kw.pop("color", g.fin), kw.pop("rays", 9), (rx + 4 * z, cy), kw.pop("alpha", 235), **kw)


def fin_pelvic(g, u, length=16, back=8, **kw):
    x = g.rx + u * g.L
    z = g.z
    y = edge_y(g.outline, x, False) - 2 * z
    free = [(x - back * 0.4 * z, y + length * 0.7 * z + g.flap * 0.5), (x - back * z, y + length * z + g.flap)]
    return mkfin(fin_shape((x + 3 * z, y), free, (x - 4 * z, y - 1 * z)), kw.pop("color", g.fin), 4, (x, y - 2 * z), kw.pop("alpha", 200), **kw)


def fin_pectoral(g, u=0.7, length=18, drop=0.2, **kw):
    z = g.z
    x, y = g.rx + u * g.L, g.cy + g.hb * drop
    free = [(x - length * 0.55 * z, y + length * 0.35 * z + g.flap), (x - length * z, y + length * 0.55 * z + g.flap * 1.3)]
    return mkfin(fin_shape((x + 2 * z, y - 2 * z), free, (x - 2 * z, y + 3 * z)), kw.pop("color", (240, 245, 250)), 5, (x, y), kw.pop("alpha", 150), **kw)


def bars(g, layer, centers, width, color, alpha=230, bow=0.0, top=1.7, bot=1.7):
    """Vertical body bars at the given u positions, slightly bowed."""
    for u in centers:
        x = g.rx + u * g.L
        w = width * g.L
        b = bow * g.L
        left = [(x - w / 2 + b, g.cy - top * g.ht), (x - w / 2, g.cy), (x - w / 2 + b, g.cy + bot * g.hb)]
        right = [(x + w / 2 + b, g.cy - top * g.ht), (x + w / 2, g.cy), (x + w / 2 + b, g.cy + bot * g.hb)]
        pygame.draw.polygon(layer, (*color, alpha), left + right[::-1])


class FWFish(Fish):
    """Shared plumbing for the freshwater species: one renderer driven by each species' proportions and markings."""
    family_name = None
    beat = 2.0                   # tail-beat speed; sprite caches use period 628.32 / beat
    W, H = 200, 150              # sprite canvas, in unscaled pixels
    L, HT, HB = 100, 26, 22      # body length, half-depth above and below the axis
    shape = dict(peak=0.55, pt=0.75, pn=0.6, ped=0.12)
    sway_amp = 7
    shadow = 14
    eye_r, eye_u, eye_dy = 5.2, 0.8, -0.22
    eye_col = (232, 200, 90)
    scale_size = 6
    shine = 0.32
    base_color = (160, 160, 170)
    fin_color = None

    def __init__(self, x, y):
        super().__init__(x, y)
        self.angle = 0.0
        self.lerp_speed = 0.18
        self.max_speed = 2.5
        self.mouth_open_timer = 0
        self.flare, self.flare_t = 0, 0

    # ---- behaviour helpers ----
    def set_flare(self, level, frames=20):
        """Erect the fins (level 1 = half, 2 = full) for a few frames: courtship and threat displays."""
        self.flare, self.flare_t = level, frames

    def tilt(self, cap=30):
        if self.vel.length() > 0.1:
            ta = max(-cap, min(cap, math.degrees(math.atan2(-self.vel.y, abs(self.vel.x)))))
            self.angle += (ta - self.angle) * self.lerp_speed

    def wobble(self, strength=0.4, chance=0.04):
        if random.random() < chance:
            self.apply_force(pygame.Vector2(random.uniform(-strength, strength), random.uniform(-strength, strength) * 0.6))

    def prefer_depth(self, lo, hi, strength=0.004):
        if self.pos.y < lo:
            self.apply_force(pygame.Vector2(0, (lo - self.pos.y) * strength))
        elif self.pos.y > hi:
            self.apply_force(pygame.Vector2(0, (hi - self.pos.y) * strength))

    def eat_daphnia(self, reach=230):
        """Small fish hunt the drifting daphnia when they are hungry."""
        if self.hunger < 30 or (eco.t + self.id) % 3:
            return
        best, bd = None, reach * reach
        for k in daphnia:
            d = self.pos.distance_squared_to(k.pos)
            if d < bd:
                best, bd = k, d
        if best is not None:
            self.apply_force(unit(best.pos - self.pos) * (0.3 + self.hunger / 260.0))
            if bd < 20 * 20:
                daphnia.remove(best)
                daphnia.append(Daphnia())
                self.hunger = max(0.0, self.hunger - 35)
                self.mouth_open_timer = 15

    # ---- drawing: override these ----
    def palette(self):
        c = self.get_depth_color(self.base_color)
        if is_dark(c):
            return tone(c, 0.9), tone(c, 1.5), tone(c, 2.1), self.get_depth_color(self.fin_color or self.base_color)
        return tone(c, 0.82), tone(c, 1.05), mix(c, (255, 238, 205), 0.4), self.get_depth_color(self.fin_color or self.base_color)

    def back_fins(self, g):
        return [fin_tail(g), fin_on_top(g, 0.62, 0.3, 14, -4, rays=9), fin_on_belly(g, 0.5, 0.25, 11, -3, rays=7)]

    def front_fins(self, g):
        return [fin_pectoral(g)]

    def decorate(self, g, layer):
        pass

    def finish(self, g):
        pass

    def face(self, g):
        z = g.z
        ex, ey = int(g.rx + self.eye_u * g.L), int(g.cy + self.eye_dy * g.ht)
        draw_eye(g.fs, ex, ey, self.eye_r * z, self.eye_col, tone(g.mid, 0.3))
        nose = g.cx + g.L / 2
        if self.mouth_open_timer > 0:
            pygame.draw.polygon(g.fs, (70, 12, 12), [(nose - 1 * z, g.cy - 2 * z), (nose - 8 * z, g.cy + 1 * z), (nose - 1 * z, g.cy + 6 * z)])
        else:
            pygame.draw.line(g.fs, tone(g.mid, 0.35), (nose - 1 * z, g.cy + 2 * z), (nose - 6 * z, g.cy + 3 * z), max(1, int(z)))

    def draw(self, surface):
        self.draw_shadow(surface, self.shadow)
        if self.mouth_open_timer > 0:
            self.mouth_open_timer -= 1
        z = self.z * SS
        W, H = int(self.W * z), int(self.H * z)
        fs = pygame.Surface((W, H), pygame.SRCALPHA)
        cx, cy = W // 2, H // 2
        t = pygame.time.get_ticks() * 0.01
        L, ht, hb = self.L * z, self.HT * z, self.HB * z
        outline = body_outline(cx, cy, L, ht, hb, **self.shape)
        g = SimpleNamespace(fs=fs, cx=cx, cy=cy, L=L, ht=ht, hb=hb, z=z, t=t, outline=outline, rx=cx - L / 2,
                            sway=math.sin(t * self.beat) * self.sway_amp * z, flap=math.sin(t * self.beat * 2) * 2.2 * z, f=self)
        g.top, g.mid, g.belly, g.fin = self.palette()
        fins = self.back_fins(g)
        if self.flare:
            fins = [flare_fin(f, 1.0 + 0.3 * self.flare) for f in fins]
        for fin in fins:
            draw_fin(fs, *fin)
        paint_body(fs, outline, g.top, g.mid, g.belly, scale=(self.scale_size * z, tone(g.mid, 0.62), 34), shine=self.shine)
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.decorate(g, layer)
        clip_to_polygon(layer, outline)
        fs.blit(layer, (0, 0))
        pygame.draw.aalines(fs, tone(g.mid, 0.42), True, outline)
        self.finish(g)
        for fin in self.front_fins(g):
            draw_fin(fs, *fin)
        self.face(g)
        blit_fish(surface, fs, (self.pos.x, self.pos.y), self.vel.x >= 0, self.angle)


# ---------------- cichlids: territorial, pair up, dig and guard nests ----------------
class Cichlid(FWFish):
    """Base for every fish in the tank. Mbuna and friends: they patrol a territory, dig the sand, squabble with other
    species (and males of their own kind), pair up, spawn at a sword plant and guard the clutch."""
    family_name = "cichlid"
    beat = 1.6
    L, HT, HB = 92, 27, 23
    shape = dict(peak=0.55, pt=0.7, pn=0.55, ped=0.14)
    eye_r, eye_u = 5.4, 0.8
    aggr = 0.4              # how readily it picks fights with other species (0..1)
    social_base = 0.25      # how strongly it keeps to its own kind (0..1); the demasoni live in colonies
    bold_floor = 0.5        # minimum bravery
    hunts = False           # piscivores that pick off other species' fry
    open_water = False      # swims in the open instead of keeping to rocks and plants
    space = None            # personal-water multiplier override (see SPACE_FACTOR)
    common = "cichlid"
    unique = False          # True when its markings are random per fish, so each needs its own sprites

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.35, 0.8)))
        self.z = random.uniform(0.55, 0.85)
        self.territory = pygame.Vector2(x, self.pos.y)
        self.max_speed = 2.8
        self.state, self.target_rival, self.sift_timer = "PATROL", None, 0

    def pick_rival(self, fishes):
        """Another species that wanders into its space, or a rival male of its own kind, draws a flaring chase."""
        if random.random() > 0.05 * self.aggr + 0.004:
            return None
        for o in fishes:
            if o is self or not isinstance(o, Cichlid) or o is getattr(self, "partner", None) or not o.alive:
                continue
            d2 = self.pos.distance_squared_to(o.pos)
            if type(o) is type(self):
                if d2 < 62 * 62 and getattr(self, "sex", "M") == "M" == getattr(o, "sex", "F") and getattr(o, "growth", 1.0) >= 1.0:
                    return o
            elif d2 < 90 * 90 and getattr(o, "growth", 1.0) >= 0.7:
                return o
        return None

    def behavior(self, fishes):
        self.tilt(25)
        self.eat_daphnia(180)
        if self.state == "PATROL":
            if self.pos.distance_to(self.territory) > 150:
                self.apply_force((self.territory - self.pos) * 0.01)
            rival = self.pick_rival(fishes)
            if rival is not None:
                self.target_rival, self.state, self.sift_timer = rival, "DEFEND", 0
                return
            r = random.random()
            if r < 0.004:
                self.state, self.sift_timer = "SIFT", 120
            elif r < 0.0075 and rock_spots:   # mbuna pick the algae film off the rocks
                self.state, self.sift_timer = "PECK", 240
                self.peck_spot = min(rock_spots, key=lambda rs: rs[0].distance_squared_to(self.territory))[0].copy()
            self.wobble(0.3, 0.03)
        elif self.state == "DEFEND":
            if (not self.target_rival or not self.target_rival.alive or self.pos.distance_to(self.target_rival.pos) > 200
                    or self.sift_timer > 150):
                self.target_rival, self.state, self.sift_timer = None, "PATROL", 0
            else:
                self.sift_timer += 1
                d = self.target_rival.pos - self.pos
                if d.length() > 40:
                    self.set_flare(1, 15)
                    self.apply_force(unit(d) * (0.08 + 0.06 * self.aggr))
                else:  # flare, circle and shove
                    self.set_flare(2, 15)
                    self.apply_force(pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)) - d * 0.05)
        elif self.state == "PECK":
            to = self.peck_spot + pygame.Vector2(0, -12) - self.pos
            self.sift_timer -= 1
            if to.length() > 16:
                self.apply_force(unit(to) * 0.12)
            else:
                self.vel *= 0.85
                self.mouth_open_timer = 4 if (self.sift_timer // 10) % 2 else 0
                self.hunger = max(0.0, self.hunger - 0.04)
                self.angle += (-35 - self.angle) * 0.1
            if self.sift_timer <= 0:
                self.state, self.sift_timer = "PATROL", 0
        elif self.state == "SIFT":
            ty = ground_y(self.pos.x) - 14 * self.z
            self.apply_force(pygame.Vector2(0, (ty - self.pos.y) * 0.1))
            self.vel *= 0.9
            self.sift_timer -= 1
            if self.sift_timer <= 0:
                self.state = "PATROL"
                self.sift_timer = 0
            elif self.sift_timer % 20 == 0:
                burst(pygame.Vector2(self.pos.x + 10, ground_y(self.pos.x) - 3), (190, 170, 130), 4, 0.8, 24, 1, 0.03)
        self.prefer_depth(lane(0.3), ground_y(self.pos.x) - 30, 0.006)

    def back_fins(self, g):
        return [fin_tail(g, "round", 17, 24, rays=9), fin_on_top(g, 0.78, 0.1, 15, -9, 0.6, rays=14),
                fin_on_belly(g, 0.56, 0.2, 11, -4, rays=8), fin_pelvic(g, 0.62, 18, 10)]

    def dimorphic(self, male, female):
        return male if getattr(self, "sex", "M") == "M" else female


class PeacockCichlid(Cichlid):
    """Electric-blue peacock cichlid with an orange-gold flank and yellow fins."""
    base_color = (40, 120, 225)
    fin_color = (240, 190, 50)
    aggr, social_base, common, unique = 0.3, 0.3, "Peacock cichlid", True

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed, self.hover = 2.0, 0

    def behavior(self, fishes):
        if self.state == "PATROL" and random.random() < 0.01:
            self.hover = 100
        if self.hover > 0:  # hovers over the sand, looking for tiny food
            self.hover -= 1
            self.vel *= 0.82
            self.tilt(25)
            self.eat_daphnia(180)
            return
        super().behavior(fishes)

    def palette(self):
        top, mid, belly, fin = super().palette()
        return top, mid, mix(self.get_depth_color((170, 150, 100)), (255, 230, 170), 0.3), fin

    def decorate(self, g, layer):
        for k in range(26):  # warm flank wash that fades towards the head
            u = 0.04 + 0.5 * k / 25
            pygame.draw.line(layer, (*self.get_depth_color((240, 150, 40)), int(190 * (1 - k / 25) ** 0.8)),
                             (g.rx + u * g.L, g.cy - g.ht * 1.4), (g.rx + u * g.L, g.cy + g.hb * 1.4), max(2, int(g.L * 0.022)))
        bars(g, layer, [0.34, 0.46, 0.58, 0.7], 0.035, tone(g.top, 0.55), 120, 0.015)
        rng = random.Random(self.id)
        for _ in range(16):  # iridescent speckle on the head
            u = rng.uniform(0.62, 0.92)
            y = g.cy + rng.uniform(-0.7, 0.6) * g.ht
            pygame.draw.circle(layer, (190, 235, 255, 150), (int(g.rx + u * g.L), int(y)), max(1, int(g.z * 0.9)))


class YellowPrinceCichlid(Cichlid):
    """Lemon-yellow lamprologine with an orange wash on the head and a stripe through the eye."""
    base_color = (252, 196, 28)
    fin_color = (255, 170, 40)
    aggr, social_base, common = 0.25, 0.4, "Yellow lab"
    L, HT, HB = 84, 22, 19
    eye_col = (240, 120, 40)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.6

    def decorate(self, g, layer):
        pygame.draw.ellipse(layer, (255, 140, 30, 120), (g.rx + 0.7 * g.L, g.cy - g.ht * 1.0, g.L * 0.34, g.ht * 1.5))
        pygame.draw.line(layer, (150, 70, 20, 130), (g.rx + 0.68 * g.L, g.cy - g.ht * 0.1), (g.rx + 0.96 * g.L, g.cy - g.ht * 0.22), max(1, int(g.z * 1.6)))
        pygame.draw.line(layer, (255, 245, 190, 120), (g.rx + 0.2 * g.L, g.cy - g.ht * 0.1), (g.rx + 0.65 * g.L, g.cy - g.ht * 0.25), max(1, int(g.z * 1.4)))

    def back_fins(self, g):
        return [fin_tail(g, "round", 15, 26, color=tone(g.fin, 1.05), rays=9), fin_on_top(g, 0.82, 0.06, 13, -10, 0.6, rays=14),
                fin_on_belly(g, 0.5, 0.15, 10, -5, rays=8), fin_pelvic(g, 0.62, 18, 10)]


class IceBlueCichlid(Cichlid):
    """Pale ice-blue mbuna with soft grey-blue bars and white fin edges."""
    base_color = (176, 226, 252)
    fin_color = (205, 235, 252)
    aggr, social_base, hunts, bold_floor, common = 0.55, 0.2, True, 0.6, "Ice blue ahli"
    L, HT, HB = 86, 24, 20

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.5

    def decorate(self, g, layer):
        bars(g, layer, [0.26 + 0.085 * i for i in range(7)], 0.035, (70, 130, 180), 150, 0.02)

    def back_fins(self, g):
        return [fin_tail(g, "round", 16, 24, edge=(250, 252, 255), width=SS, rays=9),
                fin_on_top(g, 0.8, 0.1, 13, -8, 0.6, rays=14, edge=(250, 252, 255), width=SS),
                fin_on_belly(g, 0.54, 0.2, 10, -4, rays=8, edge=(250, 252, 255), width=SS), fin_pelvic(g, 0.62, 18, 10, color=(236, 246, 255))]


class DemasoniCichlid(Cichlid):
    """Small, feisty sky-blue mbuna with sharp black bars."""
    base_color = (96, 168, 236)
    fin_color = (70, 120, 200)
    aggr, social_base, space, bold_floor, common = 0.95, 0.95, 9.0, 0.65, "Demasoni"
    L, HT, HB = 80, 22, 19
    eye_r = 4.8

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 3.0

    def decorate(self, g, layer):
        bars(g, layer, [0.2 + 0.085 * i for i in range(8)], 0.03, (12, 18, 36), 235, 0.018)
        pygame.draw.line(layer, (14, 20, 40, 220), (g.rx + 0.1 * g.L, g.cy - g.ht * 0.78), (g.rx + 0.82 * g.L, g.cy - g.ht * 0.9), max(1, int(g.z * 1.8)))

    def back_fins(self, g):
        return [fin_tail(g, "round", 14, 22, edge=(14, 20, 40), width=SS, rays=9),
                fin_on_top(g, 0.8, 0.1, 12, -8, 0.6, rays=14, edge=(14, 20, 40), width=SS),
                fin_on_belly(g, 0.52, 0.2, 9, -4, rays=8, edge=(14, 20, 40), width=SS), fin_pelvic(g, 0.62, 15, 9, color=(20, 28, 56))]


# ---------------- more cichlids: a Lake Malawi mbuna community around the demasoni, plus an angelfish ----------------
class CobaltZebra(Cichlid):
    """Cobalt blue zebra: deep cobalt body, soft darker bars, a long dorsal with a pale edge."""
    base_color = (34, 92, 214)
    fin_color = (28, 70, 190)
    L, HT, HB = 90, 25, 21
    aggr, social_base, common = 0.5, 0.5, "Cobalt zebra"

    def decorate(self, g, layer):
        bars(g, layer, [0.24 + 0.08 * i for i in range(8)], 0.032, (8, 24, 90), 110, 0.02)
        pygame.draw.line(layer, (150, 205, 255, 90), (g.rx + 0.12 * g.L, g.cy - g.ht * 0.7), (g.rx + 0.8 * g.L, g.cy - g.ht * 0.86), max(1, int(g.z * 1.3)))

    def back_fins(self, g):
        return [fin_tail(g, "round", 16, 25, color=tone(g.fin, 1.05), rays=9),
                fin_on_top(g, 0.84, 0.06, 14, -9, 0.6, rays=15, edge=(170, 215, 255), width=SS),
                fin_on_belly(g, 0.52, 0.18, 11, -4, rays=8), fin_pelvic(g, 0.62, 18, 10, color=(60, 110, 220))]


class RedZebra(Cichlid):
    """Red zebra: a warm orange body with cream blotches and an orange-pink fin set."""
    base_color = (240, 128, 48)
    fin_color = (246, 150, 100)
    L, HT, HB = 86, 24, 20
    aggr, social_base, common, unique = 0.6, 0.4, "Red zebra", True

    def palette(self):
        top, mid, belly, fin = super().palette()
        return top, mid, mix(belly, (255, 232, 205), 0.45), fin

    def decorate(self, g, layer):
        rng = random.Random(self.id * 7 + 3)
        for _ in range(9):  # cream and rusty blotches
            u = rng.uniform(0.22, 0.86)
            y = g.cy + rng.uniform(-0.8, 0.7) * g.ht
            col = (255, 236, 205, 150) if rng.random() < 0.6 else (190, 70, 30, 120)
            pygame.draw.ellipse(layer, col, (g.rx + u * g.L, y, g.L * rng.uniform(0.05, 0.1), g.ht * rng.uniform(0.3, 0.6)))
        bars(g, layer, [0.34, 0.5, 0.66], 0.03, (170, 60, 30), 55, 0.015)


class KenyiCichlid(Cichlid):
    """Kenyi: the male turns mustard-yellow, the female stays blue-grey with dark bars and orange blotches."""
    fin_color = (250, 190, 60)
    L, HT, HB = 88, 25, 21
    aggr, social_base, common, unique = 0.75, 0.35, "Kenyi", True

    @property
    def base_color(self):
        return self.dimorphic((196, 138, 44), (112, 152, 204))

    def palette(self):
        top, mid, belly, fin = super().palette()
        if getattr(self, "sex", "M") == "F":
            fin = self.get_depth_color((160, 190, 225))
        return top, mid, belly, fin

    def decorate(self, g, layer):
        if getattr(self, "sex", "M") == "F":
            bars(g, layer, [0.24 + 0.08 * i for i in range(8)], 0.034, (30, 50, 90), 150, 0.02)
            rng = random.Random(self.id)
            for _ in range(5):
                pygame.draw.ellipse(layer, (240, 150, 50, 150), (g.rx + rng.uniform(0.3, 0.8) * g.L, g.cy + rng.uniform(-0.6, 0.4) * g.ht, g.L * 0.07, g.ht * 0.5))
        else:
            bars(g, layer, [0.26 + 0.09 * i for i in range(6)], 0.034, (70, 40, 14), 120, 0.015)
            pygame.draw.ellipse(layer, (255, 120, 30, 120), (g.rx + 0.74 * g.L, g.cy - g.ht * 0.9, g.L * 0.28, g.ht * 1.4))


class AuratusCichlid(Cichlid):
    """Golden mbuna: the male is black with pale-blue stripes along the flank, the female golden with a dark stripe."""
    fin_color = (240, 190, 40)
    L, HT, HB = 84, 22, 19
    aggr, social_base, bold_floor, common = 1.0, 0.3, 0.7, "Auratus"

    @property
    def base_color(self):
        return self.dimorphic((34, 34, 44), (238, 188, 40))

    def decorate(self, g, layer):
        stripe = self.dimorphic((170, 205, 240, 235), (36, 30, 24, 230))
        wd = max(2, int(g.ht * 0.34))
        for dy in (-0.56, 0.12):
            pygame.draw.line(layer, stripe, (g.rx + 0.14 * g.L, g.cy + dy * g.ht), (g.rx + 0.94 * g.L, g.cy + (dy - 0.12) * g.ht), wd)

    def back_fins(self, g):
        edge = self.dimorphic((190, 220, 250), (60, 45, 20))
        return [fin_tail(g, "round", 15, 24, edge=edge, width=SS, rays=9),
                fin_on_top(g, 0.82, 0.08, 13, -9, 0.6, rays=14, edge=edge, width=SS),
                fin_on_belly(g, 0.5, 0.18, 10, -4, rays=8), fin_pelvic(g, 0.62, 16, 9)]


class SocolofiCichlid(Cichlid):
    """Pindani / Socolofi: a pale pearl-pink body with salmon fins and a rosy blush on the cheek."""
    base_color = (246, 226, 226)
    fin_color = (240, 152, 150)
    L, HT, HB = 88, 25, 21
    eye_col = (200, 40, 50)
    aggr, social_base, bold_floor, common = 0.2, 0.3, 0.3, "Socolofi"

    def decorate(self, g, layer):
        pygame.draw.ellipse(layer, (255, 140, 150, 110), (g.rx + 0.7 * g.L, g.cy - g.ht * 0.5, g.L * 0.3, g.ht * 1.1))
        pygame.draw.line(layer, (255, 255, 255, 120), (g.rx + 0.15 * g.L, g.cy - g.ht * 0.55), (g.rx + 0.8 * g.L, g.cy - g.ht * 0.78), max(1, int(g.z * 1.5)))

    def back_fins(self, g):
        return [fin_tail(g, "round", 17, 25, rays=9), fin_on_top(g, 0.8, 0.08, 14, -9, 0.6, rays=14, edge=(255, 255, 255), width=SS),
                fin_on_belly(g, 0.52, 0.18, 11, -4, rays=8), fin_pelvic(g, 0.62, 20, 11, color=(255, 200, 190))]


class AngelFish(Cichlid):
    """Silver angelfish: a tall, compressed disc with long trailing dorsal, anal and pelvic fins and bold dark bars.
    It cruises the open water and picks off other species' fry."""
    base_color = (212, 216, 222)
    fin_color = (200, 204, 212)
    beat = 1.2
    W, H = 200, 220
    L, HT, HB = 62, 38, 36
    shape = dict(peak=0.55, pt=0.62, pn=0.5, ped=0.2)
    eye_r, eye_u = 5.0, 0.78
    eye_col = (210, 50, 40)
    aggr, social_base, bold_floor, hunts, open_water, space, common = 0.2, 0.45, 0.25, True, True, 17.0, "Angelfish"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.0
        self.z = random.uniform(0.6, 0.85)
        self.territory = pygame.Vector2(x, lane(random.uniform(0.2, 0.5)))
        self.pos.y = self.territory.y

    def behavior(self, fishes):
        super().behavior(fishes)
        self.prefer_depth(lane(0.12), lane(0.6), 0.004)

    def decorate(self, g, layer):
        bars(g, layer, [0.3, 0.55, 0.78], 0.045, (24, 24, 30), 205, 0.01, 2.6, 2.6)
        pygame.draw.line(layer, (255, 255, 255, 100), (g.rx + 0.2 * g.L, g.cy - g.ht * 0.5), (g.rx + 0.7 * g.L, g.cy - g.ht * 0.75), max(1, int(g.z * 1.6)))

    def back_fins(self, g):
        return [fin_tail(g, "fork", 20, 30, notch=0.7, rays=10, alpha=170),
                fin_on_top(g, 0.78, 0.18, 52, -30, 0.5, rays=14, alpha=170, edge=(60, 60, 70), width=SS),
                fin_on_belly(g, 0.7, 0.16, 50, -28, 0.5, rays=14, alpha=170, edge=(60, 60, 70), width=SS),
                fin_pelvic(g, 0.62, 44, 14, color=(225, 228, 235))]


# ---------------- bottom dwellers ----------------
class Pleco(FWFish):
    """Sailfin pleco: armoured, spotted, grazes algae with a sucker mouth."""
    family_name = "pleco"
    social_base = 0.1
    bottom = True
    unique = True
    nocturnal = True
    beat = 1.3
    W, H = 220, 150
    L, HT, HB = 120, 19, 12
    shape = dict(peak=0.42, pt=0.6, pn=0.75, ped=0.1)
    base_color = (82, 72, 58)
    shadow = 26
    eye_r, eye_u, eye_dy = 3.4, 0.78, -0.55
    eye_col = (200, 170, 70)
    sway_amp = 4

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 3.5
        self.z = random.uniform(0.55, 0.78)
        self.target_algae = None
        self.eating_timer = 0
        self.graze_spot, self.graze_t, self.cling = None, 0, False

    def pick_graze_spot(self):
        """A leaf, a rock face or a patch of the floor to rasp the film off."""
        r = random.random()
        leafy = [p for p in plants if not p.hang and p.height > 45]
        if r < 0.55 and leafy:
            p = random.choice(leafy)
            return pygame.Vector2(p.pos_x + random.uniform(-10, 10), ground_y(p.pos_x) - random.uniform(25, p.height * 0.9))
        if r < 0.85 and rock_spots:
            spot = random.choice(rock_spots)[0]
            return pygame.Vector2(spot.x + random.uniform(-14, 14), spot.y - random.uniform(0, 30))
        x = random.randint(80, SCREEN_WIDTH - 80)
        return pygame.Vector2(x, ground_y(x) - 20 * self.z)

    def graze(self):
        self.graze_t -= 1
        if self.graze_spot is None or self.graze_t <= 0:
            self.graze_spot = self.pick_graze_spot()
            self.graze_t = random.randint(500, 1100)
        to = self.graze_spot - self.pos
        if to.length() > 14:
            self.apply_force(unit(to) * 0.16)
            return
        self.vel *= 0.8   # stuck on with the sucker mouth, rasping slowly
        self.mouth_open_timer = 4 if (self.graze_t // 12) % 3 == 0 else 0
        self.apply_force(pygame.Vector2(math.sin(self.graze_t * 0.12) * 0.05, 0))
        self.hunger = max(0.0, self.hunger - 0.03)
        eco.water = min(100.0, eco.water + 0.0008)   # they keep the tank's film algae down
        self.cling = self.graze_spot.y < ground_y(self.graze_spot.x) - 30 * self.z

    def behavior(self, fishes):
        self.hunger = min(MAX_HUNGER, self.hunger + self.vel.length() * 0.02)
        self.cling = False
        if self.hunger > 20 and algae:
            self.target_algae = min(algae, key=lambda a: self.pos.distance_squared_to(pygame.Vector2(a)))
        else:
            self.target_algae = None
        if self.eating_timer > 0:
            self.eating_timer -= 1
            self.vel *= 0.1
            self.mouth_open_timer = 4
        elif self.target_algae:
            tv = pygame.Vector2(self.target_algae)
            if self.pos.distance_to(tv) < 10:
                if self.target_algae in algae:
                    algae.remove(self.target_algae)
                    self.hunger = max(0, self.hunger - 25)
                    self.eating_timer = 24
                self.target_algae = None
            else:
                self.apply_force((unit(tv - self.pos) * self.max_speed - self.vel) * 0.3)
        else:
            self.graze()
        floor = ground_y(self.pos.x) - 22 * self.z
        if not self.target_algae and not self.cling and self.pos.y < floor:
            self.apply_force(pygame.Vector2(0, 0.2))
        if self.cling:
            self.angle += (50 - self.angle) * 0.1   # head up, flat on a leaf or rock face
        else:
            self.tilt(18)

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.7), tone(c, 1.35), mix(c, (200, 185, 150), 0.55), tone(c, 1.05)

    def back_fins(self, g):
        return [fin_tail(g, "fork", 17, 24, 0.7, color=tone(g.mid, 0.95), rays=9),
                fin_on_top(g, 0.76, 0.36, 36, -14, 0.35, color=tone(g.mid, 1.05), rays=16, edge=tone(g.mid, 1.4), width=SS),
                fin_on_belly(g, 0.36, 0.2, 9, -3, rays=6, color=tone(g.mid, 0.9)), fin_pelvic(g, 0.6, 14, 14, color=tone(g.mid, 0.95))]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.76, 28, 0.4, color=tone(g.mid, 1.1), alpha=205, edge=tone(g.mid, 0.8))]

    def decorate(self, g, layer):
        rng = random.Random(self.id)
        for _ in range(38):
            u = rng.uniform(0.1, 0.86)
            y = g.cy + rng.uniform(-0.8, 0.6) * g.ht
            r = max(1.0, rng.uniform(1.0, 2.1) * g.z)
            pygame.draw.circle(layer, (*tone(g.top, 0.55), 190), (int(g.rx + u * g.L), int(y)), int(r))
        for k in range(4):  # armour plate ridges along the flank
            y = g.cy - g.ht * (0.5 - 0.35 * k)
            pygame.draw.line(layer, (*tone(g.mid, 1.4), 70), (g.rx + 0.12 * g.L, y), (g.rx + 0.78 * g.L, y - g.ht * 0.1), max(1, int(g.z * 0.8)))

    def finish(self, g):
        nose = g.cx + g.L / 2
        # the sucker mouth is a rounded disc on the underside of the head
        pygame.draw.ellipse(g.fs, tone(g.belly, 0.95), (nose - 17 * g.z, g.cy + g.hb * 0.0, 17 * g.z, 11 * g.z))
        pygame.draw.ellipse(g.fs, tone(g.top, 0.7), (nose - 14 * g.z, g.cy + g.hb * 0.2, 11 * g.z, 6 * g.z), max(1, int(g.z * 0.8)))

    def face(self, g):
        z = g.z
        draw_eye(g.fs, int(g.rx + self.eye_u * g.L), int(g.cy + self.eye_dy * g.ht), self.eye_r * z, self.eye_col, tone(g.mid, 0.3))


class Otocinclus(Pleco):
    """Otocinclus: a tiny olive algae-grazer with a dark stripe and a small sucker mouth."""
    family_name = "oto"
    social_base = 0.7
    nocturnal = False   # otocinclus graze by day and sleep at night
    unique = False
    beat = 2.4
    W, H = 100, 70
    L, HT, HB = 36, 7, 6
    shape = dict(peak=0.5, pt=0.8, pn=0.7, ped=0.12)
    base_color = (150, 150, 112)
    eye_r, eye_u, eye_dy = 2.4, 0.8, -0.3
    shadow = 7
    sway_amp = 2

    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.5, 0.8)
        self.max_speed = 2.6

    def back_fins(self, g):
        c = tone(g.mid, 1.05)
        return [fin_tail(g, "fork", 6, 9, 0.5, color=c, alpha=200, rays=5),
                fin_on_top(g, 0.55, 0.3, 7, -2, 0.4, color=c, alpha=200, rays=5),
                fin_on_belly(g, 0.4, 0.2, 4, -1, color=c, alpha=200, rays=3), fin_pelvic(g, 0.6, 5, 4, color=c)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.74, 8, 0.3, color=tone(g.mid, 1.1), alpha=190)]

    def decorate(self, g, layer):
        pygame.draw.line(layer, (*tone(g.top, 0.42), 225), (g.rx + 0.14 * g.L, g.cy - 0.05 * g.ht), (g.rx + 0.9 * g.L, g.cy + 0.0 * g.ht), max(1, int(g.z * 2.0)))
        pygame.draw.line(layer, (235, 235, 205, 90), (g.rx + 0.2 * g.L, g.cy + 0.55 * g.ht), (g.rx + 0.8 * g.L, g.cy + 0.5 * g.ht), max(1, int(g.z)))

    def finish(self, g):
        nose = g.cx + g.L / 2
        pygame.draw.ellipse(g.fs, tone(g.belly, 0.95), (nose - 6 * g.z, g.cy + g.hb * 0.05, 6 * g.z, 4 * g.z))


class BristlenosePleco(Pleco):
    """Bristlenose pleco: a dark, pale-speckled armoured grazer with fleshy tentacles on its snout; shy by day."""
    W, H = 180, 120
    L, HT, HB = 90, 15, 10
    base_color = (70, 64, 52)
    shadow = 20

    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.55, 0.75)
        self.max_speed = 3.0

    def decorate(self, g, layer):
        rng = random.Random(self.id)
        for _ in range(34):
            u = rng.uniform(0.12, 0.86)
            y = g.cy + rng.uniform(-0.8, 0.6) * g.ht
            pygame.draw.circle(layer, (*tone(g.top, 1.9), 170), (int(g.rx + u * g.L), int(y)), max(1, int(rng.uniform(0.8, 1.6) * g.z)))

    def finish(self, g):
        super().finish(g)
        z, nose = g.z, g.cx + g.L / 2
        for k in range(4):   # the snout bristles
            x0 = nose - (2 + 3 * k) * z
            pygame.draw.line(g.fs, tone(g.mid, 1.6), (x0, g.cy - g.ht * 0.35), (x0 + 5 * z, g.cy - g.ht * 0.35 - (7 - k) * z), max(1, int(z * 1.1)))


# ---------------- open-water schools ----------------
class BalaShark(FWFish):
    """Silver torpedo with black-edged fins; fast, schooling, in sudden bursts."""
    family_name = "bala"
    social_base = 1.0
    lane_frac = 0.42
    beat = 2.6
    W, H = 230, 150
    L, HT, HB = 120, 21, 19
    shape = dict(peak=0.4, pt=0.8, pn=0.75, ped=0.1)
    base_color = (205, 210, 220)
    fin_color = (232, 236, 242)
    sway_amp = 9
    eye_r, eye_u, eye_dy = 6.0, 0.82, -0.2
    eye_col = (215, 220, 225)
    shadow = 22

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.3, 0.6)))
        self.z = random.uniform(0.5, 0.78)
        self.max_speed = 5.5
        self.lerp_speed = 0.3

    def behavior(self, fishes):
        if random.random() < 0.02:
            self.apply_force(pygame.Vector2(random.uniform(-2, 2), random.uniform(-0.5, 0.5)))
        self.prefer_depth(lane(0.2), lane(0.75), 0.004)
        self.tilt(30)

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.7), tone(c, 1.0), self.get_depth_color((246, 248, 252)), self.get_depth_color(self.fin_color)

    def back_fins(self, g):
        blk = (14, 14, 16)
        return [fin_tail(g, "fork", 38, 36, 0.5, rays=12, edge=blk, width=2 * SS),
                fin_on_top(g, 0.58, 0.3, 36, -10, 0.45, rays=10, edge=blk, width=2 * SS),
                fin_on_belly(g, 0.42, 0.2, 24, -8, 0.4, rays=8, edge=blk, width=2 * SS),
                fin_pelvic(g, 0.58, 22, 8, edge=blk, width=SS)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.72, 24, 0.3, color=(250, 252, 255), alpha=190)]

    def decorate(self, g, layer):
        pygame.draw.line(layer, (110, 116, 126, 120), (g.rx + 0.18 * g.L, g.cy + g.ht * 0.05), (g.rx + 0.88 * g.L, g.cy - g.ht * 0.05), max(1, int(g.z * 1.2)))
        pygame.draw.ellipse(layer, (255, 255, 255, 80), (g.rx + 0.3 * g.L, g.cy - g.ht * 0.85, g.L * 0.45, g.ht * 0.55))


class NeonTetra(FWFish):
    """A glowing blue stripe over a silver, iridescent body with a red belly; tiny and shoaling."""
    family_name = "tetra"
    social_base = 1.0
    lane_frac = 0.4
    small_prey = True
    shy = True
    darty = True
    beat = 3.4
    W, H = 130, 80
    L, HT, HB = 56, 11, 11
    shape = dict(peak=0.5, pt=0.8, pn=0.7, ped=0.12)
    base_color = (176, 186, 206)
    sway_amp = 3
    eye_r, eye_u, eye_dy = 4.0, 0.84, -0.12
    eye_col = (206, 222, 240)
    scale_size = 3
    shadow = 10
    shine = 0.4

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.3, 0.55)))
        self.z = random.uniform(0.5, 0.85)
        self.max_speed = 2.6

    def behavior(self, fishes):
        self.eat_daphnia(160)
        self.prefer_depth(lane(0.18), lane(0.6), 0.003)
        self.wobble(0.5, 0.02)
        self.tilt(28)

    def dart_glide(self, busy):
        """Real tetras do not cruise at a steady speed: a quick flick forward, then a long glide while the shoal catches up."""
        if busy or getattr(self, "fear", 0) > 0.3 or getattr(self, "sleepy", 0) > 0.4 or getattr(self, "refuge", None) is not None:
            return
        self.dart_t = getattr(self, "dart_t", random.randint(0, 40)) - 1
        gliding = getattr(self, "gliding", True)
        if self.dart_t <= 0:
            gliding = not gliding
            self.gliding = gliding
            self.dart_t = random.randint(22, 70) if gliding else random.randint(7, 14)
        if gliding:
            self.vel *= 0.972
        elif self.vel.length_squared() > 1e-4:
            self.acc += unit(self.vel) * 0.16

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.62), tone(c, 0.98), tone(c, 1.3), tone(c, 0.95)

    def back_fins(self, g):
        clear = (196, 206, 224)
        return [fin_tail(g, "fork", 11, 13, 0.6, color=clear, alpha=185, rays=8, edge=(226, 234, 246), width=SS),
                fin_on_top(g, 0.56, 0.38, 7, -2, 0.5, color=clear, alpha=185, rays=5),
                fin_on_belly(g, 0.52, 0.26, 6, -1, color=clear, alpha=185, rays=4)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.72, 9, 0.15, alpha=140)]

    # ---- shared tetra bits ----
    def gloss(self, g, layer, tint=(190, 235, 255)):
        """Iridescent sheen: a cool band along the back and a bright sliver low on the flank."""
        z = g.z
        for dy, a in ((-0.66, 80), (-0.4, 44)):
            pygame.draw.line(layer, (*tint, a), (g.rx + 0.18 * g.L, g.cy + dy * g.ht), (g.rx + 0.8 * g.L, g.cy + (dy - 0.14) * g.ht), max(1, int(z * 1.7)))
        pygame.draw.line(layer, (255, 255, 255, 70), (g.rx + 0.28 * g.L, g.cy + g.hb * 0.66), (g.rx + 0.7 * g.L, g.cy + g.hb * 0.72), max(1, int(z * 1.2)))

    def gill(self, g):
        x = g.rx + 0.78 * g.L
        pygame.draw.arc(g.fs, tone(g.mid, 0.5), (x - 6 * g.z, g.cy - g.ht * 0.95, 12 * g.z, g.ht * 1.9), math.pi * 0.5 + 0.3, math.pi * 1.5 - 0.3, max(1, int(g.z)))

    def finish(self, g):
        self.gill(g)

    def red_belly(self, g, layer, u0, u1, col=(255, 36, 70)):
        red = self.get_depth_color(col)
        pts = [(u0, 0.05), (u0 + (u1 - u0) * 0.45, 0.14), (u0 + (u1 - u0) * 0.8, 0.22), (u1 + 0.02, 0.5), (u1 - 0.04, 1.0),
               (u1 - 0.14, 1.8), (u0, 1.8)]
        pygame.draw.polygon(layer, (*red, 250), [(g.rx + u * g.L, g.cy + v * g.hb) for u, v in pts])
        hi = mix(red, (255, 176, 176), 0.55)
        pygame.draw.line(layer, (*hi, 170), (g.rx + (u0 + 0.08) * g.L, g.cy + g.hb * 0.34), (g.rx + (u1 - 0.1) * g.L, g.cy + g.hb * 0.6), max(1, int(g.z * 1.2)))
        dk = tone(red, 0.6)
        pygame.draw.line(layer, (*dk, 120), (g.rx + (u0 + 0.06) * g.L, g.cy + g.hb * 1.35), (g.rx + (u1 - 0.14) * g.L, g.cy + g.hb * 1.3), max(1, int(g.z * 1.5)))

    def blue_line(self, g, layer, u0, u1):
        glow = self.get_depth_color((40, 220, 255))
        for w, a in ((5.0, 50), (3.2, 120), (1.8, 230), (0.9, 255)):
            col = mix(glow, (230, 255, 255), 0.55 if w < 1.5 else (0.25 if w < 2 else 0.0))
            pygame.draw.line(layer, (*col, a), (g.rx + u0 * g.L, g.cy - g.ht * 0.12), (g.rx + u1 * g.L, g.cy - g.ht * 0.2), max(1, int(g.z * w * 0.7)))

    def decorate(self, g, layer):
        self.gloss(g, layer)
        self.red_belly(g, layer, 0.08, 0.66)
        self.blue_line(g, layer, 0.14, 0.88)


class RummyNose(NeonTetra):
    """Red-headed tetra with a black-and-white barred tail; tight, darting school."""
    family_name = "tetra"
    lane_frac = 0.65
    beat = 3.2
    W, H = 140, 90
    L, HT, HB = 62, 12, 12
    base_color = (204, 210, 218)
    eye_r, eye_u, eye_dy = 4.2, 0.86, -0.1
    eye_col = (244, 224, 120)
    shadow = 11

    def __init__(self, x, y):
        super().__init__(x, y)
        self.pos.y = lane(random.uniform(0.5, 0.8))
        self.max_speed = 2.9

    def behavior(self, fishes):
        self.eat_daphnia(160)
        self.prefer_depth(lane(0.42), lane(0.82), 0.003)
        self.wobble(0.6, 0.03)
        self.tilt(28)

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.7), tone(c, 1.02), tone(c, 1.28), (240, 240, 240)

    def back_fins(self, g):
        return [fin_tail(g, "fork", 14, 15, 0.55, color=self.get_depth_color((246, 246, 246)), rays=9, alpha=215),
                fin_on_top(g, 0.56, 0.38, 8, -2, 0.5, color=(210, 216, 226), alpha=190, rays=5),
                fin_on_belly(g, 0.52, 0.26, 6, -1, color=(210, 216, 226), alpha=190, rays=4)]

    def decorate(self, g, layer):
        self.gloss(g, layer, (255, 225, 225))
        red = self.get_depth_color((238, 22, 26))
        for k in range(22):  # the red mask: strongest at the snout, fading back past the gill
            u = 0.7 + 0.3 * k / 21
            pygame.draw.line(layer, (*red, int(255 * min(1.0, (k + 2) / 7.0))), (g.rx + u * g.L, g.cy - g.ht * 1.4), (g.rx + u * g.L, g.cy + g.hb * 1.4), max(2, int(g.L * 0.02)))
        pygame.draw.line(layer, (255, 150, 140, 130), (g.rx + 0.74 * g.L, g.cy - g.ht * 0.7), (g.rx + 0.97 * g.L, g.cy - g.ht * 0.55), max(1, int(g.z * 1.3)))
        pygame.draw.line(layer, (150, 40, 40, 110), (g.rx + 0.12 * g.L, g.cy - g.ht * 0.04), (g.rx + 0.72 * g.L, g.cy - g.ht * 0.1), max(1, int(g.z * 1.2)))

    def finish(self, g):
        z = g.z
        rx, cy, sw = g.rx, g.cy, g.sway
        for dy in (-0.62, 0.0, 0.62):  # three black bars across the white tail
            pygame.draw.line(g.fs, (12, 12, 14), (rx - 1 * z, cy + dy * 8 * z + sw * 0.1), (rx - 11 * z, cy + dy * 13 * z + sw * 0.85), max(1, int(2 * z)))
        self.gill(g)


class BoesemaniRainbow(FWFish):
    """Boesemani rainbowfish: slate-blue front half, glowing orange rear half, tall twin dorsals."""
    family_name = "rainbow"
    social_base = 0.9
    lane_frac = 0.3
    shy = True
    beat = 2.2
    W, H = 200, 150
    L, HT, HB = 90, 31, 22
    shape = dict(peak=0.55, pt=0.7, pn=0.6, ped=0.14)
    base_color = (82, 122, 176)
    eye_r, eye_u, eye_dy = 5.2, 0.82, -0.22
    eye_col = (236, 214, 120)

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.15, 0.5)))
        self.z = random.uniform(0.6, 0.9)
        self.max_speed = 2.3
        self.curiosity_target, self.curiosity_timer = None, 0

    def behavior(self, fishes):
        self.eat_daphnia(200)
        self.prefer_depth(lane(0.1), lane(0.62), 0.004)
        self.curiosity_timer -= 1
        if self.curiosity_timer <= 0:
            if random.random() < 0.02:
                near = [f for f in fishes if f is not self and self.pos.distance_squared_to(f.pos) < 250 * 250]
                self.curiosity_target = random.choice(near) if near else None
                self.curiosity_timer = random.randint(150, 400)
            else:
                self.curiosity_target = None
        t = self.curiosity_target
        if t is not None and t.alive:
            d = self.pos.distance_to(t.pos)
            if d > 50:
                self.apply_force(unit(t.pos - self.pos) * 0.07)
            elif d < 30:
                self.apply_force(unit(self.pos - t.pos) * 0.09)
        if getattr(self, "sex", "M") == "M" and getattr(self, "growth", 1.0) >= 1.0 and getattr(self, "fear", 0) < 0.3:
            if (eco.t + self.id) % 20 == 0:   # rival males square up: fins spread, swimming side by side and quivering
                self.duel = None
                for o in fishes:
                    if o is not self and type(o) is type(self) and getattr(o, "sex", "") == "M" and self.pos.distance_squared_to(o.pos) < 130 ** 2:
                        self.duel = o
                        break
            r = getattr(self, "duel", None)
            if r is not None and r.alive:
                to = r.pos - self.pos
                if to.length() > 45:
                    self.apply_force(unit(to) * 0.05)
                else:
                    self.vel += (r.vel - self.vel) * 0.05
                    self.apply_force(unit(pygame.Vector2(-to.y, to.x)) * math.sin(eco.t * 0.45 + self.id) * 0.06)
                    self.set_flare(2, 15)
        self.tilt(26)

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.65), tone(c, 1.0), mix(c, (220, 228, 240), 0.55), self.get_depth_color((246, 120, 36))

    def back_fins(self, g):
        orange, dk = g.fin, tone(g.fin, 0.45)
        return [fin_tail(g, "fork", 28, 30, 0.55, rays=12, edge=dk, width=SS),
                fin_on_top(g, 0.74, 0.58, 12, -3, 0.5, color=tone(g.top, 1.3), rays=5),
                fin_on_top(g, 0.45, 0.1, 22, -9, 0.4, rays=12, edge=dk, width=SS),
                fin_on_belly(g, 0.55, 0.1, 17, -8, 0.4, rays=12, edge=dk, width=SS), fin_pelvic(g, 0.62, 17, 8, color=orange)]

    def decorate(self, g, layer):
        warm = self.get_depth_color((246, 118, 34))
        for k in range(40):  # glowing orange rear half, melting into the blue
            u = 0.08 + 0.55 * k / 39
            a = int(235 * (1 - max(0.0, (u - 0.34) / 0.3)) ** 1.2)
            pygame.draw.line(layer, (*warm, a), (g.rx + u * g.L, g.cy - g.ht * 1.5), (g.rx + u * g.L, g.cy + g.hb * 1.5), max(2, int(g.L * 0.016)))
        pygame.draw.line(layer, (255, 255, 255, 90), (g.rx + 0.3 * g.L, g.cy - g.ht * 0.35), (g.rx + 0.84 * g.L, g.cy - g.ht * 0.4), max(1, int(g.z * 1.3)))


class PearlGourami(FWFish):
    """Pearl gourami: lace of pale pearls, a dark zig-zag flank stripe, long feeler fins; gulps air at the surface."""
    family_name = "gourami"
    social_base = 0.3
    lane_frac = 0.18
    unique = True
    beat = 1.5
    W, H = 220, 160
    L, HT, HB = 86, 31, 29
    shape = dict(peak=0.5, pt=0.7, pn=0.65, ped=0.16)
    base_color = (176, 150, 118)
    fin_color = (200, 176, 146)
    eye_r, eye_u, eye_dy = 5.0, 0.8, -0.2
    eye_col = (230, 110, 60)
    sway_amp = 5
    scale_size = 5

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.08, 0.3)))
        self.z = random.uniform(0.6, 0.85)
        self.max_speed = 1.4
        self.target_y = self.pos.y
        self.is_gulping, self.inquiry_timer, self.look_target = False, 0, None

    def behavior(self, fishes):
        self.eat_daphnia(200)
        self.nest_cd = getattr(self, "nest_cd", random.randint(1500, 3500)) - 1
        nest = getattr(self, "nest", None)
        if nest is not None and nest.s <= 0:
            nest = self.nest = None
            self.target_y = lane(random.uniform(0.08, 0.3))
        if (nest is None and self.nest_cd <= 0 and getattr(self, "sex", "M") == "M" and getattr(self, "growth", 1.0) >= 1.0
                and self.hunger < 40 and getattr(self, "fear", 0) < 0.3):
            nest = self.nest = BubbleNest(min(max(self.pos.x, 100), SCREEN_WIDTH - 100), WATER_TOP + 8, self)
            foam_nests.append(nest)
            self.nest_cd = random.randint(5000, 9000)
        if nest is not None and nest.life > 0:   # he hovers under it, blows bubbles into it and sees off visitors
            self.target_y = nest.y + 40
            self.apply_force((pygame.Vector2(nest.x, nest.y + 40) - self.pos) * 0.012)
            self.vel *= 0.95
            if (eco.t + self.id) % 90 == 0:
                self.mouth_open_timer = 12
                bubbles.append(Bubble(self.pos.x + 12, self.pos.y - 6))
            if (eco.t + self.id) % 10 == 0:
                for o in fishes:
                    if o is not self and self.pos.distance_squared_to(o.pos) < 90 ** 2:
                        o.apply_force(unit(o.pos - self.pos) * 0.5)
        if not self.is_gulping and random.random() < 0.002:
            self.is_gulping = True
        if self.is_gulping:
            self.apply_force(pygame.Vector2(0, (WATER_TOP + 12 - self.pos.y) * 0.05))
            if self.pos.y <= WATER_TOP + 18:
                self.is_gulping = False
                self.mouth_open_timer = 20
                burst(self.pos + (14, 0), (230, 245, 255), 3, 0.5, 30, 1, -0.01)
        else:
            self.apply_force(pygame.Vector2(0, (self.target_y - self.pos.y) * 0.01))
        self.inquiry_timer -= 1
        if self.inquiry_timer <= 0:
            near = [f for f in fishes if f is not self and self.pos.distance_squared_to(f.pos) < 150 * 150]
            self.look_target = random.choice(near) if near else None
            self.inquiry_timer = random.randint(200, 500)
        t = self.look_target
        if t is not None and t.alive:
            if self.pos.distance_squared_to(t.pos) > 60 * 60:
                self.apply_force(unit(t.pos - self.pos) * 0.02)
            else:
                self.vel *= 0.95
        if self.vel.length() > self.max_speed:
            self.vel *= 0.9
        self.tilt(22)

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.7), tone(c, 1.0), mix(self.get_depth_color((236, 170, 90)), (255, 235, 200), 0.3), self.get_depth_color(self.fin_color)

    def back_fins(self, g):
        edge = tone(g.fin, 1.3)
        return [fin_tail(g, "round", 20, 25, rays=11, edge=edge, width=SS),
                fin_on_top(g, 0.58, 0.1, 13, -4, 0.55, rays=14, edge=edge, width=SS),
                fin_on_belly(g, 0.7, 0.1, 15, -4, 0.55, rays=16, edge=edge, width=SS)]

    def front_fins(self, g):
        z = g.z
        out = [fin_pectoral(g, 0.68, 14, 0.15)]
        x0, y0 = g.rx + 0.62 * g.L, edge_y(g.outline, g.rx + 0.62 * g.L, False)
        sway = math.sin(g.t * 1.2) * 3 * z
        for k, (dx, ln) in enumerate(((0, 40), (7, 34))):  # the long thread-like feeler fins
            pts = [(x0 + dx * z, y0 - z), (x0 + dx * z + 12 * z * (k + 1) * 0.6 + sway, y0 + ln * 0.5 * z), (x0 + dx * z + 22 * z + sway * 1.5, y0 + ln * z)]
            pygame.draw.lines(g.fs, tone(g.fin, 1.15), False, smooth_open(pts, 4), max(1, int(1.5 * z)))
            pygame.draw.circle(g.fs, (240, 130, 70), (int(pts[-1][0]), int(pts[-1][1])), max(1, int(1.6 * z)))
        return out

    def decorate(self, g, layer):
        rng = random.Random(self.id)
        pts = [(g.rx + (0.84 - 0.74 * k / 8) * g.L, g.cy + (0.05 + (0.22 if k % 2 else -0.18)) * g.ht) for k in range(9)]
        pygame.draw.lines(layer, (*tone(g.top, 0.45), 190), False, smooth_open(pts, 4), max(2, int(g.z * 2.0)))
        for _ in range(64):  # pearls
            u = rng.uniform(0.1, 0.9)
            y = g.cy + rng.uniform(-0.95, 0.95) * g.ht * 0.85
            pygame.draw.circle(layer, (255, 250, 235, 215), (int(g.rx + u * g.L), int(y)), max(1, int(rng.uniform(0.9, 1.7) * g.z)))


# ---------------- loaches and barbs ----------------
class ClownLoach(FWFish):
    """Clown loach: orange with three bold black bands, red fins and barbels; shuffles over the substrate in groups."""
    family_name = "loach"
    social_base = 0.8
    bottom = True
    beat = 2.0
    W, H = 210, 130
    L, HT, HB = 100, 17, 15
    shape = dict(peak=0.55, pt=0.8, pn=0.6, ped=0.17)
    base_color = (250, 148, 20)
    fin_color = (214, 50, 34)
    eye_r, eye_u, eye_dy = 4.2, 0.8, -0.15
    eye_col = (240, 190, 60)
    shadow = 22
    sway_amp = 6

    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.55, 0.8)
        self.max_speed = 2.5
        self.lerp_speed = 0.12

    def behavior(self, fishes):
        floor = ground_y(self.pos.x) - 20 * self.z
        self.apply_force(pygame.Vector2(0, 0.15 if self.pos.y < floor else -0.1))
        self.apply_force(pygame.Vector2(math.sin(pygame.time.get_ticks() * 0.005 + self.id) * 0.4, 0))
        if random.random() < 0.005:  # the loach "zoomies"
            self.apply_force(pygame.Vector2(random.uniform(-5, 5), random.uniform(-3, 1)))
        self.eat_daphnia(160)
        self.vel *= 0.96
        if self.vel.length() > 0.1:
            ta = -20 if self.pos.y > floor - 14 else math.degrees(math.atan2(-self.vel.y, abs(self.vel.x)))
            self.angle += (ta - self.angle) * self.lerp_speed

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.82), tone(c, 1.05), mix(c, (255, 225, 150), 0.5), self.get_depth_color(self.fin_color)

    def back_fins(self, g):
        edge = (40, 10, 10)
        return [fin_tail(g, "fork", 22, 26, 0.6, rays=11, edge=edge, width=SS),
                fin_on_top(g, 0.62, 0.34, 17, -6, 0.45, rays=10, edge=edge, width=SS),
                fin_on_belly(g, 0.4, 0.24, 11, -3, rays=7), fin_pelvic(g, 0.58, 12, 8)]

    def decorate(self, g, layer):
        blk = (14, 14, 14)
        bars(g, layer, [0.8], 0.085, blk, 245, -0.03, 2.2, 2.2)
        bars(g, layer, [0.5], 0.07, blk, 245, 0.0, 2.2, 2.2)
        bars(g, layer, [0.22], 0.075, blk, 245, 0.025, 2.2, 2.2)

    def finish(self, g):
        z, nose = g.z, g.cx + g.L / 2
        for k, dy in enumerate((0.4, 1.4, 2.4)):  # barbels
            wag = math.sin(g.t * 3 + k) * 1.5 * z
            pygame.draw.line(g.fs, (250, 230, 190), (nose - 3 * z, g.cy + dy * 2.2 * z), (nose + 5 * z, g.cy + (dy * 2.2 + 5) * z + wag), max(1, int(z * 0.8)))


class Corydoras(ClownLoach):
    """Bronze corydoras: a stout, armoured catfish with a dark eye mask and a green sheen that sifts the sand in small groups."""
    family_name = "cory"
    social_base = 1.0
    nocturnal = False   # corydoras are active by day
    beat = 2.6
    W, H = 130, 90
    L, HT, HB = 56, 14, 11
    shape = dict(peak=0.45, pt=0.8, pn=0.6, ped=0.14)
    base_color = (176, 136, 82)
    fin_color = (196, 168, 120)
    eye_r, eye_u, eye_dy = 3.2, 0.8, -0.15
    eye_col = (30, 24, 20)
    shadow = 11
    sway_amp = 4

    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.5, 0.75)
        self.max_speed = 2.2
        self.mode, self.mode_t, self.topped = "sift", random.randint(20, 120), False
        self.air_cd, self.dirx = random.randint(1200, 4000), random.choice((-1, 1))

    def behavior(self, fishes):
        """Sift the sand head-down in short pauses between slow walks, and now and then dash to the surface for a gulp of air."""
        floor = ground_y(self.pos.x) - 18 * self.z
        self.mode_t -= 1
        self.air_cd -= 1
        self.max_speed = 4.6 if self.mode == "air" else 2.2   # the dash for air is quick
        if self.mode == "air":
            if not self.topped:
                self.apply_force(pygame.Vector2(0, -0.32))
                if self.pos.y < WATER_TOP + 55:
                    self.topped = True
                    for _ in range(2):
                        bubbles.append(Bubble(self.pos.x, self.pos.y))
            else:
                self.apply_force(pygame.Vector2(0, 0.45))
                if self.pos.y > floor - 30:
                    self.mode, self.air_cd, self.mode_t = "sift", random.randint(2400, 5200), 60
            self.vel.x *= 0.97
            self.tilt(55)
            return
        if self.air_cd <= 0 and getattr(self, "fear", 0) < 0.3 and getattr(self, "sleepy", 0) < 0.4:
            self.mode, self.topped = "air", False
            return
        self.apply_force(pygame.Vector2(0, 0.16 if self.pos.y < floor else -0.12))
        if self.pos.x < 70:
            self.dirx = 1
        elif self.pos.x > SCREEN_WIDTH - 70:
            self.dirx = -1
        if self.mode_t <= 0:
            self.mode = "walk" if self.mode == "sift" else "sift"
            self.mode_t = random.randint(50, 140) if self.mode == "walk" else random.randint(40, 110)
        if self.mode == "sift":
            self.vel *= 0.82
            self.mouth_open_timer = 3
            self.angle += (-30 - self.angle) * 0.15
            if self.mode_t % 22 == 0:
                burst(pygame.Vector2(self.pos.x + 16 * self.z * self.dirx, self.pos.y + 10 * self.z), (206, 190, 150), 3, 0.7, 24, 1, 0.02)
        else:
            self.apply_force(pygame.Vector2(self.dirx * 0.22, 0))
            if random.random() < 0.02:
                self.dirx = random.choice((-1, 1))
            self.tilt(14)

    def back_fins(self, g):
        c = (214, 200, 172)
        return [fin_tail(g, "fork", 13, 15, 0.5, color=c, alpha=200, rays=7),
                fin_on_top(g, 0.52, 0.26, 12, -2, 0.4, color=c, alpha=200, rays=6),
                fin_on_belly(g, 0.36, 0.2, 7, -2, color=c, alpha=200, rays=4), fin_pelvic(g, 0.58, 8, 6, color=c)]

    def decorate(self, g, layer):
        z = g.z
        pygame.draw.line(layer, (*tone(g.top, 0.5), 150), (g.rx + 0.15 * g.L, g.cy - 0.55 * g.ht), (g.rx + 0.82 * g.L, g.cy - 0.65 * g.ht), max(1, int(z * 2.2)))
        pygame.draw.line(layer, (70, 190, 150, 80), (g.rx + 0.22 * g.L, g.cy - 0.25 * g.ht), (g.rx + 0.78 * g.L, g.cy - 0.32 * g.ht), max(1, int(z * 1.4)))
        pygame.draw.ellipse(layer, (40, 30, 24, 170), (g.rx + 0.7 * g.L, g.cy - 0.6 * g.ht, 0.17 * g.L, 0.62 * g.ht))   # the dark eye mask
        pygame.draw.line(layer, (*tone(g.mid, 1.4), 90), (g.rx + 0.2 * g.L, g.cy + 0.1 * g.ht), (g.rx + 0.8 * g.L, g.cy + 0.05 * g.ht), max(1, int(z)))

    def finish(self, g):
        z, nose = g.z, g.cx + g.L / 2
        for dy in (0.5, 1.6):   # two pairs of barbels feel through the sand
            wag = math.sin(g.t * 3 + dy) * 1.0 * z
            pygame.draw.line(g.fs, (236, 220, 186), (nose - 2 * z, g.cy + dy * 2.2 * z), (nose + 3 * z, g.cy + (dy * 2.2 + 3.5) * z + wag), max(1, int(z * 0.8)))


class TigerBarb(FWFish):
    """Tiger barb: golden body with four heavy black bars, red-tipped fins and a red snout; busy surface-level school."""
    family_name = "barb"
    social_base = 0.9
    lane_frac = 0.14
    shy = True
    beat = 3.0
    W, H = 150, 110
    L, HT, HB = 60, 25, 21
    shape = dict(peak=0.5, pt=0.7, pn=0.6, ped=0.14)
    base_color = (232, 180, 62)
    fin_color = (230, 70, 40)
    eye_r, eye_u, eye_dy = 4.2, 0.8, -0.18
    eye_col = (250, 250, 250)
    scale_size = 4
    sway_amp = 4
    shadow = 11

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.04, 0.25)))
        self.z = random.uniform(0.55, 0.85)
        self.max_speed = 1.9
        self.target_y = lane(random.uniform(0.04, 0.22))

    def behavior(self, fishes):
        self.eat_daphnia(190)
        self.apply_force(pygame.Vector2(0, (self.target_y - self.pos.y) * 0.02))
        if random.random() < 0.012:
            self.apply_force(pygame.Vector2(random.uniform(-1.6, 1.6), random.uniform(-0.4, 0.4)))
        self.vel.x *= 0.99
        self.nip_cd = getattr(self, "nip_cd", random.randint(60, 240)) - 1
        v = getattr(self, "nip_target", None)
        if v is not None and (not v.alive or self.pos.distance_squared_to(v.pos) > 220 ** 2):
            v = self.nip_target = None
        if v is None and self.nip_cd <= 0 and (eco.t + self.id) % 15 == 0:
            for o in fishes:   # long-finned, slow fish are the favourite targets
                if o is not self and isinstance(o, (GuppyBase, AngelFish)) and self.pos.distance_squared_to(o.pos) < 160 ** 2:
                    v = self.nip_target = o
                    break
        if v is not None:
            rear = v.pos - unit(v.vel) * 14
            to = rear - self.pos
            self.apply_force(unit(to) * 0.3)
            if to.length() < 14:   # a nip: the victim flinches away and is stressed
                v.stress = min(100.0, getattr(v, "stress", 0.0) + 6)
                v.apply_force(unit(v.pos - self.pos) * 1.0)
                self.mouth_open_timer = 8
                self.set_flare(1, 10)
                self.nip_cd = random.randint(150, 400)
                self.nip_target = None
        self.tilt(25)

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.78), tone(c, 1.08), mix(c, (255, 238, 190), 0.55), self.get_depth_color(self.fin_color)

    def back_fins(self, g):
        blk = (14, 14, 16)
        return [fin_tail(g, "fork", 20, 21, 0.55, rays=9, edge=g.fin, width=SS),
                fin_on_top(g, 0.64, 0.34, 15, -4, 0.5, rays=8, edge=blk, width=SS),
                fin_on_belly(g, 0.5, 0.26, 10, -3, rays=6), fin_pelvic(g, 0.6, 12, 6)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.72, 13, 0.15)]

    def decorate(self, g, layer):
        bars(g, layer, [0.84, 0.66, 0.47, 0.24], 0.06, (12, 12, 16), 238, 0.015, 2.0, 2.0)
        red = self.get_depth_color((230, 60, 40))
        pygame.draw.ellipse(layer, (*red, 190), (g.rx + 0.9 * g.L, g.cy - g.ht * 0.3, g.L * 0.14, g.ht * 0.9))


# ---------------- more tetras, so the tetra family can fill a tank on its own ----------------
class CardinalTetra(NeonTetra):
    """Cardinal tetra: like a neon, but the red runs the full length of the belly and the blue line glows brighter."""
    L, HT, HB = 62, 11, 11
    lane_frac = 0.45

    def decorate(self, g, layer):
        self.gloss(g, layer)
        self.red_belly(g, layer, 0.06, 0.9, (246, 28, 56))
        self.blue_line(g, layer, 0.1, 0.92)


class EmberTetra(NeonTetra):
    """Ember tetra: a tiny, glowing orange-red fish that shoals in dense clouds, with a gold sheen."""
    W, H = 100, 60
    L, HT, HB = 42, 9, 9
    base_color = (240, 106, 34)
    eye_col = (252, 236, 176)
    eye_r = 3.4
    shadow = 8
    lane_frac = 0.55

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.7), tone(c, 1.02), tone(mix(c, (255, 210, 120), 0.35), 1.2), tone(c, 1.0)

    def back_fins(self, g):
        clear = self.get_depth_color((250, 156, 76))
        return [fin_tail(g, "fork", 9, 10, 0.6, color=clear, alpha=200, rays=6, edge=(255, 214, 140), width=SS),
                fin_on_top(g, 0.56, 0.38, 6, -1, 0.5, color=clear, alpha=185, rays=4),
                fin_on_belly(g, 0.52, 0.28, 5, -1, color=clear, alpha=185, rays=3)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.72, 7, 0.15, alpha=130, color=(255, 200, 130))]

    def decorate(self, g, layer):
        self.gloss(g, layer, (255, 226, 150))
        pygame.draw.line(layer, (255, 224, 130, 190), (g.rx + 0.16 * g.L, g.cy - g.ht * 0.3), (g.rx + 0.86 * g.L, g.cy - g.ht * 0.42), max(1, int(g.z * 1.5)))
        pygame.draw.line(layer, (180, 50, 20, 120), (g.rx + 0.2 * g.L, g.cy + g.hb * 0.15), (g.rx + 0.8 * g.L, g.cy + g.hb * 0.1), max(1, int(g.z * 1.1)))


class BlackSkirtTetra(NeonTetra):
    """Black skirt tetra: a deeper, glossy silver-grey body with two dark bars behind the gill and a smoky 'skirt' fin."""
    W, H = 140, 100
    L, HT, HB = 58, 16, 18
    beat = 2.8
    base_color = (172, 176, 190)
    eye_r = 4.2
    lane_frac = 0.5

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.66), tone(c, 1.02), tone(c, 1.3), self.get_depth_color((60, 62, 76))

    def back_fins(self, g):
        smoke = self.get_depth_color((54, 56, 70))
        return [fin_tail(g, "fork", 13, 14, 0.55, color=tone(smoke, 1.5), alpha=185, rays=8, edge=(120, 124, 140), width=SS),
                fin_on_top(g, 0.58, 0.34, 11, -3, 0.5, color=tone(smoke, 1.3), alpha=200, rays=6, edge=(40, 40, 52), width=SS),
                fin_on_belly(g, 0.66, 0.14, 17, -5, 0.5, color=smoke, alpha=175, rays=11, edge=(150, 154, 170), width=SS)]

    def decorate(self, g, layer):
        self.gloss(g, layer, (210, 225, 255))
        bars(g, layer, [0.57, 0.68], 0.04, (16, 16, 22), 215, 0.012, 1.8, 1.8)
        pygame.draw.line(layer, (30, 30, 40, 100), (g.rx + 0.12 * g.L, g.cy + g.hb * 0.05), (g.rx + 0.5 * g.L, g.cy + g.hb * 0.02), max(1, int(g.z * 1.2)))


class LemonTetra(NeonTetra):
    """Lemon tetra: translucent pale yellow with a glowing yellow anal fin edged in black and a red-flecked eye."""
    W, H = 130, 80
    L, HT, HB = 54, 13, 13
    base_color = (234, 228, 150)
    eye_col = (240, 72, 50)
    lane_frac = 0.35

    def palette(self):
        c = self.get_depth_color(self.base_color)
        return tone(c, 0.78), tone(c, 1.02), tone(c, 1.2), self.get_depth_color((248, 232, 80))

    def back_fins(self, g):
        y = self.get_depth_color((248, 234, 84))
        return [fin_tail(g, "fork", 12, 13, 0.55, color=y, alpha=190, rays=7),
                fin_on_top(g, 0.56, 0.36, 8, -2, 0.5, color=y, alpha=195, rays=5, edge=(24, 24, 24), width=SS),
                fin_on_belly(g, 0.7, 0.18, 11, -3, 0.5, color=y, alpha=220, rays=8, edge=(24, 24, 24), width=SS)]

    def decorate(self, g, layer):
        self.gloss(g, layer, (255, 250, 170))
        pygame.draw.ellipse(layer, (255, 246, 120, 90), (g.rx + 0.2 * g.L, g.cy - g.ht * 0.9, g.L * 0.6, g.ht * 1.2))
        pygame.draw.arc(layer, (255, 120, 60, 150), (g.rx + 0.8 * g.L, g.cy - g.ht * 0.95, g.L * 0.1, g.ht * 0.5), 0.3, 2.9, max(1, int(g.z * 1.2)))


# ---------------- guppies: lively livebearers in the tetra family. Males are the showy ones, with big patterned fan tails ----------------
class GuppyBase(NeonTetra):
    """Shared guppy plumbing. Males flaunt an oversized fan tail and dorsal; females are rounder, larger and plainer with a
    small tinted tail. Subclasses set the colours and the tail pattern."""
    darty = False
    beat = 4.2
    W, H = 200, 130
    L, HT, HB = 46, 12, 11
    shadow = 11
    lane_frac = 0.3
    eye_r, eye_u, eye_dy = 4.2, 0.84, -0.14
    eye_col = (236, 214, 150)
    male_color = (90, 160, 210)
    female_color = (176, 184, 160)
    tail_color = (60, 120, 210)
    tail_edge = (150, 220, 255)
    TAIL_L, TAIL_S = 48, 27
    TAIL_ALPHA = 222

    def __init__(self, x, y):
        super().__init__(x, y)
        self.pos.y = lane(random.uniform(0.18, 0.5))
        self.max_speed = 2.8
        self.show = 0
        self.gh = random.uniform(-0.7, 0.7)    # colour gene: hue steps away from the wild type
        self.gt = random.uniform(-0.6, 0.6)    # tail gene: a shorter or longer fan
        self.gen = 1                           # generation: 1 = bought, 2+ = bred in this tank
        self.lace = [random.random() < 0.14, random.random() < 0.14]   # lace pattern: recessive, needs both copies
        self.sheen = random.uniform(0.0, 1.0)  # metallic sheen: blends between the parents
        self.fin = random.choices((0, 1, 2), (6, 2, 2))[0]   # 0 round, 1 delta (wide, short), 2 long

    @property
    def gene_key(self):
        return (int(round(clamp(self.gh, -2.0, 2.0))), int(round(clamp(self.gt, -1.0, 1.0))),
                int(self.lace_on()), 1 if self.sheen > 0.66 else 0, self.fin)

    def fin_s(self):
        return (1.0, 1.28, 0.82)[getattr(self, "fin", 0)]

    def fin_l(self):
        return (1.0, 0.82, 1.22)[getattr(self, "fin", 0)]

    def lace_on(self):
        return bool(self.lace[0] and self.lace[1])

    def lace_mesh(self, g, layer):
        step = max(4, int(g.z * 3.4))
        col = (22, 30, 52, 120)
        for x in range(int(g.rx + 0.1 * g.L), int(g.rx + 0.86 * g.L), step):
            u = (x - g.rx) / g.L
            half = int(g.ht * 0.85 * math.sqrt(max(0.0, 1.0 - ((u - 0.48) / 0.46) ** 2)))
            if half < 2:
                continue
            pygame.draw.line(layer, col, (x, g.cy - half), (x + step, g.cy + half), 1)
            pygame.draw.line(layer, col, (x, g.cy + half), (x + step, g.cy - half), 1)

    def sheen_band(self, g, layer):
        pygame.draw.line(layer, (255, 255, 255, 96), (g.rx + 0.2 * g.L, g.cy - g.ht * 0.32), (g.rx + 0.82 * g.L, g.cy - g.ht * 0.2),
                         max(2, int(g.z * 2.2)))
        pygame.draw.line(layer, (190, 235, 255, 70), (g.rx + 0.25 * g.L, g.cy + g.ht * 0.08), (g.rx + 0.78 * g.L, g.cy + g.ht * 0.02),
                         max(1, int(g.z * 1.2)))

    def gtint(self, c):
        return hue_shift(c, int(round(clamp(self.gh, -2.0, 2.0))))

    def tlvl(self):
        return int(round(clamp(self.gt, -1.0, 1.0)))

    def male(self):
        return getattr(self, "sex", "M") == "M"

    def behavior(self, fishes):
        self.eat_daphnia(180)
        self.prefer_depth(lane(0.1), lane(0.55), 0.004)
        self.wobble(0.6, 0.05)
        self.tilt(26)
        if getattr(self, "growth", 1.0) < 1.0:
            return
        if self.male():
            c = getattr(self, "suit", None)
            calm = getattr(self, "fear", 0) < 0.3 and getattr(self, "sleepy", 0) < 0.4
            if (eco.t + self.id) % 25 == 0 and calm:
                if c is None or not c.alive or self.pos.distance_squared_to(c.pos) > 320 ** 2:
                    c, best = None, 300 ** 2
                    for o in fishes:
                        if o is not self and type(o) is type(self) and getattr(o, "sex", "") == "F" and getattr(o, "growth", 1.0) >= 1.0:
                            d2 = self.pos.distance_squared_to(o.pos)
                            if d2 < best:
                                c, best = o, d2
                self.suit = c
            c = getattr(self, "suit", None)
            if c is not None and c.alive and calm:
                to = c.pos - self.pos
                if to.length() > 70:
                    self.apply_force(unit(to) * 0.26)   # chase her
                else:
                    self.vel += (c.vel - self.vel) * 0.06   # shadow her and shimmy in an S
                    self.apply_force(unit(pygame.Vector2(-to.y, to.x)) * math.sin(eco.t * 0.3 + self.id) * 0.12)
                    self.angle += math.sin(eco.t * 0.35 + self.id) * 7
                    self.show = 1
                    self.set_flare(2, 15)
        elif (eco.t + self.id) % 8 == 0 and getattr(self, "fear", 0) < 0.3:   # a female not in the mood slips away from an insistent male
            for o in fishes:
                if getattr(o, "suit", None) is self and self.pos.distance_squared_to(o.pos) < 60 ** 2 and random.random() < 0.5:
                    self.apply_force(unit(self.pos - o.pos) * 0.9)
                    break

    def palette(self):
        c = self.get_depth_color(self.gtint(self.male_color if self.male() else self.female_color))
        return tone(c, 0.64), tone(c, 1.0), tone(c, 1.3), self.get_depth_color(self.gtint(self.tail_color))

    def fan_tail(self, g, spread, length, color, alpha, edge=None):
        z, rx, cy, sw = g.z, g.rx, g.cy, g.sway
        sp, ln = spread * z, length * z
        free = [(rx - 0.38 * ln, cy - 0.55 * sp + sw * 0.25), (rx - 0.82 * ln, cy - 1.05 * sp + sw * 0.7), (rx - ln, cy - 0.42 * sp + sw * 0.95),
                (rx - ln, cy + 0.42 * sp + sw * 0.95), (rx - 0.82 * ln, cy + 1.05 * sp + sw * 0.7), (rx - 0.38 * ln, cy + 0.55 * sp + sw * 0.25)]
        return mkfin(fin_shape((rx + 5 * z, cy - 4 * z), free, (rx + 5 * z, cy + 4 * z)), color, 15 if edge else 8, (rx + 4 * z, cy), alpha,
                     edge, SS if edge else 1)

    def back_fins(self, g):
        if self.male():
            tail = self.fan_tail(g, self.TAIL_S * (1 + 0.1 * self.tlvl()) * self.fin_s(), self.TAIL_L * (1 + 0.15 * self.tlvl()) * self.fin_l(), self.get_depth_color(self.gtint(self.tail_color)), self.TAIL_ALPHA, self.tail_edge)
            dors = fin_on_top(g, 0.62, 0.2, 21, -13, 0.4, color=self.get_depth_color(self.gtint(self.tail_color)), alpha=205, rays=10, edge=self.tail_edge, width=SS)
            anal = fin_on_belly(g, 0.5, 0.36, 7, -1, color=tone(self.get_depth_color(self.gtint(self.tail_color)), 1.15), alpha=190, rays=4)
            return [tail, dors, anal]
        soft = mix(self.get_depth_color(self.gtint(self.tail_color)), (226, 226, 214), 0.45)
        return [self.fan_tail(g, 12, 18, soft, 160, None), fin_on_top(g, 0.6, 0.34, 8, -3, 0.5, color=soft, alpha=170, rays=5),
                fin_on_belly(g, 0.52, 0.34, 5, -1, color=soft, alpha=165, rays=3)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.72, 10, 0.15, alpha=140)]

    def decorate(self, g, layer):
        self.gloss(g, layer, (200, 240, 255))
        if self.lace_on():
            self.lace_mesh(g, layer)
        if self.sheen > 0.66:
            self.sheen_band(g, layer)
        if self.male():
            self.male_pattern(g, layer)
        else:   # a soft gravid spot above the anal fin and a faint lateral line
            pygame.draw.circle(layer, (60, 56, 40, 120), (int(g.rx + 0.5 * g.L), int(g.cy + g.hb * 0.5)), max(2, int(g.z * 2.4)))
            pygame.draw.line(layer, (*tone(self.female_color, 0.7), 90), (g.rx + 0.14 * g.L, g.cy - g.ht * 0.05), (g.rx + 0.8 * g.L, g.cy - g.ht * 0.12), max(1, int(g.z * 1.1)))

    def male_pattern(self, g, layer):
        pass

    def tail_speckles(self, g, colors, count, size=1.5, bars=0):
        """Scatter the male's tail with spots (and optional dark bars), seeded so every male of a kind matches."""
        rng = random.Random(len(type(self).__name__) * 977)
        z, rx, cy, sw = g.z, g.rx, g.cy, g.sway
        sp, ln = self.TAIL_S * z * (1 + 0.1 * self.tlvl()) * self.fin_s(), self.TAIL_L * z * (1 + 0.15 * self.tlvl()) * self.fin_l()
        for _ in range(count):
            u = rng.uniform(0.18, 0.94)
            v = rng.uniform(-0.78, 0.78) * (0.32 + 0.68 * u)
            px, py = rx - u * ln, cy + v * sp * 1.7 + sw * u * 0.9
            pygame.draw.circle(g.fs, rng.choice(colors), (int(px), int(py)), max(1, int(size * z * rng.uniform(0.6, 1.2))))
        for k in range(bars):
            u = 0.3 + 0.6 * k / max(1, bars - 1)
            px = rx - u * ln
            half = (0.3 + 0.7 * u) * sp * 0.95
            pygame.draw.line(g.fs, (20, 16, 26), (px, cy - half + sw * u * 0.9), (px - 3 * z, cy + half + sw * u * 0.9), max(1, int(1.3 * z)))

    def finish(self, g):
        if self.male():
            self.tail_pattern(g)
        self.gill(g)

    def tail_pattern(self, g):
        pass


class MosaicGuppy(GuppyBase):
    """Blue mosaic guppy: an iridescent teal-blue body and a deep blue fan tail studded with glowing cyan and black mosaic spots."""
    male_color = (46, 142, 214)
    female_color = (170, 186, 176)
    tail_color = (28, 82, 190)
    tail_edge = (120, 230, 255)

    def male_pattern(self, g, layer):
        rng = random.Random(7)
        for _ in range(26):   # glittering scale dots along the flank
            u, v = rng.uniform(0.3, 0.92), rng.uniform(-0.7, 0.7)
            pygame.draw.circle(layer, (150, 236, 255, 170), (int(g.rx + u * g.L), int(g.cy + v * g.ht)), max(1, int(g.z * 0.9)))
        pygame.draw.line(layer, (10, 30, 90, 150), (g.rx + 0.14 * g.L, g.cy - g.ht * 0.8), (g.rx + 0.8 * g.L, g.cy - g.ht * 0.9), max(1, int(g.z * 1.6)))

    def tail_pattern(self, g):
        self.tail_speckles(g, [(120, 236, 255), (10, 20, 60), (200, 250, 255)], 30, 1.5, 0)


class TuxedoGuppy(GuppyBase):
    """Red tuxedo guppy: a pale front half, a dark blue-black back half, and a blazing red tail edged in black."""
    male_color = (232, 228, 214)
    female_color = (184, 180, 160)
    tail_color = (226, 38, 38)
    tail_edge = (30, 14, 20)

    def male_pattern(self, g, layer):
        for k in range(24):   # dark rear half fading out towards the head
            u = 0.04 + 0.5 * k / 23
            pygame.draw.line(layer, (16, 24, 58, int(235 * (1 - k / 28))), (g.rx + u * g.L, g.cy - g.ht * 1.4), (g.rx + u * g.L, g.cy + g.hb * 1.4), max(2, int(g.L * 0.026)))
        pygame.draw.line(layer, (255, 255, 255, 110), (g.rx + 0.58 * g.L, g.cy - g.ht * 0.7), (g.rx + 0.86 * g.L, g.cy - g.ht * 0.78), max(1, int(g.z * 1.3)))

    def tail_pattern(self, g):
        self.tail_speckles(g, [(255, 110, 90), (60, 8, 16), (255, 170, 120)], 18, 1.4, 0)


class SunsetGuppy(GuppyBase):
    """Sunset cobra guppy: a gold-orange body and a yellow-orange tail with black snake-skin bars and spots."""
    male_color = (240, 150, 40)
    female_color = (206, 190, 150)
    tail_color = (255, 196, 40)
    tail_edge = (255, 90, 20)
    TAIL_ALPHA = 244

    def male_pattern(self, g, layer):
        for k in range(7):   # cobra snake-skin: dark wavy bars over the rear body
            u = 0.12 + 0.07 * k
            x0 = g.rx + u * g.L
            pts = [(x0 + math.sin(j * 1.3 + k) * 1.6 * g.z, g.cy - g.ht * 1.0 + j * g.ht * 0.36) for j in range(6)]
            pygame.draw.lines(layer, (60, 24, 8, 170), False, pts, max(1, int(g.z * 1.2)))
        pygame.draw.line(layer, (255, 236, 150, 130), (g.rx + 0.3 * g.L, g.cy - g.ht * 0.74), (g.rx + 0.88 * g.L, g.cy - g.ht * 0.86), max(1, int(g.z * 1.5)))

    def tail_pattern(self, g):
        self.tail_speckles(g, [(40, 16, 8), (210, 60, 20), (255, 236, 150)], 22, 1.5, 4)


class MoscowGuppy(GuppyBase):
    """Moscow purple guppy: a deep violet body with a magenta glow and a dark purple fan tail rimmed in hot pink."""
    male_color = (112, 54, 176)
    female_color = (180, 170, 190)
    tail_color = (92, 36, 150)
    tail_edge = (255, 110, 220)

    def male_pattern(self, g, layer):
        pygame.draw.line(layer, (255, 130, 230, 130), (g.rx + 0.14 * g.L, g.cy - g.ht * 0.62), (g.rx + 0.82 * g.L, g.cy - g.ht * 0.78), max(1, int(g.z * 2.0)))
        pygame.draw.line(layer, (255, 190, 245, 90), (g.rx + 0.3 * g.L, g.cy + g.hb * 0.55), (g.rx + 0.76 * g.L, g.cy + g.hb * 0.62), max(1, int(g.z * 1.4)))
        rng = random.Random(11)
        for _ in range(14):
            pygame.draw.circle(layer, (255, 170, 240, 150), (int(g.rx + rng.uniform(0.3, 0.9) * g.L), int(g.cy + rng.uniform(-0.7, 0.7) * g.ht)), max(1, int(g.z * 0.9)))

    def tail_pattern(self, g):
        self.tail_speckles(g, [(255, 120, 230), (30, 8, 60), (200, 150, 255)], 24, 1.5, 0)


# ---------------- betta, discus, killifish ----------------
BETTA_MORPHS = [((200, 24, 40), (150, 10, 36)), ((40, 80, 220), (24, 40, 160)),
                ((30, 170, 160), (18, 100, 120)), ((226, 150, 40), (200, 70, 30))]


class Betta(PearlGourami):
    """Betta: a short jewel-coloured body with huge flowing fins. Males build bubble nests and flare at rival males."""
    family_name = "betta"
    social_base = 0.1
    W, H = 250, 180
    L, HT, HB = 62, 20, 18
    shape = dict(peak=0.52, pt=0.8, pn=0.7, ped=0.2)
    eye_r, eye_u, eye_dy = 4.2, 0.8, -0.15
    eye_col = (230, 210, 120)
    base_color = (200, 24, 40)
    fin_color = (150, 10, 36)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.body_c, self.fin_c = random.choice(BETTA_MORPHS)
        self.max_speed = 1.5

    def male(self):
        return getattr(self, "sex", "M") == "M"

    def behavior(self, fishes):
        super().behavior(fishes)
        if self.male() and (eco.t + self.id) % 10 == 0 and getattr(self, "growth", 1.0) >= 1.0:
            for o in fishes:
                if o is not self and type(o) is Betta and getattr(o, "sex", "") == "M" and self.pos.distance_squared_to(o.pos) < 240 ** 2:
                    self.set_flare(2, 30)
                    self.apply_force(unit(o.pos - self.pos) * 0.2)
                    break

    def palette(self):
        c = self.get_depth_color(self.body_c)
        return tone(c, 0.7), tone(c, 1.0), mix(c, (255, 220, 200), 0.25), tone(self.get_depth_color(self.fin_c), 1.35)

    def back_fins(self, g):
        edge = tone(g.fin, 1.4)
        if self.male():
            return [fin_tail(g, "round", 42, 54, rays=18, edge=edge, width=SS, alpha=200),
                    fin_on_top(g, 0.56, 0.12, 24, -12, 0.5, rays=14, edge=edge, width=SS, alpha=200),
                    fin_on_belly(g, 0.66, 0.1, 28, -14, 0.5, rays=16, edge=edge, width=SS, alpha=200)]
        return [fin_tail(g, "round", 20, 24, rays=10, alpha=205), fin_on_top(g, 0.55, 0.3, 9, -3, 0.5, rays=8),
                fin_on_belly(g, 0.6, 0.3, 10, -3, 0.5, rays=8)]

    def front_fins(self, g):
        out = [fin_pectoral(g, 0.7, 12, 0.15, alpha=140)]
        if self.male():
            out.append(fin_pelvic(g, 0.62, 24, 10, color=g.fin, alpha=190))
        return out

    def decorate(self, g, layer):
        for dy, a in ((-0.6, 70), (-0.1, 40)):
            pygame.draw.line(layer, (255, 255, 255, a), (g.rx + 0.2 * g.L, g.cy + dy * g.ht),
                             (g.rx + 0.82 * g.L, g.cy + (dy - 0.12) * g.ht), max(1, int(g.z * 1.5)))
        rng = random.Random(self.id)
        for _ in range(22):   # iridescent scale glints
            pygame.draw.circle(layer, (*tone(g.belly, 1.2), 90), (int(g.rx + rng.uniform(0.2, 0.85) * g.L),
                                                                  int(g.cy + rng.uniform(-0.8, 0.8) * g.ht)), max(1, int(g.z * 0.9)))


DISCUS_MORPHS = [((226, 120, 60), (240, 170, 90), (60, 160, 190)), ((236, 190, 80), (250, 226, 150), (230, 120, 60)),
                 ((70, 140, 200), (150, 200, 230), (30, 80, 150))]


class Discus(FWFish):
    """Discus: a tall, round, calm cichlid with wavy turquoise streaks. Pairs stay close."""
    family_name = "discus"
    social_base = 0.7
    lane_frac = 0.4
    unique = True
    beat = 1.3
    W, H = 220, 230
    L, HT, HB = 76, 44, 42
    shape = dict(peak=0.5, pt=0.85, pn=0.8, ped=0.25)
    eye_r, eye_u, eye_dy = 5.0, 0.8, -0.18
    eye_col = (210, 40, 30)
    sway_amp = 4
    scale_size = 7
    shadow = 16

    def __init__(self, x, y):
        super().__init__(x, y)
        self.body_c, self.belly_c, self.stripe_c = random.choice(DISCUS_MORPHS)
        self.pos.y = lane(random.uniform(0.25, 0.55))
        self.z = random.uniform(0.62, 0.8)
        self.max_speed = 1.6

    def behavior(self, fishes):
        self.eat_daphnia(180)
        self.prefer_depth(lane(0.2), lane(0.65), 0.004)
        self.wobble(0.3, 0.03)
        p = getattr(self, "partner", None)
        if p is not None and p.alive and (eco.t + self.id) % 3 == 0:
            to = p.pos - self.pos
            if to.length() > 90:
                self.apply_force(unit(to) * 0.05)
        self.tilt(12)

    def palette(self):
        c = self.get_depth_color(self.body_c)
        return tone(c, 0.78), tone(c, 1.0), mix(self.get_depth_color(self.belly_c), (255, 240, 220), 0.3), tone(c, 0.9)

    def back_fins(self, g):
        edge = tone(g.fin, 1.3)
        return [fin_tail(g, "round", 22, 20, rays=10, edge=edge, width=SS),
                fin_on_top(g, 0.84, 0.12, 15, -3, 0.5, rays=20, edge=edge, width=SS, alpha=205),
                fin_on_belly(g, 0.8, 0.12, 15, -3, 0.5, rays=20, edge=edge, width=SS, alpha=205)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.68, 16, 0.1, alpha=150), fin_pelvic(g, 0.6, 22, 8, color=g.fin, alpha=190)]

    def decorate(self, g, layer):
        col = self.get_depth_color(self.stripe_c)
        for k in range(10):   # wavy streaks across the whole disc
            x = g.rx + (0.16 + 0.07 * k) * g.L
            pts = [(x + math.sin(j * 1.1 + k) * 3 * g.z, g.cy + (j - 3) / 3.0 * g.ht * 0.96) for j in range(7)]
            pygame.draw.lines(layer, (*col, 140), False, pts, max(1, int(g.z * 1.5)))
        bars(g, layer, [0.3, 0.52, 0.74], 0.025, (40, 30, 30), alpha=55, bow=0.02)


class Killifish(FWFish):
    """Gardner's killifish: a small surface dweller. Males are blue-green with red spots and a dark-banded tail."""
    family_name = "killi"
    social_base = 0.5
    lane_frac = 0.12
    beat = 3.2
    W, H = 140, 100
    L, HT, HB = 38, 9, 8
    shape = dict(peak=0.55, pt=0.7, pn=0.55, ped=0.2)
    eye_r, eye_u, eye_dy = 3.2, 0.8, -0.1
    eye_col = (230, 190, 70)
    sway_amp = 4
    shadow = 7

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.04, 0.22)))
        self.z = random.uniform(0.55, 0.8)
        self.max_speed = 2.4

    def male(self):
        return getattr(self, "sex", "M") == "M"

    def behavior(self, fishes):
        self.eat_daphnia(200)
        self.prefer_depth(lane(0.02), lane(0.28), 0.006)
        self.wobble(0.5, 0.05)
        if random.random() < 0.0015:   # skim the surface for fallen insects
            self.apply_force(pygame.Vector2(0, (WATER_TOP + 14 - self.pos.y) * 0.06))
        if (eco.t + self.id) % 20 == 0:
            near = [o for o in fishes if o is not self and type(o) is Killifish and self.pos.distance_squared_to(o.pos) < 220 ** 2]
            if near:
                c = sum((o.pos for o in near), pygame.Vector2()) / len(near)
                self.apply_force(unit(c - self.pos) * 0.12)
        self.tilt(24)

    def palette(self):
        if self.male():
            c = self.get_depth_color((50, 150, 170))
            return tone(c, 0.6), tone(c, 1.0), mix(c, (255, 240, 200), 0.4), self.get_depth_color((236, 176, 50))
        c = self.get_depth_color((150, 138, 108))
        return tone(c, 0.7), tone(c, 1.0), mix(c, (240, 230, 205), 0.4), self.get_depth_color((170, 160, 130))

    def back_fins(self, g):
        if self.male():
            edge = (30, 20, 20)
            return [fin_tail(g, "round", 20, 24, rays=10, edge=edge, width=SS),
                    fin_on_top(g, 0.4, 0.16, 11, -3, 0.5, rays=8, alpha=215),
                    fin_on_belly(g, 0.5, 0.2, 9, -2, 0.5, rays=7, alpha=215)]
        return [fin_tail(g, "round", 14, 17, rays=8), fin_on_top(g, 0.4, 0.2, 7, -2, 0.5, rays=6), fin_on_belly(g, 0.5, 0.25, 6, -1, 0.5, rays=5)]

    def front_fins(self, g):
        return [fin_pectoral(g, 0.72, 9, 0.12, alpha=140)]

    def decorate(self, g, layer):
        rng = random.Random(5)
        if self.male():
            for _ in range(16):   # red flank spots
                pygame.draw.circle(layer, (220, 50, 40, 220), (int(g.rx + rng.uniform(0.2, 0.85) * g.L),
                                                               int(g.cy + rng.uniform(-0.6, 0.7) * g.ht)), max(1, int(g.z * 1.0)))
            pygame.draw.line(layer, (255, 255, 255, 80), (g.rx + 0.2 * g.L, g.cy - g.ht * 0.6), (g.rx + 0.8 * g.L, g.cy - g.ht * 0.7), max(1, int(g.z * 1.4)))
        else:
            pygame.draw.circle(layer, (50, 44, 34, 190), (int(g.rx + 0.24 * g.L), int(g.cy - g.ht * 0.1)), max(2, int(g.z * 2.4)))


# Every species stays available; which ones are actually stocked comes from the active set in aquarium_config.json.
FW_CLASSES = (DemasoniCichlid, YellowPrinceCichlid, CobaltZebra, RedZebra, KenyiCichlid, PeacockCichlid, AuratusCichlid,
              IceBlueCichlid, SocolofiCichlid, AngelFish,
              NeonTetra, RummyNose, CardinalTetra, EmberTetra, BlackSkirtTetra, LemonTetra,
              MosaicGuppy, TuxedoGuppy, SunsetGuppy, MoscowGuppy,
              Pleco, BalaShark, BoesemaniRainbow, PearlGourami, ClownLoach, TigerBarb,
              Corydoras, Otocinclus, BristlenosePleco, Betta, Discus, Killifish)
COMMUNITY_TARGET = {}    # class -> share of the community      (filled by load_fish_config)
COMMUNITY_GROUP = {}     # class -> (smallest, largest) group    (filled by load_fish_config)


def habitat_anchor(fish_class):
    """Where this species likes to hang out: cichlids by a sword plant or rock, bottom dwellers on the sand and rocks,
    angelfish and everything else at the depth set by the species' lane_frac."""
    floor = SCREEN_HEIGHT - SAND_HEIGHT
    x = random.randint(80, SCREEN_WIDTH - 80)
    if getattr(fish_class, "open_water", False):
        return pygame.Vector2(x, lane(random.uniform(0.2, 0.45)))
    if fish_class.family_name == "cichlid":
        pool = nest_spots + cave_spots * 3 + [spot for spot, _ in rock_spots]
        if pool:
            spot = random.choice(pool)
            return pygame.Vector2(spot.x, spot.y - random.randint(15, 80))
    if getattr(fish_class, "bottom", False):
        if rock_spots and random.random() < 0.6:
            spot = random.choice(rock_spots)[0]
            return pygame.Vector2(spot.x, spot.y - random.randint(0, 30))
        return pygame.Vector2(x, floor - 30)
    return pygame.Vector2(x, lane(getattr(fish_class, "lane_frac", 0.4)))


def spawn_group(fish_class, count):
    anchor = habitat_anchor(fish_class)
    group = []
    for _ in range(count):
        x = max(30, min(SCREEN_WIDTH - 30, anchor.x + random.randint(-45, 45)))
        y = max(WATER_TOP + 30, min(SCREEN_HEIGHT - SAND_HEIGHT - 30, anchor.y + random.randint(-35, 35)))
        group.append(fish_class(x, y))
    return group


# ---- carrying capacity: how many fish the tank can hold, worked out from geometry, water chemistry and frame budget ----
# Space:  every species claims "personal water" = (its drawn body area) x (how much room that lifestyle wants).
#         Schooling fish tolerate crowding (small factor); lone roamers and territorial fish need far more.
#         The tank's usable water area, times the number of depth lanes the z-sorting gives us, is the supply.
# Water:  update_water() adds  0.05 + 0.0015/plant + 0.03/crawler  per tick-pair and each fish costs 0.003, so the
#         filter can carry (gain * WATER_MARGIN) / 0.003 fish before quality starts to fall; the margin leaves room for
#         algae and uneaten food.
# Speed:  a hard ceiling so the sim stays smooth.
SPACE_FACTOR = {"tetra": 5.0, "barb": 6.0, "rainbow": 7.0, "bala": 8.0, "loach": 8.0, "gourami": 12.0, "pleco": 14.0,
                "cichlid": 14.0, "cory": 5.0, "oto": 4.0,
                "betta": 14.0, "discus": 13.0, "killi": 6.0}
DEPTH_LANES = 2.2        # fish at different z overlap on screen without actually crowding each other
WATER_MARGIN = 0.7       # use at most 70% of the water-cleaning budget for fish
FRAME_BUDGET = 45        # most fish the frame time will tolerate (was 56: too slow on busy frames)
FILL_TARGET = 0.85       # seed the tank at this share of its capacity; the rest is headroom for breeding
FOOTPRINTS = {}
# Q cycles these. strips = how many slices the plant layer is spread over (more = lighter frames), smooth = smoothscale to the
# display (off = faster nearest scaling), fish = share of the fish cap that can be stocked.
QUALITY_SPECS = {"LOW": dict(strips=4, smooth=False, fish=0.7), "MED": dict(strips=3, smooth=True, fish=1.0),
                 "HIGH": dict(strips=2, smooth=True, fish=1.0)}
QUALITY = ["MED"]
VOL = {"master": 1.0, "fx": 1.0}
GOV = {"on": True, "base": None, "n": 0, "sum": 0.0, "cool": 0}   # "auto_quality" in aquarium_config.json
_Q_ORDER = ["HIGH", "MED", "LOW"]    # most to least work per frame


def quality_governor():
    """Every three seconds: if frames take longer than 17 ms of real work, drop one quality step; if there is plenty of room, climb back
    toward the quality the player chose. The player's own choice (Q key or config) is always the ceiling."""
    if not GOV["on"] or PM["on"] or pygame.display.get_surface() is None:
        return
    if GOV["base"] is None:
        GOV["base"] = QUALITY[0]
    GOV["n"] += 1
    GOV["sum"] += clock.get_rawtime()
    GOV["cool"] = max(0, GOV["cool"] - 1)
    if GOV["n"] < 180:
        return
    avg = GOV["sum"] / GOV["n"]
    GOV["n"], GOV["sum"] = 0, 0.0
    i = _Q_ORDER.index(QUALITY[0])
    if avg > 17.0 and i < len(_Q_ORDER) - 1:
        QUALITY[0] = _Q_ORDER[i + 1]
        GOV["cool"] = 3600
        notify(f"Quality lowered to {QUALITY[0]} for smoother play (frames took {avg:.0f} ms; 'auto_quality': false turns this off)", log=False)
    elif avg < 9.0 and GOV["cool"] == 0 and i > _Q_ORDER.index(GOV["base"]):
        QUALITY[0] = _Q_ORDER[i - 1]
        GOV["cool"] = 1800
        notify(f"Quality raised to {QUALITY[0]}", log=False)

# ---- fish sets: pick the community from aquarium_config.json ("active_set": cichlid_set / tetra_set / mixed_set) ----
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aquarium_config.json")
DEFAULT_SETS = {
    "cichlid_set": {"DemasoniCichlid": [9, 6, 9], "YellowPrinceCichlid": [4, 3, 4], "CobaltZebra": [3, 3, 3], "RedZebra": [3, 2, 3],
                    "KenyiCichlid": [3, 2, 3], "PeacockCichlid": [3, 2, 3], "AuratusCichlid": [2, 2, 2], "IceBlueCichlid": [2, 2, 2],
                    "SocolofiCichlid": [2, 2, 2], "AngelFish": [2, 2, 2]},
    "tetra_set": {"NeonTetra": [10, 8, 11], "RummyNose": [6, 5, 7], "CardinalTetra": [8, 6, 9], "EmberTetra": [9, 7, 10],
                  "BlackSkirtTetra": [4, 3, 4], "LemonTetra": [5, 4, 5], "MosaicGuppy": [4, 3, 5], "TuxedoGuppy": [4, 3, 5],
                  "SunsetGuppy": [4, 3, 5], "MoscowGuppy": [4, 3, 5], "Corydoras": [6, 4, 6], "Otocinclus": [5, 3, 5],
                  "BristlenosePleco": [2, 1, 2]},
    "mixed_set": {"DemasoniCichlid": [4, 3, 4], "YellowPrinceCichlid": [2, 2, 2], "CobaltZebra": [2, 2, 2], "PeacockCichlid": [2, 2, 2],
                  "AngelFish": [2, 2, 2], "NeonTetra": [5, 4, 5], "RummyNose": [4, 3, 4], "CardinalTetra": [5, 4, 5],
                  "EmberTetra": [4, 4, 4], "BlackSkirtTetra": [2, 2, 2], "MosaicGuppy": [3, 3, 3],
                  "SunsetGuppy": [3, 3, 3], "BalaShark": [2, 2, 2], "BoesemaniRainbow": [3, 3, 3],
                  "TigerBarb": [3, 3, 3], "ClownLoach": [3, 3, 3], "Pleco": [2, 1, 2], "PearlGourami": [2, 2, 2]},
    "showcase_set": {"Betta": [2, 1, 2], "Discus": [4, 2, 4], "Killifish": [6, 4, 6], "MosaicGuppy": [4, 3, 5],
                     "SunsetGuppy": [4, 3, 5], "Corydoras": [5, 4, 5], "Otocinclus": [4, 3, 4], "NeonTetra": [8, 6, 9]},
}
CONFIG_HELP = ("active_set picks which set of fish is stocked (cichlid_set, tetra_set, mixed_set, or any set you add under 'sets'). "
               "Each set maps a species class name to [share, smallest_group, largest_group]. max_fish caps the number of fish "
               "(lower it if the frame rate drops). Press R in game to reload this file. Species: "
               + ", ".join(c.__name__ for c in FW_CLASSES))
DEFAULT_SET = "tetra_set"
ACTIVE_SET = DEFAULT_SET


def load_fish_config():
    """Read aquarium_config.json (creating it with the default sets the first time) and apply the active set."""
    global FRAME_BUDGET, ACTIVE_SET
    cfg = {"_help": CONFIG_HELP, "active_set": DEFAULT_SET, "max_fish": FRAME_BUDGET, "sets": DEFAULT_SETS}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            user = json.load(fh)
        cfg["active_set"] = user.get("active_set", cfg["active_set"])
        cfg["max_fish"] = user.get("max_fish", cfg["max_fish"])
        cfg["sets"] = dict(DEFAULT_SETS)
        cfg["sets"].update(user.get("sets", {}))
    except FileNotFoundError:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except OSError:
            pass
    except (OSError, ValueError) as err:
        print(f"aquarium_config.json could not be read ({err}); using the defaults")
    sets = cfg["sets"]
    name = cfg["active_set"]
    if name not in sets:
        print(f"unknown fish set '{name}', using {DEFAULT_SET} (available: {', '.join(sets)})")
        name = DEFAULT_SET if DEFAULT_SET in sets else next(iter(sets))
    by_name = {c.__name__: c for c in FW_CLASSES}
    target, group = {}, {}
    for cname, spec in sets[name].items():
        cls = by_name.get(cname)
        if cls is None:
            print(f"fish set '{name}': unknown species '{cname}' skipped")
            continue
        try:
            share = max(1, int(spec[0]))
            lo = max(1, int(spec[1])) if len(spec) > 1 else 1
            hi = max(lo, int(spec[2])) if len(spec) > 2 else lo
        except (TypeError, ValueError, IndexError):
            print(f"fish set '{name}': bad entry for {cname}, expected [share, smallest, largest]")
            continue
        target[cls], group[cls] = share, (lo, hi)
    if not target:
        print(f"fish set '{name}' is empty; using {DEFAULT_SET}")
        name = DEFAULT_SET
        target = {by_name[c]: v[0] for c, v in DEFAULT_SETS[name].items()}
        group = {by_name[c]: (v[1], v[2]) for c, v in DEFAULT_SETS[name].items()}
    COMMUNITY_TARGET.clear()
    COMMUNITY_TARGET.update(target)
    COMMUNITY_GROUP.clear()
    COMMUNITY_GROUP.update(group)
    try:
        FRAME_BUDGET = max(6, int(cfg["max_fish"]))
    except (TypeError, ValueError):
        pass
    ACTIVE_SET = name
    print(f"fish set: {name} ({len(target)} species, up to {FRAME_BUDGET} fish)")


load_fish_config()


def family_of(cls):
    return getattr(cls, "family_name", None) or "cichlid"


def footprint(cls):
    """Average on-screen body area (px^2) of an adult of this species, measured by drawing it and taking the
    bounding box of the pixels (clipped so the sand shadow is ignored)."""
    if cls not in FOOTPRINTS:
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60
        window = pygame.Rect(cx - 220, cy - 150, 440, 300)
        draw = ORIGINAL_DRAW.get(cls, cls.draw)
        areas = []
        for _ in range(4):
            canvas.fill((0, 0, 0, 0))
            canvas.set_clip(window)
            probe = cls(cx, cy)
            probe.vel = pygame.Vector2(1, 0)
            draw(probe, canvas)
            r = canvas.subsurface(window).get_bounding_rect()
            areas.append(0.72 * r.w * r.h)  # a fish fills about 72% of its bounding box
        FOOTPRINTS[cls] = sum(areas) / len(areas)
    return FOOTPRINTS[cls]


def demand(cls):
    """Square pixels of water one fish of this species needs to live comfortably."""
    return footprint(cls) * (getattr(cls, "space", None) or SPACE_FACTOR[family_of(cls)])


def tank_budget():
    """Total 'personal water' the tank can supply, as the lower of the space and water-quality limits."""
    area = SCREEN_WIDTH * (SCREEN_HEIGHT - WATER_TOP - SAND_HEIGHT) * DEPTH_LANES
    water_fish = (0.05 + 0.0015 * len(plants) + 0.03 * len(crawlers)) * WATER_MARGIN / 0.003
    mean_demand = sum(demand(c) * s for c, s in COMMUNITY_TARGET.items()) / sum(COMMUNITY_TARGET.values())
    return min(area, water_fish * mean_demand, FRAME_BUDGET * QUALITY_SPECS[QUALITY[0]]["fish"] * mean_demand)


def tank_load(extra=()):
    return sum(demand(type(f)) for f in fishes if f.alive) + sum(demand(c) for c in extra)


def tank_capacity():
    """How many fish of the community mix fit."""
    mean_demand = sum(demand(c) * s for c, s in COMMUNITY_TARGET.items()) / sum(COMMUNITY_TARGET.values())
    return int(tank_budget() / mean_demand)


def has_room(cls, count=1):
    return tank_load([cls] * count) <= tank_budget()


def spawn_community(total=None):
    """A starting community in the community's proportions, placed in species groups at their habitats and sized so
    the stocked load stays at FILL_TARGET of the tank's budget."""
    if total is None:
        total = int(tank_capacity() * FILL_TARGET)
    scale = total / sum(COMMUNITY_TARGET.values())
    population = []
    for fish_class, share in COMMUNITY_TARGET.items():
        quota = max(1, round(share * scale))
        while quota > 0:
            lo, hi = COMMUNITY_GROUP[fish_class]
            size = min(quota, random.randint(lo, hi))
            population += spawn_group(fish_class, size)
            quota -= size
    while len(population) > 1 and sum(demand(type(f)) for f in population) > tank_budget() * FILL_TARGET:
        population.pop()  # rounding pushed us over: drop the last arrivals
    return population


def spawn_random_fish(fishes=None):
    """One replacement fish, favouring whichever species is furthest below its share of the community."""
    current = globals().get("fishes") or []
    counts = {cls: 0 for cls in COMMUNITY_TARGET}
    for f in current:
        if type(f) in counts:
            counts[type(f)] += 1
    total = max(len(current), 1)
    weights = [max(0.4, share * total / 30 - counts[cls] + 0.5) for cls, share in COMMUNITY_TARGET.items()]
    fish_class = random.choices(list(COMMUNITY_TARGET), weights)[0]
    return spawn_group(fish_class, 1)[0]


# =====================================================================
#  ECOSYSTEM LAYER
#  Day/night, tank mood, random events, hunters (channa, fire eel,
#  crayfish) and the social life of the fish: fear, hiding, sleep,
#  curiosity, mating, nest guarding and cleaning stations.
# =====================================================================
DAY_LENGTH = 14400  # frames in one full day/night cycle (about four minutes)
BASE_DAPHNIA = 40
EMOTE_SIZE = 22

eco = None
predators, stations = [], []
fx, emotes, ripples, inks, respawn_queue = [], [], [], [], []
nest_spots, rock_spots, cave_spots, thicket_spots = [], [], [], []
mouse_track = {"pos": pygame.Vector2(-999, -999), "still": 0, "speed": 0.0, "inside": False}


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def unit(v, fallback=(1.0, 0.0)):
    return v.normalize() if v.length_squared() > 1e-9 else pygame.Vector2(fallback)


def ground_y(x):
    return (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2


journal = []  # (stamp, text) pairs, newest last


def notify(text, log=True):
    global light_notif_text, light_notif_alpha
    light_notif_text = text
    light_notif_alpha = 255
    if log and eco is not None:
        hours = eco.clock * 24
        journal.append((f"Day {eco.day} {int(hours):02d}:{int((hours % 1) * 60):02d}", text))
        del journal[:-80]


# ---- procedural sound effects (no asset files needed) ----
SFX = {}


def build_sfx():
    init = pygame.mixer.get_init()
    if not init or init[1] != -16:
        return
    freq, _, channels = init

    def make(fn, dur):
        buf = array("h")
        for i in range(int(freq * dur)):
            v = int(max(-1.0, min(1.0, fn(i / freq, i / (freq * dur)))) * 12000)
            buf.extend([v] * channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    rnd = random.Random(7)
    SFX["thump"] = make(lambda t, u: (math.sin(math.tau * (90 - 50 * u) * t) * 0.9 + rnd.uniform(-0.25, 0.25)) * (1 - u) ** 2, 0.4)
    SFX["knock"] = make(lambda t, u: (math.sin(math.tau * 210 * t) * 0.7 + rnd.uniform(-0.3, 0.3)) * (1 - u) ** 3, 0.14)
    SFX["bubble"] = make(lambda t, u: math.sin(math.tau * (420 + 700 * u) * t) * 0.5 * (1 - u) ** 1.5, 0.09)
    SFX["chime"] = make(lambda t, u: (math.sin(math.tau * 660 * t) + math.sin(math.tau * 880 * (t - 0.12 if t > 0.12 else 0))) * 0.3 * (1 - u) ** 1.2, 0.5)
    SFX["click"] = make(lambda t, u: rnd.uniform(-1, 1) * (1 - u) ** 4, 0.06)
    SFX["hatch"] = make(lambda t, u: math.sin(math.tau * (500 + 900 * ((u * 3) % 1)) * t) * 0.4 * (1 - u), 0.3)
    SFX["shutter"] = make(lambda t, u: rnd.uniform(-1, 1) * (1 - (u * 5) % 1) ** 5 * (1 if u < 0.4 else 0.55) * (1 - u), 0.22)
    SFX["hum"] = make(lambda t, u: math.sin(math.tau * 50 * t) * 0.6 + math.sin(math.tau * 100 * t) * 0.25 + math.sin(math.tau * 150 * t) * 0.08, 1.0)
    low = [0.0]

    def _thunder(t, u):
        low[0] += (rnd.uniform(-1, 1) - low[0]) * 0.025
        return low[0] * 7 * (1 - u) ** 1.6 * (0.55 + 0.45 * math.sin(t * 8))

    SFX["thunder"] = make(_thunder, 2.0)
    SFX["power"] = make(lambda t, u: math.sin(math.tau * (320 - 280 * u) * t) * 0.5 * (1 - u) ** 1.2, 0.7)


def play_sfx(name, volume=0.6):
    snd = SFX.get(name)
    if snd is not None and not is_muted:
        snd.set_volume(volume * VOL["master"] * VOL["fx"])
        snd.play()


def apply_music_volume():
    try:
        night = eco.night if eco is not None else 0.0   # the music softens as the tank goes dark
        pygame.mixer.music.set_volume(0.0 if is_muted else 0.7 * VOL["master"] * (1.0 - 0.45 * night))
    except pygame.error:
        pass


AWAY = {"on": True}
PRED = {"on": False}   # "predators": channa, fire eel and crayfish hunt the fish
TURTLE = {"on": False}   # "show_turtle": the rare turtle visitor event
CRAY = {"on": False}   # "show_crayfish" in aquarium_config.json
strains = {}   # "Class|hue|tail" -> [best generation, number born]
GOALS_DONE = set()
VISIT = {"on": False}      # "show_visitors": the frog and kingfisher guests
NEWTANK = {"on": False}    # "new_tank": start with an uncycled tank (nitrogen-cycle game)
X = {"points": 0, "owned": [], "memorial": [], "reqs": 0, "shows": 0, "wins": 0, "show_day": -9, "scapes": 0, "clips": 0,
     "guests": 0, "ferts": 0, "sound": "AUTO", "weeks": [], "best_scape": 0, "tours": 0, "blooms": 0,
     "sold": 0, "streak": 0, "chal": {}, "chal_won": [], "raids": 0, "relapses": 0,
     "cash": 0, "gear": [], "line": {}, "fow": "", "tut": 0, "tut_on": True, "evok": 0, "wx": True}
X_DEFAULT = json.loads(json.dumps(X))


def load_prefs():
    """Quality and volume are kept in aquarium_config.json next to the fish sets."""
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return
    q = str(data.get("quality", "MED")).upper()
    if q in QUALITY_SPECS:
        QUALITY[0] = q
    GOV["on"] = bool(data.get("auto_quality", True))
    GOV["base"] = QUALITY[0]
    AWAY["on"] = bool(data.get("away_mode", True))
    PRED["on"] = bool(data.get("predators", False))
    CRAY["on"] = bool(data.get("show_crayfish", False))
    TURTLE["on"] = bool(data.get("show_turtle", False))
    VISIT["on"] = bool(data.get("show_visitors", False))
    NEWTANK["on"] = bool(data.get("new_tank", False))
    ex = data.get("extra")
    if isinstance(ex, dict):
        for k in X:
            if k in ex and type(ex[k]) is type(X[k]):
                X[k] = ex[k]
    if isinstance(data.get("strains"), dict):
        for k, v in data["strains"].items():
            if isinstance(v, list) and len(v) == 2:
                strains[str(k)] = [int(v[0]), int(v[1])]
    if isinstance(data.get("goals"), list):
        GOALS_DONE.update(str(x) for x in data["goals"])
    audio = data.get("audio", {})
    try:
        VOL["master"] = clamp(float(audio.get("master", 1.0)))
        VOL["fx"] = clamp(float(audio.get("effects", 1.0)))
    except (TypeError, ValueError, AttributeError):
        pass


def save_prefs():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        data = {}
    except (OSError, ValueError):
        return   # the file is being edited or broken: never overwrite the fish sets
    data["quality"] = GOV["base"] or QUALITY[0]
    data["auto_quality"] = GOV["on"]
    data["audio"] = {"master": VOL["master"], "effects": VOL["fx"]}
    data["away_mode"] = AWAY["on"]
    data["predators"] = PRED["on"]
    data["show_crayfish"] = CRAY["on"]
    data["show_turtle"] = TURTLE["on"]
    data["show_visitors"] = VISIT["on"]
    data["new_tank"] = NEWTANK["on"]
    data["extra"] = X
    data["goals"] = sorted(GOALS_DONE)
    data["strains"] = {k: v for k, v in strains.items()}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


load_prefs()


def nice_name(obj):
    name = obj.__name__ if isinstance(obj, type) else obj.__class__.__name__
    return "".join(" " + c if c.isupper() and i else c for i, c in enumerate(name))


class Fleck:
    """A tiny drifting speck: scales from a catch, sparkles from a cleaning, jet bubbles."""

    def __init__(self, pos, vel, color, life, size=2, gravity=0.015):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.color = color
        self.life = self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self):
        self.vel *= 0.96
        self.vel.y += self.gravity
        self.pos += self.vel
        self.life -= 1

    def draw(self, surface):
        col = mix((20, 50, 100), self.color, clamp(self.life / self.max_life))
        pygame.draw.circle(surface, col, (int(self.pos.x), int(self.pos.y)), self.size)


def burst(pos, color, count=10, speed=2.0, life=60, size=2, gravity=0.015):
    for _ in range(count):
        if len(fx) > 400:
            return
        ang = random.uniform(0, math.tau)
        sp = random.uniform(0.3, speed)
        fx.append(Fleck(pos, (math.cos(ang) * sp, math.sin(ang) * sp), color,
                        random.randint(max(2, life // 2), life), size, gravity))


MIST_CACHE = {}


class Mist:
    """A cloud of blood that blooms around a bitten fish and thins out."""

    def __init__(self, pos, size, delay=0):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(random.uniform(-0.4, 0.4), random.uniform(-0.3, 0.05))
        self.size = size
        self.delay = delay
        self.t = 0
        self.max_life = 120
        self.life = self.max_life + delay

    def update(self):
        self.life -= 1
        if self.delay > 0:
            self.delay -= 1
            return
        self.t += 1
        self.pos += self.vel
        self.vel *= 0.97
        self.pos.x += eco.current * 4

    def draw(self, surface):
        if self.delay > 0:
            return
        r = int(self.size * (0.3 + 0.9 * (1 - math.exp(-self.t / 30)))) // 3 * 3
        if r < 3:
            return
        spr = MIST_CACHE.get(r)
        if spr is None:
            spr = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for k in range(r, 0, -2):
                pygame.draw.circle(spr, (175, 18, 28, int(120 * (1 - k / r) ** 0.7) + 14), (r, r), k)
            MIST_CACHE[r] = spr
        spr.set_alpha(int(255 * clamp(1 - self.t / self.max_life) ** 1.3))
        surface.blit(spr, spr.get_rect(center=(int(self.pos.x), int(self.pos.y))))


class Chunk:
    """A torn bit of flesh or scale that tumbles away from the bite."""

    def __init__(self, pos, color):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(1.0, 3.4)
        self.pos = pygame.Vector2(pos) + (random.uniform(-6, 6), random.uniform(-4, 4))
        self.vel = pygame.Vector2(math.cos(ang) * sp, math.sin(ang) * sp - 0.4)
        self.color = color
        self.rot = random.uniform(0, math.tau)
        self.spin = random.uniform(-0.45, 0.45)
        r = random.uniform(2.2, 5.0)
        self.shape = [(random.uniform(0.5, 1.0) * r, k * math.tau / 5 + random.uniform(-0.4, 0.4)) for k in range(5)]
        self.life = self.max_life = random.randint(55, 95)

    def update(self):
        self.vel *= 0.95
        self.vel.y += 0.035
        self.pos += self.vel
        self.rot += self.spin
        self.life -= 1

    def draw(self, surface):
        f = clamp(self.life / self.max_life)
        col = mix((20, 50, 100), self.color, f ** 0.6)
        pts = [(self.pos.x + math.cos(a + self.rot) * rr, self.pos.y + math.sin(a + self.rot) * rr) for rr, a in self.shape]
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.line(surface, mix((20, 50, 100), (170, 20, 30), f), pts[0], pts[2], 1)


def bite_effect(prey):
    """Blood mist plus a spray of flesh bits and scales around the bitten fish."""
    if len(fx) > 360:
        return
    pos = pygame.Vector2(prey.pos)
    col = getattr(prey, "base_color", (220, 170, 150))
    size = 34 + 40 * max(getattr(prey, "z", 0.6), 0.3)
    for i in range(3):
        fx.append(Mist(pos + (random.uniform(-10, 10), random.uniform(-7, 7)), size * random.uniform(0.8, 1.2), i * 7))
    for _ in range(7):
        fx.append(Chunk(pos, col if random.random() < 0.6 else (215, 70, 75)))
    burst(pos, (190, 25, 35), 10, 2.4, 60, 2, 0.0)
    burst(pos, mix(col, (255, 255, 255), 0.35), 8, 2.8, 60, 1)


def eat_fish(hunter, prey, scare=0.5):
    """Shared kill routine for every hunter: the prey dies, blood clouds the water, scraps sink."""
    prey.alive = False
    hunter.kills = getattr(hunter, "kills", 0) + 1
    eco.kills += 1
    eco.scare(scare)
    bite_effect(prey)
    play_sfx("thump")
    for _ in range(2):
        pellets.append(Scrap(prey.pos.x + random.uniform(-14, 14), prey.pos.y + random.uniform(-8, 8)))
    who = f"{hunter.name} the {getattr(hunter, 'label', nice_name(hunter))}" if hasattr(hunter, "name") else hunter.label
    notify(f"{who} caught {getattr(prey, 'name', 'a')} the {nice_name(prey)}!" if hasattr(prey, "name")
           else f"{who} caught a {nice_name(prey)}!")


INK_BASE = None


class Ink:
    """A cloud of ink (unused in freshwater; kept so old saves load): swells quickly, then thins out. Fish steer clear of it."""

    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.age = 0
        self.life = 280

    @property
    def radius(self):
        return 14 + 54 * (1 - math.exp(-self.age / 55))

    def update(self):
        self.age += 1
        self.pos.x += eco.current * 8
        self.pos.y -= 0.03

    def draw(self, surface):
        global INK_BASE
        if INK_BASE is None:
            INK_BASE = pygame.Surface((96, 96), pygame.SRCALPHA)
            for r in range(48, 0, -2):
                pygame.draw.circle(INK_BASE, (16, 12, 24, min(255, int(215 * (1 - r / 48) ** 0.5) + 40)), (48, 48), r)
        r = int(self.radius)
        sprite = pygame.transform.smoothscale(INK_BASE, (r * 2, r * 2))
        sprite.set_alpha(int(255 * clamp(1 - self.age / self.life) ** 0.8))
        surface.blit(sprite, sprite.get_rect(center=(int(self.pos.x), int(self.pos.y))))


# ---- emotes: little speech bubbles that show what a fish is feeling ----
_emote_font = None
EMOTE_CACHE = {}
EMOTE_COLORS = {"!": (210, 40, 40), "?": (40, 100, 200), "z": (90, 90, 170), "*": (220, 160, 20), "<3": (225, 60, 110)}


def emote_sprite(glyph):
    global _emote_font
    spr = EMOTE_CACHE.get(glyph)
    if spr is None:
        if _emote_font is None:
            _emote_font = pygame.font.SysFont("Arial", 15, bold=True)
        spr = pygame.Surface((EMOTE_SIZE, EMOTE_SIZE), pygame.SRCALPHA)
        c = EMOTE_SIZE // 2
        pygame.draw.circle(spr, (250, 250, 255, 235), (c, c), c)
        pygame.draw.circle(spr, (50, 70, 110, 255), (c, c), c, 1)
        txt = _emote_font.render(glyph, True, EMOTE_COLORS.get(glyph, (40, 40, 40)))
        spr.blit(txt, txt.get_rect(center=(c, c)))
        EMOTE_CACHE[glyph] = spr
    return spr


def add_emote(f, glyph, life=75):
    if f.emote_cd > 0 or len(emotes) > 40:
        return
    f.emote_cd = 140
    emotes.append({"who": f, "glyph": glyph, "life": life, "max": life})


def draw_emotes(surface):
    for e in emotes[:]:
        e["life"] -= 1
        if e["life"] <= 0:
            emotes.remove(e)
            continue
        f = e["who"]
        age = e["max"] - e["life"]
        spr = emote_sprite(e["glyph"])
        surface.blit(spr, spr.get_rect(center=(int(f.pos.x), int(f.pos.y - 24 - 30 * f.z - age * 0.2))))


# ---- the world clock, mood and random events ----
MOOD_COLORS = {"CALM": (130, 220, 160), "CURIOUS": (130, 200, 255), "HUNGRY": (255, 200, 100),
               "TENSE": (255, 190, 90), "PANIC": (255, 90, 90), "DANGER": (255, 70, 70),
               "SLEEPING": (160, 160, 255), "FEEDING FRENZY": (110, 255, 200)}


class Ecosystem:
    def __init__(self):
        self.t = 0
        self.clock = 0.36           # 0 = midnight, 0.5 = noon
        self.cycle_on = True
        self.daylight = 1.0
        self.night = 0.0
        self.fear = 0.0             # ambient jumpiness of the whole tank
        self.avg_fear = 0.0
        self.current = 0.0
        self.current_goal = 0.0
        self.bloom = 0.0
        self.bloom_goal = 0.0
        self.event = None
        self.event_timer = 0
        self.next_event = random.randint(1800, 3000)
        self.kills = 0
        self.births = 0
        self.show_hud = True
        self.mood_counts = {}
        self.tank_mood = "CALM"
        self.day = 1
        self.moon_done = -1
        self.water = 90.0           # water quality, 0..100
        self.selected = None        # the fish being followed
        self.follow = False
        self.cam = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.show_journal = False
        self.feed_idx = 0
        self.decor_idx = 0
        self.photo = False
        self.glass = [0.0] * GLASS_COLS    # algae film on the front glass, per column
        self.wipe = -1.0                   # x of the squeegee while wiping, else -1
        self.filter = 1.0                  # how clean the filter sponge is
        self.lights = "SUN"                # SUN follows the clock, ON / OFF override it
        self.air_on = True
        self.realtime = False
        self.cinema = False
        self.cin_t = 0
        self.dark = 0.0                    # extra darkness: storms and power cuts
        self.dark_goal = 0.0
        self.flash = 0.0                   # lightning
        self.power = False
        self.storm_next = 0
        self.thunder_due = -1
        self.bag = None
        self.warned = set()
        self.temp = 25.0
        self.heater = "LOW"
        self.season = 0
        self.cloud = 0.0                   # cloudy water from overfeeding
        self.med_cd = 0
        self.nursery = None                # centre of the nursery net, if placed
        self.overgrown = 0.0
        self.timelapse = 0
        self.blue = 0                      # frames of methylene blue left in the water
        self.vit_cd = 0

    @property
    def full_moon(self):
        return self.day % 4 == 0

    def scare(self, amount):
        self.fear = clamp(self.fear + amount)

    def update(self):
        self.t += 1
        if self.realtime:
            nowf = real_clock_fraction()
            if nowf < self.clock - 0.5:
                self.day += 1
            self.clock = nowf
        elif self.cycle_on:
            self.clock += 1.0 / DAY_LENGTH
            if self.clock >= 1.0:
                self.clock -= 1.0
                self.day += 1
                notify(f"Day {self.day} begins", log=False)
        if self.event == "MOON SPAWNING" and self.t % 3 == 0 and fishes:
            f = random.choice(fishes)
            burst(f.pos, random.choice([(255, 190, 230), (170, 240, 255)]), 3, 0.8, 120, 2, -0.012)
        update_water()
        update_breeding()
        care_update()
        self.daylight = 0.5 + 0.5 * math.sin(math.tau * (self.clock - 0.25))
        self.night = clamp((0.32 - self.daylight) / 0.27)
        light_override()
        self.fear = max(0.0, self.fear - 0.0035)
        self.current += (self.current_goal - self.current) * 0.01
        self.bloom += (self.bloom_goal - self.bloom) * 0.01
        if self.event:
            self.event_timer -= 1
            if self.event_timer <= 0:
                self.end_event()
        elif self.night > 0.6 and self.full_moon and self.moon_done != self.day:
            self.moon_done = self.day
            self.start_event("MOON SPAWNING")
        elif self.t >= self.next_event:
            self.start_event()

    def start_event(self, name=None):
        if self.event:
            self.end_event()
        options = ["CURRENT SURGE", "DAPHNIA BLOOM", "THUNDERSTORM", "POWER CUT"]
        if self.bag is None and len(fishes) < FRAME_BUDGET - 5:
            options.append("NEW ARRIVALS")
        if PRED["on"] and sum(isinstance(p, Channa) for p in predators) < 2:
            options.append("CHANNA VISITOR")
        if TURTLE["on"] and not any(isinstance(v, Turtle) for v in visitors):
            options.append("RARE VISITOR")
        if VISIT["on"] and not any(isinstance(v, (Frog, Kingfisher)) for v in visitors):
            options.append("GUEST VISITOR")
        if name not in options and name != "MOON SPAWNING":
            name = random.choice([o for o in options if not (o == "THUNDERSTORM" and wx_ok())])
        self.event = name
        play_sfx("chime", 0.4)
        if name == "CURRENT SURGE":
            side = random.choice([-1, 1])
            self.current_goal = side * random.uniform(0.05, 0.1)
            self.event_timer = 840
            notify("The filter surges! Fish and plants are swept " + ("right" if side > 0 else "left"))
        elif name == "DAPHNIA BLOOM":
            self.bloom_goal = 1.0
            self.event_timer = 1500
            for _ in range(36):
                if len(daphnia) < 100:
                    daphnia.append(Daphnia())
            notify("Daphnia bloom! Live food everywhere")
        elif name == "MOON SPAWNING":
            self.bloom_goal = 0.6
            self.event_timer = 1500
            notify("Full moon! The whole tank is in a spawning mood")
            return
        elif name == "THUNDERSTORM":
            self.event_timer = 1500
            self.storm_next = random.randint(40, 140)
            self.dark_goal = 0.38
            notify("A thunderstorm rolls in: the lights may flicker")
        elif name == "POWER CUT":
            self.event_timer = 1000
            self.power = True
            self.dark_goal = 1.0
            self.current_goal = 0.0
            play_sfx("power", 0.7)
            notify("Power cut! The lights, filter and air stone are off")
        elif name == "NEW ARRIVALS":
            self.event_timer = 1100
            self.bag = ArrivalBag()
            notify("A bag of new fish floats at the surface to settle in")
        elif name == "RARE VISITOR":
            spawn_rare_visitor()
            self.event_timer = 300
        elif name == "GUEST VISITOR":
            spawn_guest()
            self.event_timer = 300
        else:
            spawn_visitor()
            self.event_timer = 300
            notify("An channa drifts in from the river")
        self.next_event = self.t + self.event_timer + random.randint(2400, 4800)

    def end_event(self):
        if self.event == "THUNDERSTORM":
            stats["storms"] += 1
            self.dark_goal = 0.0
            notify("The storm passes")
        if self.event == "POWER CUT":
            stats["powercuts"] += 1
            self.power = False
            self.dark_goal = 0.0
            self.dark = max(self.dark, 0.9)
            play_sfx("chime", 0.5)
            notify("Power is back: lights and filter restart")
        if self.event == "NEW ARRIVALS" and self.bag is not None:
            self.bag.release()
        if self.event == "DAPHNIA BLOOM":
            del daphnia[BASE_DAPHNIA:]
        if self.event == "MOON SPAWNING":
            notify("The moonlit mood fades")
            self.next_event = self.t + random.randint(1800, 3600)
        self.current_goal = 0.0
        self.bloom_goal = 0.0
        self.event = None

    def tap(self, pos):
        """Knocking on the glass: nearby fish bolt, hunters lose the scent."""
        pos = pygame.Vector2(pos)
        ripples.append([pos, 4.0, 50])
        play_sfx("knock")
        for f in fishes:
            d = f.pos.distance_to(pos)
            if d < 300 and hasattr(f, "bravery"):
                f.fear = max(f.fear, 0.7 * (1 - d / 300) * (1.2 - 0.5 * f.bravery))
        for p in predators:
            p.startle(pos)
        self.scare(0.1)

    def refresh_moods(self):
        if self.t % 20:
            return
        prey = [f for f in fishes if hasattr(f, "mood")]
        n = max(1, len(prey))
        counts = {}
        for f in prey:
            counts[f.mood] = counts.get(f.mood, 0) + 1
        self.mood_counts = counts
        self.avg_fear = sum(f.fear for f in prey) / n
        scared = counts.get("scared", 0) / n
        sleeping = (counts.get("sleeping", 0) + counts.get("hiding", 0)) / n
        hunters = [p for p in predators if p.hunts_fish]
        if any(p.state == "strike" for p in hunters):
            self.tank_mood = "DANGER"
        elif scared > 0.35:
            self.tank_mood = "PANIC"
        elif scared > 0.12 or any(p.state == "stalk" for p in hunters):
            self.tank_mood = "TENSE"
        elif self.night > 0.5 and sleeping > 0.4:
            self.tank_mood = "SLEEPING"
        elif self.event == "DAPHNIA BLOOM":
            self.tank_mood = "FEEDING FRENZY"
        elif counts.get("hungry", 0) / n > 0.4:
            self.tank_mood = "HUNGRY"
        elif counts.get("curious", 0) / n > 0.2:
            self.tank_mood = "CURIOUS"
        else:
            self.tank_mood = "CALM"


# =====================================================================
#  CARE, EVENTS, CLOCK, CAMERA, AWAY MODE AND GOALS
# =====================================================================
stats = {"fry": 0, "storms": 0, "powercuts": 0, "wipes": 0, "rinses": 0, "photos": 0, "arrivals": 0,
         "shrimplets": 0, "moults": 0, "away": 0}
feed_mem = {"x": 0.0, "y": 0.0, "conf": 0.0, "told": False}
moult_shells = []
GLASS_COLS = 40
GLASS_RATE = [random.Random(31 + i).uniform(0.6, 1.4) for i in range(GLASS_COLS)]
AIR_X = int(SCREEN_WIDTH * 0.09)
AUTOSAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aquarium_autosave.json")
_glass = {"surfs": None, "cw": 1, "bar": None}


def real_clock_fraction():
    t = time.localtime()
    return (t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec) / 86400.0


# ---- live weather: with the real-time clock on, the tank copies the weather outside the user's window
# The place comes from one IP lookup (ipwho.is); the weather from Open-Meteo (no key). Both run on a background thread
# every 15 minutes and fail quietly: with no network the tank just keeps its own weather. W in the hub's Life tab turns it off.
WX = {"ok": False, "code": 0, "temp": 15.0, "cloud": 0.0, "rain": 0.0, "snow": False, "storm": False, "label": "",
      "place": "", "lat": None, "lon": None, "next": 0.0, "busy": False, "err": "", "last_storm": -99999}
WX_NAMES = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
            56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain",
            67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Showers", 81: "Showers",
            82: "Heavy showers", 85: "Snow showers", 86: "Snow showers", 95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"}
WX_RAIN = {51: 0.25, 53: 0.35, 55: 0.45, 56: 0.35, 57: 0.5, 61: 0.45, 63: 0.7, 65: 1.0, 66: 0.5, 67: 0.8, 80: 0.5, 81: 0.75, 82: 1.0,
           71: 0.35, 73: 0.6, 75: 0.9, 77: 0.4, 85: 0.5, 86: 0.9, 95: 1.0, 96: 1.0, 99: 1.0}


def _wx_get(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "PixelAquarium/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def wx_apply(d):
    code = int(d.get("weather_code", 0))
    precip = float(d.get("precipitation") or 0.0)
    rain = max(WX_RAIN.get(code, 0.0), min(1.0, precip / 4.0))
    WX.update(code=code, temp=float(d.get("temperature_2m", 15.0)), cloud=clamp(float(d.get("cloud_cover") or 0.0) / 100.0),
              rain=rain, snow=70 <= code <= 77 or code in (85, 86), storm=code in (95, 96, 99),
              label=WX_NAMES.get(code, "Rain" if rain > 0 else "Clouds"), ok=True, err="")
    if code in (45, 48):
        WX["cloud"] = max(WX["cloud"], 0.85)


def _wx_fetch():
    try:
        if WX["lat"] is None:
            g = _wx_get("https://ipwho.is/")
            WX["lat"], WX["lon"] = float(g["latitude"]), float(g["longitude"])
            WX["place"] = ", ".join(str(x) for x in (g.get("city"), g.get("country_code")) if x)
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={WX['lat']:.2f}&longitude={WX['lon']:.2f}"
               "&current=temperature_2m,precipitation,weather_code,cloud_cover")
        wx_apply(_wx_get(url)["current"])
    except Exception as ex:
        WX["err"] = str(ex)[:60] or "offline"
    finally:
        WX["busy"] = False


def wx_ok():
    return bool(eco.realtime and X.get("wx", True) and WX["ok"])


def wx_dt():
    """The room follows the outdoors a little: a cold day cools the tank, a hot one warms it (the heater can still hold it)."""
    return clamp((WX["temp"] - 18.0) * 0.06, -1.2, 1.2) if wx_ok() else 0.0


def wx_tick(t):
    if not (eco.realtime and X.get("wx", True)):
        return
    now = time.time()
    if now >= WX["next"] and not WX["busy"]:
        WX["busy"] = True
        WX["next"] = now + (900 if WX["ok"] else 120)
        import threading
        threading.Thread(target=_wx_fetch, daemon=True).start()
    if not WX["ok"]:
        return
    if WX["label"] != WX.get("seen"):
        WX["seen"] = WX["label"]
        notify(f"Weather outside{(' in ' + WX['place']) if WX['place'] else ''}: {WX['label']}, {WX['temp']:.0f}C", log=False)
    if WX["storm"] and not eco.event and t - WX["last_storm"] > 3600:
        WX["last_storm"] = t
        eco.start_event("THUNDERSTORM")
    elif WX["rain"] > 0 and eco.event != "THUNDERSTORM" and t % max(3, int(14 - 11 * WX["rain"])) == 0 and not WX["snow"]:
        ripples.append([pygame.Vector2(random.uniform(40, SCREEN_WIDTH - 40), WATER_TOP + 2), 3.0, 36])


def light_override():
    """Lights switch (L), blackouts and storm clouds adjust the night level after the clock has set it."""
    e = eco
    if e.lights == "ON":
        e.night = 0.0
        e.daylight = max(e.daylight, 0.8)
    elif e.lights == "OFF":
        e.night = max(e.night, 0.92)
        e.daylight = min(e.daylight, 0.1)
    if e.dark > 0.01:
        e.night = clamp(max(e.night, e.dark))
    if e.lights not in ("ON", "OFF") and wx_ok():
        e.night = clamp(e.night + (0.24 * WX["cloud"] + (0.08 if WX["rain"] > 0 else 0.0)) * (1.0 - e.night))


# ---- the fish learn where dinner arrives ----
def feed_record(pos):
    m = feed_mem
    x, y = pos[0], clamp(pos[1], WATER_TOP + 50, WATER_TOP + 220)
    if m["conf"] <= 0.02 or abs(x - m["x"]) > 260:
        m["conf"] = m["conf"] * 0.5 if m["conf"] > 0.02 else 0.0
        m["x"], m["y"] = x, y
    else:
        m["x"] += (x - m["x"]) * 0.3
        m["y"] += (y - m["y"]) * 0.3
    m["conf"] = min(1.0, m["conf"] + 0.12)


def feed_learning(f):
    m = feed_mem
    if m["conf"] < 0.2 or pellets or not f.alive or f.hunger < 40:
        return
    if (getattr(f, "hidden", False) or getattr(f, "sleepy", 0) > 0.5 or getattr(f, "fear", 0) > 0.25 or eco.night > 0.5
            or getattr(f, "bottom", False) or getattr(f, "nesting", 0) or getattr(f, "guard_t", 0) > 0):
        return
    if getattr(f, "bravery", 0.5) < 0.4:   # shy fish only come out once the habit is firm and no hunter is near
        if m["conf"] < 0.55 or any(p.hunts_fish and p.pos.distance_squared_to(f.pos) < 420 ** 2 for p in predators):
            return
    to = pygame.Vector2(m["x"], m["y"]) - f.pos
    if to.length_squared() < 50 * 50:
        f.vel *= 0.97
        return
    f.apply_force(unit(to) * 0.012 * m["conf"] * (0.5 + f.hunger / 100.0))


# ---- glass film, filter, air stone ----
class StoneBubble(Bubble):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = random.uniform(1.6, 2.6)
        self.r = random.choice((1, 2, 2, 3))
        self.ph = random.uniform(0, 6.28)

    def update(self):
        self.pos.y -= self.speed
        self.ph += 0.2
        self.pos.x += math.sin(self.ph) * 0.35 + eco.current * 5

    def draw(self, surface):
        p = (int(self.pos.x), int(self.pos.y))
        pygame.draw.circle(surface, (190, 225, 250), p, self.r, 1)
        if self.r >= 2:
            surface.set_at((p[0] - 1, p[1] - 1), (255, 255, 255))


def build_glass():
    film = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    film.fill((70, 120, 50, 40))
    rng = random.Random(404)
    for _ in range(3200):
        x = rng.randint(0, SCREEN_WIDTH - 1)
        y = SCREEN_HEIGHT - 1 - int(abs(rng.gauss(0, SCREEN_HEIGHT * 0.34)))
        if rng.random() < 0.3:
            y = rng.randint(WATER_TOP, SCREEN_HEIGHT - 1)
        y = max(WATER_TOP, y)
        col = rng.choice(((70, 120, 40), (86, 130, 48), (60, 100, 36), (104, 134, 60)))
        pygame.draw.circle(film, (*col, rng.randint(50, 130)), (x, y), rng.choice((1, 1, 2, 2, 3, 4)))
    cw = SCREEN_WIDTH // GLASS_COLS + 1
    _glass["cw"] = cw
    _glass["surfs"] = [film.subsurface(pygame.Rect(i * cw, 0, min(cw, SCREEN_WIDTH - i * cw), SCREEN_HEIGHT)).copy()
                       for i in range(GLASS_COLS)]
    bar = pygame.Surface((10, SCREEN_HEIGHT), pygame.SRCALPHA)
    bar.fill((255, 255, 255, 55))
    _glass["bar"] = bar


def draw_glass(surface):
    e = eco
    if e.wipe < 0 and max(e.glass) < 0.05:
        return
    if _glass["surfs"] is None:
        build_glass()
    cw = _glass["cw"]
    for i, v in enumerate(e.glass):
        if v > 0.05:
            sf = _glass["surfs"][i]
            sf.set_alpha(int(255 * min(1.0, v)))
            surface.blit(sf, (i * cw, 0))
    if e.wipe >= 0:
        surface.blit(_glass["bar"], (int(e.wipe) - 5, 0))


def start_wipe():
    e = eco
    if e.wipe >= 0:
        return
    avg = sum(e.glass) / GLASS_COLS
    e.wipe = 0.0
    play_sfx("click", 0.5)
    if avg > 0.06:
        stats["wipes"] += 1
        notify("You wipe the glass clean", log=False)
    else:
        notify("The glass is already clean", log=False)


def rinse_filter():
    e = eco
    if e.filter > 0.85:
        notify("The filter sponge is still clean", log=False)
        return
    e.filter = 1.0
    e.water = min(100.0, e.water + 4.0)
    stats["rinses"] += 1
    play_sfx("bubble", 0.4)
    notify("Filter sponge rinsed: the flow is back")


def draw_air_stone(surface):
    y = int(ground_y(AIR_X)) - 4
    pygame.draw.line(surface, (30, 34, 40), (AIR_X - 14, y), (AIR_X - 70, y - 2), 2)
    pygame.draw.ellipse(surface, (96, 100, 110), (AIR_X - 12, y - 6, 24, 12))
    pygame.draw.ellipse(surface, (140, 146, 156), (AIR_X - 10, y - 6, 20, 7))


def draw_shells(surface):
    for sh in moult_shells[:]:
        sh[3] -= 1
        if sh[3] <= 0:
            moult_shells.remove(sh)
            continue
        gy = ground_y(sh[0]) - 8
        if sh[1] < gy:
            sh[1] += 0.25
        z = max(0.1, sh[4])
        w, h = max(6, int(46 * z)), max(4, int(24 * z))
        a = int(150 * min(1.0, sh[3] / 300.0))
        sp = pygame.Surface((w + 8, h + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(sp, (232, 226, 214, a), (4, 1, w - 4, h))
        pygame.draw.polygon(sp, (232, 226, 214, a), [(5, h // 2), (0, 1), (0, h)])
        if not sh[2]:
            sp = pygame.transform.flip(sp, True, False)
        surface.blit(sp, (int(sh[0]) - w // 2, int(sh[1]) - h // 2))


# ---- a bag of new fish, acclimating at the surface ----
class ArrivalBag:
    def __init__(self):
        self.pos = pygame.Vector2(random.uniform(SCREEN_WIDTH * 0.25, SCREEN_WIDTH * 0.75), WATER_TOP + 16)
        self.t = 0
        self.done = False
        self.newcomers = [spawn_random_fish() for _ in range(random.randint(3, 4))]

    def update(self):
        self.t += 1
        self.pos.x = clamp(self.pos.x + math.sin(self.t * 0.01) * 0.25 + eco.current * 3, 120, SCREEN_WIDTH - 120)
        self.pos.y = WATER_TOP + 14 + math.sin(self.t * 0.03) * 2
        if self.t % 25 == 0 and fishes:
            for f in random.sample(fishes, min(5, len(fishes))):   # curious tank mates come to look
                if getattr(f, "curious", 0) > 0.55 and getattr(f, "fear", 0) < 0.2 and f.pos.distance_squared_to(self.pos) < 520 ** 2:
                    f.apply_force(unit(pygame.Vector2(self.pos.x, self.pos.y + 90) - f.pos) * 0.8)
        if self.t >= 1000:
            self.release()

    def release(self):
        if self.done:
            return
        self.done = True
        placed = 0
        for nf in self.newcomers:
            if not has_room(type(nf)):
                continue
            nf.pos = pygame.Vector2(self.pos.x + random.uniform(-30, 30), self.pos.y + 30)
            nf.vel = pygame.Vector2(random.uniform(-1, 1), 0.8)
            if hasattr(nf, "fear"):
                nf.fear = 0.5
            fishes.append(nf)
            placed += 1
        if placed:
            stats["arrivals"] += 1
            burst(self.pos + (0, 24), (200, 235, 255), 14, 1.4, 50, 2, -0.01)
            play_sfx("bubble", 0.5)
            notify(f"{placed} new fish are released into the tank")
        eco.bag = None

    def draw(self, surface):
        x, y = int(self.pos.x), int(self.pos.y)
        w, h = 120, 54
        bag = pygame.Surface((w + 20, h + 40), pygame.SRCALPHA)
        pygame.draw.ellipse(bag, (170, 215, 240, 70), (10, 18, w, h))
        pygame.draw.ellipse(bag, (230, 245, 255, 130), (10, 18, w, h), 2)
        pygame.draw.polygon(bag, (210, 235, 250, 170), [(w // 2 - 4, 16), (w // 2 + 24, 16), (w // 2 + 10, 2)])
        n = max(1, len(self.newcomers))
        for i, nf in enumerate(self.newcomers):
            cx = 26 + i * (w - 40) // n
            col = tuple(getattr(nf, "base_color", (240, 170, 90))[:3])
            pygame.draw.ellipse(bag, (*col, 210), (cx, 34 + (i % 2) * 8 + int(math.sin(self.t * 0.05 + i) * 3), 22, 9))
        surface.blit(bag, (x - (w + 20) // 2, y - 10))


# ---- cinema camera: drifts to whatever is interesting ----
def cinema_update():
    e = eco
    e.cin_t -= 1
    f = e.selected
    if f is not None and f.alive and f in fishes and e.cin_t > 0:
        return
    hunters = [p for p in predators if p.hunts_fish and p.state in ("stalk", "strike")]
    best, bs = None, -1.0
    for g in fishes:
        if not g.alive or not hasattr(g, "family"):
            continue
        sc = random.random()
        if getattr(g, "nesting", 0) or getattr(g, "guard_t", 0) > 0:
            sc += 3
        if getattr(g, "suit", None) is not None:
            sc += 3
        if g.growth < 0.3:
            sc += 1.5
        if getattr(g, "sick", False):
            sc += 1
        for p in hunters:
            if g.pos.distance_squared_to(p.pos) < 260 ** 2:
                sc += 5
        if g is f:
            sc -= 1.5
        if sc > bs:
            best, bs = g, sc
    if best is not None:
        e.selected, e.follow = best, True
        e.cin_t = 300 if bs > 5 else 540


# ---- goals ----
GOALS = [
    ("first_fry", "First fry", "A brood or clutch hatches", lambda: stats["fry"] >= 1),
    ("nursery", "Nursery", "Raise 20 fry", lambda: stats["fry"] >= 20),
    ("boom", "Baby boom", "Have 10 youngsters at once", lambda: sum(1 for f in fishes if f.growth < 1.0) >= 10),
    ("strain", "Own strain", "Breed a third-generation guppy", lambda: any(isinstance(f, GuppyBase) and f.gen >= 3 for f in fishes)),
    ("morph", "New morph", "A bred guppy with a very different colour",
     lambda: any(isinstance(f, GuppyBase) and f.gen >= 2 and abs(f.gene_key[0]) >= 2 for f in fishes)),
    ("dinner", "Dinner bell", "The fish learn your feeding spot", lambda: feed_mem["conf"] >= 0.8),
    ("wipe", "Clear view", "Wipe the glass (C)", lambda: stats["wipes"] >= 1),
    ("rinse", "Fresh sponge", "Rinse the filter (F)", lambda: stats["rinses"] >= 1),
    ("crystal", "Crystal tank", "Clean glass and fresh water on day 3+",
     lambda: eco.day >= 3 and sum(eco.glass) / GLASS_COLS < 0.08 and eco.water >= 85),
    ("storm", "Weathered a storm", "Sit through a thunderstorm", lambda: stats["storms"] >= 1),
    ("blackout", "Lights out", "Survive a power cut", lambda: stats["powercuts"] >= 1),
    ("arrivals", "Welcome aboard", "Release a bag of new fish", lambda: stats["arrivals"] >= 1),
    ("colony", "Shrimp colony", "30 shrimp in the tank", lambda: len(shimps) >= 30),
    ("shrimplets", "Shrimplets", "A shrimp hatches", lambda: stats["shrimplets"] >= 1),
    ("week", "Week one", "Reach day 7", lambda: eco.day >= 7),
    ("photog", "Photographer", "Take a photo (P)", lambda: stats["photos"] >= 1),
    ("showcase", "Showcase", "Betta, discus and killifish together",
     lambda: all(any(type(f) is c for f in fishes) for c in (Betta, Discus, Killifish))),
    ("nest", "Bubble nest", "See a bubble nest being built", lambda: bool(foam_nests)),
    ("away", "Welcome back", "Return to a tank that kept going", lambda: stats["away"] >= 1),
    ("cured", "Fish doctor", "Cure a sick fish with medicine (U)", lambda: stats["cured"] >= 1),
    ("quarantine", "Quarantine", "Net off a sick fish (I)", lambda: stats["quarantines"] >= 1),
    ("raised", "Raised in the nursery", "Grow fry in the nursery net (S)", lambda: stats["raised"] >= 1),
    ("trim", "Green thumb", "Trim an overgrown plant (D, TRIM)", lambda: stats["trims"] >= 1),
    ("worms", "Feeding frenzy", "Feed bloodworm (4)", lambda: stats["blood"] >= 1),
    ("wafer", "Bottom of the menu", "Drop an algae wafer (5)", lambda: stats["wafers"] >= 1),
    ("rainbow", "Rainbow shrimp", "Red, blue and yellow shrimp together", lambda: {s.gene for s in shimps} >= {0, 1, 2}),
    ("book", "Strain collector", "Record 5 guppy strains (Tab)", lambda: len(strains) >= 5),
    ("gen5", "Fifth generation", "Breed a fifth-generation guppy", lambda: any(v[0] >= 5 for v in strains.values())),
    ("winter", "Full year", "Reach winter", lambda: eco.season == 3 and eco.day >= 60),
    ("lapse", "Time traveller", "Use the timelapse (hold backslash)", lambda: stats["lapses"] >= 1),
]
_goal_fonts = {}


def check_goals():
    for gid, title, desc, fn in GOALS:
        if gid in GOALS_DONE:
            continue
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        if ok:
            GOALS_DONE.add(gid)
            notify(f"Goal unlocked: {title}  (+3 points)")
            X["points"] += 3
            play_sfx("chime", 0.5)
            save_prefs()


def draw_goals(surface):
    if not _goal_fonts:
        _goal_fonts["t"] = pygame.font.SysFont("Arial", 26, bold=True)
        _goal_fonts["h"] = pygame.font.SysFont("Arial", 17, bold=True)
        _goal_fonts["d"] = pygame.font.SysFont("Arial", 14)
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    surface.blit(dim, (0, 0))
    cols = 3 if len(GOALS) > 32 else 2
    rows = (len(GOALS) + cols - 1) // cols
    w, h = 26 + cols * 390, 110 + rows * 46
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 20, 40, 238), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
    panel.blit(_goal_fonts["t"].render(f"Goals   {len(GOALS_DONE)} / {len(GOALS)}", True, (235, 245, 255)), (26, 20))
    for i, (gid, title, desc, _fn) in enumerate(GOALS):
        x, y = 26 + (i // rows) * 390, 76 + (i % rows) * 46
        done = gid in GOALS_DONE
        pygame.draw.rect(panel, (90, 210, 140) if done else (70, 90, 120), (x, y + 2, 20, 20), 0 if done else 2, border_radius=4)
        if done:
            pygame.draw.lines(panel, (8, 30, 20), False, [(x + 4, y + 12), (x + 9, y + 17), (x + 16, y + 6)], 3)
        panel.blit(_goal_fonts["h"].render(title, True, (255, 232, 140) if done else (200, 215, 232)), (x + 30, y))
        panel.blit(_goal_fonts["d"].render(desc, True, (150, 175, 200)), (x + 30, y + 21))
    panel.blit(_goal_fonts["d"].render("Press G or Esc to close", True, (150, 175, 200)), (26, h - 28))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))


def draw_care_status(surface):
    if not eco.show_hud or screensaver:
        return
    avg = sum(eco.glass) / GLASS_COLS
    parts = [f"GLASS {int(avg * 100)}%", f"FILTER {int(eco.filter * 100)}%", f"LIGHTS {eco.lights}",
             "AIR " + ("ON" if eco.air_on and not eco.power else "OFF"),
             f"{eco.temp:.1f}C HEAT {eco.heater if not eco.power else 'OFF'}", SEASONS[eco.season]]
    if eco.timelapse:
        parts.append("TIMELAPSE")
    if eco.realtime:
        parts.append("CLOCK " + time.strftime("%H:%M"))
        if wx_ok():
            parts.append(f"{WX['label'].upper()} {WX['temp']:.0f}C")
    if eco.cinema:
        parts.append("CINEMA")
    if eco.power:
        parts.append("POWER CUT")
    surface.blit(hud_font().render("   ".join(parts), True, HUD_DIM), (14, SCREEN_HEIGHT - 26))


# ---- hum + per-frame care ----
def start_hum():
    snd = SFX.get("hum")
    if snd is not None:
        snd.set_volume(0.0)
        snd.play(-1)


def care_update():
    e = eco
    t = e.t
    e.dark += (e.dark_goal - e.dark) * 0.03
    e.flash = max(0.0, e.flash - 0.07)
    feed_mem["conf"] = max(0.0, feed_mem["conf"] - 0.00004)
    if feed_mem["conf"] >= 0.6 and not feed_mem["told"]:
        feed_mem["told"] = True
        notify("The fish are learning where dinner arrives", log=False)
    elif feed_mem["conf"] < 0.2:
        feed_mem["told"] = False
    # glass film grows with light and dirty water, and is grazed away by the clean-up crew
    lit = (1.0 - 0.6 * e.night) * (1.0 - 0.25 * e.overgrown)
    boost = (1.0 + (100.0 - e.water) / 90.0) * (1.5 if e.lights == "ON" else 1.0) * lit
    half = GLASS_COLS / 2.0
    for i in range(GLASS_COLS):
        e.glass[i] = min(1.0, e.glass[i] + 0.000028 * GLASS_RATE[i] * (1.0 + 0.5 * abs(i - half) / half) * boost)
    if t % 4 == 0:
        for f in fishes:
            if isinstance(f, (Otocinclus, Pleco)):
                i = min(GLASS_COLS - 1, max(0, int(f.pos.x / SCREEN_WIDTH * GLASS_COLS)))
                e.glass[i] = max(0.0, e.glass[i] - 0.005)
        for c in crawlers:
            i = min(GLASS_COLS - 1, max(0, int(c.pos.x / SCREEN_WIDTH * GLASS_COLS))) if hasattr(c, "pos") else 0
            e.glass[i] = max(0.0, e.glass[i] - 0.003)
    if e.wipe >= 0:
        e.wipe += SCREEN_WIDTH / 36.0
        for i in range(min(GLASS_COLS, int(e.wipe / SCREEN_WIDTH * GLASS_COLS) + 1)):
            e.glass[i] = 0.0
        if e.wipe >= SCREEN_WIDTH:
            e.wipe = -1.0
    avg = sum(e.glass) / GLASS_COLS
    if avg > 0.55 and "glass" not in e.warned:
        e.warned.add("glass")
        notify("Algae is filming the glass: press C to wipe it", log=False)
    elif avg < 0.3:
        e.warned.discard("glass")
    if not e.power:
        e.filter = max(0.0, e.filter - 0.000008)
    if e.filter < 0.3 and "filter" not in e.warned:
        e.warned.add("filter")
        notify("The filter flow is weak: press F to rinse the sponge", log=False)
    elif e.filter > 0.5:
        e.warned.discard("filter")
    # air stone bubble curtain
    if e.air_on and not e.power and t % 3 == 0 and len(bubbles) < 240:
        bubbles.append(StoneBubble(AIR_X + random.uniform(-5, 5), ground_y(AIR_X) - 8))
        if random.random() < 0.18:
            play_sfx("bubble", 0.06)
    wx_tick(t)
    # thunderstorm
    if e.event == "THUNDERSTORM":
        if t % 4 == 0:
            ripples.append([pygame.Vector2(random.uniform(40, SCREEN_WIDTH - 40), WATER_TOP + 2), 3.0, 36])
        e.storm_next -= 1
        if e.storm_next <= 0:
            e.flash = 1.0
            if random.random() < 0.3:
                e.dark = 0.85
            e.thunder_due = t + random.randint(18, 70)
            e.storm_next = random.randint(160, 420)
        if e.thunder_due >= 0 and t >= e.thunder_due:
            e.thunder_due = -1
            play_sfx("thunder", 0.8)
            e.scare(0.12)
            for f in fishes:
                if hasattr(f, "fear"):
                    f.fear = max(f.fear, 0.28 * (1.25 - getattr(f, "bravery", 0.5)))
    if e.bag is not None:
        e.bag.update()
    if e.cinema:
        cinema_update()
    if t % 30 == 0:
        snd = SFX.get("hum")
        if snd is not None:
            snd.set_volume(0.0 if (is_muted or e.power) else 0.045 * VOL["master"] * VOL["fx"])
    if t % 60 == 0:
        apply_music_volume()
        check_goals()
    if t % 18000 == 0 and t and current_state == STATE_AQUARIUM and AWAY["on"]:
        save_game(AUTOSAVE_PATH, quiet=True)
    care_update2()


stats.update({"cured": 0, "quarantines": 0, "raised": 0, "trims": 0, "blood": 0, "wafers": 0, "lapses": 0})
SEASONS = ("SPRING", "SUMMER", "AUTUMN", "WINTER")
SEASON_TEMP = (0.0, 2.0, 0.0, -3.0)
HEAT = {"OFF": 0.0, "LOW": 2.5, "HIGH": 5.0}
TEMP_PREF = {"Discus": (28.0, 31.0), "Betta": (26.0, 30.0), "Killifish": (20.0, 26.0)}   # others: 22-28
TALL_PLANTS = ("Rotala", "Ludwigia", "Vallisneria", "Hairgrass", "TigerLotus", "Cabomba", "Hygrophila")
NURSERY_W, NURSERY_H = 220, 140
QNET_W, QNET_H = 150, 106
_misc = {"moon": None, "nursery": None, "qnet": None}
_rain = []


def season_index():
    if eco.realtime:
        return {12: 3, 1: 3, 2: 3, 3: 0, 4: 0, 5: 0, 6: 1, 7: 1, 8: 1}.get(time.localtime().tm_mon, 2)
    return (eco.day // 20) % 4


# ---- sickness: medicine and quarantine ----
def dose_medicine():
    e = eco
    if e.med_cd > 0:
        notify("The last dose is still working", log=False)
        return
    sick = [f for f in fishes if getattr(f, "sick", False)]
    if not sick:
        notify("Nothing to treat: no fish is sick", log=False)
        return
    for f in sick:
        f.sick, f.sick_t = False, 0
    stats["cured"] += len(sick)
    e.med_cd = 1800
    e.water = max(0.0, e.water - 2.0)
    lost = 0
    if len(shimps) > 6:
        keep = [s for s in shimps if random.random() > 0.15]
        lost = len(shimps) - len(keep)
        shimps[:] = keep
    play_sfx("chime", 0.5)
    notify(f"Medicine cured {len(sick)} fish" + (f", but {lost} shrimp did not like it" if lost else ""))


def _pour(color, n=40):
    for _ in range(n):
        burst((random.uniform(80, SCREEN_WIDTH - 80), WATER_TOP + 6), color, 1, 1.0, 120, 3, 0.02)


def pour_methylene_blue():
    e = eco
    if e.blue > 600:
        notify("The water is still blue from the last dose", log=False)
        return
    e.blue = 2400
    _pour((60, 120, 255))
    play_sfx("bubble", 0.5)
    sick = sum(1 for f in fishes if getattr(f, "sick", False))
    lost = 0
    if len(shimps) > 6:
        keep = [s for s in shimps if random.random() > 0.08]
        lost = len(shimps) - len(keep)
        shimps[:] = keep
    notify("Methylene blue added: sick fish recover much faster" + (f" ({lost} shrimp lost)" if lost else ""))


def pour_vitamins():
    e = eco
    if e.vit_cd > 0:
        notify("The fish have had their vitamins for now", log=False)
        return
    e.vit_cd = 3600
    _pour((255, 200, 90))
    play_sfx("chime", 0.4)
    for f in fishes:
        if hasattr(f, "family"):
            f.stress = max(0.0, f.stress - 30.0)
            f.hunger = max(0.0, f.hunger - 10.0)
            f.immune = max(getattr(f, "immune", 0), 5400)
            f.health = min(100.0, f.health + 20.0)
    notify("Vitamins added: calmer, fed and more resistant fish")


def toggle_quarantine():
    f = eco.selected
    if f is None or f not in fishes:
        notify("Select a fish first (Shift-click), then press I", log=False)
        return
    if getattr(f, "qpos", None) is not None:
        f.qpos = None
        notify(f"{f.name} is released from quarantine", log=False)
        return
    f.qpos = pygame.Vector2(clamp(f.pos.x, QNET_W, SCREEN_WIDTH - QNET_W), clamp(f.pos.y, WATER_TOP + QNET_H, SCREEN_HEIGHT - SAND_HEIGHT - QNET_H // 2))
    stats["quarantines"] += 1
    notify(f"{f.name} is in quarantine" + (": it will recover faster" if f.sick else ""), log=False)


def toggle_nursery():
    e = eco
    if e.nursery is None:
        e.nursery = (int(SCREEN_WIDTH * 0.82), WATER_TOP + 280)
        notify("Nursery net placed: new guppy fry will be born inside it", log=False)
    else:
        e.nursery = None
        for f in fishes:
            f.box = False
        notify("Nursery net removed", log=False)


def _mesh(w, h, col, line):
    sf = pygame.Surface((w, h), pygame.SRCALPHA)
    sf.fill((*col, 26))
    for x in range(0, w, 14):
        pygame.draw.line(sf, (*line, 70), (x, 0), (x, h))
    for y in range(0, h, 14):
        pygame.draw.line(sf, (*line, 70), (0, y), (w, y))
    pygame.draw.rect(sf, (*line, 190), (0, 0, w, h), 2)
    return sf


def draw_nets(surface):
    e = eco
    if e.nursery is not None:
        if _misc["nursery"] is None:
            _misc["nursery"] = _mesh(NURSERY_W, NURSERY_H, (120, 230, 170), (190, 250, 210))
        surface.blit(_misc["nursery"], (e.nursery[0] - NURSERY_W // 2, e.nursery[1] - NURSERY_H // 2))
    for f in fishes:
        q = getattr(f, "qpos", None)
        if q is not None:
            if _misc["qnet"] is None:
                _misc["qnet"] = _mesh(QNET_W, QNET_H, (240, 200, 120), (255, 230, 170))
            surface.blit(_misc["qnet"], (int(q.x) - QNET_W // 2, int(q.y) - QNET_H // 2))


# ---- plants: growth and pruning ----
def scale_plant(p, k):
    for attr in ("stems", "blades", "stalks", "vines"):
        lst = getattr(p, attr, None)
        if lst:
            setattr(p, attr, [(t[0], t[1], t[2] * k) + tuple(t[3:]) for t in lst])
    lv = getattr(p, "leaves", None)
    if lv:
        if p.species in ("Sword", "JavaFern"):   # (tilt, length, width, phase)
            p.leaves = [(t[0], t[1] * k, t[2] * k ** 0.5, t[3]) for t in lv]
        else:                                    # (angle, stalk, length, phase)
            p.leaves = [(t[0], t[1] * k, t[2] * k, t[3]) for t in lv]
    if hasattr(p, "radius"):
        p.radius *= k
    p.height *= k
    p.psize = p.psize * k


def trim_plants(x=None):
    """Prune overgrown plants near x, or every overgrown plant in the tank when x is None."""
    done = 0
    for p in plants[:]:
        if p.species not in TALL_PLANTS or (x is not None and abs(p.pos_x - x) > 75):
            continue
        base = getattr(p, "base_h", p.height)
        if p.height <= base * 1.12:
            continue
        was = p.height
        scale_plant(p, base * 0.9 / p.height)
        burst((p.pos_x, SCREEN_HEIGHT - SAND_HEIGHT - was * 0.8), (90, 170, 70), 7, 1.0, 70, 2, 0.01)
        done += 1
        if was > base * 1.4 and random.random() < 0.5 and len(plants) < 150:   # a clipping takes root
            kid = Plant(p.pos_x + random.choice((-34, 34)), p.species)
            kid.base_h = kid.height
            plants.append(kid)
            plants.sort(key=PLANT_ORDER)
    if done:
        stats["trims"] += done
        play_sfx("click", 0.5)
        notify(f"Pruned {done} plant" + ("s" if done > 1 else ""), log=False)
    else:
        notify("Nothing overgrown here to prune", log=False)


# ---- strain book ----
def record_strain(kid, born=False):
    key = f"{type(kid).__name__}|{kid.gene_key[0]}|{kid.gene_key[1]}"
    new = key not in strains
    rec = strains.setdefault(key, [kid.gen, 0])
    rec[0] = max(rec[0], kid.gen)
    if born:
        rec[1] += 1
        if new:
            notify(f"New {nice_name(kid)} strain recorded (Tab)", log=False)
            save_prefs()


def draw_strains(surface):
    if not _goal_fonts:
        _goal_fonts["t"] = pygame.font.SysFont("Arial", 26, bold=True)
        _goal_fonts["h"] = pygame.font.SysFont("Arial", 17, bold=True)
        _goal_fonts["d"] = pygame.font.SysFont("Arial", 14)
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    surface.blit(dim, (0, 0))
    items = sorted(strains.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))[:30]
    rows = max(1, (len(items) + 2) // 3)
    w, h = 1020, 120 + rows * 54
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 20, 40, 238), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
    panel.blit(_goal_fonts["t"].render(f"Strain book   {len(strains)} recorded", True, (235, 245, 255)), (26, 20))
    if not items:
        panel.blit(_goal_fonts["d"].render("Breed fish to record colour (and guppy tail) strains here.", True, (150, 175, 200)), (26, 80))
    for i, (key, (best, born)) in enumerate(items):
        cname, gh, gt = key.split("|")
        cls = FISH_CLASSES.get(cname)
        if cls is None:
            continue
        gh, gt = int(gh), int(gt)
        x, y = 26 + (i % 3) * 330, 74 + (i // 3) * 54
        body = hue_shift(getattr(cls, "male_color", (120, 170, 210)), gh)
        tail = hue_shift(getattr(cls, "tail_color", (90, 140, 200)), gh)
        tl = 10 + 4 * gt
        pygame.draw.polygon(panel, tail, [(x + 30, y + 22), (x + 30 - tl - 8, y + 4), (x + 30 - tl - 8, y + 40)])
        pygame.draw.ellipse(panel, body, (x + 26, y + 12, 44, 20))
        pygame.draw.circle(panel, (20, 20, 20), (x + 62, y + 20), 2)
        panel.blit(_goal_fonts["h"].render(nice_name(cls), True, (255, 232, 140) if best >= 4 else (200, 215, 232)), (x + 84, y + 4))
        panel.blit(_goal_fonts["d"].render(f"best gen {best}   bred {born}" + ("   * line" if best >= 4 else ""), True, (150, 175, 200)), (x + 84, y + 26))
    panel.blit(_goal_fonts["d"].render("Press Tab or Esc to close", True, (150, 175, 200)), (26, h - 28))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))


# ---- moonlight and rain on the glass ----
def draw_moon(surface):
    e = eco
    if e.night < 0.3 or e.power or e.lights == "ON":
        return
    if _misc["moon"] is None:
        m = pygame.Surface((420, 420), pygame.SRCALPHA)
        for r in range(210, 0, -6):
            pygame.draw.circle(m, (180, 205, 255, int(46 * (1 - r / 210.0) ** 1.6) + 1), (210, 210), r)
        _misc["moon"] = m
    m = _misc["moon"]
    m.set_alpha(int(255 * clamp((e.night - 0.3) / 0.5)))
    u = ((e.clock - 0.75) % 1.0) / 0.5
    x = int(SCREEN_WIDTH * (0.1 + 0.8 * clamp(u)))
    surface.blit(m, (x - 210, WATER_TOP - 150))


def draw_rain(surface):
    storm = eco.event == "THUNDERSTORM"
    wet = wx_ok() and WX["rain"] > 0
    snow = wet and WX["snow"] and not storm
    cap = 90 if storm else (int(16 + 74 * WX["rain"]) if wet else 0)
    if len(_rain) < cap and (storm or random.random() < 0.3 + 0.7 * WX["rain"]):
        for _ in range(2 if storm else 1):
            _rain.append([random.uniform(0, SCREEN_WIDTH), random.uniform(WATER_TOP, SCREEN_HEIGHT * 0.5), random.uniform(0.3, 1.2), random.randint(0, 60)])
    for d in _rain[:]:
        if d[3] > 0:
            d[3] -= 1
        elif snow:
            d[1] += 0.45 + d[2] * 0.3
            d[0] += math.sin(d[1] * 0.04 + d[2] * 9) * 0.5
        else:
            d[1] += d[2]
            d[2] *= 1.01
            if random.random() < 0.01:
                d[3] = random.randint(10, 50)
        x, y = int(d[0]), int(d[1])
        if snow:
            pygame.draw.circle(surface, (238, 244, 252), (x, y), 2)
        else:
            pygame.draw.line(surface, (200, 225, 245), (x, int(y - min(14, d[2] * 10))), (x, y), 1)
            pygame.draw.circle(surface, (225, 240, 252), (x, y), 2)
        if y > SCREEN_HEIGHT - 40 or (not (storm or wet) and random.random() < 0.01):
            _rain.remove(d)


# ---- slower care: temperature, seasons, nursery, quarantine, fry predation, plants, cloudy water ----
def care_update2():
    e = eco
    t = e.t
    ready = [f for f in fishes if hasattr(f, "family")]   # newcomers get their traits on their first update
    si = season_index()
    if si != e.season:
        e.season = si
        notify(f"Season: {SEASONS[si].title()}")
    target = 22.5 + 2.5 * e.daylight + SEASON_TEMP[si] + (0.0 if e.power else HEAT[e.heater] + EQ["drift"]) + EV["dt"] + wx_dt()
    e.temp += (target - e.temp) * 0.0008
    e.med_cd = max(0, e.med_cd - 1)
    e.vit_cd = max(0, e.vit_cd - 1)
    e.blue = max(0, e.blue - 1)
    if not e.realtime and e.cycle_on and pygame.key.get_pressed()[pygame.K_BACKSLASH]:
        e.clock += 0.004
        if e.clock >= 1.0:
            e.clock -= 1.0
            e.day += 1
        e.timelapse = 10
        stats["lapses"] += 1 if stats["lapses"] == 0 else 0
    else:
        e.timelapse = max(0, e.timelapse - 1)
    q_half = (QNET_W // 2 - 8, QNET_H // 2 - 8)
    for f in ready:
        if getattr(f, "immune", 0) > 0:
            f.immune -= 1
        q = getattr(f, "qpos", None)
        if q is not None:
            f.pos.x = clamp(f.pos.x, q.x - q_half[0], q.x + q_half[0])
            f.pos.y = clamp(f.pos.y, q.y - q_half[1], q.y + q_half[1])
            f.vel *= 0.94
            if f.sick and t % 2 == 0:
                f.sick_t -= 1
        if getattr(f, "box", False):
            if f.growth >= 0.5 or e.nursery is None:
                f.box = False
                if f.growth >= 0.5:
                    stats["raised"] += 1
                    notify(f"{f.name} is big enough to leave the nursery", log=False)
            else:
                nx, ny = e.nursery
                f.pos.x = clamp(f.pos.x, nx - NURSERY_W // 2 + 8, nx + NURSERY_W // 2 - 8)
                f.pos.y = clamp(f.pos.y, ny - NURSERY_H // 2 + 8, ny + NURSERY_H // 2 - 8)
                f.vel *= 0.96
                if t % 60 == 0:
                    f.hunger = max(0.0, f.hunger - 8)   # the keeper feeds them
    if t % 30 == 0:
        off_n = {"cold": 0, "hot": 0}
        for f in ready:
            lo, hi = TEMP_PREF.get(type(f).__name__, (22.0, 28.0))
            off = max(lo - e.temp, e.temp - hi, 0.0)
            if off > 0.3:
                f.stress = min(100.0, f.stress + 1.5 * off)
                if off > 1.5:
                    off_n["cold" if e.temp < lo else "hot"] += 1
        for k in ("cold", "hot"):
            if off_n[k] >= 4 and k not in e.warned:
                e.warned.add(k)
                notify(f"The water is too {k} for several fish: press Y to change the heater", log=False)
            elif off_n[k] == 0:
                e.warned.discard(k)
        resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
        e.cloud += (clamp((resting - 8) / 20.0) - e.cloud) * 0.15
        if e.cloud > 0.5 and "cloud" not in e.warned:
            e.warned.add("cloud")
            notify("Overfeeding: the water is going cloudy", log=False)
        elif e.cloud < 0.2:
            e.warned.discard("cloud")
    if t % 20 == 0:   # fry are prey while exposed; plants give cover
        for f in ready:
            if f.growth >= 0.35 or getattr(f, "box", False) or not f.alive:
                continue
            covered = any(abs(p.pos_x - f.pos.x) < 36 and f.pos.y > SCREEN_HEIGHT - SAND_HEIGHT - p.height
                          for b in (int(f.pos.x // 48) - 1, int(f.pos.x // 48), int(f.pos.x // 48) + 1) for p in PLANT_BUCKETS.get(b, ()))
            chance = 0.03 if covered else 0.15
            for o in ready:
                if (o is not f and o.growth >= 1.0 and o.hunger > 50 and not getattr(o, "bottom", False)
                        and not isinstance(o, Otocinclus) and o.pos.distance_squared_to(f.pos) < 28 ** 2
                        and random.random() < chance):
                    f.alive = False
                    o.hunger = max(0.0, o.hunger - 25)
                    o.mouth_open_timer = 10
                    notify(f"{o.name} ate a fry", log=False)
                    break
    if t % 300 == 0:   # plants grow when the water is good; overgrown ones shade the tank
        grown = tall = 0
        for p in plants:
            if p.species in TALL_PLANTS:
                if not hasattr(p, "base_h"):
                    p.base_h = p.height
                if e.water > 40 and p.height < p.base_h * 1.8:
                    scale_plant(p, 1.03)
                tall += 1
                grown += p.height > p.base_h * 1.4
        e.overgrown = grown / max(1, tall)
        if e.overgrown > 0.5 and "plants" not in e.warned:
            e.warned.add("plants")
            notify("The plants are overgrown: choose TRIM (D) and click to prune", log=False)
        elif e.overgrown < 0.25:
            e.warned.discard("plants")
    if t % 60 == 0 and e.season == 0:   # spring: everyone is readier to breed
        for f in ready:
            if getattr(f, "breed_cd", 0) > 0:
                f.breed_cd = max(0, f.breed_cd - 60)
    if t % 600 == 0:
        for f in ready:
            if isinstance(f, GuppyBase):
                record_strain(f)


# ======================================================================================================================
# fw21: the long-term tank - personalities, friendships, life stories, more genes, requests, a genetic show,
# water chemistry, algae kinds, fertiliser, disease kinds, an equipment shop, aquascapes, album and timelapse,
# soundscapes and a statistics dashboard.
# ======================================================================================================================
F21 = {}


def f21(kind):
    if "t" not in F21:
        F21["t"] = pygame.font.SysFont("Arial", 26, bold=True)
        F21["h"] = pygame.font.SysFont("Arial", 17, bold=True)
        F21["d"] = pygame.font.SysFont("Arial", 14)
        F21["s"] = pygame.font.SysFont("Arial", 12)
    return F21[kind]


UI21 = {"panel": None, "web": False, "rename": None, "mem": False, "page": 0, "judge": None}
PERSONAS = ("greedy", "shy", "bossy", "explorer", "calm")
PERSONA_TXT = {"greedy": "first to every meal", "shy": "hides, stays low", "bossy": "shoves other fish about",
               "explorer": "roams the whole tank", "calm": "hard to rattle"}
DISEASES = {"ich": "white spot (ich)", "finrot": "fin rot", "swim": "swim bladder trouble"}
FIN_NAMES = ("round", "delta", "long")
CHEM = {"nh3": 0.0, "no2": 0.0, "no3": 6.0, "ph": 7.1, "b1": 0.04 if NEWTANK["on"] else 1.0,
        "b2": 0.04 if NEWTANK["on"] else 1.0, "done": not NEWTANK["on"], "won": False, "age": 0, "ok": 0,
        "kh": 6.0, "gh": 8.0}
HAIR = [0.0] * GLASS_COLS
DIA = [0.0]
FERT = {"t": 0}
REQ = {"cur": None, "next": 2}
SHOWR = {"rows": [], "day": 0}
DASH = {k: deque(maxlen=240) for k in ("pop", "water", "births", "deaths", "no3", "temp", "ph", "gh", "kh", "points", "cash")}
WEEK = {"day": 1, "births": 0, "deaths": 0, "reqs": 0, "water": []}
REC = {"on": False, "frames": [], "n": 0}
ALB_PATH = os.path.join("screenshots", "album.json")
ALB_THUMBS = {}
SCAPES_PATH = "aquarium_scapes.json"
SND21 = {"ready": False, "chan": [], "snd": [], "cur": [0.0, 0.0, 0.0]}

SHOP = [("filter", "Canister filter", 30, "The filter clogs far slower and cleans harder"),
        ("magnet", "Glass magnet", 25, "Algae film on the glass grows about half as fast"),
        ("thermo", "Thermostat", 20, "Holds the water close to 25C whatever the room does"),
        ("co2", "CO2 diffuser", 35, "Plants grow faster, and fertiliser stops feeding algae"),
        ("uv", "UV steriliser", 40, "Disease spreads far less and sick fish recover sooner"),
        ("oto", "Otocinclus pair", 15, "Two algae eaters join the tank (repeatable)"),
        ("hospital", "Hospital tank", 25, "Fish in quarantine (I) recover twice as fast")]

SCAPE_BUILTIN = [
    ("Jungle", 11, [("CABOMBA", .10), ("LUDWIGIA", .22), ("SWORD", .34), ("HYGRO", .50), ("ROTALA", .62), ("CRYPT", .74), ("CABOMBA", .88), ("DRIFTWOOD", .45)]),
    ("Zen rocks", 23, [("ROCK", .20), ("ROCK", .34), ("DRIFTWOOD", .62), ("ROCK", .78), ("MOSS", .27), ("MOSS", .70), ("DWARF", .48), ("DWARF", .54)]),
    ("Meadow", 37, [("DWARF", .12), ("DWARF", .22), ("DWARF", .32), ("DWARF", .55), ("DWARF", .66), ("CLOVER", .42), ("CLOVER", .80), ("MOSS", .90)]),
    ("Open water", 53, [("SWORD", .08), ("CRYPT", .16), ("ROCK", .30), ("SWORD", .92), ("CRYPT", .84), ("HYGRO", .96)])]


# ---------------------------------------------------------------- panels, fonts
def set_panel(name):
    global show_help, show_goals, show_strains
    UI21["panel"] = None if UI21["panel"] == name else name
    if UI21["panel"]:
        show_help = show_goals = show_strains = False
    UI21["page"] = 0
    if UI21["panel"] == "test":
        CH["kit"] = True


def begin_panel(w, h, title):
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 20, 40, 240), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
    panel.blit(f21("t").render(title, True, (235, 245, 255)), (26, 18))
    return panel


def end_panel(surface, panel, hint="Esc to close"):
    panel.blit(f21("d").render(hint, True, (150, 175, 200)), (26, panel.get_height() - 26))
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    surface.blit(dim, (0, 0))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))


def txt21(panel, text, x, y, kind="d", col=(200, 215, 232)):
    panel.blit(f21(kind).render(text, True, col), (x, y))


# ---------------------------------------------------------------- 1-5: personalities, friends, names, stories
def story(f, text):
    bio = getattr(f, "bio", None)
    if bio is None:
        return
    if len(bio) >= 16:
        del bio[2]
    bio.append((eco.day, text))


def ensure_life(f):
    if hasattr(f, "persona"):
        return
    f.persona = random.choice(PERSONAS)
    if f.persona == "shy":
        f.bravery = min(f.bravery, 0.3)
    elif f.persona == "bossy":
        f.bravery = max(f.bravery, 0.7)
    f.fav = False
    f.friend = f.rival = None
    f.meet = f.mourn = f.rival_t = f.fav_cd = 0
    f.xt, f.xt_t = None, 0
    f.bio = []
    f.born_day = eco.day - int(f.age // DAY_LENGTH)
    f._sk = f.sick
    f._elder = False
    if not hasattr(f, "gh") and not hasattr(f, "hl"):
        f.hl = random.gauss(0.0, 0.35)    # a colour line gene for every species that is not a guppy
    if not hasattr(f, "gen"):
        f.gen = 1
    story(f, f"Hatched on day {eco.day}" if f.age < 900 else "Joined the tank")


def pick_disease(f):
    w = {"ich": 6 if eco.temp < 24.5 else 1,
         "finrot": 6 if (eco.water < 55 or CHEM["nh3"] > 0.4) else 1,
         "swim": 6 if (eco.cloud > 0.35 or f.hunger < 8) else 1}
    return random.choices(list(w), list(w.values()))[0]


def disease_effects(f):
    d = getattr(f, "disease", "ich")
    if "uv" in X["owned"]:
        f.sick_t -= 0.25
    if d == "ich":
        if eco.temp >= 28.0:
            f.sick_t -= 0.7      # heat speeds up the parasite's life cycle: it drops off sooner
        elif eco.temp < 24.0:
            f.sick_t += 0.15
    elif d == "finrot":
        if eco.water >= 80 and CHEM["nh3"] < 0.3:
            f.sick_t -= 0.6      # clean water lets the fins regrow
        elif eco.water < 50:
            f.sick_t += 0.25
    elif d == "swim":
        f.apply_force(pygame.Vector2(0, 0.025))     # it can't hold its depth
        if 25 < f.hunger < 70:
            f.sick_t -= 0.6      # a short fast lets the bladder settle
        elif f.hunger < 12:
            f.sick_t += 0.2


def fish_life(f):
    """Per-fish extras, run right after prey_social: ageing, personality, friends, rivals, grief, disease."""
    if not hasattr(f, "family") or not f.alive:
        return
    ensure_life(f)
    carrier_tick(f)
    t, pos, pers = eco.t, f.pos, f.persona
    key = (t + f.id) % 30
    lf = f.life_frac()
    if lf > 0.8:
        f.max_speed *= 0.82                 # elders slow down (and their colours are already washed out)
        if not f._elder:
            f._elder = True
            story(f, "Grew old and slow")
    if f.mourn > 0:
        f.mourn -= 1
        f.max_speed *= 0.6
        f.stress = min(100.0, f.stress + 0.01)
    if f.sick != f._sk:
        f._sk = f.sick
        story(f, f"Fell ill: {DISEASES.get(getattr(f, 'disease', 'ich'), 'a sickness')}" if f.sick else "Recovered")
    if f.sick:
        disease_effects(f)
    if f.growth < 1.0:
        return
    if pers == "greedy" and f.hunger > 20 and t % 3 == 0 and pellets:
        best, bd = None, 380 * 380
        for p in pellets:
            d2 = pos.distance_squared_to(p.pos)
            if d2 < bd:
                best, bd = p, d2
        if best is not None:
            f.apply_force(unit(best.pos - pos) * 0.12)
        f.hunger = min(100.0, f.hunger + 0.012)
    elif pers == "shy" and hasattr(f, "prefer_depth"):
        f.prefer_depth(lane(0.5), lane(0.92), 0.002)
    elif pers == "calm":
        f.fear *= 0.985
        f.stress = max(0.0, f.stress - 0.02)
    elif pers == "explorer":
        if f.xt is None or f.xt_t <= 0:
            if random.random() < 0.004:
                f.xt = pygame.Vector2(random.uniform(80, SCREEN_WIDTH - 80), random.uniform(WATER_TOP + 60, SCREEN_HEIGHT - SAND_HEIGHT - 40))
                f.xt_t = 420
        else:
            f.xt_t -= 1
            d = f.xt - pos
            if d.length_squared() < 3600:
                f.xt_t = 0
            else:
                f.apply_force(unit(d) * 0.03)
    if pers == "bossy" and key == 0:
        for o in fishes:
            if o is f or not hasattr(o, "persona") or o.growth < 1.0:
                continue
            if pos.distance_squared_to(o.pos) < 6400:
                if o.persona == "bossy" and o is not f.partner and f.rival is None and o.rival is None and random.random() < 0.25:
                    f.rival, o.rival = o, f
                    f.rival_t = o.rival_t = 3600
                    story(f, f"Fell out with {o.name}")
                    story(o, f"Fell out with {f.name}")
                elif o is not f.friend and o is not f.partner and o.persona != "bossy":
                    o.apply_force(unit(o.pos - pos) * 0.5)
                    o.stress = min(100.0, o.stress + 0.8)
                break
    r = f.rival
    if r is not None:
        f.rival_t -= 1
        if f.rival_t <= 0 or not r.alive or r.rival is not f:
            f.rival = None
        else:
            d = r.pos - pos
            if d.length_squared() < 180 * 180:
                f.apply_force(unit(d) * 0.03 * (1 if f.bravery >= r.bravery else -1))
                f.stress = min(100.0, f.stress + 0.01)
    fr = f.friend
    if fr is not None:
        if not fr.alive:
            f.friend = None
        else:
            d = fr.pos - pos
            dist = d.length()
            if dist > 120:
                f.apply_force(d / dist * min(0.02, 0.0001 * (dist - 120)))
    elif key == 1:
        near = None
        for o in fishes:
            if (o is not f and type(o) is type(f) and getattr(o, "friend", 1) is None and o.growth >= 1.0 and o is not f.rival
                    and o is not f.partner and pos.distance_squared_to(o.pos) < 8100):
                near = o
                break
        if near is not None:
            f.meet += 30
            if f.meet >= 1200:
                f.friend, near.friend = near, f
                f.meet = near.meet = 0
                story(f, f"Became friends with {near.name}")
                story(near, f"Became friends with {f.name}")
                notify(f"{f.name} and {near.name} have become friends", log=False)
        else:
            f.meet = max(0, f.meet - 15)


def record_death(f, cause=None):
    if not hasattr(f, "persona"):
        return
    stats["deaths"] = stats.get("deaths", 0) + 1
    if cause is None:
        if f.sick:
            cause = "illness"
        elif f.age >= f.lifespan * 0.95:
            cause = "old age"
        elif f.hunger >= 98:
            cause = "hunger"
        elif eco.water < 40:
            cause = "poor water"
        else:
            cause = "unknown causes"
    if f.growth < 1.0 and not f.fav:
        return    # fry come and go; the memorial is for grown fish
    story(f, f"Died: {cause}")
    X["memorial"].append({"name": f.name, "cls": nice_name(f), "days": max(1, int(f.age // DAY_LENGTH)), "cause": cause,
                          "day": eco.day, "persona": f.persona, "gen": getattr(f, "gen", 1),
                          "note": f.bio[-2][1] if len(f.bio) > 1 else ""})
    del X["memorial"][:-80]
    fr = f.friend
    if fr is not None and fr.alive and fr is not f:
        fr.friend = None
        fr.mourn = 2400
        story(fr, f"Mourned {f.name}")
        add_emote(fr, "..")
        notify(f"{fr.name} is mourning {f.name}", log=False)
    if f.rival is not None:
        f.rival.rival = None
    save_prefs()


def fish_extra(f):
    ensure_life(f)
    d = {"persona": f.persona, "fav": f.fav, "bio": f.bio[-16:], "born": f.born_day, "gen": getattr(f, "gen", 1),
         "friend": f.friend.name if f.friend is not None else None, "disease": getattr(f, "disease", "ich")}
    if hasattr(f, "hl"):
        d["hl"] = f.hl
    if hasattr(f, "lace"):
        d.update(lace=list(f.lace), sheen=f.sheen, fin=f.fin)
    return d


def fish_extra_apply(f, d):
    if not isinstance(d, dict):
        return
    try:
        ensure_life(f)
        if d.get("persona") in PERSONAS:
            f.persona = d["persona"]
        bio = [tuple(b) for b in d.get("bio", []) if isinstance(b, (list, tuple)) and len(b) == 2]
        if bio:
            f.bio = bio
        f.fav = bool(d.get("fav"))
        f.born_day = int(d.get("born", f.born_day))
        if d.get("disease") in DISEASES:
            f.disease = d["disease"]
        f._friend_name = d.get("friend")
        if not hasattr(f, "gh"):
            f.gen = int(d.get("gen", 1))
            if "hl" in d:
                f.hl = clamp(float(d["hl"]), -2.4, 2.4)
        if hasattr(f, "lace"):
            lc = d.get("lace")
            if isinstance(lc, list) and len(lc) == 2:
                f.lace = [bool(lc[0]), bool(lc[1])]
            f.sheen = clamp(float(d.get("sheen", f.sheen)))
            f.fin = int(d.get("fin", f.fin)) % 3
    except (TypeError, ValueError):
        pass


def relink_friends():
    by = {f.name: f for f in fishes if hasattr(f, "persona")}
    for f in fishes:
        nm = getattr(f, "_friend_name", None)
        if nm and nm in by and by[nm] is not f:
            f.friend = by[nm]


# ---------------------------------------------------------------- 6-7: genes
def inherit_extra(kid, m, f):
    """Guppy lace is recessive (two copies needed, so it can skip generations); sheen blends; fin shape is picked from a parent."""
    pm, pf = getattr(m, "lace", [False, False]), getattr(f, "lace", [False, False])
    kid.lace = [random.choice(pm), random.choice(pf)]
    for i in (0, 1):
        if random.random() < 0.015:
            kid.lace[i] = not kid.lace[i]
    kid.sheen = clamp((getattr(m, "sheen", 0.5) + getattr(f, "sheen", 0.5)) / 2 + random.gauss(0, 0.18))
    kid.fin = random.choice((getattr(m, "fin", 0), getattr(f, "fin", 0))) if random.random() > 0.08 else random.choice((0, 1, 2))


def inherit_line(kid, parents):
    """Egg-layers (tetras, cichlids, bettas...) pass a colour line down; breeding the same shift again builds a strain."""
    try:
        m, f = parents
    except (TypeError, ValueError):
        return
    kid.hl = clamp((getattr(m, "hl", 0.0) + getattr(f, "hl", 0.0)) / 2 + random.gauss(0, 0.45), -2.4, 2.4)
    kid.gen = max(getattr(m, "gen", 1), getattr(f, "gen", 1)) + 1
    record_strain(kid, True)


def gene_text(f):
    if hasattr(f, "lace"):
        lace = "lace" if f.lace_on() else ("lace carrier" if any(f.lace) else "no lace")
        gk = f.gene_key
        return f"hue {gk[0]:+d}  tail {gk[1]:+d}  {lace}  sheen {int(f.sheen * 100)}%  {FIN_NAMES[f.fin]} fins"
    if hasattr(f, "hl"):
        return f"colour line {f.gene_key[0]:+d}   gen {getattr(f, 'gen', 1)}"
    return ""


# ---------------------------------------------------------------- 8: breeding requests
def hue_word(h):
    return ("much " if abs(h) > 1 else "") + ("greener/bluer" if h > 0 else "redder")


def new_request():
    gup = sorted({type(f) for f in fishes if isinstance(f, GuppyBase)}, key=lambda c: c.__name__)
    oth = sorted({type(f) for f in fishes if hasattr(f, "hl") and not isinstance(f, Predator)
                  and sum(1 for g in fishes if type(g) is type(f)) >= 2}, key=lambda c: c.__name__)
    r = None
    if gup and (not oth or random.random() < 0.75):
        c = random.choice(gup)
        kind = random.choice(("hue", "hue", "tail", "both", "lace", "fin"))
        h = random.choice((-1, 1, -1, 1, 2, -2))
        r = {"cls": c.__name__, "hue": 0, "tail": 0, "lace": 0, "fin": 0}
        if kind == "hue":
            r.update(hue=h, text=f"{nice_name(c)} shifted {hue_word(h)}", reward=6 * abs(h))
        elif kind == "tail":
            r.update(tail=1, text=f"{nice_name(c)} with a long fan tail", reward=7)
        elif kind == "both":
            r.update(hue=h, tail=1, text=f"{nice_name(c)} {hue_word(h)} with a long fan tail", reward=8 + 6 * abs(h))
        elif kind == "lace":
            r.update(lace=1, text=f"Lace-pattern {nice_name(c)} (breed two carriers)", reward=16)
        else:
            fn = random.choice((1, 2))
            r.update(fin=fn, text=f"{nice_name(c)} with {FIN_NAMES[fn]} fins", reward=9)
        r["swatch"] = hue_shift(getattr(c, "male_color", (120, 170, 210)), r["hue"])
    elif oth:
        c = random.choice(oth)
        h = random.choice((-1, 1))
        r = {"cls": c.__name__, "hue": h, "tail": 0, "lace": 0, "fin": 0, "reward": 8, "text": f"{nice_name(c)} line shifted {hue_word(h)}",
             "swatch": hue_shift(getattr(c, "male_color", (120, 170, 210)), h)}
    if r:
        r["due"] = eco.day + 10
    return r


def req_match(r):
    for f in fishes:
        if (type(f).__name__ != r["cls"] or not hasattr(f, "persona") or f.growth < 1.0 or getattr(f, "gen", 1) < 2
                or f.sick or not f.alive):
            continue
        gk = f.gene_key
        if r["hue"] and gk[0] * (1 if r["hue"] > 0 else -1) < abs(r["hue"]):
            continue
        if r["tail"] and gk[1] < 1:
            continue
        if r["lace"] and not (hasattr(f, "lace") and f.lace_on()):
            continue
        if r["fin"] and getattr(f, "fin", 0) != r["fin"]:
            continue
        return f
    return None


def request_tick():
    r = REQ["cur"]
    if r is None:
        if eco.day >= REQ["next"] and eco.t % 300 == 0:
            REQ["cur"] = new_request()
            if REQ["cur"]:
                notify("New breeding request: " + REQ["cur"]["text"], log=False)
            else:
                REQ["next"] = eco.day + 1
        return
    if eco.t % 120:
        return
    f = req_match(r)
    if f is not None:
        X["points"] += r["reward"]
        X["reqs"] += 1
        WEEK["reqs"] += 1
        story(f, f"Filled a breeding request (+{r['reward']} points)")
        notify(f"Request done with {f.name}! +{r['reward']} points", log=True)
        play_sfx("chime", 0.6)
        REQ["cur"], REQ["next"] = None, eco.day + 1
        save_prefs()
    elif eco.day > r["due"]:
        notify("The breeding request expired", log=False)
        REQ["cur"], REQ["next"] = None, eco.day + 2


# ---------------------------------------------------------------- 9: genetic show
def show_score(f):
    gk = f.gene_key
    s = 8.0 * abs(gk[0])
    if hasattr(f, "lace"):
        s += 6.0 * max(0, gk[1]) + 10.0 * f.sheen + (14.0 if f.lace_on() else 0.0) + (5.0 if f.fin else 0.0)
    s += 0.12 * f.health + 0.06 * max(0.0, 100.0 - f.hunger) - 0.05 * f.stress
    if f.sick:
        s -= 10.0
    return max(0.0, s)


def run_show():
    if eco.day - X["show_day"] < 3:
        notify(f"The next genetic show is in {3 - (eco.day - X['show_day'])} day(s)", log=False)
        return False
    mine = sorted((f for f in fishes if hasattr(f, "persona") and f.growth >= 1.0 and not f.sick and f.alive and not isinstance(f, Predator)),
                  key=show_score, reverse=True)[:3]
    if not mine:
        notify("No healthy adult fish to enter", log=False)
        return False
    pool = [(show_score(f), f.name, f) for f in mine]
    lvl = 18 + 4 * min(X["wins"], 6)
    for i in range(3):
        pool.append((random.uniform(lvl - 10, lvl + 14), "Rival " + random.choice(FISH_NAMES), None))
    pool.sort(key=lambda r: r[0], reverse=True)
    SHOWR["rows"] = [(sc, nm, f is not None) for sc, nm, f in pool]
    SHOWR["day"] = eco.day
    X["show_day"] = eco.day
    X["shows"] += 1
    prize = {0: 25, 1: 15, 2: 8}
    won = 0
    for rank, (sc, nm, f) in enumerate(pool[:3]):
        if f is not None:
            won += prize[rank]
            story(f, f"Placed #{rank + 1} at the genetic show")
            if rank == 0:
                X["wins"] += 1
    X["points"] += won
    notify(f"Genetic show: {won} points won" if won else "Genetic show: no placings this time", log=True)
    play_sfx("chime", 0.6)
    save_prefs()
    return True


# ---------------------------------------------------------------- 14: water chemistry and the nitrogen cycle
def chem_tick():
    c = CHEM
    n = sum(1 for f in fishes if hasattr(f, "family"))
    resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
    c["nh3"] += 0.00015 * n + 0.0004 * resting
    fl = 0.4 + 0.6 * eco.filter + (0.3 if "filter" in X["owned"] else 0.0)
    if eco.power:
        fl *= 0.8 if "ups" in X["gear"] else 0.3
    fl *= 0.6 + 0.4 * EQ["media"]
    floor = 0.55 if c["done"] else 0.02
    c["b1"] = clamp(c["b1"] * (1.002 if c["nh3"] > 0.05 else 0.99995), floor, 1.0)
    c["b2"] = clamp(c["b2"] * (1.002 if c["no2"] > 0.05 else 0.99995), floor, 1.0)
    k1 = min(c["nh3"], 0.012 * c["b1"] * fl)
    c["nh3"] -= k1
    c["no2"] += k1
    k2 = min(c["no2"], 0.012 * c["b2"] * fl)
    c["no2"] -= k2
    c["no3"] += k2 * 15
    green = sum(1 for p in plants if p.species != "MossBall")
    c["no3"] = max(0.0, c["no3"] - 0.0004 * green * (1.6 if FERT["t"] > 0 else 1.0))
    c["nh3"] = min(8.0, c["nh3"])
    c["no2"] = min(8.0, c["no2"])
    c["no3"] = min(200.0, c["no3"])
    target = 7.3 - 0.006 * c["no3"] - (0.3 if "co2" in X["owned"] else 0.0)
    c["ph"] += (target - c["ph"]) * 0.02
    c["age"] += 1
    if not c["done"]:
        # cycled = both colonies exist and have kept ammonia and nitrite near zero for two minutes
        c["ok"] = c["ok"] + 1 if (c["b1"] > 0.1 and c["b2"] > 0.1 and c["nh3"] < 0.1 and c["no2"] < 0.2) else 0
    if not c["done"] and c["ok"] >= 120:
        c["done"], c["won"] = True, True
        c["b1"], c["b2"] = max(c["b1"], 0.6), max(c["b2"], 0.6)
        X["points"] += 10
        notify("The tank has cycled: both bacteria colonies are established! +10 points")
        play_sfx("chime", 0.6)
        save_prefs()
    tox = max(0.0, c["nh3"] - 0.4) + 0.8 * max(0.0, c["no2"] - 0.5) + 0.01 * max(0.0, c["no3"] - 80)
    if tox > 0:
        eco.water = clamp(eco.water - 0.12 * tox, 0.0, 100.0)
        for f in fishes:
            if hasattr(f, "stress"):
                f.stress = min(100.0, f.stress + 0.3 * tox)
        if "tox" not in eco.warned:
            eco.warned.add("tox")
            notify("Ammonia / nitrite / nitrate is high: do a water change (W), check the kit (;)", log=False)
    elif c["nh3"] < 0.2 and c["no2"] < 0.3:
        eco.warned.discard("tox")


def chem_water_change():
    WCOUNT[0] += 1
    for k, v in (("nh3", 0.6), ("no2", 0.6), ("no3", 0.65)):
        CHEM[k] *= v
    CHEM["ph"] += (7.2 - CHEM["ph"]) * 0.4
    CHEM["kh"] += (6.0 - CHEM["kh"]) * 0.4      # fresh tap water: KH 6, GH 8
    CHEM["gh"] += (8.0 - CHEM["gh"]) * 0.4
    del DEB[:]
    DEBS[0] = int(DEBS[0] * 0.4)
    for i in range(GLASS_COLS):
        HAIR[i] *= 0.9


def chem_rinse():
    CHEM["b1"] = max(0.55 if CHEM["done"] else 0.02, CHEM["b1"] * 0.8)
    CHEM["b2"] = max(0.55 if CHEM["done"] else 0.02, CHEM["b2"] * 0.8)


# ---------------------------------------------------------------- 12-13: fertiliser, hair algae, diatoms
def dose_fert():
    if FERT["t"] > 0:
        notify("Fertiliser is still in the water", log=False)
        return
    FERT["t"] = 7200
    CHEM["no3"] += 8
    X["ferts"] += 1
    play_sfx("bubble")
    notify("Fertiliser dosed: plants grow faster" + ("" if "co2" in X["owned"] else ", but algae will love it too"), log=True)


def algae_tick():
    lit = 0.0 if (eco.lights == "OFF" or eco.power) else ((1.0 - eco.night) if eco.lights == "SUN" else 1.0)
    co2 = "co2" in X["owned"]
    feed = 0.25 + clamp(CHEM["no3"] / 40.0, 0.0, 2.0) + (1.5 if FERT["t"] > 0 and not co2 else 0.0)
    rate = 0.004 * lit * feed
    for _ in range(2):
        i = random.randrange(GLASS_COLS)
        HAIR[i] = min(1.0, HAIR[i] + rate * random.random() * 3)
        if HAIR[i] > 0.4:
            j = i + random.choice((-1, 1))
            if 0 <= j < GLASS_COLS:
                HAIR[j] = min(1.0, HAIR[j] + 0.01)
    if lit == 0.0:
        for i in range(GLASS_COLS):
            HAIR[i] *= 0.998

    def col(x):
        return max(0, min(GLASS_COLS - 1, int(x / SCREEN_WIDTH * GLASS_COLS)))
    low = SCREEN_HEIGHT - SAND_HEIGHT - 90
    for s in shimps:
        if s.pos.y > low:
            HAIR[col(s.pos.x)] = max(0.0, HAIR[col(s.pos.x)] - 0.01)
    for sn in crawlers:
        HAIR[col(sn.x)] = max(0.0, HAIR[col(sn.x)] - 0.02)
    clean = 0.0006 * len(crawlers)
    for f in fishes:
        if isinstance(f, Otocinclus):
            HAIR[col(f.pos.x)] = max(0.0, HAIR[col(f.pos.x)] - 0.02)
            clean += 0.003
    if not CHEM["done"]:
        DIA[0] = min(1.0, DIA[0] + 0.0015 * (0.3 + lit))
    DIA[0] = max(0.0, DIA[0] - clean - (0.0015 if CHEM["done"] else 0.0))
    avg = sum(HAIR) / GLASS_COLS
    if avg > 0.3 and "hair" not in eco.warned:
        eco.warned.add("hair")
        notify("Hair algae is spreading: add shrimp, snails or otos, cut the lights, ease off the fertiliser", log=False)
    elif avg < 0.12:
        eco.warned.discard("hair")


def draw_algae_world(surface):
    if DIA[0] > 0.03:
        h = 150
        if F21.get("dia") is None:
            s = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
            for i in range(h):
                pygame.draw.line(s, (122, 90, 38, int(120 * (i / h) ** 1.6)), (0, i), (SCREEN_WIDTH, i))
            F21["dia"] = s
        F21["dia"].set_alpha(int(255 * DIA[0]))
        surface.blit(F21["dia"], (0, SCREEN_HEIGHT - SAND_HEIGHT - h + 30))
    clk = eco.t * 0.03
    for i in range(GLASS_COLS):
        hv = HAIR[i]
        if hv < 0.12:
            continue
        x = (i + 0.5) * SCREEN_WIDTH / GLASS_COLS
        y = ground_y(x)
        for k in range(int(hv * 6) + 2):
            h = 22 + hv * 70 + k * 5
            bx = x + (k - 2) * 6
            pts = [(bx + math.sin(clk + i + k + j * 0.7) * j * 2.0, y + 4 - h * j / 5) for j in range(6)]
            pygame.draw.lines(surface, (126 + 24 * (k % 2), 176, 70), False, pts, 3)
            pygame.draw.lines(surface, (170, 206, 96), False, pts, 1)


# ---------------------------------------------------------------- 10: shop
def buy_item(i):
    if not 0 <= i < len(SHOP):
        return
    iid, name, cost, _ = SHOP[i]
    if iid != "oto" and iid in X["owned"]:
        notify(f"You already own the {name}", log=False)
        return
    if X["points"] < cost:
        notify(f"The {name} costs {cost} points (you have {X['points']})", log=False)
        return
    if iid == "oto":
        if len(fishes) >= FRAME_BUDGET - 3:
            notify("The tank is too full for more fish", log=False)
            return
        for _ in range(2):
            fishes.append(Otocinclus(random.randint(120, SCREEN_WIDTH - 120), SCREEN_HEIGHT - SAND_HEIGHT - 80))
    else:
        X["owned"].append(iid)
    X["points"] -= cost
    play_sfx("chime", 0.6)
    notify(f"Bought: {name}", log=True)
    save_prefs()


def shop_tick():
    own = X["owned"]
    if "filter" in own:
        eco.filter = min(1.0, eco.filter + 0.0008)
    if "magnet" in own:
        for i in range(GLASS_COLS):
            eco.glass[i] = max(0.0, eco.glass[i] - 0.0008)
    if "thermo" in own and not eco.power:
        eco.temp += (25.0 - eco.temp) * 0.05


# ---------------------------------------------------------------- 11: aquascapes
def load_user_scapes():
    try:
        with open(SCAPES_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return [s for s in data if isinstance(s, dict) and "name" in s and "seed" in s and isinstance(s.get("placed"), list)]
    except (OSError, ValueError):
        return []


def all_scapes():
    out = []
    for name, seed, items in SCAPE_BUILTIN:
        out.append({"name": name, "seed": seed, "placed": [[k, int(fr * SCREEN_WIDTH), 0.9] for k, fr in items]})
    return out + load_user_scapes()[-5:]


def apply_scape(sc):
    rebuild_world(int(sc["seed"]))
    placed.clear()
    if isinstance(sc.get("layout"), dict):
        layout_apply(sc["layout"])
        PM["rocks_dirty"] = True
        pm_finalize()
    for k, x, z in ([] if isinstance(sc.get("layout"), dict) else sc["placed"]):
        if k in ("ROCK", "DRIFTWOOD", "SWORD", "ROTALA", "LUDWIGIA", "DWARF", "CRYPT", "CLOVER", "MOSS", "CABOMBA", "HYGRO"):
            place_decor(k, float(x), float(z))
    build_cover()
    X["scapes"] += 1
    notify(f"Aquascape: {sc['name']}", log=True)
    save_prefs()


def save_scape():
    mine = load_user_scapes()
    mine.append({"name": f"My scape {len(mine) + 1}", "seed": world_seed, "placed": [[k, x, z] for k, x, z, _ in placed]})
    if LAYOUT["custom"]:
        mine[-1]["layout"] = layout_snapshot()
    try:
        with open(SCAPES_PATH, "w", encoding="utf-8") as fh:
            json.dump(mine[-20:], fh)
        notify(f"Saved as {mine[-1]['name']}", log=False)
    except OSError as err:
        notify(f"Could not save the scape: {err}", log=False)


# ---------------------------------------------------------------- 18: album and timelapse recorder
def album_load():
    try:
        with open(ALB_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return [a for a in data if isinstance(a, dict) and "file" in a]
    except (OSError, ValueError):
        return []


def album_add(name, score=0):
    items = album_load()
    items.append({"score": score, "file": name, "day": eco.day, "season": SEASONS[eco.season], "fish": len(fishes), "water": int(eco.water),
                  "when": time.strftime("%Y-%m-%d %H:%M")})
    try:
        with open(ALB_PATH, "w", encoding="utf-8") as fh:
            json.dump(items[-400:], fh)
    except OSError:
        pass


def rec_toggle():
    if REC["on"]:
        rec_stop()
    else:
        REC.update(on=True, frames=[], n=0, every=20)
        notify("Recording a timelapse clip (F12 to stop)", log=False)


def rec_capture(surface):
    if not REC["on"]:
        return
    REC["n"] += 1
    if REC["n"] % REC.get("every", 20):
        return
    w = 480
    h = int(w * SCREEN_HEIGHT / SCREEN_WIDTH)
    small = pygame.transform.smoothscale(surface, (w, h))
    REC["frames"].append((small.get_size(), pygame.image.tostring(small, "RGB")))
    if len(REC["frames"]) >= 400:
        rec_stop()


def _rec_save(name, frames):
    try:
        from PIL import Image
        ims = [Image.frombytes("RGB", sz, raw) for sz, raw in frames]
        ims[0].save(name, save_all=True, append_images=ims[1:], duration=100, loop=0)
    except Exception as err:   # no Pillow, disk full...: the game carries on
        print("timelapse clip not saved:", err)


def rec_stop():
    frames = REC["frames"]
    REC.update(on=False, frames=[], n=0)
    if len(frames) < 4:
        notify("Clip too short to save", log=False)
        return
    import threading
    os.makedirs("screenshots", exist_ok=True)
    name = time.strftime("screenshots/timelapse_%Y%m%d_%H%M%S.gif")
    threading.Thread(target=_rec_save, args=(name, frames), daemon=True).start()
    X["clips"] += 1
    notify(f"Timelapse clip saved: {name}", log=True)
    save_prefs()


# ---------------------------------------------------------------- 19: soundscapes
def build_soundscape():
    SND21["ready"] = True
    if pygame.mixer.get_init() is None:
        return
    try:
        import numpy as np
        freq, _, chans = pygame.mixer.get_init()
        n = freq * 4
        t = np.arange(n) / freq
        rng = np.random.default_rng(5)

        def mk(a):
            a = (np.clip(a, -1, 1) * 9000).astype(np.int16)
            if chans > 1:
                a = np.repeat(a[:, None], chans, axis=1)
            return pygame.mixer.Sound(buffer=np.ascontiguousarray(a).tobytes())
        rain = np.convolve(rng.standard_normal(n), np.ones(5) / 5, "same") * 0.9
        gate = ((t * 2) % 1.0 < 0.4) & (np.sin(2 * np.pi * 28 * t) > 0)
        crick = np.sin(2 * np.pi * 4300 * t) * gate * 0.5 + np.sin(2 * np.pi * 4700 * t) * (np.roll(gate, freq // 3)) * 0.35
        room = np.convolve(rng.standard_normal(n), np.ones(160) / 160, "same") * 9 + np.sin(2 * np.pi * 60 * t) * 0.12 + np.sin(2 * np.pi * 120 * t) * 0.05
        pygame.mixer.set_reserved(3)
        SND21["snd"] = [mk(rain), mk(crick), mk(room)]
        SND21["chan"] = [pygame.mixer.Channel(i) for i in range(3)]
        for ch, snd in zip(SND21["chan"], SND21["snd"]):
            ch.set_volume(0.0)
            ch.play(snd, loops=-1)
    except Exception as err:
        print("soundscape unavailable:", err)
        SND21["chan"] = []


def sound_tick():
    on = X["sound"] == "AUTO"
    if on and not SND21["ready"]:
        build_soundscape()
    if not SND21["chan"]:
        return
    storm = eco.event == "THUNDERSTORM"
    night = clamp((eco.night - 0.2) / 0.6)
    target = [0.5 if storm else 0.0, 0.0 if storm else 0.3 * night, 0.14 * (1.0 - 0.3 * night)]
    master = 0.0 if (is_muted or not on) else VOL["master"] * VOL["fx"]
    for i, ch in enumerate(SND21["chan"]):
        SND21["cur"][i] += (target[i] * master - SND21["cur"][i]) * 0.15
        try:
            ch.set_volume(max(0.0, SND21["cur"][i]))
        except pygame.error:
            pass


def cycle_sound():
    X["sound"] = "OFF" if X["sound"] == "AUTO" else "AUTO"
    notify("Soundscape: " + X["sound"] + ("  (rain in storms, crickets at night, room hum)" if X["sound"] == "AUTO" else ""), log=False)
    save_prefs()



# ---------------------------------------------------------------- care: carriers, sales, weekly chores, challenges, raids
CH = {"day": None, "wipes": 0, "rinses": 0, "wc": 0, "kit": False}
WCOUNT = [0]
RAID = {"t": -1, "kills": 0, "warned": False}
CHALLENGES = [
    ("mix", "Community", "Keep 6 or more species together for 8 days in a row", 30, 15),
    ("hands", "Hands off", "No water change for 10 days, and the water still 60+ at the end", 10, 12),
    ("line", "Master breeder", "Raise a third-generation fish within 25 days", 25, 18),
    ("boom", "Fry boom", "Have 12 fish hatch within 20 days", 20, 14),
]


def carrier_tick(f):
    """A recovered fish still carries the sickness for a while: stress and foul water can bring it back, and it can pass it on."""
    c = getattr(f, "carrier", 0)
    if c <= 0:
        return
    f.carrier = c - 1
    if f.sick or getattr(f, "immune", 0) > 0 or getattr(f, "qpos", None) is not None:
        return
    if f.stress > 55 and eco.water < 65 and random.random() < 0.0004:
        infect(f)
        X["relapses"] += 1
        story(f, "The sickness came back")
        return
    if eco.water < 70 and eco.t % 120 == 0 and random.random() < 0.02:
        for o in fishes:
            if (o is not f and hasattr(o, "sick") and not o.sick and getattr(o, "immune", 0) <= 0 and not getattr(o, "qpos", None)
                    and o.pos.distance_squared_to(f.pos) < 70 * 70):
                infect(o)
                break


def sale_price(f):
    gk = f.gene_key
    p = 3 + 5 * abs(gk[0]) + 3 * (getattr(f, "gen", 1) - 1)
    if hasattr(f, "lace") and f.lace_on():
        p += 6
    rec = strains.get(f"{type(f).__name__}|{gk[0]}|{gk[1]}")
    if rec is not None and rec[1] <= 2:
        p += 4      # a rare strain
    return int(max(2, p))


def sellable():
    out = [f for f in fishes if hasattr(f, "persona") and f.growth >= 1.0 and f.alive and not f.sick and not f.fav
           and not isinstance(f, Predator) and getattr(f, "gen", 1) >= 2]
    out.sort(key=sale_price, reverse=True)
    return out[:9]


def sell_fish(i):
    lst = sellable()
    if not 0 <= i < len(lst):
        return
    f = lst[i]
    price = sale_price(f)
    story(f, f"Sold for {price} points")
    fishes.remove(f)
    if eco.selected is f:
        eco.selected = None
    X["points"] += price
    X["cash"] += price
    X["sold"] += 1
    play_sfx("chime", 0.5)
    notify(f"Sold {f.name} the {nice_name(f)} for {price} points", log=True)
    save_prefs()


def chore_status():
    return [("Water change (W)", WCOUNT[0] > CH["wc"]), ("Rinse the filter (F)", stats["rinses"] > CH["rinses"]),
            ("Wipe the glass (C)", stats["wipes"] > CH["wipes"]), ("Check the test kit (;)", CH["kit"])]


def chore_tick():
    if CH["day"] is None:
        CH.update(day=eco.day, wipes=stats["wipes"], rinses=stats["rinses"], wc=WCOUNT[0], kit=False)
        return
    if eco.day - CH["day"] < 7:
        return
    if all(ok for _, ok in chore_status()):
        X["streak"] += 1
        pts = 4 + min(X["streak"], 6)
        X["points"] += pts
        notify(f"Weekly chores done: {X['streak']} week streak, +{pts} points", log=True)
        play_sfx("chime", 0.5)
    else:
        if X["streak"]:
            notify("A chore was missed this week: the streak is over", log=False)
        X["streak"] = 0
    CH.update(day=eco.day, wipes=stats["wipes"], rinses=stats["rinses"], wc=WCOUNT[0], kit=False)
    save_prefs()


def chal_start(i):
    if not 0 <= i < len(CHALLENGES):
        return
    if X["chal"]:
        notify("Finish or abandon the current challenge first (press its number again to abandon)", log=False)
        return
    cid = CHALLENGES[i][0]
    X["chal"] = {"id": cid, "start": eco.day, "wc": WCOUNT[0], "births": eco.births, "since": eco.day}
    notify(f"Challenge started: {CHALLENGES[i][1]}", log=True)
    save_prefs()


def chal_info(cid):
    return next(c for c in CHALLENGES if c[0] == cid)


def chal_progress(st):
    """(state, text): state is 'run', 'won' or 'lost'."""
    cid, day = st["id"], eco.day
    left = chal_info(cid)[3] - (day - st["start"])
    if cid == "mix":
        species = len({type(f) for f in fishes if hasattr(f, "persona") and not isinstance(f, Predator)})
        held = day - st["since"]
        if held >= 8:
            return "won", "done"
        if left < 0:
            return "lost", "time ran out"
        return "run", f"{species} species now, held {held}/8 days, {left} days left"
    if cid == "hands":
        if WCOUNT[0] > st["wc"]:
            return "lost", "you changed the water"
        if day - st["start"] >= 10:
            return ("won", "done") if eco.water >= 60 else ("lost", "the water went bad")
        return "run", f"{10 - (day - st['start'])} days to go, water {int(eco.water)}%"
    if cid == "line":
        best = max([getattr(f, "gen", 1) for f in fishes] + [1])
        if best >= 3:
            return "won", "done"
        if left < 0:
            return "lost", "time ran out"
        return "run", f"best generation {best}/3, {left} days left"
    n = eco.births - st["births"]
    if n >= 12:
        return "won", "done"
    if left < 0:
        return "lost", "time ran out"
    return "run", f"{n}/12 hatched, {left} days left"


def chal_tick():
    st = X["chal"]
    if not st:
        return
    if st["id"] == "mix":
        species = len({type(f) for f in fishes if hasattr(f, "persona") and not isinstance(f, Predator)})
        if species < 6:
            st["since"] = eco.day
    state, _ = chal_progress(st)
    if state == "run":
        return
    c = chal_info(st["id"])
    if state == "won":
        X["points"] += c[4]
        X["chal_won"].append(c[0])
        notify(f"Challenge won: {c[1]}! +{c[4]} points", log=True)
        play_sfx("chime", 0.6)
    else:
        notify(f"Challenge failed: {c[1]}", log=True)
    X["chal"] = {}
    save_prefs()


def raid_tick():
    """With predators enabled, a raid now and then: a warning, then the hunters get hungry. Hiding places decide how it goes."""
    if not PRED["on"] or not predators or eco.day < 3:
        RAID["t"] = -1
        return
    if RAID["t"] < 0:
        if eco.t % 600 == 0 and random.random() < 0.02:
            RAID["t"] = eco.t + 1200
            RAID["kills"] = eco.kills
            RAID["warned"] = True
            notify("Shadows are circling the tank: the hunters are about to get hungry. Hiding places (Home) help.", log=True)
        return
    if eco.t == RAID["t"] or (eco.t > RAID["t"] and RAID["warned"]):
        for p in predators:
            p.hunger = max(p.hunger, 88.0)
        RAID["warned"] = False
        RAID["end"] = eco.t + 3000
    if eco.t > RAID.get("end", 10 ** 9):
        lost = eco.kills - RAID["kills"]
        X["raids"] += 1
        if lost == 0:
            X["points"] += 8
            notify("The raid is over and nobody was caught! +8 points", log=True)
            play_sfx("chime", 0.5)
        else:
            notify(f"The raid is over: {lost} fish lost", log=True)
        RAID["t"] = -1
        RAID.pop("end", None)


def draw_care_panels(surface):
    p = UI21["panel"]
    if p == "sell":
        lst = sellable()
        panel = begin_panel(860, 130 + 34 * max(1, len(lst)), f"Sell fish   {X['points']} points")
        if not lst:
            txt21(panel, "Nothing to sell yet: bred fish (generation 2+) that are grown, healthy and not starred.", 26, 70)
        for i, f in enumerate(lst):
            y = 70 + 34 * i
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, f"{f.name} the {nice_name(f)}", 62, y + 4, "h", (255, 232, 140))
            txt21(panel, f"gen {getattr(f, 'gen', 1)}   {gene_text(f)}", 380, y + 6, "d", HUD_DIM)
            txt21(panel, f"{sale_price(f)} pts", 760, y + 4, "h", (235, 245, 255))
        end_panel(surface, panel, "1-9 sell   Esc to close   (rare and well-bred strains sell for more; starred fish are never listed)")
    elif p == "care":
        panel = begin_panel(900, 150 + 40 * len(CHALLENGES) + 120, f"Care and challenges   streak {X['streak']}")
        txt21(panel, "This week's chores", 26, 64, "h", (255, 232, 140))
        for i, (name, ok) in enumerate(chore_status()):
            x = 26 + (i % 2) * 420
            y = 92 + (i // 2) * 26
            pygame.draw.rect(panel, (90, 210, 140) if ok else (70, 90, 120), (x, y + 2, 16, 16), 0 if ok else 2, border_radius=3)
            txt21(panel, name, x + 26, y, "d", (200, 215, 232))
        days = 7 - (eco.day - (CH["day"] if CH["day"] is not None else eco.day))
        txt21(panel, f"{days} days left this week. Finish all four for streak points.", 26, 148, "d", HUD_DIM)
        txt21(panel, "Challenges", 26, 184, "h", (255, 232, 140))
        st = X["chal"]
        for i, (cid, title, desc, _d, reward) in enumerate(CHALLENGES):
            y = 212 + 40 * i
            active = bool(st) and st["id"] == cid
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, title + (f"   (won x{X['chal_won'].count(cid)})" if cid in X["chal_won"] else ""), 62, y, "h",
                  (150, 230, 170) if active else (200, 215, 232))
            txt21(panel, chal_progress(st)[1] if active else desc, 62, y + 20, "d", (150, 230, 170) if active else HUD_DIM)
            txt21(panel, f"+{reward} pts", 800, y + 4, "h", (235, 245, 255))
        end_panel(surface, panel, "1-4 start a challenge (again to abandon)   Esc to close")



# ---------------------------------------------------------------- settings, save slots, backups, progress reset
SLOT_DIR = os.path.dirname(CONFIG_FILE)
PREV_PATH = os.path.join(SLOT_DIR, "aquarium_prev.json")
N_SLOTS = 5
SET = {"mode": None, "slots": None, "reset": 0}
QUAL_NAMES = ("LOW", "MED", "HIGH")


def slot_path(i):
    return os.path.join(SLOT_DIR, f"aquarium_slot{i + 1}.json")


def slot_meta():
    out = []
    for i in range(N_SLOTS):
        try:
            with open(slot_path(i), encoding="utf-8") as fh:
                d = json.load(fh)
            e = d.get("eco", {})
            when = time.strftime("%d %b %H:%M", time.localtime(d["saved_at"])) if isinstance(d.get("saved_at"), (int, float)) else "?"
            out.append(f"day {e.get('day', '?')}, {len(d.get('fish', []))} fish, saved {when}")
        except (OSError, ValueError, KeyError, TypeError):
            out.append(None)
    return out


def backup_current():
    """Called before any load, so a load can be taken back (R in the settings panel)."""
    try:
        save_game(PREV_PATH, quiet=True)
    except Exception:
        pass


def restore_previous():
    if not os.path.exists(PREV_PATH):
        notify("There is no earlier state to restore", log=False)
        return
    load_game(PREV_PATH)
    notify("Restored the tank from before the last load", log=True)


def reset_progress():
    for k in X:
        X[k] = json.loads(json.dumps(X_DEFAULT[k]))
    GOALS_DONE.clear()
    strains.clear()
    save_prefs()
    notify("Progress reset: points, goals, strains, memorial and purchases are cleared (fish sets and options are kept)", log=True)


SETTING_ROWS = [
    ("Predators", lambda: PRED["on"], "predators", "channa, fire eel and crayfish hunt the fish"),
    ("Crayfish", lambda: CRAY["on"], "crayfish", "show the crayfish"),
    ("Turtle", lambda: TURTLE["on"], "turtle", "rare turtle visitor"),
    ("Visitors", lambda: VISIT["on"], "visitors", "frog and kingfisher guests"),
    ("Away mode", lambda: AWAY["on"], "away", "the tank keeps going while the game is closed"),
    ("Auto quality", lambda: GOV["on"], "auto", "drop the plant detail automatically when frames are slow"),
    ("Quality", lambda: QUALITY[0], "quality", "LOW / MED / HIGH (also Q)"),
    ("New tank mode", lambda: NEWTANK["on"], "newtank", "start the next game with an uncycled tank"),
    ("Soundscape", lambda: X["sound"], "sound", "ambient rain, crickets and room hum (also backquote)"),
]


def setting_toggle(i):
    key = SETTING_ROWS[i][2]
    if key == "predators":
        PRED["on"] = not PRED["on"]
    elif key == "crayfish":
        CRAY["on"] = not CRAY["on"]
    elif key == "turtle":
        TURTLE["on"] = not TURTLE["on"]
    elif key == "visitors":
        VISIT["on"] = not VISIT["on"]
    elif key == "away":
        AWAY["on"] = not AWAY["on"]
    elif key == "auto":
        GOV["on"] = not GOV["on"]
    elif key == "quality":
        QUALITY[0] = QUAL_NAMES[(QUAL_NAMES.index(QUALITY[0]) + 1) % 3]
        GOV["base"] = QUALITY[0]
    elif key == "newtank":
        NEWTANK["on"] = not NEWTANK["on"]
    elif key == "sound":
        cycle_sound()
    save_prefs()
    if key in ("predators", "crayfish", "turtle", "visitors"):
        notify("Changed: it takes effect the next time the tank is started", log=False)


def settings_key(k):
    """Digits 1-9 change a setting. S then 1-5 saves to a slot, L then 1-5 loads one, R restores the state before the last load,
    Z twice resets progress."""
    if SET["mode"] in ("save", "load") and pygame.K_1 <= k <= pygame.K_5:
        i = k - pygame.K_1
        if SET["mode"] == "save":
            save_game(slot_path(i))
            notify(f"Saved to slot {i + 1}", log=False)
        elif os.path.exists(slot_path(i)):
            backup_current()
            load_game(slot_path(i))
        else:
            notify(f"Slot {i + 1} is empty", log=False)
        SET["mode"], SET["slots"] = None, None
        return True
    if pygame.K_1 <= k <= pygame.K_9:
        setting_toggle(k - pygame.K_1)
        return True
    if k == pygame.K_s:
        SET["mode"] = None if SET["mode"] == "save" else "save"
        SET["slots"] = None
        return True
    if k == pygame.K_l:
        SET["mode"] = None if SET["mode"] == "load" else "load"
        SET["slots"] = None
        return True
    if k == pygame.K_r:
        backup = os.path.exists(PREV_PATH)
        restore_previous() if backup else notify("There is no earlier state to restore", log=False)
        return True
    if k == pygame.K_z:
        SET["reset"] += 1
        if SET["reset"] >= 2:
            SET["reset"] = 0
            reset_progress()
        else:
            notify("Press Z again to reset all progress (points, goals, strains, memorial, purchases)", log=False)
        return True
    return False


def draw_settings(surface):
    if SET["slots"] is None:
        SET["slots"] = slot_meta()
    panel = begin_panel(1000, 600, "Settings and saves")
    for i, (name, getter, _k, desc) in enumerate(SETTING_ROWS):
        y = 66 + 34 * i
        v = getter()
        on = v is True or (isinstance(v, str) and v not in ("OFF",))
        txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
        txt21(panel, name, 62, y + 2, "h", (200, 215, 232))
        txt21(panel, ("ON" if v is True else "OFF" if v is False else str(v)), 230, y + 2, "h", (150, 230, 170) if on else (160, 170, 185))
        txt21(panel, desc, 320, y + 4, "d", HUD_DIM)
    y0 = 66 + 34 * len(SETTING_ROWS) + 14
    txt21(panel, "Save slots", 26, y0, "h", (255, 232, 140))
    mode = SET["mode"]
    txt21(panel, ("Press 1-5 to " + mode + "...") if mode else "S then 1-5 saves   L then 1-5 loads   R restores the state before the last load", 150, y0 + 2, "d", (255, 232, 150) if mode else HUD_DIM)
    for i, m in enumerate(SET["slots"]):
        txt21(panel, f"{i + 1}", 26, y0 + 28 + 24 * i, "h", (130, 190, 235))
        txt21(panel, m or "empty", 62, y0 + 28 + 24 * i, "d", (200, 215, 232) if m else (110, 125, 145))
    txt21(panel, "Z twice: reset progress (points, goals, strains, memorial, purchases). Fish sets, audio and options stay.", 26, 600 - 52, "d", (240, 170, 150))
    end_panel(surface, panel, "Esc to close   (Ctrl+S opens this panel)")



# ---------------------------------------------------------------- hub: gear and cash, breeding line, upkeep, history, life, guide
# Also here: water hardness, equipment wear, snail and shrimp colonies, weather events, debris, night life, the hand, the gamepad.
EQ = {"drift": 0.0, "stone": 1.0, "media": 1.0, "sd": -9}
EV = {"name": None, "until": 0, "dt": 0.0, "start": -9, "b0": 0}
DEB = []
DEBS = [0]
HUB = {"tab": 0}
HUB_TABS = ("Gear", "Line", "Upkeep", "History", "Life", "Guide")
HAND = {"f": None, "held": 0, "drip": 0}
TUTF = set()
TUTP = {"t": 0}
PAD = {"js": None, "btn": {}, "next": 0}
CAT = {"t": 0}
P6 = {"day": None, "init": False, "tour": 0, "last_event": ""}
SOFT_FISH = ("NeonTetra", "CardinalTetra", "RummyNose", "LemonTetra", "BlackSkirtTetra", "Otocinclus", "Corydoras")
HARD_FISH = ("Killifish", "MosaicGuppy", "MoscowGuppy", "TuxedoGuppy", "SunsetGuppy", "KenyiCichlid", "AuratusCichlid", "SocolofiCichlid")
GEAR = [("filter2", "Filter upgrade II", 40, "Sponge clogs even slower and the flow stays strong"),
        ("led", "LED rack", 60, "Tall plants grow a little faster every day"),
        ("ups", "Battery backup", 50, "A power cut no longer stops the filter or the water quality"),
        ("autofeed", "Auto feeder", 70, "Drops a pinch of flakes twice a day (watch the waste)"),
        ("heater_pro", "Smart heater", 45, "The heater never drifts off its setting"),
        ("mineral", "Mineral kit", 30, "Lets you raise or lower hardness from the Upkeep tab")]
TUT = [("Click the water to drop food. Hold the button to drip it. Keys 1-6 change the food.", "click"),
       ("Press F1 to see every key.", pygame.K_F1),
       ("Press , to open the equipment shop.", pygame.K_COMMA),
       ("Press ; for the water test kit (now with KH and GH).", pygame.K_SEMICOLON),
       ("Press / for the dashboard and the week summary.", pygame.K_SLASH),
       ("Press Del for the hub: gear, breeding line, upkeep, history, life.", pygame.K_DELETE),
       ("Hold Ctrl and drag a fish to lift it. Right-click taps the glass.", "hand"),
       ("That is the tour. Ctrl+S opens settings and save slots.", None)]


def buy_gear(i):
    if not 0 <= i < len(GEAR):
        return
    gid, name, cost, _ = GEAR[i]
    if gid in X["gear"]:
        notify(f"You already own the {name}", log=False)
    elif X["cash"] < cost:
        notify(f"The {name} costs {cost} cash (you have {X['cash']}). Sell bred fish and keep a good scape to earn it", log=False)
    else:
        X["cash"] -= cost
        X["gear"].append(gid)
        play_sfx("chime", 0.6)
        notify(f"Bought: {name}", log=True)
        save_prefs()


# ---- hardness
def hardness_range(f):
    n = type(f).__name__
    return (2.0, 8.0) if n in SOFT_FISH else (8.0, 16.0) if n in HARD_FISH else (4.0, 12.0)


def hardness_off(f):
    lo, hi = hardness_range(f)
    return max(lo - CHEM["gh"], CHEM["gh"] - hi, 0.0)


def hardness_tick():
    bad = 0
    for f in fishes:
        if hasattr(f, "stress") and hasattr(f, "family"):
            off = hardness_off(f)
            if off > 1.5:
                f.stress = min(100.0, f.stress + 0.35 * off)
                bad += 1
    if bad >= 4 and "gh" not in eco.warned:
        eco.warned.add("gh")
        notify(f"The water hardness (GH {CHEM['gh']:.0f}) does not suit {bad} fish: see Upkeep (Del)", log=False)
    elif bad == 0:
        eco.warned.discard("gh")


def chem6_tick():
    c = CHEM
    green = sum(1 for p in plants if p.species != "MossBall")
    c["kh"] = clamp(c["kh"] - 0.0012 * (1.0 + c["no3"] / 60.0), 0.5, 25.0)
    c["gh"] = clamp(c["gh"] + 0.0003 * len(rocks) - 0.00006 * green, 0.5, 25.0)
    c["ph"] += ((6.9 + 0.12 * (c["kh"] - 4.0)) - c["ph"]) * 0.01
    if c["kh"] < 2.0 and c["ph"] < 6.4 and "khlow" not in eco.warned:
        eco.warned.add("khlow")
        notify("KH is nearly gone: the pH can crash. Do a water change (W)", log=False)
    elif c["kh"] > 3.0:
        eco.warned.discard("khlow")
    if "filter2" in X["gear"]:
        eco.filter = min(1.0, eco.filter + 0.0004)
    if DEBS[0] > 20:
        HAIR[random.randrange(GLASS_COLS)] += 0.002 * DEBS[0] / 30.0
        c["no3"] = min(200.0, c["no3"] + 0.004 * DEBS[0])
    if eco.power and "ups" in X["gear"]:
        eco.water = clamp(eco.water + 0.08, 0.0, 100.0)
    if EQ["stone"] < 0.3 and eco.air_on:
        eco.water = clamp(eco.water - 0.03 * (0.3 - EQ["stone"]) / 0.3, 0.0, 100.0)


# ---- debris on the sand
def debris_spawn():
    resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
    rate = 0.12 + 0.012 * len(fishes) + 0.04 * resting + (0.15 if EV["name"] == "leaf fall" else 0.0)
    rate *= 1.3 - 0.6 * eco.filter
    if len(DEB) < 70 and random.random() < min(0.9, rate):
        DEB.append([random.uniform(30, SCREEN_WIDTH - 30), random.uniform(WATER_TOP + 40, SCREEN_HEIGHT * 0.65),
                    random.uniform(-0.12, 0.12), random.uniform(0.06, 0.22), random.uniform(0, 6)])


def debris_update():
    if not DEB:
        return
    cur = eco.current * 6
    pull = 0.0 if eco.power else eco.filter * 0.0006
    for d in DEB[:]:
        d[0] += d[2] + cur + math.sin(eco.t * 0.03 + d[4]) * 0.15
        d[1] += d[3]
        if random.random() < pull:
            DEB.remove(d)
        elif d[1] >= ground_y(d[0]) - 4:
            DEB.remove(d)
            DEBS[0] = min(60, DEBS[0] + 1)


def siphon():
    if eco.day - EQ["sd"] < 1:
        notify("The sand was already siphoned today", log=False)
        return
    EQ["sd"] = eco.day
    del DEB[:]
    DEBS[0] = 0
    CHEM["nh3"] *= 0.8
    CHEM["no3"] *= 0.85
    eco.water = clamp(eco.water + 3.0, 0.0, 100.0)
    play_sfx("bubble")
    notify("Siphoned the sand: the mulm is gone", log=True)


# ---- colonies
def colony_tick():
    resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
    fed = CHEM["no3"] > 12 or resting > 3 or sum(HAIR) / GLASS_COLS > 0.15
    snails = [c for c in crawlers if isinstance(c, (MysterySnail, Ramshorn))]
    n = len(snails)
    if fed and n < 22 and random.random() < 0.55:
        crawlers.append(Ramshorn() if random.random() < 0.7 else MysterySnail())
        if n + 1 == 15:
            notify("A snail boom: too much food is feeding them. Feed less", log=False)
    elif not fed and n > 4 and random.random() < 0.4:
        crawlers.remove(snails[-1])
    moss = sum(1 for p in plants if p.species in ("MossBall", "DwarfGrass", "Clover"))
    if moss >= 2 and CHEM["no3"] < 70 and CHEM["nh3"] < 0.5 and len(shimps) < 40 and random.random() < 0.5:
        shimps.append(TinyShrimp())
    elif (CHEM["no3"] > 90 or CHEM["nh3"] > 1.0) and len(shimps) > 6 and random.random() < 0.5:
        shimps.pop()
        notify("A shrimp died in the dirty water", log=False)


# ---- weather and seasonal events
def event_end():
    name = EV["name"]
    ok = True
    if name in ("cold snap", "heat wave"):
        st = [f.stress for f in fishes if hasattr(f, "stress")]
        ok = (sum(st) / len(st) < 40) if st else True
    elif name == "spawning season":
        ok = eco.births - EV["b0"] >= 3
    elif name == "leaf fall":
        ok = CHEM["nh3"] < 0.3 and CHEM["no3"] < 40
    EV.update(name=None, dt=0.0)
    if ok:
        X["points"] += 6
        X["cash"] += 6
        X["evok"] += 1
        notify(f"You came through the {name}: +6 points, +6 cash", log=True)
        play_sfx("chime", 0.5)
    else:
        notify(f"The {name} is over; it left the tank a little worse for wear", log=True)
    save_prefs()


def events_tick():
    if EV["name"]:
        if eco.day >= EV["until"]:
            event_end()
        return
    if eco.day - EV["start"] < 6 or random.random() > 0.16 or eco.event:
        return
    name = ("spawning season", "heat wave", "leaf fall", "cold snap")[eco.season % 4]
    EV.update(name=name, start=eco.day, until=eco.day + 2, b0=eco.births)
    if name == "cold snap":
        EV["dt"] = -4.0
        notify("Cold snap! The room is cooling: raise the heater (Y)", log=True)
    elif name == "heat wave":
        EV["dt"] = 4.0
        notify("Heat wave! Heater off (Y), lights off (L) and keep the water clean", log=True)
    elif name == "spawning season":
        eco.start_event("MOON SPAWNING")
        notify("Spawning season: the fish are in the mood. Keep cover and clean water for the fry", log=True)
    else:
        for _ in range(30):
            debris_spawn()
        CHEM["no3"] = min(200.0, CHEM["no3"] + 5)
        notify("Leaf fall: debris is raining into the tank. Siphon the sand and change water", log=True)


# ---- breeding line
def line_state():
    L = X["line"]
    if not L.get("cls"):
        pool = {}
        for f in fishes:
            if hasattr(f, "hl") and hasattr(f, "family"):
                pool[type(f).__name__] = pool.get(type(f).__name__, 0) + 1
        if pool:
            L["cls"] = max(pool, key=pool.get)
            L["target"] = round(random.choice((-1, 1)) * random.uniform(0.35, 0.7), 2)
            L["need"] = 2
            L["done"] = 0
    return L


def line_score(f, target):
    return int(100 * max(0.0, 1.0 - abs(f.hl - target) / 0.8))


def line_candidates():
    L = line_state()
    if not L.get("cls"):
        return []
    out = [(line_score(f, L["target"]), f) for f in fishes if type(f).__name__ == L["cls"] and hasattr(f, "hl")]
    out.sort(key=lambda a: -a[0])
    return out


def line_check():
    L = line_state()
    if not L.get("cls"):
        return
    for sc, f in line_candidates():
        if sc >= 80 and f.growth >= 1.0 and getattr(f, "gen", 1) >= L["need"]:
            L["done"] += 1
            X["points"] += 15
            X["cash"] += 10
            story(f, f"Met the {L['cls']} line standard (generation {f.gen})")
            notify(f"{f.name} meets the {nice_name(type(f))} line standard! +15 points, +10 cash", log=True)
            play_sfx("chime", 0.6)
            L["need"] = int(f.gen) + 2
            L["target"] = round(clamp(L["target"] + random.choice((-1, 1)) * random.uniform(0.3, 0.6), -1.0, 1.0), 2)
            save_prefs()
            return


def line_cycle(retarget):
    L = line_state()
    names = sorted({type(f).__name__ for f in fishes if hasattr(f, "hl") and hasattr(f, "family")})
    if not names:
        return
    if not retarget:
        i = (names.index(L["cls"]) + 1) % len(names) if L.get("cls") in names else 0
        L["cls"] = names[i]
    L["target"] = round(random.choice((-1, 1)) * random.uniform(0.3, 0.7), 2)
    L["need"] = max((getattr(f, "gen", 1) for f in fishes if type(f).__name__ == L["cls"]), default=1) + 1
    notify(f"New {nice_name(type(next(f for f in fishes if type(f).__name__ == L['cls'])))} line target set", log=False)


# ---- per-day work
def day6():
    P6["day"] = eco.day
    EQ["stone"] = max(0.0, EQ["stone"] - 0.04)
    EQ["media"] = max(0.0, EQ["media"] - 0.03)
    if "heater_pro" in X["gear"]:
        EQ["drift"] = 0.0
    else:
        EQ["drift"] = clamp(EQ["drift"] + random.gauss(0.0, 0.25), -3.0, 3.0)
        if abs(EQ["drift"]) > 1.5 and "drift" not in eco.warned:
            eco.warned.add("drift")
            notify("The heater is drifting off its setting: recalibrate it in Upkeep (Del)", log=False)
        elif abs(EQ["drift"]) < 0.8:
            eco.warned.discard("drift")
    if EQ["media"] < 0.3 and "media" not in eco.warned:
        eco.warned.add("media")
        notify("The filter media is worn out: replace it in Upkeep (Del)", log=False)
    elif EQ["media"] > 0.5:
        eco.warned.discard("media")
    if EQ["stone"] < 0.3 and "stone" not in eco.warned:
        eco.warned.add("stone")
        notify("The air stone is clogged: replace it in Upkeep (Del)", log=False)
    elif EQ["stone"] > 0.5:
        eco.warned.discard("stone")
    colony_tick()
    events_tick()
    if "led" in X["gear"]:
        for p in plants:
            if p.species in TALL_PLANTS and p.hp > 0.6 and hasattr(p, "base_h") and p.height < p.base_h * 1.8:
                scale_plant(p, 1.008)
    try:
        score = int(judge_layout()["overall"])
    except Exception:
        score = 0
    inc = max(0, (score - 35) // 10)
    P6["tour"] = inc
    if inc:
        X["cash"] += inc
        notify(f"Tank tour: visitors admired the scape and paid {inc} cash", log=False)
    if eco.day % 7 == 0:
        pool = [f for f in fishes if hasattr(f, "persona") and f.alive]
        if pool:
            best = max(pool, key=lambda f: (f.fav, len(f.bio), f.age))
            X["fow"] = best.name
            notify(f"Fish of the week: {best.name} the {nice_name(best)} ({best.persona})", log=True)
    if eco.overgrown > 0.6:    # a dense canopy shades the carpet: it fades until you prune
        for p in plants:
            if p.species in ("DwarfGrass", "Clover") and random.random() < 0.15:
                p.hp = max(0.2, p.hp - 0.1)
    line_check()
    if random.random() < 0.25 and CAT["t"] <= 0:
        CAT["t"] = 900
    save_prefs()


def fw6_update():
    pad_poll()
    if current_state != STATE_AQUARIUM or PM["on"]:
        return
    t = eco.t
    if not P6["init"]:
        P6["init"] = True
        P6["day"] = eco.day
        dash_sample()
        dash_sample()
        if X["tut_on"] and (eco.day > 5 or X["points"] > 20):
            X["tut_on"] = False      # a tank that is already running does not need the tour
    elif P6["day"] != eco.day:
        day6()
    hand_update()
    debris_update()
    if t % 30 == 0:
        debris_spawn()
        hardness_tick()
    if t % 60 == 0:
        chem6_tick()
    if "autofeed" in X["gear"] and t % (DAY_LENGTH // 2) == 0 and len(pellets) < 30:
        for _ in range(3):
            pellets.append(Flake(random.randint(80, SCREEN_WIDTH - 80), WATER_TOP))
    if CAT["t"] > 0:
        CAT["t"] -= 1
        for f in fishes:
            if hasattr(f, "fear") and f.pos.x < SCREEN_WIDTH * 0.35:
                f.fear = max(f.fear, 0.12)
    if X["tut_on"]:
        while X["tut"] < len(TUT) - 1 and TUT[X["tut"]][1] in TUTF:
            X["tut"] += 1
        if X["tut"] >= len(TUT) - 1:
            TUTP["t"] += 1
            if TUTP["t"] > 600:
                X["tut_on"] = False
                save_prefs()


# ---- the hand: lift a fish with Ctrl+drag, drip food by holding the button
def hand_event(e):
    if current_state != STATE_AQUARIUM or PM["on"] or UI21["panel"] is not None:
        return False
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and pygame.key.get_mods() & pygame.KMOD_CTRL:
        pos = pygame.Vector2(world_mouse(e.pos))
        best, bd = None, 70
        for f in fishes:
            d = f.pos.distance_to(pos)
            if d < bd and hasattr(f, "stress"):
                best, bd = f, d
        if best is not None:
            HAND["f"], HAND["held"] = best, 0
            TUTF.add("hand")
            return True
    if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and HAND["f"] is not None:
        f = HAND["f"]
        HAND["f"] = None
        f.fear = max(f.fear, 0.4)
        if HAND["held"] > 240 and hasattr(f, "bio"):
            story(f, "Was held in a hand for far too long")
        return True
    return False


def hand_update():
    f = HAND["f"]
    if f is not None:
        if not f.alive or f not in fishes:
            HAND["f"] = None
        else:
            mx, my = world_mouse(pygame.mouse.get_pos())
            f.pos.update(clamp(mx, 24, SCREEN_WIDTH - 24), clamp(my, WATER_TOP + 12, SCREEN_HEIGHT - SAND_HEIGHT - 12))
            f.vel.update(0, 0)
            HAND["held"] += 1
            if HAND["held"] % 30 == 0:
                f.stress = min(100.0, f.stress + 0.5)
    mods = pygame.key.get_mods()
    pressed = pygame.mouse.get_pressed()[0] and f is None and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT))
    ok = (pressed and UI21["panel"] is None and not show_help and not confirm_quit and not screensaver
          and DECOR_TOOLS[eco.decor_idx] == "OFF")
    HAND["drip"] = HAND["drip"] + 1 if ok else 0
    if HAND["drip"] > 25 and HAND["drip"] % 10 == 0 and len(pellets) < 40:
        drop_feed(world_mouse(pygame.mouse.get_pos()))


# ---- gamepad: the stick moves the pointer, A clicks, the other buttons press the main keys
PAD_KEYS = {1: pygame.K_ESCAPE, 2: pygame.K_F1, 3: pygame.K_DELETE, 4: pygame.K_COMMA, 5: pygame.K_SEMICOLON,
            6: pygame.K_TAB, 7: pygame.K_p}
PAD_HAT = {(-1, 0): pygame.K_LEFT, (1, 0): pygame.K_RIGHT, (0, 1): pygame.K_UP, (0, -1): pygame.K_DOWN}


def _pad_key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


def pad_poll():
    if eco.t >= PAD["next"]:
        PAD["next"] = eco.t + 180
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            n = pygame.joystick.get_count()
            if PAD["js"] is None and n > 0:
                PAD["js"] = pygame.joystick.Joystick(0)
                notify("Controller connected: stick = pointer, A = click, B = back, X = help, Y = hub", log=False)
            elif PAD["js"] is not None and n == 0:
                PAD["js"] = None
        except pygame.error:
            PAD["js"] = None
    js = PAD["js"]
    if js is None:
        return
    try:
        ax, ay = js.get_axis(0), js.get_axis(1)
        x, y = pygame.mouse.get_pos()
        if abs(ax) > 0.2 or abs(ay) > 0.2:
            pygame.mouse.set_pos((int(clamp(x + ax * 20, 0, DISPLAY_W - 1)), int(clamp(y + ay * 20, 0, DISPLAY_H - 1))))
            x, y = pygame.mouse.get_pos()
        now = {i: js.get_button(i) for i in range(min(js.get_numbuttons(), 8))}
        if js.get_numaxes() > 5:
            now["rt"] = js.get_axis(5) > 0.5
        hat = js.get_hat(0) if js.get_numhats() else (0, 0)
    except pygame.error:
        PAD["js"] = None
        return
    old = PAD["btn"]
    for i, v in now.items():
        if v and not old.get(i):
            if i == 0:
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
            elif i == "rt":
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=3))
            elif i in PAD_KEYS:
                _pad_key(PAD_KEYS[i])
        elif old.get(i) and not v and i == 0:
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))
    if hat != old.get("hat") and hat in PAD_HAT:
        _pad_key(PAD_HAT[hat])
    now["hat"] = hat
    PAD["btn"] = now


# ---- keys inside the hub
def hub_key(k):
    if k in (pygame.K_LEFT, pygame.K_RIGHT):
        HUB["tab"] = (HUB["tab"] + (1 if k == pygame.K_RIGHT else -1)) % len(HUB_TABS)
        return True
    if pygame.K_1 <= k < pygame.K_1 + len(HUB_TABS):
        HUB["tab"] = k - pygame.K_1
        return True
    tab = HUB["tab"]
    if tab == 0 and pygame.K_a <= k < pygame.K_a + len(GEAR):
        buy_gear(k - pygame.K_a)
    elif tab == 1 and k == pygame.K_n:
        line_cycle(False)
    elif tab == 1 and k == pygame.K_t:
        line_cycle(True)
    elif tab == 2:
        if k == pygame.K_r:
            EQ["media"] = 1.0
            chem_rinse()
            notify("New filter media fitted (the bacteria take a small knock)", log=True)
        elif k == pygame.K_a:
            EQ["stone"] = 1.0
            notify("New air stone fitted", log=True)
        elif k == pygame.K_h:
            EQ["drift"] = 0.0
            notify("Heater recalibrated", log=True)
        elif k == pygame.K_v:
            siphon()
        elif k == pygame.K_t:
            trim_plants()
        elif k in (pygame.K_m, pygame.K_p):
            if "mineral" not in X["gear"]:
                notify("You need the Mineral kit (Gear tab) to change hardness", log=False)
            elif k == pygame.K_m:
                CHEM["kh"] = min(25.0, CHEM["kh"] + 2.0)
                CHEM["gh"] = min(25.0, CHEM["gh"] + 2.0)
                notify("Minerals added: harder water", log=False)
            else:
                CHEM["kh"] = max(0.5, CHEM["kh"] - 1.0)
                CHEM["gh"] = max(0.5, CHEM["gh"] - 2.0)
                notify("Peat added: softer water", log=False)
    elif tab == 4 and k == pygame.K_w:
        X["wx"] = not X.get("wx", True)
        if X["wx"]:
            WX["next"] = 0.0
        save_prefs()
        notify("Live weather " + ("on (needs the real-time clock, O)" if X["wx"] else "off"), log=False)
    elif tab == 5 and k == pygame.K_t:
        X["tut_on"] = not X["tut_on"]
        if X["tut_on"]:
            X["tut"], TUTP["t"] = 0, 0
            TUTF.clear()
        save_prefs()
    return True


def _hub_gear(panel, y0):
    txt21(panel, f"Cash {X['cash']}   (earned from selling bred fish, line standards, weathering events and tank tours: last tour paid {P6['tour']})", 26, y0, "d", HUD_DIM)
    for i, (gid, name, cost, desc) in enumerate(GEAR):
        y = y0 + 40 + 56 * i
        own = gid in X["gear"]
        txt21(panel, chr(65 + i), 26, y, "t", (130, 190, 235))
        txt21(panel, name, 62, y, "h", (150, 230, 170) if own else (255, 232, 140) if X["cash"] >= cost else (200, 215, 232))
        txt21(panel, desc, 62, y + 22, "d", HUD_DIM)
        txt21(panel, "OWNED" if own else f"{cost} cash", 960, y + 4, "h", (150, 230, 170) if own else (235, 245, 255))
    txt21(panel, "Press the letter to buy", 26, y0 + 40 + 56 * len(GEAR), "d", HUD_DIM)


def _hub_line(panel, y0):
    L = line_state()
    if not L.get("cls"):
        txt21(panel, "No fish with a colour line yet.", 26, y0)
        return
    txt21(panel, f"Breeding line: {nice_name(type(next(f for f in fishes if type(f).__name__ == L['cls'])))}    standards met {L['done']}", 26, y0, "h", (255, 232, 140))
    txt21(panel, f"Breed an adult of generation {L['need']} or later whose colour line is near the target. A score of 80 meets the standard.", 26, y0 + 28, "d", HUD_DIM)
    bx, bw = 26, 700
    pygame.draw.rect(panel, (24, 44, 74), (bx, y0 + 76, bw, 18), border_radius=6)
    for v in (-1, -0.5, 0, 0.5, 1):
        pygame.draw.line(panel, (70, 100, 140), (bx + bw * (v + 1) / 2, y0 + 72), (bx + bw * (v + 1) / 2, y0 + 98), 1)
    tx = bx + bw * (L["target"] + 1) / 2
    pygame.draw.polygon(panel, (255, 220, 90), [(tx, y0 + 70), (tx - 8, y0 + 56), (tx + 8, y0 + 56)])
    txt21(panel, f"target {L['target']:+.2f}", tx + 12, y0 + 52, "h", (255, 232, 140))
    cands = line_candidates()
    for sc, f in cands[:12]:
        px = bx + bw * (clamp(f.hl, -1.0, 1.0) + 1) / 2
        pygame.draw.circle(panel, (120, 215, 160) if sc >= 80 else (120, 170, 220), (int(px), y0 + 85), 5)
    txt21(panel, "Closest fish (name, generation, score):", 26, y0 + 112, "h")
    for i, (sc, f) in enumerate(cands[:8]):
        y = y0 + 142 + 26 * i
        txt21(panel, f"{f.name}", 26, y, "d", (200, 215, 232))
        txt21(panel, f"gen {getattr(f, 'gen', 1)}   {'adult' if f.growth >= 1.0 else 'young'}", 220, y, "d", HUD_DIM)
        pygame.draw.rect(panel, (24, 44, 74), (420, y + 3, 260, 12), border_radius=4)
        pygame.draw.rect(panel, (110, 215, 140) if sc >= 80 else (120, 170, 220), (420, y + 3, max(3, int(2.6 * sc)), 12), border_radius=4)
        txt21(panel, str(sc), 690, y, "d")
    txt21(panel, "N: next species      T: new target", 26, 640 - 60, "d", HUD_DIM)


def _hub_upkeep(panel, y0):
    c = CHEM
    bar21(panel, 26, y0, 340, EQ["media"], (110, 215, 140) if EQ["media"] > 0.4 else (240, 90, 80), "Filter media", f"{int(EQ['media'] * 100)}%   R replace")
    bar21(panel, 26, y0 + 36, 340, EQ["stone"], (110, 215, 140) if EQ["stone"] > 0.4 else (240, 90, 80), "Air stone", f"{int(EQ['stone'] * 100)}%   A replace")
    bar21(panel, 26, y0 + 72, 340, (EQ["drift"] + 3) / 6.0, (110, 215, 140) if abs(EQ["drift"]) < 1.2 else (240, 200, 90), "Heater drift", f"{EQ['drift']:+.1f} C   H recalibrate")
    bar21(panel, 26, y0 + 108, 340, DEBS[0] / 60.0, (110, 215, 140) if DEBS[0] < 25 else (240, 200, 90), "Mulm on the sand", f"{DEBS[0]}   V siphon")
    txt21(panel, f"Canopy {int(eco.overgrown * 100)}% overgrown   T trim all plants", 400, y0 + 4, "h", (255, 232, 140) if eco.overgrown > 0.5 else (200, 215, 232))
    bar21(panel, 26, y0 + 160, 340, c["kh"] / 20.0, (110, 215, 140) if 3 <= c["kh"] <= 10 else (240, 200, 90), "Carbonate KH", f"{c['kh']:.1f}")
    bar21(panel, 26, y0 + 196, 340, c["gh"] / 20.0, (110, 215, 140) if 4 <= c["gh"] <= 12 else (240, 200, 90), "General GH", f"{c['gh']:.1f}   M harder, P softer")
    soft = [f for f in fishes if hardness_off(f) > 1.5]
    txt21(panel, f"{len(soft)} fish are outside their hardness range" if soft else "Every fish is happy with the hardness", 26, y0 + 240, "h", (255, 160, 130) if soft else (150, 230, 170))
    txt21(panel, "Soft-water fish: tetras, rummynose, otos, corydoras.  Hard-water fish: guppies, killifish, cichlids.  Water changes pull GH and KH toward the tap (8 / 6).", 26, y0 + 268, "d", HUD_DIM)
    txt21(panel, "Heater (Y), filter sponge (F) and the glass (C) are still done from the tank.  M and P need the Mineral kit.", 26, y0 + 292, "d", HUD_DIM)


def _hub_history(panel, y0):
    spec = [("pop", (120, 200, 255), "Fish", "{:.0f}"), ("water", (110, 215, 140), "Water quality", "{:.0f}"),
            ("no3", (240, 200, 90), "Nitrate", "{:.0f}"), ("ph", (200, 150, 255), "pH", "{:.2f}"),
            ("gh", (255, 150, 150), "GH", "{:.1f}"), ("points", (255, 232, 140), "Points", "{:.0f}")]
    for i, (k, col, title, fmt) in enumerate(spec):
        chart21(panel, (26 + (i % 3) * 360, y0 + (i // 3) * 220, 340, 200), DASH[k], col, title, fmt)
    txt21(panel, "History covers this session and fills in about every ten seconds.", 26, y0 + 446, "d", HUD_DIM)


def live_weather_text():
    if not eco.realtime:
        return "turn on the real-time clock (O) to copy the weather outside"
    if not X.get("wx", True):
        return "off  (W switches it on)"
    if wx_ok():
        return f"{WX['place'] or 'your area'}: {WX['label']}, {WX['temp']:.0f}C, cloud {int(WX['cloud'] * 100)}%   (W switches it off)"
    return "offline: " + WX["err"] if WX["err"] and not WX["busy"] else "looking up the weather..."


def _hub_life(panel, y0):
    snails = sum(1 for c in crawlers if isinstance(c, (MysterySnail, Ramshorn)))
    rows = [("Snails", f"{snails}   (they boom when there is spare food)"), ("Shrimp", f"{len(shimps)}   (they breed in moss and carpets)"),
            ("Algae eaters", f"{sum(1 for f in fishes if isinstance(f, (Otocinclus, Pleco)))} fish"),
            ("Canopy", f"{int(eco.overgrown * 100)}% overgrown   (trim with D > TRIM)"),
            ("Weather", (f"{EV['name']}  until day {EV['until']}" if EV["name"] else "quiet")),
            ("Weathered", f"{X['evok']} events survived"), ("Fish of the week", X["fow"] or "chosen every 7th day"),
            ("Cat", "watching the tank tonight" if CAT["t"] > 0 else "asleep"),
            ("Live weather", live_weather_text())]
    for i, (a, b) in enumerate(rows):
        txt21(panel, a, 26, y0 + 34 * i, "h", (255, 232, 140))
        txt21(panel, b, 260, y0 + 34 * i + 2, "d")
    txt21(panel, "Events follow the season: spawning in spring, heat in summer, leaf fall in autumn, cold snaps in winter.", 26, y0 + 34 * len(rows) + 10, "d", HUD_DIM)


def _hub_guide(panel, y0):
    txt21(panel, "Tour: " + ("ON" if X["tut_on"] else "OFF") + "     T switches it " + ("off" if X["tut_on"] else "on and restarts it"), 26, y0, "h", (150, 230, 170) if X["tut_on"] else (200, 215, 232))
    for i, (text, key) in enumerate(TUT):
        done = key is None and not X["tut_on"] or (key is not None and key in TUTF) or (X["tut_on"] and i < X["tut"])
        txt21(panel, ("[x] " if done else "[ ] ") + text, 26, y0 + 40 + 30 * i, "d", (150, 230, 170) if done else (200, 215, 232))
    txt21(panel, "Controller: stick moves the pointer, A clicks, B back, X help, Y hub, LB shop, RB test kit, D-pad moves in panels, right trigger taps the glass.", 26, y0 + 40 + 30 * len(TUT) + 12, "d", HUD_DIM)
    txt21(panel, "Touch screens work as a mouse: tap to feed, long-press for the glass tap needs a right button, so use a controller or mouse for that.", 26, y0 + 40 + 30 * len(TUT) + 36, "d", HUD_DIM)


def draw_hub(surface):
    panel = begin_panel(1120, 640, f"Tank hub     cash {X['cash']}     points {X['points']}")
    x = 26
    for i, name in enumerate(HUB_TABS):
        on = i == HUB["tab"]
        r = pygame.Rect(x, 56, 150, 28)
        pygame.draw.rect(panel, (40, 90, 150) if on else (20, 40, 70), r, border_radius=8)
        txt21(panel, f"{i + 1} {name}", r.x + 14, r.y + 4, "h", (255, 255, 255) if on else (150, 175, 205))
        x += 160
    (_hub_gear, _hub_line, _hub_upkeep, _hub_history, _hub_life, _hub_guide)[HUB["tab"]](panel, 104)
    end_panel(surface, panel, "Left/Right or 1-6: tabs   Esc: close   (Del opens the hub)")


# ---- the world overlay: light shafts, debris, the moth, sleepers, the cat
SHAFT = {"surf": None}
TXT6 = {}


def _shaft_surface():
    h = int(SCREEN_HEIGHT * 0.85)
    sf = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
    for x0, w in ((0.10, 70), (0.30, 120), (0.55, 90), (0.78, 60)):
        for k, a in ((2.0, 10), (1.4, 12), (0.9, 14)):
            top = int(SCREEN_WIDTH * x0)
            ww = int(w * k)
            pygame.draw.polygon(sf, (190, 225, 255, a), [(top - ww // 2, 0), (top + ww // 2, 0), (top + ww // 2 + int(h * 0.3), h), (top - ww // 2 + int(h * 0.3), h)])
    return sf


def draw_world6(surface):
    if QUALITY[0] != "LOW":
        a = eco.daylight * (1.0 - eco.night) * (0.0 if (eco.lights == "OFF" or eco.power) else 1.0)
        if a > 0.08:
            if SHAFT["surf"] is None:
                SHAFT["surf"] = _shaft_surface()
            sf = SHAFT["surf"]
            sf.set_alpha(int(255 * a * (0.6 + 0.4 * math.sin(eco.t * 0.008))))
            surface.blit(sf, (int((eco.clock - 0.5) * SCREEN_WIDTH * 0.35), WATER_TOP))
    for d in DEB:
        pygame.draw.circle(surface, (140, 124, 98), (int(d[0]), int(d[1])), 2 if d[4] > 3 else 1)
    n = min(DEBS[0], 60)
    for i in range(n):
        x = 30 + (i * 97 + 13 * (i % 7)) % (SCREEN_WIDTH - 60)
        pygame.draw.circle(surface, (112, 98, 76), (x, ground_y(x) - 1), 2)
    if eco.night > 0.45 and not PM["on"]:
        mx = SCREEN_WIDTH * 0.5 + math.sin(eco.t * 0.011) * SCREEN_WIDTH * 0.3
        my = WATER_TOP - 22 + math.sin(eco.t * 0.07) * 9
        wing = 2 + abs(math.sin(eco.t * 0.5)) * 6
        pygame.draw.ellipse(surface, (232, 228, 205), (mx - wing - 2, my - 3, wing, 6))
        pygame.draw.ellipse(surface, (232, 228, 205), (mx + 2, my - 3, wing, 6))
        pygame.draw.circle(surface, (120, 110, 90), (int(mx), int(my)), 2)
        if eco.t % 240 == 0:
            ripples.append([pygame.Vector2(mx, WATER_TOP + 2), 2.0, 30])
    if eco.night > 0.6 and not PM["on"]:
        z = TXT6.get("z")
        if z is None:
            z = TXT6["z"] = f21("s").render("z", True, (200, 220, 255))
        for f in fishes:
            if getattr(f, "sleepy", 0) > 0.55:
                surface.blit(z, (int(f.pos.x) + 10, int(f.pos.y) - 22 - (eco.t // 2 + f.id) % 24))


def draw_cat(surface):
    t = CAT["t"]
    if t <= 0 or PM["on"] or screensaver:
        return
    up = min(1.0, (900 - t) / 90.0, t / 90.0)
    dy = int((1.0 - up) * 220)
    base = SCREEN_HEIGHT - 10 + dy
    ink = (9, 10, 16)
    pygame.draw.ellipse(surface, ink, (-40, base - 90, 330, 200))
    pygame.draw.circle(surface, ink, (130, base - 110), 52)
    pygame.draw.polygon(surface, ink, [(90, base - 145), (96, base - 205), (128, base - 156)])
    pygame.draw.polygon(surface, ink, [(138, base - 156), (170, base - 205), (176, base - 140)])
    blink = (t // 7) % 40 == 0
    for ex in (112, 150):
        if blink:
            pygame.draw.line(surface, (230, 200, 90), (ex - 7, base - 112), (ex + 7, base - 112), 2)
        else:
            pygame.draw.ellipse(surface, (236, 206, 80), (ex - 8, base - 124, 16, 20))
            pygame.draw.ellipse(surface, ink, (ex - 2, base - 122, 4, 16))
    tail = [(250, base - 30 + int(math.sin(eco.t * 0.05 + i * 0.7) * 10), ) for i in range(1)]
    pygame.draw.lines(surface, ink, False, [(260 + i * 14, base - 20 - i * 8 + int(math.sin(eco.t * 0.06 + i * 0.6) * 10)) for i in range(6)], 12)


def draw_hud6(surface):
    if screensaver or current_state != STATE_AQUARIUM:
        return
    draw_cat(surface)
    if X["tut_on"] and UI21["panel"] is None and not PM["on"]:
        i = min(X["tut"], len(TUT) - 1)
        font = f21("h")
        img = font.render(f"Tour {i + 1}/{len(TUT)}:  {TUT[i][0]}", True, (235, 245, 255))
        box = pygame.Rect(0, 0, img.get_width() + 40, 40)
        box.midtop = (SCREEN_WIDTH // 2, 14)
        pygame.draw.rect(surface, (8, 20, 40), box, border_radius=10)
        pygame.draw.rect(surface, (120, 190, 230), box, 2, border_radius=10)
        surface.blit(img, img.get_rect(center=box.center))
    if HAND["f"] is not None:
        f = HAND["f"]
        pygame.draw.circle(surface, (255, 235, 160), (int(f.pos.x), int(f.pos.y)), int(34 * f.z) + 6, 2)
    if UI21["panel"] is not None or not eco.show_hud or PM["on"] or show_help or confirm_quit:
        return
    mp = pygame.Vector2(world_mouse(pygame.mouse.get_pos()))
    best, bd = None, 9999
    for f in fishes:
        if hasattr(f, "persona"):
            d = f.pos.distance_to(mp) - 30 * f.z
            if d < 14 and d < bd:
                best, bd = f, d
    if best is None:
        return
    f = best
    lines = [(f"{f.name} the {nice_name(f)}" + ("   FISH OF THE WEEK" if X["fow"] == f.name else ""), (255, 232, 140)),
             (f"{f.persona}: {PERSONA_TXT[f.persona]}", (210, 225, 240))]
    if f.friend is not None:
        lines.append((f"friend: {f.friend.name}", (130, 235, 160)))
    if f.rival is not None:
        lines.append((f"rival: {f.rival.name}", (255, 130, 120)))
    off = hardness_off(f)
    if off > 1.5:
        lines.append((f"unhappy with the hardness (GH {CHEM['gh']:.0f})", (255, 180, 130)))
    if f.sick:
        lines.append((DISEASES.get(getattr(f, "disease", "ich"), "sick"), (255, 160, 130)))
    font = hud_font()
    w = max(font.size(t)[0] for t, _ in lines) + 20
    box = make_panel(w, 12 + 17 * len(lines))
    for i, (txt, col) in enumerate(lines):
        box.blit(font.render(txt, True, col), (10, 6 + 17 * i))
    x = int(clamp(mp.x + 16, 4, SCREEN_WIDTH - w - 4))
    y = int(clamp(mp.y + 16, 4, SCREEN_HEIGHT - box.get_height() - 4))
    surface.blit(box, (x, y))


# ---------------------------------------------------------------- 20: dashboard
def dash_sample():
    DASH["pop"].append(len(fishes))
    DASH["water"].append(eco.water)
    DASH["births"].append(eco.births)
    DASH["deaths"].append(stats.get("deaths", 0))
    DASH["no3"].append(CHEM["no3"])
    DASH["temp"].append(eco.temp)
    DASH["ph"].append(CHEM["ph"])
    DASH["gh"].append(CHEM["gh"])
    DASH["kh"].append(CHEM["kh"])
    DASH["points"].append(X["points"])
    DASH["cash"].append(X["cash"])
    WEEK["water"].append(eco.water)


def week_tick():
    if "init" not in WEEK:
        WEEK.update(init=True, day=eco.day, births=eco.births, deaths=stats.get("deaths", 0), reqs=X["reqs"])
    if eco.day - WEEK["day"] < 7:
        return
    w = WEEK["water"]
    summary = {"week": len(X["weeks"]) + 1, "fish": len(fishes), "births": eco.births - WEEK["births"],
               "deaths": stats.get("deaths", 0) - WEEK["deaths"], "reqs": X["reqs"] - WEEK["reqs"],
               "water": int(sum(w) / len(w)) if w else int(eco.water), "day": eco.day}
    X["weeks"].append(summary)
    del X["weeks"][:-8]
    WEEK.update(day=eco.day, births=eco.births, deaths=stats.get("deaths", 0), reqs=X["reqs"], water=[])
    notify(f"Week {summary['week']} summary is ready (press /)", log=True)
    save_prefs()


# ---------------------------------------------------------------- per-frame driver
def fw21_update():
    t = eco.t
    if FERT["t"] > 0:
        FERT["t"] -= 1
    if t % 60 == 0:
        chem_tick()
        algae_tick()
        shop_tick()
    if t % 30 == 0:
        sound_tick()
    if t % 300 == 0 and (FERT["t"] > 0 or "co2" in X["owned"]):
        k = 1.0 + (0.03 if FERT["t"] > 0 else 0.0) + (0.02 if "co2" in X["owned"] else 0.0)
        for p in plants:
            if p.species in TALL_PLANTS:
                if not hasattr(p, "base_h"):
                    p.base_h = p.height
                if p.height < p.base_h * 1.8:
                    scale_plant(p, k)
    if t % 600 == 0:
        dash_sample()
        week_tick()
        for f in fishes:
            if getattr(f, "fav", False):
                if f.fav_cd <= 0 and (f.sick or f.hunger > 85):
                    notify(f"* {f.name} " + ("is sick" if f.sick else "is very hungry"), log=False)
                    f.fav_cd = 3000
                else:
                    f.fav_cd -= 600
    request_tick()
    raid_tick()
    fw6_update()
    if t % 600 == 0:
        plant_care()
        chore_tick()
        chal_tick()
        check_goals()


def save21():
    return {"chem": dict(CHEM), "hair": [round(h, 3) for h in HAIR], "dia": DIA[0], "fert": FERT["t"],
            "req": REQ["cur"], "req_next": REQ["next"],
            "eq": dict(EQ), "ev": dict(EV), "debs": DEBS[0]}


def load21(d):
    if not isinstance(d, dict):
        return
    try:
        c = d.get("chem")
        if isinstance(c, dict):
            for k in CHEM:
                v = c.get(k)
                if isinstance(CHEM[k], bool):
                    if isinstance(v, bool):
                        CHEM[k] = v
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    CHEM[k] = type(CHEM[k])(v)
        h = d.get("hair")
        if isinstance(h, list) and len(h) == GLASS_COLS:
            HAIR[:] = [clamp(float(v)) for v in h]
        DIA[0] = clamp(float(d.get("dia", 0.0)))
        FERT["t"] = int(d.get("fert", 0))
        r = d.get("req")
        REQ["cur"] = r if isinstance(r, dict) and "cls" in r and "text" in r else None
        if REQ["cur"]:
            REQ["cur"]["swatch"] = tuple(REQ["cur"].get("swatch", (150, 190, 220)))
        REQ["next"] = int(d.get("req_next", 2))
        for src, dst in ((d.get("eq"), EQ), (d.get("ev"), EV)):
            if isinstance(src, dict):
                for k in dst:
                    v = src.get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and isinstance(dst[k], (int, float)):
                        dst[k] = int(v) if k in ("sd", "until", "start", "b0") else float(v)
                    elif isinstance(v, str) or v is None and k == "name":
                        dst[k] = v
        DEBS[0] = int(clamp(float(d.get("debs", 0)), 0, 60))
    except (TypeError, ValueError):
        pass


# ---------------------------------------------------------------- events
def fw21_event(e):
    """Returns True when the event was used here (rename typing, panel keys, the new hotkeys)."""
    u = UI21
    if e.type == pygame.KEYDOWN:
        TUTF.add(e.key)
    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        TUTF.add("click")
    if hand_event(e):
        return True
    if e.type == pygame.MOUSEBUTTONDOWN:
        return u["panel"] is not None or u["rename"] is not None
    if e.type != pygame.KEYDOWN:
        return False
    k = e.key
    if u["rename"] is not None:
        f = eco.selected
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            nm = u["rename"].strip()
            if nm and f is not None:
                story(f, f"Renamed from {f.name} to {nm}")
                f.name = nm
                notify(f"Renamed to {nm}", log=False)
            u["rename"] = None
        elif k == pygame.K_ESCAPE:
            u["rename"] = None
        elif k == pygame.K_BACKSPACE:
            u["rename"] = u["rename"][:-1]
        elif getattr(e, "unicode", "") and e.unicode.isprintable() and len(u["rename"]) < 14:
            u["rename"] += e.unicode
        return True
    p = u["panel"]
    if p is not None:
        if k == pygame.K_ESCAPE:
            u["panel"] = None
            return True
        if k in (pygame.K_g, pygame.K_TAB, pygame.K_F1):
            u["panel"] = None
            return False
        if p == "settings" and settings_key(k):
            return True
        if p == "hub":
            return hub_key(k)
        if p == "sell" and pygame.K_1 <= k <= pygame.K_9:
            sell_fish(k - pygame.K_1)
            return True
        if p == "care" and pygame.K_1 <= k <= pygame.K_4:
            if X["chal"] and X["chal"].get("id") == CHALLENGES[k - pygame.K_1][0]:
                X["chal"] = {}
                notify("Challenge abandoned", log=False)
            else:
                chal_start(k - pygame.K_1)
            return True
        if p == "shop" and pygame.K_1 <= k <= pygame.K_7:
            buy_item(k - pygame.K_1)
            return True
        if p == "scape":
            if pygame.K_1 <= k <= pygame.K_9:
                sc = all_scapes()
                if k - pygame.K_1 < len(sc):
                    apply_scape(sc[k - pygame.K_1])
                return True
            if k == pygame.K_n:
                save_scape()
                return True
        if p == "album" and k == pygame.K_b:
            UI21["best"] = not UI21.get("best", False)
            UI21["page"] = 0
            return True
        if p == "album" and k in (pygame.K_LEFT, pygame.K_RIGHT):
            u["page"] = max(0, u["page"] + (1 if k == pygame.K_RIGHT else -1))
            return True
        if p == "story" and k == pygame.K_m:
            u["mem"] = not u["mem"]
            return True
        if p == "show" and k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            run_show()
            return True
        if p == "ba" and k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            ba_save()
            return True
    if k == pygame.K_F2:
        u["web"] = not u["web"]
        notify("Social web: " + ("ON (green friends, red rivals)" if u["web"] else "OFF"), log=False)
    elif k == pygame.K_F4:
        if p == "show":
            u["panel"] = None
        elif run_show() or SHOWR["rows"]:
            set_panel("show")
    elif k == pygame.K_F6:
        f = eco.selected
        if f is not None and hasattr(f, "persona"):
            u["rename"] = ""
        else:
            notify("Select a fish first (Shift-click), then press F6 to rename it", log=False)
    elif k == pygame.K_F7:
        f = eco.selected
        if f is not None and hasattr(f, "persona"):
            f.fav = not f.fav
            notify(f"{f.name} {'is now a favourite' if f.fav else 'is no longer a favourite'}", log=False)
        else:
            notify("Select a fish first (Shift-click), then press F7 to star it", log=False)
    elif k == pygame.K_F8:
        set_panel("story")
    elif k == pygame.K_COMMA:
        set_panel("shop")
    elif k == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
        SET["mode"], SET["slots"] = None, None
        set_panel("settings")
    elif k == pygame.K_DELETE:
        set_panel("hub")
    elif k == pygame.K_7:
        set_panel("sell")
    elif k == pygame.K_8:
        set_panel("care")
    elif k == pygame.K_PERIOD:
        set_panel("scape")
    elif k == pygame.K_SLASH:
        set_panel("dash")
    elif k == pygame.K_SEMICOLON:
        set_panel("test")
    elif k == pygame.K_QUOTE:
        dose_fert()
    elif k == pygame.K_BACKQUOTE:
        cycle_sound()
    elif k == pygame.K_PAGEUP:
        set_panel("album")
    elif k == pygame.K_F12:
        rec_toggle()
    else:
        return False
    return True


# ---------------------------------------------------------------- drawing
def draw_world21(surface):
    """Under the glass: sick-fish marks, favourite stars, the social web."""
    for f in fishes:
        if not hasattr(f, "persona"):
            continue
        d = getattr(f, "disease", "ich")
        x, y = int(f.pos.x), int(f.pos.y)
        if f.sick and d == "finrot":
            ang = math.atan2(f.vel.y, f.vel.x) + math.pi if f.vel.length_squared() > 0.01 else math.pi
            for k in range(4):
                a = ang + (k - 1.5) * 0.35
                r0, r1 = 24 * f.z, 36 * f.z
                pygame.draw.line(surface, (150, 40, 44), (x + math.cos(a) * r0, y + math.sin(a) * r0 * 0.6),
                                 (x + math.cos(a) * r1, y + math.sin(a) * r1 * 0.6), 2)
        elif f.sick and d == "swim" and eco.t % 90 < 6:
            pygame.draw.circle(surface, (200, 230, 255), (x + 10, y - int(30 * f.z)), 3, 1)
        if f.fav:
            sx, sy = x, y - int(38 * max(f.z, 0.5)) - 22
            pts = []
            for i in range(10):
                r = 7 if i % 2 == 0 else 3
                a = -math.pi / 2 + i * math.pi / 5
                pts.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
            pygame.draw.polygon(surface, (255, 220, 90), pts)
    if UI21["web"]:
        for f in fishes:
            if not hasattr(f, "persona"):
                continue
            if f.friend is not None and f.friend.alive and id(f) < id(f.friend):
                pygame.draw.line(surface, (110, 235, 150), f.pos, f.friend.pos, 2)
            if f.rival is not None and f.rival.alive and id(f) < id(f.rival):
                pygame.draw.line(surface, (255, 100, 90), f.pos, f.rival.pos, 2)
            if f.mourn > 0:
                pygame.draw.circle(surface, (150, 160, 230), (int(f.pos.x), int(f.pos.y)), int(30 * f.z) + 6, 1)
            if f.friend is not None or f.rival is not None or f.fav or f is eco.selected:
                lab = f21("s").render(f"{f.name} - {f.persona}", True, (235, 245, 255))
                surface.blit(lab, lab.get_rect(midtop=(int(f.pos.x), int(f.pos.y + 26 * max(f.z, 0.5)))))


def draw_card21(surface):
    f = eco.selected
    if f is None or not eco.show_hud or not hasattr(f, "persona") or isinstance(f, Predator):
        return
    lines = [(("* " if f.fav else "") + f.persona.upper() + ": " + PERSONA_TXT[f.persona], (255, 232, 140))]
    if f.friend is not None:
        lines.append((f"friend: {f.friend.name}", (130, 235, 160)))
    if f.rival is not None:
        lines.append((f"rival: {f.rival.name}", (255, 130, 120)))
    if f.mourn > 0:
        lines.append(("grieving a lost friend", (170, 180, 240)))
    if f.life_frac() > 0.8:
        lines.append(("elder: slower, paler", (200, 200, 205)))
    if f.sick:
        lines.append((DISEASES.get(getattr(f, "disease", "ich"), "sick"), (255, 160, 130)))
    g = gene_text(f)
    if g:
        lines.append((g, HUD_DIM))
    lines.append(("F6 rename  F7 star  F8 story", HUD_DIM))
    font = hud_font()
    panel = make_panel(250, 14 + 16 * len(lines))
    for i, (txt, col) in enumerate(lines):
        panel.blit(font.render(txt[:40], True, col), (10, 7 + 16 * i))
    surface.blit(panel, (12, 188 + 246 + 6))


def draw_hud21(surface):
    if screensaver:
        return
    if UI21["rename"] is not None and eco.selected is not None:
        s = f21("h").render(f"Rename {eco.selected.name}:  {UI21['rename']}_", True, (255, 240, 150))
        box = pygame.Rect(0, 0, max(380, s.get_width() + 40), 44)
        box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120)
        pygame.draw.rect(surface, (8, 20, 40), box, border_radius=10)
        pygame.draw.rect(surface, (120, 190, 230), box, 2, border_radius=10)
        surface.blit(s, s.get_rect(center=box.center))
    if REC["on"] and eco.t % 60 < 40:
        pygame.draw.circle(surface, (235, 50, 50), (SCREEN_WIDTH - 26, 26), 7)
        surface.blit(hud_font().render(f"REC {len(REC['frames'])}", True, (255, 200, 200)), (SCREEN_WIDTH - 90, 20))
    if not eco.show_hud:
        return
    r = REQ["cur"]
    key = (X["points"], r["text"] if r else None, max(0, r["due"] - eco.day) if r else 0)
    cache = F21.get("hud")
    if cache is None or cache[0] != key:
        font = hud_font()
        h = 52 if r else 24
        panel = make_panel(430, h)
        panel.blit(font.render(f"POINTS {X['points']}   (, shop  / dashboard  ; test kit)", True, (255, 232, 140)), (10, 5))
        if r:
            pygame.draw.circle(panel, r.get("swatch", (150, 190, 220)), (20, 36), 7)
            panel.blit(font.render(("REQUEST: " + r["text"])[:56], True, (210, 225, 240)), (34, 22))
            panel.blit(font.render(f"+{r['reward']} pts   {key[2]} days left", True, HUD_DIM), (34, 36))
        cache = F21["hud"] = (key, panel)
    surface.blit(cache[1], (14, SCREEN_HEIGHT - 30 - cache[1].get_height()))


def bar21(panel, x, y, w, frac, col, label, val):
    txt21(panel, label, x, y - 2, "h")
    pygame.draw.rect(panel, (24, 44, 74), (x + 150, y, w, 14), border_radius=5)
    pygame.draw.rect(panel, col, (x + 150, y, max(3, int(w * clamp(frac))), 14), border_radius=5)
    txt21(panel, val, x + 160 + w, y - 1, "d", (210, 225, 240))


def chart21(panel, rect, data, color, title, fmt="{:.0f}"):
    x, y, w, h = rect
    pygame.draw.rect(panel, (14, 34, 60), rect, border_radius=6)
    txt21(panel, title, x + 8, y + 4, "d", (200, 215, 232))
    d = list(data)
    if len(d) >= 2:
        lo, hi = min(d), max(d)
        if hi - lo < 1e-6:
            hi = lo + 1.0
        pts = [(x + 8 + (w - 16) * i / (len(d) - 1), y + h - 10 - (h - 44) * (v - lo) / (hi - lo)) for i, v in enumerate(d)]
        pygame.draw.lines(panel, color, False, pts, 2)
        txt21(panel, fmt.format(d[-1]), x + w - 70, y + 4, "h", color)
        txt21(panel, f"{fmt.format(lo)} - {fmt.format(hi)}", x + 8, y + h - 18, "s", (130, 155, 185))
    else:
        txt21(panel, "collecting data...", x + 8, y + 40, "s", (130, 155, 185))


def draw_panel21(surface):
    p = UI21["panel"]
    if p is None:
        return
    if p == "ba":
        draw_ba(surface)
        return
    if p == "judge":
        draw_judge(surface)
        return
    if p == "story":
        f = eco.selected if (eco.selected is not None and hasattr(eco.selected, "persona")) else None
        if f is not None and not UI21["mem"]:
            panel = begin_panel(760, 130 + 24 * max(1, len(f.bio)), f"{f.name} the {nice_name(f)}")
            txt21(panel, f"{f.persona}  -  {PERSONA_TXT[f.persona]}  -  {f.life_stage()}  -  born day {f.born_day}", 26, 56)
            g = gene_text(f)
            if g:
                txt21(panel, g, 26, 76, "d", HUD_DIM)
            for i, (day, text) in enumerate(f.bio):
                txt21(panel, f"Day {day}", 26, 104 + 24 * i, "h", (255, 232, 140))
                txt21(panel, text, 110, 106 + 24 * i)
            end_panel(surface, panel, "Esc to close   M: memorial of lost fish")
        else:
            mem = X["memorial"][-14:][::-1]
            panel = begin_panel(860, 110 + 30 * max(1, len(mem)), f"Memorial   {len(X['memorial'])} remembered")
            if not mem:
                txt21(panel, "Nobody has been lost yet.", 26, 70)
            for i, m in enumerate(mem):
                y = 70 + 30 * i
                txt21(panel, f"{m['name']} the {m['cls']}", 26, y, "h", (255, 232, 140))
                txt21(panel, f"lived {m['days']} days, {m['persona']}, gen {m['gen']}  -  {m['cause']} (day {m['day']})", 300, y + 2)
            end_panel(surface, panel, "Esc to close   (select a fish and press F8 for its story)")
    elif p in ("sell", "care"):
        draw_care_panels(surface)
    elif p == "settings":
        draw_settings(surface)
    elif p == "hub":
        draw_hub(surface)
    elif p == "shop":
        panel = begin_panel(820, 120 + 52 * len(SHOP), f"Equipment shop   {X['points']} points")
        for i, (iid, name, cost, desc) in enumerate(SHOP):
            y = 70 + 52 * i
            own = iid != "oto" and iid in X["owned"]
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, name, 62, y, "h", (150, 230, 170) if own else (255, 232, 140) if X["points"] >= cost else (200, 215, 232))
            txt21(panel, desc, 62, y + 22, "d", HUD_DIM)
            txt21(panel, "OWNED" if own else f"{cost} pts", 700, y + 4, "h", (150, 230, 170) if own else (235, 245, 255))
        end_panel(surface, panel, "Press 1-7 to buy   Esc to close   (earn points from requests, shows, goals and the cycle)")
    elif p == "scape":
        sc = all_scapes()
        panel = begin_panel(720, 130 + 36 * len(sc), "Aquascapes")
        for i, s in enumerate(sc):
            y = 70 + 36 * i
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, s["name"], 62, y + 2, "h", (255, 232, 140))
            txt21(panel, f"{len(s['layout']['items']) if isinstance(s.get('layout'), dict) else len(s['placed'])} pieces" + ("  (yours)" if i >= len(SCAPE_BUILTIN) else "  (preset)"), 260, y + 4, "d", HUD_DIM)
        end_panel(surface, panel, "1-9: replace the layout (your fish stay)   N: save the current layout   Esc: close")
    elif p == "test":
        c = CHEM
        panel = begin_panel(760, 540, "Water test kit")
        rows = [("Ammonia NH3", c["nh3"] / 2.0, c["nh3"] < 0.25, c["nh3"] < 0.6, f"{c['nh3']:.2f} ppm"),
                ("Nitrite NO2", c["no2"] / 2.0, c["no2"] < 0.25, c["no2"] < 0.8, f"{c['no2']:.2f} ppm"),
                ("Nitrate NO3", c["no3"] / 120.0, c["no3"] < 30, c["no3"] < 60, f"{c['no3']:.0f} ppm"),
                ("pH", (c["ph"] - 5.5) / 3.0, 6.6 <= c["ph"] <= 7.6, 6.2 <= c["ph"] <= 8.0, f"{c['ph']:.1f}"),
                ("Carbonate KH", c["kh"] / 20.0, 3 <= c["kh"] <= 10, 1.5 <= c["kh"] <= 14, f"{c['kh']:.1f} dKH"),
                ("General GH", c["gh"] / 20.0, 4 <= c["gh"] <= 12, 2 <= c["gh"] <= 16, f"{c['gh']:.1f} dGH")]
        for i, (lab, fr, good, ok, val) in enumerate(rows):
            bar21(panel, 26, 76 + 34 * i, 340, fr, (110, 215, 140) if good else (240, 200, 90) if ok else (240, 90, 80), lab, val)
        y = 294
        bar21(panel, 26, y, 340, c["b1"], (120, 190, 235), "Bacteria: ammonia", f"{int(c['b1'] * 100)}%")
        bar21(panel, 26, y + 34, 340, c["b2"], (120, 190, 235), "Bacteria: nitrite", f"{int(c['b2'] * 100)}%")
        status = "CYCLED" if c["done"] else "CYCLING: keep ammonia low with water changes (W) while the colonies grow"
        txt21(panel, status, 26, y + 72, "h", (150, 230, 170) if c["done"] else (255, 200, 120))
        hair = sum(HAIR) / GLASS_COLS
        glass = sum(eco.glass) / GLASS_COLS
        txt21(panel, f"Algae   hair {int(hair * 100)}%    diatom film {int(DIA[0] * 100)}%    glass film {int(glass * 100)}%", 26, y + 108, "h")
        txt21(panel, "Hair algae: shrimp, snails, otos, lights off, less nitrate.   Diatoms: they fade as the tank matures.   Glass: C to wipe.", 26, y + 132, "d", HUD_DIM)
        txt21(panel, "Fertiliser (')" + (f" active for {FERT['t'] // 60}s: plants grow, algae too" if FERT["t"] > 0 else " is not in the water")
              + "      CO2 diffuser: " + ("fitted" if "co2" in X["owned"] else "not fitted"), 26, y + 158, "d", HUD_DIM)
        end_panel(surface, panel, "Esc to close   (set \"new_tank\": true in aquarium_config.json to start with an uncycled tank)")
    elif p == "dash":
        panel = begin_panel(980, 640, "Tank dashboard")
        cw, ch = 460, 150
        specs = [("pop", (120, 200, 255), "Fish in the tank"), ("water", (110, 215, 140), "Water quality"),
                 ("births", (255, 200, 110), "Births (total)"), ("deaths", (255, 120, 110), "Deaths (total)"),
                 ("no3", (190, 150, 240), "Nitrate ppm"), ("temp", (255, 160, 90), "Temperature C")]
        for i, (k, col, title) in enumerate(specs):
            chart21(panel, (26 + (i % 2) * (cw + 20), 64 + (i // 2) * (ch + 12), cw, ch), DASH[k], col, title,
                    "{:.1f}" if k == "temp" else "{:.0f}")
        wk = X["weeks"][-1] if X["weeks"] else None
        if wk:
            txt21(panel, f"Week {wk['week']} summary (day {wk['day']}):  {wk['fish']} fish,  {wk['births']} born,  {wk['deaths']} lost,  "
                         f"water {wk['water']}%,  {wk['reqs']} requests filled", 26, 560, "h", (255, 232, 140))
        else:
            txt21(panel, "The first weekly summary appears after seven tank days.", 26, 560, "d", HUD_DIM)
        end_panel(surface, panel, "Esc to close   (a sample every ten seconds)")
    elif p == "album":
        items = album_load()[::-1]
        if UI21.get("best"):
            items = sorted(items, key=lambda a: -a.get("score", 0))
        per = 6
        pages = max(1, (len(items) + per - 1) // per)
        UI21["page"] = min(UI21["page"], pages - 1)
        panel = begin_panel(1040, 600, f"Photo album   {len(items)} photos   page {UI21['page'] + 1}/{pages}" + ("   BEST OF" if UI21.get("best") else ""))
        if not items:
            txt21(panel, "Press P to take a photo; it will be filed here with the day and the tank stats.", 26, 80)
        for i, a in enumerate(items[UI21["page"] * per:(UI21["page"] + 1) * per]):
            x, y = 26 + (i % 3) * 330, 70 + (i // 3) * 250
            th = ALB_THUMBS.get(a["file"])
            if th is None:
                try:
                    th = pygame.transform.smoothscale(pygame.image.load(a["file"]).convert(), (300, 169))
                except (pygame.error, OSError, FileNotFoundError):
                    th = pygame.Surface((300, 169))
                    th.fill((30, 40, 60))
                if len(ALB_THUMBS) > 24:
                    ALB_THUMBS.clear()
                ALB_THUMBS[a["file"]] = th
            panel.blit(th, (x, y))
            txt21(panel, f"Day {a.get('day', '?')}  {a.get('season', '')}  -  {a.get('when', '')}", x, y + 174, "h", (255, 232, 140))
            txt21(panel, f"{a.get('fish', '?')} fish, water {a.get('water', '?')}%   scape score {a.get('score', '?')}", x, y + 196)
        end_panel(surface, panel, "Left / Right: pages   B: best of / newest   Esc to close   (F12 records a timelapse clip into the same folder)")
    elif p == "show":
        rows = SHOWR["rows"]
        panel = begin_panel(700, 140 + 34 * max(1, len(rows)), f"Genetic show   day {SHOWR['day']}")
        for i, (sc, nm, mine) in enumerate(rows):
            y = 70 + 34 * i
            txt21(panel, f"#{i + 1}", 26, y, "t", (255, 232, 140) if i < 3 else (130, 150, 180))
            txt21(panel, nm, 90, y + 4, "h", (150, 235, 170) if mine else (200, 215, 232))
            txt21(panel, f"{sc:.1f}", 360, y + 4, "h")
            if mine and i < 3:
                txt21(panel, f"+{(25, 15, 8)[i]} points", 460, y + 6, "d", (255, 232, 140))
        txt21(panel, "Score: colour shift, tail, sheen, lace and fin shape, plus health and condition.", 26, 90 + 34 * max(1, len(rows)), "d", HUD_DIM)
        end_panel(surface, panel, "Esc to close   (one show every three tank days)")

GOALS.extend([
    ("seller", "Fish trader", "Sell a bred fish (7)", lambda: X["sold"] >= 1),
    ("chorer", "Tank keeper", "Finish a week of chores (8)", lambda: X["streak"] >= 1),
    ("challenger", "Challenge accepted", "Win a challenge (8)", lambda: len(X["chal_won"]) >= 1),
    ("raid", "Raid survivor", "Come through a predator raid without losses", lambda: X["raids"] >= 1 and X["points"] >= 0 and RAID["t"] < 0),
    ("friends", "Best friends", "Two fish become friends (F2 shows the web)", lambda: any(getattr(f, "friend", None) is not None for f in fishes)),
    ("memorial", "Gone but remembered", "A grown fish is added to the memorial (F8)", lambda: len(X["memorial"]) >= 1),
    ("lace", "Lace guppy", "Breed a lace-pattern guppy", lambda: any(isinstance(f, GuppyBase) and f.gen >= 2 and f.lace_on() for f in fishes)),
    ("request", "Special order", "Fill a breeding request", lambda: X["reqs"] >= 1),
    ("ribbon", "Blue ribbon", "Win the genetic show (F4)", lambda: X["wins"] >= 1),
    ("shopper", "Well equipped", "Buy something from the shop (,)", lambda: len(X["owned"]) >= 1),
    ("cycled", "Cycled tank", "Finish cycling a new tank (new_tank in the config)", lambda: CHEM["won"]),
    ("scaper", "Aquascaper", "Apply an aquascape preset (.)", lambda: X["scapes"] >= 1),
    ("director", "Director", "Record a timelapse clip (F12)", lambda: X["clips"] >= 1),
    ("guest", "Special guest", "A frog or kingfisher visits (show_visitors)", lambda: X["guests"] >= 1),
    ("lush", "Lush", "Dose fertiliser (')", lambda: X["ferts"] >= 1),
    ("designer", "Designer", "Score 90 or more from the judge in planting mode (Home)", lambda: X["best_scape"] >= 90),
    ("tourist", "Tour guide", "Record a tank tour GIF (PageDown)", lambda: X["tours"] >= 1),
    ("bloom", "In bloom", "A plant flowers in your tank", lambda: X["blooms"] >= 1),
])


def quit_game():
    if AWAY["on"] and current_state == STATE_AQUARIUM:
        try:
            save_game(AUTOSAVE_PATH, quiet=True)
        except Exception:
            pass
    pygame.quit()
    sys.exit()


def apply_away(sec):
    """The tank kept going while the app was closed: time passes, the water tires, hungry fish wait, guppies breed."""
    sec = min(float(sec), 8 * 3600.0)
    if sec < 180:
        return
    e = eco
    frames = sec * 60.0
    adv = e.clock + frames * 0.1 / DAY_LENGTH   # time away passes at a tenth of tank speed
    e.day += int(adv)
    e.clock = adv % 1.0
    hrs = sec / 3600.0
    water0 = e.water
    e.water = max(25.0, e.water - hrs * 7.0)
    for i in range(GLASS_COLS):
        e.glass[i] = min(1.0, e.glass[i] + hrs * 0.2 * GLASS_RATE[i])
    e.filter = max(0.05, e.filter - hrs * 0.12)
    for f in fishes:
        f.hunger = min(80.0, f.hunger + min(30.0, sec / 120.0))
        if f.age < f.lifespan * 0.96:
            f.age = min(f.age + frames * 0.25, f.lifespan * 0.96)
    ms = [f for f in fishes if isinstance(f, GuppyBase) and f.sex == "M" and f.growth >= 1.0]
    fs = [f for f in fishes if isinstance(f, GuppyBase) and f.sex == "F" and f.growth >= 1.0]
    broods = 0
    if ms and fs:
        for _ in range(min(3, int(hrs * 1.5))):
            give_birth(random.choice(ms), random.choice(fs))
            broods += 1
    stats["away"] += 1
    msg = f"Welcome back! Away {int(sec // 3600)}h {int(sec % 3600 // 60):02d}m"
    if broods:
        msg += f": {broods} guppy broods were born"
    notify(msg + f", water {water0:.0f}% -> {e.water:.0f}%")


def try_autoload():
    if not os.path.exists(AUTOSAVE_PATH):
        return
    try:
        load_game(AUTOSAVE_PATH, away=True)
    except Exception as err:
        print("autosave could not be loaded:", err)
        init_ecosystem()
        fishes[:] = spawn_community()


def spawn_visitor():
    side = random.choice([-1, 1])
    b = Channa(-90 if side == 1 else SCREEN_WIDTH + 90, random.randint(160, 340), visitor=True)
    b.vel = pygame.Vector2(side * 2.0, 0)
    predators.append(b)


def update_mouse_track():
    mx, my = world_mouse(pygame.mouse.get_pos())
    p = pygame.Vector2(mx, my)
    speed = p.distance_to(mouse_track["pos"])
    mouse_track["speed"] += (speed - mouse_track["speed"]) * 0.3
    mouse_track["still"] = mouse_track["still"] + 1 if speed < 2.5 else 0
    mouse_track["pos"] = p
    mouse_track["inside"] = bool(pygame.mouse.get_focused()) and 0 <= mx < SCREEN_WIDTH \
        and WATER_TOP < my < SCREEN_HEIGHT - SAND_HEIGHT


def process_respawns():
    for item in respawn_queue[:]:
        due, kind = item
        if eco.t < due:
            continue
        respawn_queue.remove(item)
        if kind == "fish":
            nf = spawn_random_fish()
            if not has_room(type(nf)):
                respawn_queue.append((eco.t + 600, "fish"))  # tank is full: the newcomer waits
                continue
            side = random.choice([-1, 1])
            nf.pos = pygame.Vector2(30 if side == 1 else SCREEN_WIDTH - 30,
                                    random.randint(WATER_TOP + 80, SCREEN_HEIGHT - 150))
            nf.vel = pygame.Vector2(side * 1.5, 0)
            fishes.append(nf)
            eco.births += 1
        else:
            shimps.append(TinyShrimp())


def update_daphnia(k):
    """Daphnia drift on a lazy wander, ride the current, and jump away from fish that get close."""
    k.phase += 0.02
    k.apply_force(pygame.Vector2(math.cos(k.phase * 1.3), math.sin(k.phase)) * 0.012)
    k.apply_force(pygame.Vector2(eco.current * 0.6, 0))
    for f in fishes:
        off = k.pos - f.pos
        if off.length_squared() < 50 * 50:
            k.apply_force(unit(off) * 0.9)
            break
    k.update()
    if k.pos.x < 10:
        k.vel.x = abs(k.vel.x)
    elif k.pos.x > SCREEN_WIDTH - 10:
        k.vel.x = -abs(k.vel.x)
    if k.pos.y < WATER_TOP + 30:
        k.vel.y = abs(k.vel.y)
    elif k.pos.y > SCREEN_HEIGHT - 70:
        k.vel.y = -abs(k.vel.y)


def shrimp_flee(s):
    for p in predators:
        if isinstance(p, Crayfish) and p.state in ("hunt", "flee"):
            off = s.pos - p.pos
            if off.length_squared() < 110 * 110:
                s.pos += unit(off) * 1.6


night_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)


def draw_daylight(surface):
    alpha = int(eco.night * 105)
    if alpha > 0:
        night_surf.fill((6, 12, 48, alpha))
        surface.blit(night_surf, (0, 0))
    dusk = clamp(1.0 - abs(eco.daylight - 0.42) / 0.2)
    if dusk > 0.03:
        night_surf.fill((255, 120, 60, int(40 * dusk)))
        surface.blit(night_surf, (0, 0))
    murk = clamp((60 - eco.water) / 60)  # dirty water turns murky green
    if murk > 0.02:
        night_surf.fill((70, 100, 40, int(95 * murk)))
        surface.blit(night_surf, (0, 0))
    if eco.dark > 0.02:   # blackouts and storm clouds
        night_surf.fill((2, 4, 14, int(eco.dark * 80)))
        surface.blit(night_surf, (0, 0))
    if eco.flash > 0.03:   # lightning
        night_surf.fill((235, 240, 255, int(170 * eco.flash)))
        surface.blit(night_surf, (0, 0))
    if eco.blue > 0:   # methylene blue tints the water
        night_surf.fill((40, 100, 230, int(70 * min(1.0, eco.blue / 400.0))))
        surface.blit(night_surf, (0, 0))
    if eco.cloud > 0.03:   # overfed: cloudy water
        night_surf.fill((200, 210, 200, int(75 * eco.cloud)))
        surface.blit(night_surf, (0, 0))


def draw_fx(surface):
    for f in fx[:]:
        f.update()
        if f.life <= 0:
            fx.remove(f)
        else:
            f.draw(surface)
    for ink in inks[:]:
        ink.update()
        if ink.age >= ink.life:
            inks.remove(ink)
        else:
            ink.draw(surface)
    for r in ripples[:]:
        r[1] += 4.0
        r[2] -= 1
        if r[2] <= 0:
            ripples.remove(r)
            continue
        col = mix((20, 50, 100), (220, 240, 255), r[2] / 50.0)
        pygame.draw.circle(surface, col, (int(r[0].x), int(r[0].y)), int(r[1]), 2)


_hud_font = None
_day_strip = None


def hud_font():
    global _hud_font
    if _hud_font is None:
        _hud_font = pygame.font.SysFont("Arial", 13, bold=True)
    return _hud_font


HUD_DIM = (150, 175, 205)


def draw_bar(panel, label, x, y, value, color, width=150):
    panel.blit(hud_font().render(label, True, HUD_DIM), (x, y - 5))
    pygame.draw.rect(panel, (40, 55, 80), (x + 46, y, width, 6), border_radius=3)
    pygame.draw.rect(panel, color, (x + 46, y, int(width * clamp(value)), 6), border_radius=3)


def make_panel(w, h):
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (6, 18, 38, 195), (0, 0, w, h), border_radius=10)
    pygame.draw.rect(panel, (130, 180, 230, 110), (0, 0, w, h), 1, border_radius=10)
    return panel


def draw_hud(surface):
    global _day_strip
    if not eco.show_hud:
        return
    font = hud_font()
    if _day_strip is None:
        _day_strip = pygame.Surface((220, 6))
        for x in range(220):
            dl = 0.5 + 0.5 * math.sin(math.tau * (x / 220 - 0.25))
            pygame.draw.line(_day_strip, mix((24, 32, 80), (255, 215, 120), dl), (x, 0), (x, 5))
    panel = make_panel(250, 168)
    panel.blit(font.render("TANK MOOD", True, HUD_DIM), (12, 8))
    panel.blit(font.render(eco.tank_mood, True, MOOD_COLORS.get(eco.tank_mood, (230, 230, 230))), (92, 8))
    panel.blit(_day_strip, (12, 32))
    mx = 12 + int(eco.clock * 220)
    pygame.draw.circle(panel, (255, 255, 255) if eco.daylight > 0.3 else (190, 200, 255), (mx, 35), 5)
    pygame.draw.circle(panel, (30, 50, 90), (mx, 35), 5, 1)
    if eco.night > 0.5:
        phase = "NIGHT"
    elif eco.daylight < 0.55 and eco.clock < 0.5:
        phase = "DAWN"
    elif eco.daylight < 0.55:
        phase = "DUSK"
    else:
        phase = "DAY"
    if not eco.cycle_on:
        phase += " (paused)"
    if eco.full_moon and eco.night > 0.3:
        phase += "  - FULL MOON"
    panel.blit(font.render(phase, True, HUD_DIM), (12, 44))
    panel.blit(font.render(f"Day {eco.day}", True, (225, 235, 245)), (200, 44))
    draw_bar(panel, "FEAR", 12, 70, max(eco.fear, eco.avg_fear), mix((255, 210, 90), (255, 70, 70), max(eco.fear, eco.avg_fear)))
    draw_bar(panel, "WATER", 12, 88, eco.water / 100, mix((255, 90, 70), (90, 220, 170), eco.water / 100))
    panel.blit(font.render(f"Prey {len(fishes)}/{tank_capacity()}   Hunters {len(predators)}   Caught {eco.kills}   Born {eco.births}", True,
                           (225, 235, 245)), (12, 102))
    tool = DECOR_TOOLS[eco.decor_idx]
    panel.blit(font.render(f"Feed: {FEEDS[eco.feed_idx]}" + (f"   Build: {tool}" if tool != "OFF" else ""), True,
                           (200, 225, 255)), (12, 120))
    line = eco.event if eco.event else "F1 help  H hud  J journal  P photo  W water"
    panel.blit(font.render(line, True, (255, 230, 150) if eco.event else HUD_DIM), (12, 138))
    surface.blit(panel, (12, 12))


SPECIES_INFO = {
    "DemasoniCichlid": ("Pseudotropheus demasoni", "A tiny Malawi mbuna that lives in dense, feisty rock-dwelling groups."),
    "YellowPrinceCichlid": ("", "A golden rock-dweller that claims a cave and defends it."),
    "CobaltZebra": ("Maylandia callainos", "Males are vivid cobalt blue; they graze algae off the rocks."),
    "RedZebra": ("Maylandia estherae", "The orange females are the ones called red zebras."),
    "KenyiCichlid": ("Maylandia lombardoi", "Males turn bright yellow with age and guard their territory."),
    "PeacockCichlid": ("Aulonocara sp.", "Males flash electric colours to impress females over the sand."),
    "AuratusCichlid": ("Melanochromis auratus", "A gold-striped mbuna; males darken and turn bold."),
    "IceBlueCichlid": ("", "A pale blue Malawi cichlid that grazes the rocks."),
    "SocolofiCichlid": ("Pseudotropheus socolofi", "A pastel-blue mbuna, one of the milder ones."),
    "AngelFish": ("Pterophyllum scalare", "A tall Amazon cichlid; pairs guard eggs on broad leaves."),
    "NeonTetra": ("Paracheirodon innesi", "Its blue stripe stays visible in dim water so the shoal keeps together."),
    "RummyNose": ("Hemigrammus rhodostomus", "A red nose shows good health; the shoal turns in tight lockstep."),
    "CardinalTetra": ("Paracheirodon axelrodi", "Its red stripe runs the whole body, longer than a neon's."),
    "EmberTetra": ("Hyphessobrycon amandae", "A tiny, glowing orange tetra under two centimetres long."),
    "BlackSkirtTetra": ("Gymnocorymbus ternetzi", "The dark skirt fin gives it away; a bold, playful shoaler."),
    "LemonTetra": ("Hyphessobrycon pulchripinnis", "A glassy yellow body with a black-edged anal fin."),
    "MosaicGuppy": ("Poecilia reticulata", "A livebearer: females give birth to free-swimming fry."),
    "TuxedoGuppy": ("Poecilia reticulata", "Dark rear half, pale front: the tuxedo pattern is bred in."),
    "SunsetGuppy": ("Poecilia reticulata", "Males carry broad sweeps of red and orange in the tail."),
    "MoscowGuppy": ("Poecilia reticulata", "Prized for solid deep blue or black males."),
    "Pleco": ("Pterygoplichthys sp.", "An armoured algae grazer with a sail-like fin and a sucker mouth."),
    "BalaShark": ("Balantiocheilos melanopterus", "Not a shark: a silver minnow that needs long runs of open water."),
    "BoesemaniRainbow": ("Melanotaenia boesemani", "Half blue-grey, half orange; the colours deepen with age."),
    "PearlGourami": ("Trichopodus leerii", "Males build bubble nests; the thread-like fins are feelers."),
    "ClownLoach": ("Chromobotia macracanthus", "Bold bands, and groups that sometimes rest on their sides."),
    "TigerBarb": ("Puntigrus tetrazona", "Four black bars on a busy shoaler known for nipping fins."),
    "Corydoras": ("Corydoras aeneus", "Sifts the sand with its barbels and sometimes darts up to gulp air."),
    "Otocinclus": ("Otocinclus affinis", "A tiny grazer that clings to glass, leaves and wood."),
    "BristlenosePleco": ("Ancistrus sp.", "Males grow fleshy bristles on the snout; shy by day."),
    "Betta": ("Betta splendens", "Males flare their huge fins at rivals and blow a bubble nest."),
    "Discus": ("Symphysodon aequifasciatus", "A calm, disc-shaped cichlid; pairs stay close."),
    "Killifish": ("Aplocheilus lineatus", "A surface-dwelling hunter of fallen insects."),
    "Channa": ("Channa sp.", "A snakehead: it breathes air, ambushes from cover and guards a bubble nest."),
    "FireEel": ("Mastacembelus erythrotaenia", "A spiny eel that hides in rocks and sand and strikes from cover."),
    "Crayfish": ("", "A scavenger that lurks in rock lairs and pounces on shrimp."),
}
PORTRAITS = {}
_card_fonts = {}


def card_font(italic=False):
    f = _card_fonts.get(italic)
    if f is None:
        f = _card_fonts[italic] = pygame.font.SysFont("Arial", 12, italic=italic)
    return f


def portrait(f):
    """A small cached picture of the fish for its card, drawn side-on by the fish's own renderer."""
    key = (type(f).__name__, getattr(f, "id", 0), round(f.z * 20), getattr(f, "gene_key", 0), getattr(f, "sex", ""))
    if key in PORTRAITS:
        return PORTRAITS[key]
    canvas = pygame.Surface((320, 220), pygame.SRCALPHA)
    old_pos, old_vel, old_angle = f.pos.copy(), f.vel.copy(), getattr(f, "angle", 0.0)
    try:
        f.pos.update(160, 110)
        f.vel.update(1, 0)
        f.angle = 0.0
        f.draw(canvas)
    except Exception:
        canvas = None
    finally:
        f.pos.update(old_pos)
        f.vel.update(old_vel)
        f.angle = old_angle
    img = None
    if canvas is not None:
        r = canvas.get_bounding_rect()
        if r.w > 4 and r.h > 4:
            crop = canvas.subsurface(r)
            k = min(84 / r.w, 56 / r.h, 1.6)
            img = pygame.transform.smoothscale(crop, (max(1, int(r.w * k)), max(1, int(r.h * k))))
    if len(PORTRAITS) > 120:
        PORTRAITS.clear()
    PORTRAITS[key] = img
    return img


def species_footer(panel, f, y0):
    pygame.draw.line(panel, (130, 180, 230, 80), (12, y0 - 5), (238, y0 - 5))
    pic = portrait(f)
    if pic is not None:
        panel.blit(pic, pic.get_rect(center=(52, y0 + 32)))
    latin, fact = SPECIES_INFO.get(type(f).__name__, ("", ""))
    y = y0
    if latin:
        panel.blit(card_font(True).render(latin, True, (200, 225, 255)), (100, y))
        y += 15
    words, line = fact.split(), ""
    for w in words:
        trial = (line + " " + w).strip()
        if card_font().size(trial)[0] > 138 and line:
            panel.blit(card_font().render(line, True, HUD_DIM), (100, y))
            y += 13
            line = w
        else:
            line = trial
    if line:
        panel.blit(card_font().render(line, True, HUD_DIM), (100, y))


def draw_card(surface):
    f = eco.selected
    if f is None or not eco.show_hud:
        return
    font = hud_font()
    panel = make_panel(250, 246)
    panel.blit(font.render(f"{f.name} the {nice_name(f)}", True, (255, 240, 150)), (12, 8))
    if isinstance(f, Predator):
        panel.blit(font.render(f"{f.mood.upper()}  -  hunter  -  {f.kills} caught", True, HUD_DIM), (12, 26))
        draw_bar(panel, "HUNGER", 12, 52, f.hunger / 100, mix((120, 220, 150), (255, 90, 70), f.hunger / 100))
        draw_bar(panel, "ALERT", 12, 70, clamp(f.flash), mix((255, 210, 90), (255, 70, 70), clamp(f.flash)))
        draw_bar(panel, "ANNOY", 12, 88, clamp(f.annoyance / 900), (230, 150, 90))
        draw_bar(panel, "SPEED", 12, 106, clamp(f.vel.length() / max(f.strike_speed, 1)), (120, 180, 255))
        panel.blit(font.render("Z: follow cam   click empty water: drop", True, HUD_DIM), (12, 138))
    else:
        sex = {"M": "male", "F": "female"}.get(getattr(f, "sex", ""), "")
        panel.blit(font.render(f"{f.mood.upper()}  -  {f.life_stage()} {sex}" + ("  -  SICK" if f.sick else ""), True, HUD_DIM), (12, 26))
        draw_bar(panel, "HUNGER", 12, 52, f.hunger / 100, mix((120, 220, 150), (255, 90, 70), f.hunger / 100))
        draw_bar(panel, "FEAR", 12, 70, f.fear, mix((255, 210, 90), (255, 70, 70), f.fear))
        draw_bar(panel, "STRESS", 12, 88, f.stress / 100, (230, 150, 90))
        draw_bar(panel, "BRAVE", 12, 106, f.bravery, (120, 180, 255))
        draw_bar(panel, "AGE", 12, 124, clamp(f.life_frac()), mix((150, 220, 255), (200, 200, 205), clamp(f.life_frac())))
        note = ""
        if f.partner is not None and f.partner.alive:
            note = f"mate: {f.partner.name}"
        if f.guard_t > 0:
            note = (note + "  " if note else "") + "guarding"
        if getattr(f, "gen", 0) > 1 and len(f.parents) == 2:
            note = f"gen {f.gen}: {f.parents[0].name} x {f.parents[1].name}"[:36]
        panel.blit(font.render(note or "Z: follow cam   click empty water: drop", True, HUD_DIM), (12, 138))
    species_footer(panel, f, 164)
    surface.blit(panel, (12, 188))


def draw_journal(surface):
    if not eco.show_journal:
        return
    font = hud_font()
    entries = journal[-10:]
    panel = make_panel(380, 30 + 17 * max(1, len(entries)))
    panel.blit(font.render("JOURNAL", True, (255, 240, 150)), (12, 7))
    for i, (stamp, text) in enumerate(entries):
        line = f"{stamp}  {text}"
        panel.blit(font.render(line[:56], True, (210, 225, 240) if i == len(entries) - 1 else HUD_DIM), (12, 28 + 17 * i))
    surface.blit(panel, (SCREEN_WIDTH - 392, 56))


def draw_ui(surface):
    draw_hud(surface)
    draw_card(surface)
    draw_journal(surface)


# ---- places to hide, and the cleaner-shrimp stations ----
def build_cover():
    """Cover spots: sword-plant clumps for the small shy fish, rock and driftwood faces for everyone else."""
    nest_spots.clear()
    rock_spots.clear()
    cave_spots.clear()
    thicket_spots.clear()
    tall = [p for p in plants if p.height >= 80 and not p.hang]
    for p in plants:
        if p.species == "Sword":
            nest_spots.append(pygame.Vector2(p.pos_x, ground_y(p.pos_x) - 38))
    for p in tall:   # a thick stand of tall plants is a refuge for the shy and the small
        if sum(1 for q in tall if abs(q.pos_x - p.pos_x) < 90) >= 5 and not any(abs(t.x - p.pos_x) < 110 for t in thicket_spots):
            thicket_spots.append(pygame.Vector2(p.pos_x, ground_y(p.pos_x) - 0.4 * p.height))
    for r in rocks:
        if r.z < 0.7:
            continue
        sink = int(35 * r.z) if r.y_offset >= 0 else 0
        bottom = r.base_y + r.y_offset + sink
        rock_spots.append((pygame.Vector2(r.pos_x, bottom - r.image.get_height() * 0.45), r.z))
        if getattr(r, "kind", "") in ("CAVE", "POT"):   # cichlids spawn in a cave or a pot, and everyone shelters in it
            cave_spots.append(pygame.Vector2(r.pos_x + (8 if r.kind == "POT" and not r.fl else 0), bottom - r.image.get_height() * 0.3))


def find_cover(f):
    best, best_d = None, 520
    if f.growth < 0.7 or getattr(f, "shy", False) or getattr(f, "persona", "") == "shy" or (f.sleepy > 0.55 and f.fear < 0.3):
        for s in nest_spots + thicket_spots:
            d = f.pos.distance_to(s)
            if d < best_d:
                best, best_d = s, d
    for s, rz in rock_spots:
        if f.z < rz and (rz >= 0.95 or f.z <= 0.9):
            d = f.pos.distance_to(s) * (1.3 if (f.growth < 0.7 or getattr(f, "shy", False)) else 1.0)
            if d < best_d:
                best, best_d = s, d
    return best


class CleaningStation:
    """A cleaner shrimp perched on a rock. Stressed fish queue up here to be tidied."""

    def __init__(self, rock):
        self.z = rock.z
        sink = int(35 * rock.z) if rock.y_offset >= 0 else 0
        bottom = rock.base_y + rock.y_offset + sink
        self.pos = pygame.Vector2(rock.pos_x + random.randint(-8, 8), bottom - rock.image.get_height() * 0.9)
        self.hover = self.pos + pygame.Vector2(0, -36)
        self.occupied = 0
        self.anim = random.uniform(0, 6)

    def draw(self, surface):
        self.anim += 0.08 + 0.1 * (self.occupied > 0)
        x, y = int(self.pos.x), int(self.pos.y)
        wave = math.sin(self.anim * 2) * (3 + 3 * self.occupied)
        pygame.draw.aaline(surface, (255, 255, 255), (x + 3, y - 3), (x + 12, y - 12 + wave))
        pygame.draw.aaline(surface, (255, 255, 255), (x + 3, y - 3), (x + 9, y - 14 - wave * 0.5))
        pygame.draw.ellipse(surface, (215, 50, 40), (x - 6, y - 5, 12, 6))
        pygame.draw.line(surface, (255, 245, 235), (x - 5, y - 3), (x + 4, y - 3), 1)
        pygame.draw.circle(surface, (215, 50, 40), (x - 7, y - 3), 2)
        if self.occupied and random.random() < 0.08:
            burst(self.hover + (random.uniform(-14, 14), random.uniform(-6, 10)), (255, 240, 160), 2, 0.6, 30, 1, -0.01)


def draw_stations(surface, front):
    for st in stations:
        if (st.z >= 0.95) == front:
            st.draw(surface)


# ---- the social life of the community fish ----
def init_traits(f):
    f.family = f.family_name
    f.bravery = random.uniform(0.15, 1.0)
    f.curious = random.uniform(0.1, 1.0)
    f.bravery = max(f.bravery, getattr(f, "bold_floor", 0.0))
    f.social = getattr(f, "social_base", 0.3) * random.uniform(0.7, 1.2)
    f.base_max = f.max_speed
    f.fear = 0.0
    f.stress = 0.0
    f.sleepy = 0.0
    f.hidden = False
    f.settled = False
    f.refuge = None
    f.refuge_covered = False
    f.safe = 0
    f.refuge_cd = 0
    f.mobbing = False
    f.cleaning = 0
    f.clean_cd = random.randint(0, 600)
    f.station = None
    f.emote_cd = random.randint(0, 120)
    f.interest = 0
    f.mood = "calm"
    f.name = random.choice(FISH_NAMES)
    f.growth = 1.0
    f.adult_z = f.z
    f.sick = False
    f.sick_t = 0
    f.spots = []
    f.nesting = 0
    f.breed_cd = random.randint(600, 2400)
    f.age = random.randint(int(GROW_FRAMES * 1.2), int(LIFESPAN * 0.7))
    f.lifespan = LIFESPAN * random.uniform(0.8, 1.2)
    f.sex = random.choice("MF")
    if f.sex == "M":
        f.bravery = min(1.0, f.bravery + 0.12)           # males are bolder and do the defending
    else:
        f.bravery = max(0.1, f.bravery - 0.08)
    f.partner = None
    f.bond_t = 0
    f.courting = 0
    f.site = None
    f.widow_t = 0
    f.guard_pos = None
    f.guard_t = 0
    f.parents = ()
    f.nest = None
    f.nest_t = 0
    f.hunting = 0
    f.hunt_target = None
    f.hunt_cd = random.randint(0, 400)


FISH_NAMES = ["Bubbles", "Pip", "Fern", "Finn", "Marlo", "Sunny", "Tango", "Ziggy", "Pearl", "Rusty", "Skye", "Mochi",
              "Biscuit", "Pebble", "Kiwi", "Dot", "Comet", "Olive", "Waffles", "Nimbus", "Poppy", "Gizmo", "Lemon", "Ripple"]


PAIRING = ("cichlid", "gourami", "pleco", "discus")   # these species pair for life; the others only pair up to spawn


def pick_site(m):
    """Where a pair will lay: the foot of a sword plant for the cichlids, a quiet patch of sand for everyone else."""
    if m.family == "cichlid" and (nest_spots or cave_spots):
        sites = [(sp, 0.0) for sp in nest_spots] + [(sp, 800.0) for sp in cave_spots]   # a cave is worth almost any swim
        return pygame.Vector2(min(sites, key=lambda t: m.pos.distance_to(t[0]) - t[1])[0])
    x = clamp(m.pos.x, 110, SCREEN_WIDTH - 110)
    return pygame.Vector2(x, ground_y(x) - 38)


def find_mate(f, need_ready):
    best, bd = None, 330 * 330
    for o in fishes:
        sex = getattr(o, "sex", None)
        if (o is f or sex is None or sex == f.sex or type(o) is not type(f) or o.partner is not None
                or o.growth < 1.0 or o.age < GROW_FRAMES * 1.3 or not o.alive):
            continue
        if need_ready and (o.breed_cd > 0 or o.hunger > 50 or o.guard_t > 0):
            continue
        d = o.pos.distance_squared_to(f.pos)
        if d < bd:
            best, bd = o, d
    return best


def bond(a, b):
    a.partner, b.partner = b, a
    for x in (a, b):
        x.bond_t, x.courting, x.site, x.nesting = 0, 0, None, 0
    if a.family in PAIRING:
        notify(f"{a.name} and {b.name} paired up", log=False)


def unbond(f):
    p = f.partner
    for x in (f, p):
        if x is not None:
            x.partner, x.courting, x.site, x.nesting, x.bond_t = None, 0, None, 0, 0


def release_refuge(f):
    f.refuge = None
    f.settled = False
    f.hidden = False
    f.refuge_cd = 240
    f.safe = 0


def prey_social(f):
    """Everything a tank fish does besides eating: scare, hide, sleep, school, wonder, get cleaned."""
    if not f.alive:
        return
    if not hasattr(f, "family"):
        init_traits(f)
    pos = f.pos
    f.emote_cd = max(0, f.emote_cd - 1)
    f.refuge_cd = max(0, f.refuge_cd - 1)
    f.clean_cd = max(0, f.clean_cd - 1)
    f.mobbing = False

    # ---- what frightens me? ----
    threat, away = 0.0, pygame.Vector2()
    for p in predators:
        if not p.hunts_fish:
            continue
        s = p.scare_level(f)
        if s > 0.0:
            off = pos - p.pos
            if off.length_squared() > 0:
                away += off.normalize() * s
            threat = max(threat, s)
    for ink in inks:
        if pos.distance_squared_to(ink.pos) < ink.radius ** 2:
            threat = max(threat, 0.3)
    brave_mod = 1.2 - 0.6 * f.bravery
    target = max(threat, eco.fear * 0.8) * brave_mod

    mt = mouse_track
    mouse_d = pos.distance_to(mt["pos"]) if mt["inside"] else 1e9
    if mt["speed"] > 16 and mouse_d < 150:  # a hand slapping at the glass
        target = max(target, 0.45 * (1.15 - f.bravery))

    # ---- who is around me? ----
    mates, centroid = 0, pygame.Vector2()
    avg_vel, sep, panic = pygame.Vector2(), pygame.Vector2(), pygame.Vector2()
    panic_n, bold = 0, 0
    for o in fishes:
        if o is f or not hasattr(o, "family"):
            continue
        off = pos - o.pos
        d2 = off.length_squared()
        if d2 > 170 * 170:
            continue
        if o.fear > 0.55 and not o.hidden and d2 < 150 * 150:  # alarm spreads through the school
            panic += o.pos
            panic_n += 1
            target = max(target, o.fear * 0.7 * f.social * brave_mod)
        if o.mobbing:
            bold += 1
        if o.hunting and d2 > 0 and d2 < 160 * 160 and (f.growth < 0.7 or getattr(f, "small_prey", False)) and getattr(o, "hunts", False) and f not in o.parents:
            target = max(target, 0.7 * brave_mod)        # a hunting cichlid is a predator too
            away += off.normalize() * 0.9
        if type(o) is type(f):
            mates += 1
            centroid += o.pos
            avg_vel += o.vel
            if 0 < d2 < 40 * 40:
                sep += off.normalize()
    if away.length_squared() == 0 and panic_n:
        away = pos - panic / panic_n

    # ---- fear rises fast and fades slowly ----
    if target > f.fear:
        f.fear += (target - f.fear) * 0.35
    else:
        f.fear = max(0.0, f.fear - (0.004 if f.hidden else 0.012))

    # ---- growing up, and getting sick ----
    f.age += 1
    if f.growth < 1.0:
        f.growth = min(1.0, f.age / GROW_FRAMES)
        f.z = f.adult_z * (0.3 + 0.7 * f.growth)   # a fry is tiny and grows to full size with age
    elif f.age > f.lifespan and random.random() < 1 / 2400:
        f.alive = False
        notify(f"{f.name} the {nice_name(f)} died of old age")
        return
    if f.sick:
        # sick_t is the illness left to shake off; every sick fish recovers, faster in clean water
        f.sick_t -= (SICK_RECOVERY + 0.9 * clamp(eco.water / 100.0) + (1.5 if eco.blue > 0 else 0.0)
                     + (1.2 if "hospital" in X["owned"] and getattr(f, "qpos", None) is not None else 0.0))
        target = max(target, 0.0)
        f.stress = max(f.stress, 40.0)
        if f.sick_t <= 0:
            f.sick = False
            f.immune = 5400   # a recovered fish resists reinfection for about 90 seconds
            f.carrier = 9000  # ...but it may still carry the sickness: stress and foul water can bring it back
            notify(f"{f.name} the {nice_name(f)} recovered", log=False)
        else:
            # death is only a small chance, higher in foul water or when starving
            risk = SICK_DEATH_CHANCE * (1.0 + max(0.0, 50.0 - eco.water) / 25.0) * (2.0 if f.hunger > 85 else 1.0)
            if random.random() < risk:
                f.alive = False
                notify(f"{f.name} the {nice_name(f)} died of the sickness")
                return

    # ---- sleep: the fish bed down at night (but not during a moon spawn) ----
    sleep_goal = eco.night if f.fear < 0.3 and eco.event != "MOON SPAWNING" else 0.0
    if getattr(f, "nocturnal", False):   # plecos and corydoras rest under cover by day and graze after dark
        sleep_goal = (1.0 - eco.night) * 0.58 if f.fear < 0.3 else 0.0
    f.sleepy += (sleep_goal - f.sleepy) * 0.01

    # ---- find a refuge when scared or sleepy ----
    if (f.fear > 0.5 or f.sleepy > 0.55) and f.refuge is None and f.refuge_cd <= 0 and f.cleaning <= 0:
        spot = find_cover(f)
        if spot is not None:
            f.refuge, f.refuge_covered = spot, True
        elif f.sleepy > 0.55 and f.fear < 0.3:
            f.refuge, f.refuge_covered = pygame.Vector2(pos.x, ground_y(pos.x) - 48 * f.z - 14), False
        else:
            f.refuge_cd = 90  # nowhere to hide: keep running
    if f.refuge is not None:
        to = f.refuge - pos
        if not f.settled:
            if to.length() < 24:
                f.settled = True
                f.safe = 0
            else:
                f.apply_force(unit(to) * (0.5 + 0.5 * f.fear))
        if f.settled:
            f.hidden = f.refuge_covered
            f.apply_force(to * 0.04)
            f.vel *= 0.82
            if threat < 0.05 and f.fear < 0.3 and f.sleepy < 0.4:
                f.safe += 1
            else:
                f.safe = 0
            if f.safe > 150 or (f.hunger > 75 and threat < 0.5 and f.sleepy < 0.5):  # starving fish take risks
                release_refuge(f)
                f.refuge_cd = 600 if f.hunger > 75 else 240

    # ---- cleaning station ----
    if f.cleaning > 0 and f.fear > 0.5:
        f.cleaning = 1
    if f.cleaning > 0:
        f.cleaning -= 1
        f.apply_force((f.station.hover - pos) * 0.03)
        f.vel *= 0.85
        f.angle = 30.0
        f.stress = max(0.0, f.stress - 0.5)
        if f.cleaning == 0:
            f.station.occupied = max(0, f.station.occupied - 1)
            f.station = None
            f.clean_cd = 1500
            if f.sick:
                f.sick, f.sick_t = False, 0
                notify(f"The cleaner shrimp cured {f.name}!")
    elif (stations and f.stress > 55 and f.clean_cd <= 0 and f.fear < 0.25 and f.refuge is None
          and f.sleepy < 0.4):
        if f.station is None:
            free = [s for s in stations if s.occupied < 2 and pos.distance_to(s.pos) < 700]
            if free:
                f.station = min(free, key=lambda s: pos.distance_squared_to(s.pos))
            else:
                f.clean_cd = 300
        if f.station is not None:
            to = f.station.hover - pos
            if to.length() < 28:
                f.cleaning = 260
                f.station.occupied += 1
                add_emote(f, "*")
            else:
                f.apply_force(unit(to) * 0.35)
    else:
        f.station = None

    # ---- mates, courtship and spawning ----
    ready = (f.growth >= 1.0 and f.age > GROW_FRAMES * 1.5 and f.life_frac() < 0.85 and not f.sick and f.hunger < 40
             and f.fear < 0.2 and f.sleepy < 0.3 and f.refuge is None and f.cleaning <= 0 and f.breed_cd <= 0
             and f.guard_t <= 0 and eco.water > 60)
    f.breed_cd = max(0, f.breed_cd - 1)
    mate = f.partner
    if mate is not None and not mate.alive:           # a mate was lost
        f.partner, f.courting, f.site, f.nesting, f.bond_t = None, 0, None, 0, 0
        if f.family in PAIRING:
            f.stress = min(100.0, f.stress + 25)
            add_emote(f, "?")
        mate = None
    if mate is None and (eco.t + f.id) % 40 == 0 and f.growth >= 1.0:
        if f.family in PAIRING and f.age > GROW_FRAMES * 1.3:
            other = find_mate(f, False)
            if other is not None:
                bond(f, other)
                mate = other
        elif ready:
            other = find_mate(f, True)
            if other is not None:
                bond(f, other)
                mate = other
    if mate is not None:
        f.bond_t += 1
        off = mate.pos - pos
        dl = off.length()
        if f.family not in PAIRING and f.bond_t > 2400:
            unbond(f)
        else:
            if dl > 80:
                f.apply_force(unit(off) * min(0.12, 0.0016 * (dl - 80)))
            both_ready = ready and mate.breed_cd <= 0 and mate.hunger < 50 and mate.guard_t <= 0
            if both_ready and f.fear < 0.3:
                m = f if f.sex == "M" else mate
                if f.sex == "M":
                    f.courting += 1
                if m.courting < 260:                    # the male displays; the female plays coy
                    if f.sex == "M":
                        if dl < 170:
                            f.apply_force(unit(pygame.Vector2(-off.y, off.x)) * math.sin(eco.t * 0.18 + f.id) * 0.34)
                            f.apply_force(unit(off) * (0.07 if dl > 55 else -0.04))
                        if random.random() < 0.012:
                            add_emote(f, "<3")
                    elif dl < 60:
                        f.apply_force(unit(-off) * 0.04)
                else:                                   # then they swim to the nest site together
                    if f.sex == "M" and m.site is None:
                        m.site = pick_site(m)
                    if m.site is not None:
                        to = m.site - pos
                        if to.length() > 40:
                            f.apply_force(unit(to) * (0.16 if f.sex == "M" else 0.12))
                        else:
                            f.vel *= 0.9
                        if f.sex == "M":
                            if to.length() < 60 and dl < 100:
                                f.nesting += 1
                            else:
                                f.nesting = max(0, f.nesting - 1)
                    if f.sex == "M" and f.courting > 2600:   # no luck: give up for a while
                        f.breed_cd = mate.breed_cd = 1500
                        if f.family in PAIRING:
                            f.courting, f.site, f.nesting = 0, None, 0
                        else:
                            unbond(f)
            else:
                f.nesting = max(0, f.nesting - 1)
    else:
        f.nesting = 0

    # ---- parents defend the nest, the eggs and the fry ----
    if f.guard_t > 0:
        f.guard_t -= 1
        gp = f.guard_pos
        if f.fear < (0.65 if f.sex == "M" else 0.45) and gp is not None:
            off = gp - pos
            if off.length() > (70 if f.sex == "M" else 120):
                f.apply_force(unit(off) * 0.1)
            if off.length() < 170:
                for o in fishes:
                    if o is f or not hasattr(o, "family") or o.partner is f or f in o.parents:
                        continue
                    if o.pos.distance_squared_to(gp) < 100 * 100:
                        f.apply_force(unit(o.pos - pos) * (0.7 if f.sex == "M" else 0.45))
                        push = o.pos - gp
                        if push.length_squared() > 0:
                            o.apply_force(push.normalize() * 0.28)
                        add_emote(f, "!")
                        break
        if f.guard_t == 0:
            f.guard_pos = None
    if f.nest is not None:                            # fry stay close to the nest until they have grown
        if f.nest_t > 0 and f.fear < 0.5:
            f.nest_t -= 1
            off = f.nest - pos
            if off.length() > 90:
                f.apply_force(unit(off) * 0.08)
        else:
            f.nest = None

    # ---- hungry cichlids are hunters too: they pick off small tetras and other fish's fry ----
    if getattr(f, "hunts", False):
        f.hunt_cd = max(0, f.hunt_cd - 1)
        t = f.hunt_target
        if f.hunting > 0:
            f.hunting -= 1
            if t is None or not t.alive or t.hidden or f.fear > 0.5 or f.hunting <= 0:
                f.hunting, f.hunt_target, f.hunt_cd = 0, None, 420
            else:
                f.apply_force(unit(t.pos + t.vel * 5 - pos) * 1.1)
                if pos.distance_to(t.pos) < 24 + 12 * f.z:
                    eat_fish(f, t, 0.35)
                    f.hunger = max(0.0, f.hunger - 60)
                    f.hunting, f.hunt_target, f.hunt_cd = 0, None, 1200
        elif (f.hunt_cd <= 0 and f.growth >= 1.0 and not f.sick and f.fear < 0.3 and f.sleepy < 0.3 and f.refuge is None
              and f.guard_t <= 0 and f.hunger > (80 if len(fishes) < 0.45 * tank_capacity() else 55)):
            best, bd = None, 340 * 340
            for o in fishes:
                if o is f or not hasattr(o, "family") or o.hidden or type(o) is type(f) or f in o.parents:
                    continue
                if o.growth >= 0.7 and not getattr(o, "small_prey", False):
                    continue
                d2 = o.pos.distance_squared_to(pos)
                if d2 < bd:
                    best, bd = o, d2
            if best is not None:
                f.hunting, f.hunt_target = 300, best
                add_emote(f, "!")
            else:
                f.hunt_cd = 120

    # ---- mobbing: brave fish gang up on a lurking hunter ----
    if f.refuge is None and f.fear < 0.5 and f.sleepy < 0.3 and f.family in ("cichlid", "barb", "bala"):
        ready = f.bravery > 0.75 or (bold >= 2 and f.bravery > 0.5)
        if ready:
            for p in predators:
                if p.mobbable and (p.state in ("digest", "recover") or (p.state == "cruise" and p.hunger < 35)):
                    to = p.pos - pos
                    d = to.length()
                    if d < 330:
                        f.mobbing = True
                        if d > 120:
                            f.apply_force(unit(to) * 0.22)
                        else:
                            side = 1 if f.id % 2 else -1
                            f.apply_force(pygame.Vector2(-to.y, to.x) * (side / max(d, 1.0)) * 0.25)
                            if d < 85:
                                f.apply_force(unit(-to) * 0.2)
                        if random.random() < 0.004:
                            add_emote(f, "!")
                        break

    # ---- curiosity: drift over to a still cursor ----
    if (mt["inside"] and mt["still"] > 70 and f.curious > 0.35 and f.fear < 0.2 and f.sleepy < 0.4
            and f.hunger < 60 and f.refuge is None and f.cleaning <= 0 and not f.mobbing and mouse_d < 450):
        if mouse_d > 80:
            f.apply_force(unit(mt["pos"] - pos) * 0.07 * f.curious)
        else:
            f.vel *= 0.9
        f.interest = 20
        if mouse_d < 200:
            add_emote(f, "?")

    # ---- run! ----
    if f.fear > 0.12 and f.refuge is None and not f.mobbing and away.length_squared() > 0:
        f.apply_force(away.normalize() * (0.25 + 0.9 * f.fear))
        if random.random() < 0.08:  # zig-zag so a fleeing school looks frantic
            f.apply_force(pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)) * f.fear)
    if f.fear > 0.5 and not f.settled:
        add_emote(f, "!")

    # ---- schooling: tighter when scared ----
    school = f.social * (1.0 + f.fear * 2.5)
    if mates:
        f.apply_force((centroid / mates - pos) * 0.0008 * school)
        f.apply_force((avg_vel / mates - f.vel) * 0.02 * school)
    f.apply_force(sep * 0.25)

    # ---- tank walls, current ----
    margin = 70
    if pos.x < margin:
        f.apply_force(pygame.Vector2((margin - pos.x) * 0.004, 0))
    elif pos.x > SCREEN_WIDTH - margin:
        f.apply_force(pygame.Vector2((SCREEN_WIDTH - margin - pos.x) * 0.004, 0))
    if pos.y < WATER_TOP + 30:
        f.apply_force(pygame.Vector2(0, (WATER_TOP + 30 - pos.y) * 0.004))
    f.apply_force(pygame.Vector2(eco.current * (1.2 - 0.3 * f.z), 0))

    # ---- speed, stress, mood ----
    f.hunger = max(0.0, f.hunger - 0.09 * clamp(f.sleepy))  # a sleeping fish burns almost nothing
    mult = (1.0 + 0.9 * f.fear) * (1.0 - 0.7 * clamp(f.sleepy))
    if f.cleaning > 0 or f.settled:
        mult = min(mult, 0.45)
    if f.sick:
        mult *= 0.75
    if f.hunting:
        mult *= 1.25
    f.max_speed = f.base_max * mult
    if eco.water < 50:
        f.stress = min(100.0, f.stress + 0.04 * (50 - eco.water) / 50)
    if f.fear > 0.3:
        f.stress = min(100.0, f.stress + 0.18)
    elif f.hunger > 85:
        f.stress = min(100.0, f.stress + 0.05)
    else:
        f.stress = max(0.0, f.stress - 0.02)
    if f.settled and f.sleepy > 0.5:
        f.mood = "sleeping"
        if random.random() < 0.006:
            add_emote(f, "z", 90)
    elif f.settled and f.hidden:
        f.mood = "hiding"
    elif f.fear > 0.45:
        f.mood = "scared"
    elif f.cleaning > 0:
        f.mood = "cleaning"
    elif f.hunting:
        f.mood = "hunting"
    elif f.guard_t > 0 and f.fear < 0.45:
        f.mood = "guarding"
    elif f.partner is not None and f.courting > 0 and f.nesting == 0 and f.courting < 260 and f.sex == "M":
        f.mood = "courting"
    elif f.mobbing:
        f.mood = "bold"
    elif f.interest > 0:
        f.mood = "curious"
        f.interest -= 1
    elif f.hunger > 65:
        f.mood = "hungry"
    else:
        f.mood = "calm"


# ---- hunters ----
class Scrap(FoodPellet):
    """Bits left over from a kill. They sink slowly and any fish will take them."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vel = pygame.Vector2(random.uniform(-0.2, 0.2), random.uniform(0.35, 0.7))

    def draw(self, surface):
        pygame.draw.rect(surface, (225, 150, 150), (int(self.pos.x), int(self.pos.y), 3, 3))


FOAM = {}


def foam_sprite(strength):
    """A raft of bubbles floating at the surface (a channa's nest); cached per strength step."""
    q = max(1, int(strength * 8))
    img = FOAM.get(q)
    if img is None:
        rng = random.Random(11)
        w = 120
        img = pygame.Surface((w, 34), pygame.SRCALPHA)
        spread = 0.2 + 0.8 * q / 8
        for _ in range(8 + 8 * q):
            x = w / 2 + rng.uniform(-1, 1) * w * 0.46 * spread
            y = 17 + rng.uniform(-1, 1) * 8 * (0.5 + 0.5 * spread) - abs(x - w / 2) * 0.05
            r = rng.choice([2, 2, 3, 3, 4, 5])
            pygame.draw.circle(img, (205, 232, 246, 120), (int(x), int(y)), r)
            pygame.draw.circle(img, (240, 250, 255, 215), (int(x), int(y)), r, 1)
            pygame.draw.circle(img, (255, 255, 255, 230), (int(x - r * 0.3), int(y - r * 0.3)), 1)
        FOAM[q] = img
    return img


class BubbleNest:
    """A raft of bubbles at the surface built by a male gourami; it grows while he guards it, then slowly breaks up."""

    def __init__(self, x, y, owner):
        self.x, self.y, self.owner = x, y, owner
        self.s, self.life = 0.05, random.randint(2400, 3600)

    def update(self):
        self.life -= 1
        if self.life > 0 and self.owner.alive:
            self.s = min(1.0, self.s + 0.0012)
        else:
            self.s -= 0.0005
        return self.s > 0

    def draw(self, surface):
        img = foam_sprite(self.s)
        img.set_alpha(int(255 * min(1.0, self.s * 3)))
        surface.blit(img, img.get_rect(center=(int(self.x), int(self.y) + 4)))


foam_nests = []


class Predator(Fish):
    """Base class for the hunters. They ignore food pellets and live off the community fish."""
    label = "Predator"
    hunts_fish = True
    mobbable = False

    def __init__(self, x, y, z):
        super().__init__(x, y)
        self.z = z
        self.z_speed = 0.0
        self.vel = pygame.Vector2(random.choice([-1, 1]), 0) * 0.8
        self.state = "cruise"
        self.timer = 0
        self.cooldown = random.randint(200, 600)
        self.target = None
        self.hunger = random.uniform(10, 40)
        self.annoyance = 0.0
        self.flash = 0.0
        self.mouth = 0.0
        self.anim = random.randint(0, 600)
        self.beat = random.uniform(0, 6)
        self.angle = 0.0
        self.kills = 0
        self.lifetime = None
        self.waypoint = None
        self.way_timer = 0
        self.desired = pygame.Vector2()
        self.accel = 0.04
        self.cruise_speed = 1.2
        self.strike_speed = 12.0
        self.strike_range = 185
        self.strike_dir = pygame.Vector2(1, 0)
        self.name = random.choice(FISH_NAMES)
        self.growth = 1.0
        self.sick = False

    @property
    def mood(self):
        return {"cruise": "prowling", "stalk": "stalking", "strike": "attacking", "digest": "digesting",
                "recover": "recovering", "flee": "fleeing", "leave": "leaving", "lurk": "lurking", "gulp": "gulping air",
                "nest": "guarding nest"}.get(self.state, self.state)

    def hunger_rate(self):
        rate = 0.03 * (1.0 + 0.9 * eco.night)  # hunters hunt harder after dark
        if len(fishes) < 0.45 * tank_capacity():
            rate *= 0.3  # a thin community gets some mercy
        if ACTIVE_SET == "tetra_set":
            rate *= 0.55  # a shoal of small tetras and guppies would be picked off too fast otherwise
        return rate

    def scare_level(self, f):
        r, s = {"stalk": (190, 0.85), "strike": (300, 1.0), "cruise": (130, 0.35),
                "flee": (90, 0.2), "leave": (90, 0.2)}.get(self.state, (80, 0.12))
        d = self.pos.distance_to(f.pos)
        return s * (1.0 - d / r) ** 0.6 if d < r else 0.0

    def startle(self, pos):
        if self.state == "stalk" and self.pos.distance_to(pos) < 380:
            self.state, self.cooldown, self.target = "cruise", 360, None

    def wander(self, speed):
        self.way_timer -= 1
        if self.waypoint is None or self.way_timer <= 0 or self.pos.distance_squared_to(self.waypoint) < 1600:
            self.waypoint = pygame.Vector2(random.randint(90, SCREEN_WIDTH - 90),
                                           random.randint(WATER_TOP + 70, int(SCREEN_HEIGHT - SAND_HEIGHT - 160)))
            self.way_timer = random.randint(300, 600)
        self.desired = unit(self.waypoint - self.pos) * speed

    def pick_target(self, origin, max_dist):
        """Choose the easiest meal: close, alone, sleepy or stressed. A school is hard to single out."""
        best, best_score = None, 1e9
        for f in fishes:
            if not f.alive or getattr(f, "hidden", False) or abs(f.z - self.z) > 0.6 or getattr(f, "puff", 0.0) > 0.7:
                continue
            d = origin.distance_to(f.pos)
            if d > max_dist:
                continue
            score = d - 120 * getattr(f, "sleepy", 0.0) - 0.7 * getattr(f, "stress", 0.0)
            score += 28 * sum(1 for o in fishes if o is not f and o.pos.distance_squared_to(f.pos) < 100 * 100)
            if score < best_score:
                best, best_score = f, score
        return best

    def catch(self, point, radius):
        for f in fishes:
            if not f.alive or getattr(f, "hidden", False) or abs(f.z - self.z) > 0.6 or getattr(f, "puff", 0.0) > 0.7:
                continue
            r = radius * (1.0 - 0.35 * getattr(f, "fear", 0.0))
            if point.distance_squared_to(f.pos) < r * r and random.random() < 0.55:
                return f
        return None

    def kill(self, prey):
        burst(prey.pos, (210, 220, 235), 10, 2.6, 70, 2)
        eat_fish(self, prey, 0.5)

    def check_mobbing(self):
        """Enough brave fish nagging a resting hunter will drive it off."""
        if not self.mobbable:
            return
        self.annoyance = max(0.0, self.annoyance - 0.4)
        if self.state not in ("cruise", "digest", "recover"):
            return
        mobbers = sum(1 for f in fishes if getattr(f, "mobbing", False)
                      and f.pos.distance_squared_to(self.pos) < 220 * 220)
        if mobbers >= 3:
            self.annoyance += mobbers * 0.5
        if self.annoyance > 900:
            self.annoyance = 0.0
            self.state, self.timer, self.cooldown = "flee", 420, 700
            notify(f"The community drove off the {self.label.lower()}!")

    def move(self):
        self.vel += (self.desired - self.vel) * self.accel
        cap = self.strike_speed if self.state == "strike" else self.max_speed
        if self.vel.length() > cap:
            self.vel.scale_to_length(cap)
        self.pos += self.vel
        if self.state != "leave":
            if self.pos.y < WATER_TOP + 40 and self.state != "gulp":
                self.vel.y += 0.05
            if self.pos.y > ground_y(self.pos.x) - 45:
                self.vel.y -= 0.05
            if self.pos.x < 30:
                self.vel.x += 0.06
            elif self.pos.x > SCREEN_WIDTH - 30:
                self.vel.x -= 0.06
        if self.vel.length() > 0.1:
            ta = max(-35, min(35, math.degrees(math.atan2(-self.vel.y, abs(self.vel.x)))))
            self.angle += (ta - self.angle) * 0.15


class Channa(Predator):
    """Open-water ambusher: lurks, stalks slowly, then blasts in. Goes after strays and sleepers."""
    label = "Channa"
    mobbable = True

    def __init__(self, x, y, visitor=False):
        super().__init__(x, y, random.uniform(0.62, 0.8))
        self.max_speed = 5.0
        self.cruise_speed = 1.3
        self.strike_speed = 13.0
        self.strike_range = 185
        self.visitor = visitor
        self.lifetime = random.randint(2800, 4200) if visitor else None
        self.home = pygame.Vector2(random.randint(220, SCREEN_WIDTH - 220), random.randint(WATER_TOP + 170, int(SCREEN_HEIGHT - SAND_HEIGHT - 230)))
        self.air_cd = random.randint(1500, 2600)            # snakeheads breathe air: a trip to the surface now and then
        self.nest_cd = random.randint(2400, 4200)
        self.nest = None                                    # [x, y, strength] of a floating bubble nest
        self.gulped = False

    def wants_prey(self):
        if self.hunger > 55:
            return True
        if self.hunger > 25:
            for f in fishes:
                if (getattr(f, "sleepy", 0) > 0.6 and not getattr(f, "hidden", False)
                        and f.pos.distance_squared_to(self.pos) < 240 * 240):
                    return True
        return False

    def update(self):
        self.anim += 1
        self.timer -= 1
        self.cooldown -= 1
        self.hunger = min(100.0, self.hunger + self.hunger_rate())
        arousal = {"strike": 1.0, "stalk": 0.65, "flee": 0.5}.get(self.state, 0.1)
        self.flash += (arousal - self.flash) * 0.06
        self.mouth += ((9.0 if self.state == "strike" else 6.0 if (self.state == "gulp" and self.gulped) else 0.0) - self.mouth) * 0.3
        self.beat += 0.1 + 0.045 * self.vel.length()
        if self.lifetime is not None:
            self.lifetime -= 1
            if self.lifetime <= 0 and self.state != "leave":
                self.state = "leave"
        self.check_mobbing()
        self.air_cd -= 1
        self.nest_cd -= 1
        self.patrol_chase()
        self.tend_nest()
        self.accel = 0.04
        getattr(self, "state_" + self.state)()
        self.move()
        if self.state == "leave" and (self.pos.x < -160 or self.pos.x > SCREEN_WIDTH + 160):
            self.alive = False

    def state_cruise(self):
        self.wander(self.cruise_speed)
        if self.cooldown > 0:
            return
        if self.wants_prey():
            self.target = self.pick_target(self.pos, 650)
            if self.target:
                if self.hunger > 30 and random.random() < 0.5:   # ambush: sit still and let a meal swim past
                    self.state, self.timer, self.target = "lurk", random.randint(420, 840), None
                else:
                    self.state, self.timer = "stalk", 720
            else:
                self.cooldown = 90
        elif self.air_cd <= 0:
            self.state, self.timer, self.gulped = "gulp", 900, False
        elif not self.visitor and self.nest_cd <= 0 and self.hunger < 45 and len(fishes) > 8:
            self.nest = [min(max(self.home.x, 140), SCREEN_WIDTH - 140), WATER_TOP + 8, 0.05]
            self.state, self.timer = "nest", random.randint(1500, 2400)
            notify("A channa is blowing a bubble nest at the surface", log=True)
        elif random.random() < 0.002:
            self.state, self.timer = "lurk", random.randint(240, 480)

    def wander(self, speed):
        """A resident channa patrols around its own patch of the tank; a visitor roams freely."""
        if self.visitor:
            return super().wander(speed)
        self.way_timer -= 1
        if self.waypoint is None or self.way_timer <= 0 or self.pos.distance_squared_to(self.waypoint) < 1600:
            wp = self.home + pygame.Vector2(random.uniform(-300, 300), random.uniform(-110, 110))
            self.waypoint = pygame.Vector2(max(90, min(SCREEN_WIDTH - 90, wp.x)), max(WATER_TOP + 70, min(SCREEN_HEIGHT - SAND_HEIGHT - 160, wp.y)))
            self.way_timer = random.randint(260, 460)
        self.desired = unit(self.waypoint - self.pos) * speed

    def patrol_chase(self):
        """Residents shoulder small fish out of their territory (and out of the nest area) without eating them."""
        if self.visitor or self.state not in ("cruise", "lurk", "nest") or (eco.t + getattr(self, "id", 0)) % 6:
            return
        r = 200 if self.state == "nest" else 115
        for f in fishes:
            if f.alive and abs(f.z - self.z) < 0.5 and f.pos.distance_squared_to(self.pos) < r * r:
                f.apply_force(unit(f.pos - self.pos) * 0.9)

    def tend_nest(self):
        if self.nest is None:
            return
        if self.state == "nest":
            self.nest[2] = min(1.0, self.nest[2] + 0.0012)
        else:
            self.nest[2] -= 0.00035
            if self.nest[2] <= 0:
                self.nest = None

    def draw_nest(self, surface):
        img = foam_sprite(self.nest[2])
        img.set_alpha(int(255 * min(1.0, self.nest[2] * 3)))
        surface.blit(img, img.get_rect(center=(int(self.nest[0]), int(self.nest[1]) + 4)))

    def state_lurk(self):
        """Motionless ambush: bursts out the moment something swims within reach."""
        self.desired = pygame.Vector2()
        self.accel = 0.07
        if self.timer <= 0:
            self.state, self.cooldown = "cruise", 180
            return
        if self.hunger > 25 and (eco.t + getattr(self, "id", 0)) % 3 == 0:
            for f in fishes:
                if (f.alive and not getattr(f, "hidden", False) and abs(f.z - self.z) < 0.5
                        and f.pos.distance_squared_to(self.pos) < (self.strike_range * 0.8) ** 2):
                    self.strike_dir = unit(f.pos + f.vel * 8 - self.pos)
                    self.state, self.timer = "strike", 32
                    return

    def state_gulp(self):
        """Up for a gulp of air at the surface, then back down."""
        top = WATER_TOP + 24
        if not self.gulped:
            side = 1.0 if self.vel.x >= 0 else -1.0
            self.desired = pygame.Vector2(0.6 * side, -2.4)
            if self.pos.y <= top:
                self.gulped, self.timer = True, 50
                ripples.append([pygame.Vector2(self.pos.x + 60 * self.z * side, WATER_TOP), 4.0, 50])
                for _ in range(3):
                    bubbles.append(Bubble(self.pos.x + random.uniform(-10, 10), self.pos.y))
                play_sfx("bubble", 0.45)
            elif self.timer <= 0:
                self.state, self.air_cd = "cruise", 1200
        else:
            self.desired = pygame.Vector2(0, 0.5)
            if self.timer <= 0:
                self.state, self.air_cd, self.waypoint = "cruise", random.randint(2200, 3600), None

    def state_nest(self):
        """Hovers under its bubble nest and guards it."""
        if self.nest is None:
            self.state = "cruise"
            return
        goal = pygame.Vector2(self.nest[0], self.nest[1] + 54)
        to = goal - self.pos
        self.desired = unit(to) * min(1.0, to.length() * 0.025) if to.length() > 8 else pygame.Vector2(math.sin(self.anim * 0.02) * 0.15, 0)
        if self.anim % 70 == 0:
            bubbles.append(Bubble(self.nest[0] + random.uniform(-30, 30), self.nest[1] + 34))
        if self.timer <= 0 or self.hunger > 75:
            self.state, self.cooldown, self.nest_cd, self.waypoint = "cruise", 200, random.randint(5000, 8000), None

    def state_stalk(self):
        t = self.target
        if t is None or not t.alive or getattr(t, "hidden", False) or self.timer <= 0:
            self.state, self.cooldown, self.target = "cruise", 240, None
            return
        to = t.pos - self.pos
        d = to.length()
        self.desired = unit(to) * (1.5 + 1.3 * clamp(1.0 - d / 380.0))
        if d < self.strike_range and random.random() < 0.15:
            lead = t.pos + t.vel * (d / self.strike_speed)
            self.strike_dir = unit(lead - self.pos)
            self.state, self.timer = "strike", 32

    def state_strike(self):
        self.accel = 0.45
        self.desired = self.strike_dir * self.strike_speed
        victim = self.catch(self.pos + self.strike_dir * 92 * self.z, 34)
        if victim:
            self.kill(victim)
            self.state, self.timer, self.target = "digest", random.randint(900, 1500), None
            self.hunger = max(0.0, self.hunger - 80)
        elif self.timer <= 0:
            self.state, self.timer, self.cooldown, self.target = "recover", 160, 300, None
            eco.scare(0.08)

    def state_recover(self):
        self.wander(self.cruise_speed * 0.5)
        if self.timer <= 0:
            self.state = "cruise"

    def state_digest(self):
        self.wander(self.cruise_speed * 0.6)
        if self.timer <= 0:
            self.state = "cruise"

    def state_flee(self):
        side = 1 if self.pos.x > SCREEN_WIDTH / 2 else -1
        self.desired = pygame.Vector2(side * 3.2, -0.3)
        self.accel = 0.06
        if self.timer <= 0:
            self.state, self.waypoint = "cruise", None

    def state_leave(self):
        side = 1 if self.pos.x > SCREEN_WIDTH / 2 else -1
        self.desired = pygame.Vector2(side * 2.8, 0)

    def draw(self, surface):
        """Black and yellow snakehead (channa): drawn once per pose and cached, then flipped, rotated and blitted."""
        if self.nest is not None:
            self.draw_nest(surface)
        self.draw_shadow(surface, 46)
        tau = math.tau
        bq = int((self.beat % tau) / tau * 12) % 12
        key = ("channa", round(clamp(self.flash) * 6), min(9, int(round(self.mouth))), bq, round(self.z * 30), int((self.vigor() + 1) * 3))
        sprite = SPRITE_CACHE.get(key)
        if sprite is None:
            fs = self.render_channa(bq * tau / 12)
            sprite = pygame.transform.smoothscale(fs, (fs.get_width() // SS, fs.get_height() // SS))
            if len(SPRITE_CACHE) > 2500:
                SPRITE_CACHE.clear()
            SPRITE_CACHE[key] = sprite
        facing = self.vel.x >= 0
        ab = int(round(self.angle / 3.0))
        rkey = (key, facing, ab)
        img = ROT_CACHE.get(rkey)
        if img is None:
            img = sprite if facing else pygame.transform.flip(sprite, True, False)
            img = pygame.transform.rotate(img, ab * 3.0 if facing else -ab * 3.0)
            if len(ROT_CACHE) > 2500:
                ROT_CACHE.clear()
            ROT_CACHE[rkey] = img
        surface.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))

    def render_channa(self, beat):
        """A snakehead: a long, almost cylindrical body of even depth that undulates as it swims, small cycloid scales in a mosaic of
        black and golden-yellow patches over a cream belly, ONE long dorsal fin from just behind the head to the tail and a long anal
        fin, a rounded caudal fin with curved bands, big rounded pectoral fins, small pelvic fins, and the snakelike head: flat on top,
        covered in large plates, a very wide mouth reaching back past a small high eye, a protruding lower jaw with canine teeth,
        and tube-like nostrils on the snout."""
        z = self.z * SS
        surf_w, surf_h = int(270 * z), int(110 * z)
        fs = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2
        heat = clamp(self.flash)
        black = self.get_depth_color(mix((22, 20, 18), (42, 26, 14), heat * 0.6))
        gold = self.get_depth_color(mix((222, 172, 34), (255, 146, 28), heat * 0.7))
        gold_hi = self.get_depth_color(mix((248, 222, 112), (255, 188, 78), heat * 0.6))
        cream = self.get_depth_color(mix((236, 214, 140), (244, 176, 84), heat * 0.5))
        fin_col = self.get_depth_color((30, 26, 20))
        fin_edge = self.get_depth_color(mix((236, 184, 44), (255, 140, 30), heat))
        amp = 3.6 * z

        def uu(px):
            return (px + 94) / 188

        def wave(px):   # the whole body flexes in an S, more towards the tail
            u = uu(px)
            return math.sin(beat - u * 4.2) * amp * (1 - u) ** 1.5

        def half(u):    # even depth along the body, narrow tail stalk, flat tapering head
            t = min(1.0, u / 0.3)
            body = 3.0 + 10.2 * math.sin(t * math.pi / 2) ** 0.8
            head = max(0.0, (u - 0.8) / 0.2)
            return body * (1 - 0.52 * head ** 2.0)

        def top_y(px):
            return cy + wave(px) - half(uu(px)) * 0.97 * z

        def bot_y(px):
            return cy + wave(px) + half(uu(px)) * z

        def mid_y(px):
            return cy + wave(px)

        # ---- fins behind the body ----
        tw = wave(-92)
        tail_free = [(cx - 95 * z, cy + tw - 13 * z), (cx - 106 * z, cy + tw - 9 * z), (cx - 111 * z, cy + tw),
                     (cx - 106 * z, cy + tw + 9 * z), (cx - 95 * z, cy + tw + 13 * z)]
        draw_fin(fs, fin_shape((cx - 85 * z, cy + tw - 2.5 * z), tail_free, (cx - 85 * z, cy + tw + 2.5 * z)), fin_col, 9,
                 (cx - 86 * z, cy + tw), 235, fin_edge, SS, gold)
        for r, al in ((8, 230), (13, 215), (18, 200)):   # curved golden bands across the tail
            pygame.draw.arc(fs, (*gold, al), (cx - (86 + r * 0.55) * z, cy + tw - r * 0.95 * z, r * 1.1 * z, r * 1.9 * z), math.pi * 0.62, math.pi * 1.38, max(1, SS))
        dors = [(cx + px * z, top_y(px) - h * z) for px, h in ((-66, 5), (-44, 7), (-20, 8), (4, 8), (28, 7), (50, 5.5))]
        draw_fin(fs, fin_shape((cx - 76 * z, top_y(-76) + 1 * z), dors, (cx + 56 * z, top_y(56) + 1 * z)), fin_col, 26,
                 (cx - 10 * z, top_y(-10) + 3 * z), 235, fin_edge, SS, gold)
        anal = [(cx + px * z, bot_y(px) + h * z) for px, h in ((-60, 5), (-40, 6.5), (-18, 7), (4, 6))]
        draw_fin(fs, fin_shape((cx - 68 * z, bot_y(-68) - 1 * z), anal, (cx + 14 * z, bot_y(14) - 1 * z)), fin_col, 18,
                 (cx - 24 * z, bot_y(-24) - 3 * z), 235, fin_edge, SS, gold)
        pelv = [(cx + 40 * z, bot_y(40) + 8 * z), (cx + 31 * z, bot_y(31) + 9 * z)]
        draw_fin(fs, fin_shape((cx + 46 * z, bot_y(46) - 1 * z), pelv, (cx + 34 * z, bot_y(34) - 1 * z)), tone(gold, 0.85), 3,
                 (cx + 40 * z, bot_y(40)), 225, fin_edge, SS)

        # ---- body ----
        profile = [-94 + 188 * k / 40 for k in range(41)]
        body_pts = ([(cx + px * z, top_y(px)) for px in profile] + [(cx + px * z, bot_y(px)) for px in reversed(profile)])
        shaded_polygon(fs, body_pts, black, tone(black, 1.35))
        mask = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), body_pts)
        layer = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        # cream belly, with the gold-black mosaic sitting above it
        pygame.draw.polygon(layer, (*cream, 255), [(cx + px * z, mid_y(px) + half(uu(px)) * 0.42 * z) for px in profile]
                            + [(cx + px * z, bot_y(px)) for px in reversed(profile)])
        sw, sh = 5.4, 4.6   # scale size
        for row in range(-3, 3):
            for col in range(0, 36):
                px = -90 + col * sw + (sw / 2 if row % 2 else 0)
                u = uu(px)
                if u > 0.9:
                    continue
                py = row * sh + 1.0
                n = math.sin(col * 0.78 + row * 1.9 + 1.3) + math.sin(col * 0.33 - row * 0.7) + 0.6 * math.sin(col * 1.7 + row * 0.4 + 2.0)
                yellow = n > 0.3
                body_c = gold if yellow else black
                if row == 2:   # the lowest row blends into the belly
                    body_c = mix(body_c, cream, 0.5)
                cxx, cyy = cx + px * z, mid_y(px) + py * z
                rect = (cxx - sw * 0.62 * z, cyy - sh * 0.62 * z, sw * 1.24 * z, sh * 1.24 * z)
                pygame.draw.ellipse(layer, (*body_c, 255), rect)
                pygame.draw.arc(layer, (*tone(body_c, 0.55), 200), rect, math.pi * 0.55, math.pi * 1.45, max(1, SS // 2))
                if yellow:
                    pygame.draw.circle(layer, (*gold_hi, 160), (int(cxx - 0.8 * z), int(cyy - 0.6 * z)), max(1, int(1.1 * z)))
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        fs.blit(layer, (0, 0))
        pygame.draw.lines(fs, tone(black, 0.7), True, body_pts, SS)

        # ---- head ----
        nose = cx + 94 * z
        hy = mid_y(94)
        gape = self.mouth * z
        gx = cx + 58 * z
        # operculum (gill cover): large plates with a dark rim
        pygame.draw.arc(fs, tone(black, 0.55), (gx - 8 * z, hy - 15 * z + wave(58) - hy + cy, 22 * z, 30 * z), math.pi * 0.5, math.pi * 1.5, SS)
        pygame.draw.arc(fs, tone(gold, 0.8), (gx - 4 * z, hy - 11 * z + wave(58) - hy + cy, 18 * z, 22 * z), math.pi * 0.55, math.pi * 1.45, SS)
        # head plates: big scales over the flat top of the head
        for k, (a0, a1) in enumerate(((0.45, 0.8), (0.2, 0.55), (0.0, 0.3))):
            pygame.draw.arc(fs, tone(gold, 0.5), (nose - (50 - 9 * k) * z, hy - 9 * z, 24 * z, 14 * z), math.pi * (0.1 + a0), math.pi * (0.55 + a1), max(1, SS // 2))
        # pectoral fin: broad and rounded, right behind the gill cover
        pb = [(cx + 66 * z, hy + 4 * z), (cx + 64 * z, hy + 13 * z)]
        pec = [(cx + 52 * z, hy + 12 * z + math.sin(beat * 1.3) * 2 * z), (cx + 47 * z, hy + 20 * z), (cx + 55 * z, hy + 25 * z), (cx + 65 * z, hy + 22 * z)]
        draw_fin(fs, fin_shape(pb[0], pec, pb[1]), tone(fin_col, 1.3), 7, (cx + 64 * z, hy + 9 * z), 235, fin_edge, SS, gold)
        # mouth: very wide, the gape runs back beneath the eye; lower jaw juts out past the upper
        upper_y = hy + 2.5 * z
        if self.mouth > 1.0:
            pygame.draw.polygon(fs, (118, 32, 32), smooth_closed([(nose - 46 * z, upper_y), (nose + 1 * z, upper_y - 0.5 * z),
                                                                  (nose - 14 * z, upper_y + 7 * z + gape)], 3))
        jaw = [(nose - 46 * z, upper_y + 2 * z + gape * 0.15), (nose - 26 * z, upper_y + 7 * z + gape * 0.8),
               (nose - 4 * z, upper_y + 7.5 * z + gape * 0.7), (nose + 4 * z, upper_y + 4 * z + gape * 0.3),
               (nose + 4 * z, upper_y + 0.5 * z), (nose - 46 * z, upper_y + 0.5 * z)]
        pygame.draw.polygon(fs, tone(black, 1.5), smooth_closed(jaw, 3))
        for k in range(4):
            pygame.draw.circle(fs, gold, (int(nose - (10 + 9 * k) * z), int(upper_y + (4.5 + 0.8 * (k % 2)) * z + gape * 0.4)), max(1, int(1.1 * z)))
        pygame.draw.lines(fs, tone(black, 0.6), True, smooth_closed(jaw, 3), SS)
        pygame.draw.line(fs, tone(black, 0.5), (nose - 46 * z, upper_y + 0.5 * z), (nose + 4 * z, upper_y + 0.5 * z), SS)   # the long mouth line
        tcol = (244, 242, 232)
        for k in range(9):   # canine and villiform teeth along both jaws
            tx = nose - (6 + k * 4.6) * z
            tl = (2.8 if k % 3 == 0 else 1.7) * z
            pygame.draw.line(fs, tcol, (tx, upper_y + 0.7 * z), (tx + 0.6 * z, upper_y + 0.7 * z + tl * (1.0 + gape / (6 * z + 1e-6))), max(1, SS // 2))
        if self.mouth > 1.0:
            for k in range(6):
                tx = nose - (8 + k * 5.5) * z
                pygame.draw.line(fs, tcol, (tx, upper_y + 6.2 * z + gape * 0.6), (tx + 0.5 * z, upper_y + 3.4 * z + gape * 0.55), max(1, SS // 2))
        # snout: tube nostrils
        pygame.draw.line(fs, tone(black, 1.6), (nose - 4 * z, hy - 4.5 * z), (nose - 4 * z, hy - 7 * z), max(1, SS))
        pygame.draw.circle(fs, tone(gold, 0.8), (int(nose - 4 * z), int(hy - 7.4 * z)), max(1, int(1.2 * z)))
        # golden vermiculation across the head
        for k in range(6):
            sx = nose - (10 + 6.5 * k) * z
            sy = hy - (5.5 - (k % 3) * 1.6) * z
            pygame.draw.line(fs, gold, (sx, sy), (sx + 3.5 * z, sy - 1.2 * z + (k % 2) * 2 * z), max(1, SS))
        # small eye, set high on the head about a third of the way back from the snout, with a dark streak behind it
        ex, ey = int(nose - 26 * z), int(hy - 6 * z)
        pygame.draw.line(fs, tone(black, 0.4), (ex + 3 * z, ey), (gx - 2 * z, ey + 3 * z), max(1, SS))
        draw_eye(fs, ex, ey, 3.7 * z, (238, 150, 34), tone(black, 0.4))
        return fs


class FireEel(Predator):
    """Lives in a rock. Peeks out, scans, and lunges at anything that swims past its lair."""
    label = "Fire eel"

    def __init__(self, rock):
        super().__init__(rock.pos_x, rock.base_y, max(0.5, rock.z - 0.03))
        self.rock = rock
        sink = int(35 * rock.z) if rock.y_offset >= 0 else 0
        bottom = rock.base_y + rock.y_offset + sink
        self.lair = pygame.Vector2(rock.pos_x, bottom - rock.image.get_height() * 0.42)
        self.pos = pygame.Vector2(self.lair)
        self.dir = 1 if rock.pos_x < SCREEN_WIDTH / 2 else -1
        self.edge = rock.image.get_width() * 0.5
        self.scale = self.z
        self.reach = self.edge + 185 * self.scale
        self.ext = self.edge * 0.55
        self.ext_goal = self.ext
        self.aim = 0.0
        self.state = "hidden"
        self.timer = random.randint(120, 360)
        self.path = []
        self.spots = [(random.uniform(-0.5, 0.5), random.uniform(0.9, 1.6)) for _ in range(40)]
        self.head_dir = pygame.Vector2(self.dir, 0)

    def hunger_ready(self):
        return self.hunger > 45 or (eco.night > 0.5 and self.hunger > 25)

    def scare_level(self, f):
        if self.ext < self.edge * 0.9:
            return 0.0
        r, s = (150, 0.9) if self.state == "strike" else (110, 0.6) if self.state == "scan" else (60, 0.2)
        d = self.pos.distance_to(f.pos)
        return s * (1.0 - d / r) ** 0.6 if d < r else 0.0

    def startle(self, pos):
        if self.state in ("peek", "scan") and self.lair.distance_to(pos) < 380:
            self.state, self.timer, self.cooldown = "retreat", 200, 300

    def aim_at(self, point, rate=0.35):
        to = point - self.lair
        ang = math.atan2(to.y, abs(to.x))
        if to.x * self.dir < 0:
            ang = math.copysign(1.2, to.y)
        self.aim += (max(-1.25, min(1.25, ang)) - self.aim) * rate

    def pick_victim(self):
        best, best_d = None, self.reach * 0.92
        for f in fishes:
            if not f.alive or getattr(f, "hidden", False) or abs(f.z - self.z) > 0.6:
                continue
            if (f.pos.x - self.lair.x) * self.dir < -20:
                continue
            d = self.lair.distance_to(f.pos)
            if self.edge * 0.8 < d < best_d:
                best, best_d = f, d
        return best

    def update(self):
        self.anim += 1
        self.timer -= 1
        self.cooldown -= 1
        self.hunger = min(100.0, self.hunger + self.hunger_rate())
        self.flash += ((1.0 if self.state in ("scan", "strike") else 0.0) - self.flash) * 0.08
        self.mouth += ((10.0 if self.state == "strike" else 2.5 if self.state == "scan" else 0.0) - self.mouth) * 0.2
        getattr(self, "state_" + self.state)()
        self.ext = clamp(self.ext, self.edge * 0.5, self.reach)
        self.path = self.compute_path()
        self.pos = pygame.Vector2(self.path[-1])
        self.head_dir = unit(self.path[-1] - self.path[-3], (self.dir, 0))

    def state_hidden(self):
        self.ext += (self.edge * 0.55 - self.ext) * 0.1
        if self.timer <= 0:
            if self.hunger_ready() and self.cooldown <= 0:
                self.state, self.timer = "scan", 520
            else:
                self.state, self.timer = "peek", random.randint(90, 220)

    def state_peek(self):
        goal = self.edge + 22 * self.scale
        self.ext += (goal - self.ext) * 0.1
        mt = mouse_track
        if mt["inside"] and mt["still"] > 30 and mt["pos"].distance_to(self.lair) < 320:
            self.aim_at(mt["pos"], 0.08)  # curious about the cursor
        else:
            self.aim += (math.sin(self.anim * 0.02) * 0.4 - self.aim) * 0.05
        if self.hunger_ready() and self.cooldown <= 0 and self.pick_victim():
            self.state, self.timer = "scan", 520
        elif self.timer <= 0:
            self.state, self.timer = "hidden", random.randint(150, 420)

    def state_scan(self):
        goal = self.edge + 70 * self.scale
        self.ext += (goal - self.ext) * 0.1
        victim = self.pick_victim()
        if victim:
            self.aim_at(victim.pos, 0.12)
            if random.random() < 0.07:
                self.target = victim
                self.state, self.timer = "strike", 28
        else:
            self.aim += (math.sin(self.anim * 0.03) * 0.5 - self.aim) * 0.05
        if self.timer <= 0:
            self.state, self.timer, self.cooldown = "retreat", 200, 300

    def state_strike(self):
        t = self.target
        if t is not None and t.alive:
            self.aim_at(t.pos, 0.5)
            goal = min(self.reach, self.lair.distance_to(t.pos) + 12)
        else:
            goal = self.ext
        self.ext = min(goal, self.ext + 18)
        mouth = self.pos + self.head_dir * 20 * self.scale
        victim = self.catch(mouth, 26 + 14 * self.scale)
        if victim:
            self.kill(victim)
            self.state, self.timer = "retreat", random.randint(1100, 1700)
            self.hunger = max(0.0, self.hunger - 80)
            self.target = None
        elif self.timer <= 0:
            self.state, self.timer, self.cooldown, self.target = "retreat", 200, 300, None

    def state_retreat(self):
        self.ext -= 6
        self.aim *= 0.9
        if self.ext <= self.edge * 0.56:
            self.state = "hidden"

    def compute_path(self):
        n = 28
        tip_dir = pygame.Vector2(math.cos(self.aim) * self.dir, math.sin(self.aim))
        tip = self.lair + tip_dir * self.ext
        ctrl = self.lair + pygame.Vector2(self.dir, 0) * self.ext * 0.55
        pts = []
        for i in range(n):
            u = i / (n - 1)
            p = (1 - u) ** 2 * self.lair + 2 * (1 - u) * u * ctrl + u ** 2 * tip
            tangent = 2 * (1 - u) * (ctrl - self.lair) + 2 * u * (tip - ctrl)
            if tangent.length_squared() > 0:
                nrm = pygame.Vector2(-tangent.y, tangent.x).normalize()
                p = p + nrm * (math.sin(self.anim * 0.09 - u * 7.0) * (3 + 8 * self.flash) * self.scale * u)
            pts.append(p)
        return pts

    def draw(self, surface):
        """Fire eel (Mastacembelus): a long, slim brown body with a pale belly, one continuous dorsal fin and an anal fin,
        wavy orange 'flame' stripes, and a pointed head with a fleshy snout tip, tiny high eye and a small underslung mouth."""
        pts = self.path
        if len(pts) < 3 or self.ext < self.edge * 0.62:
            return
        s, n, d = self.scale, len(pts), self.dir
        base = self.get_depth_color((62, 44, 34))
        back = self.get_depth_color((38, 27, 23))
        belly = self.get_depth_color((186, 142, 100))
        fire = self.get_depth_color((238, 96, 28))
        glow = self.get_depth_color((255, 172, 74))
        finc = self.get_depth_color((118, 62, 36))
        nrm, rad = [], []
        for i in range(n):
            t = unit(pts[min(n - 1, i + 1)] - pts[max(0, i - 1)], (d, 0))
            nrm.append(pygame.Vector2(t.y * d, -t.x * d))   # towards the eel's back
            rad.append(s * (9.6 - 1.2 * i / (n - 1)))

        def edge(i, k):
            return pts[i] + nrm[i] * rad[i] * k

        def fin_band(side, height, lo, hi):
            idx = [i for i in range(n) if lo <= i / (n - 1) <= hi]
            if len(idx) < 3:
                return
            root = [edge(i, 0.9 * side) for i in idx]
            tip = []
            for j, i in enumerate(idx):
                u = j / (len(idx) - 1)
                h = height * rad[i] * (math.sin(math.pi * u) ** 0.5) * (1.0 + 0.12 * math.sin(self.anim * 0.12 - i * 0.7))
                tip.append(root[j] + nrm[i] * h * side)
            pygame.draw.polygon(surface, finc, root + tip[::-1])
            for j in range(0, len(idx), 2):
                pygame.draw.line(surface, tone(finc, 1.4), root[j], tip[j], 1)
            pygame.draw.lines(surface, fire, False, tip, max(1, int(1.3 * s)))

        fin_band(1, 0.8, 0.05, 0.92)     # the long dorsal fin
        fin_band(-1, 0.55, 0.2, 0.92)    # and the anal fin
        upper = [edge(i, 1.0) for i in range(n)]
        lower = [edge(i, -1.0) for i in range(n)]
        pygame.draw.polygon(surface, base, upper + lower[::-1])
        pygame.draw.polygon(surface, back, upper + [edge(i, 0.45) for i in range(n - 1, -1, -1)])          # dark back
        pygame.draw.polygon(surface, belly, [edge(i, -0.4) for i in range(n)] + lower[::-1])               # pale belly
        for off, wid, phase in ((0.26, 1.5, 0), (-0.12, 1.3, 2)):   # broken, wavy flame stripes
            run = []
            for i in range(1, n - 1):
                if (i + phase) % 5 == 4:
                    if len(run) > 1:
                        pygame.draw.lines(surface, fire, False, run, max(1, int(wid * s)))
                    run = []
                    continue
                run.append(edge(i, off + 0.1 * math.sin(i * 0.9 + phase)))
            if len(run) > 1:
                pygame.draw.lines(surface, fire, False, run, max(1, int(wid * s)))
        for i in range(2, n - 2, 3):
            q = edge(i, -0.26 + 0.1 * math.sin(i))
            pygame.draw.circle(surface, glow, (int(q.x), int(q.y)), max(1, int(1.1 * s)))
        pygame.draw.lines(surface, tone(base, 0.5), False, upper, 1)
        pygame.draw.lines(surface, tone(base, 0.5), False, lower, 1)

        # ---- head, drawn in a frame that follows the body's last segment ----
        hd = self.head_dir
        up = pygame.Vector2(hd.y * d, -hd.x * d)
        origin = pts[-1] - hd * 3 * s

        def H(a, b):
            q = origin + hd * a * s + up * b * s
            return (q.x, q.y)

        gang = math.radians(min(self.mouth, 10.0) * 2.0)
        hx, hy = 8.0, -2.4

        def jaw(a, b):   # the lower jaw swings down about the hinge
            da, db = a - hx, b - hy
            return H(hx + da * math.cos(gang) + db * math.sin(gang), hy - da * math.sin(gang) + db * math.cos(gang))

        lower_j = [(0, -2.4), (24, -2.0), (36, -1.0), (41, -1.5), (36, -4.4), (22, -7.4), (8, -8.6), (0, -8.6)]
        if self.mouth > 1.0:
            pygame.draw.polygon(surface, (120, 32, 32), [H(8, -2.4), H(44, -0.4), jaw(41, -1.5), jaw(24, -2.0)])
        pygame.draw.polygon(surface, mix(base, belly, 0.55), [jaw(a, b) for a, b in lower_j])
        upper_h = [(0, 8.6), (10, 8.4), (24, 6.8), (36, 4.2), (44, 1.4), (46.5, -0.2), (36, -1.0), (24, -2.0), (8, -2.4), (0, -2.4)]
        pygame.draw.polygon(surface, base, [H(a, b) for a, b in upper_h])
        pygame.draw.polygon(surface, back, [H(0, 8.6), H(10, 8.2), H(24, 5.8), H(36, 3.2), H(44, 1.0), H(36, 2.0), H(24, 3.2), H(8, 4.4), H(0, 4.4)])
        pygame.draw.lines(surface, fire, False, [H(28, 2.4), H(16, 3.0), H(5, 4.4)], max(1, int(1.2 * s)))
        if self.mouth > 1.0:
            for k in range(5):   # needle teeth along the upper jaw
                a = 26 + k * 3.6
                b = -2.0 + (a - 24) * 0.08
                pygame.draw.polygon(surface, (245, 245, 235), [H(a, b), H(a + 2.0, b + 0.1), H(a + 1.0, b - 2.6)])
        pygame.draw.polygon(surface, mix(base, belly, 0.3), [H(43, 1.6), H(50, 3.4), H(51.5, 1.8), H(46.5, -0.1)])   # fleshy snout tip
        pygame.draw.polygon(surface, back, [H(43, 1.6), H(50, 3.4), H(51.5, 1.8), H(46.5, -0.1)], 1)
        pygame.draw.circle(surface, back, (int(H(38, 2.4)[0]), int(H(38, 2.4)[1])), max(1, int(0.9 * s)))     # nostril
        ex, ey = H(30, 3.6)
        draw_eye(surface, int(ex), int(ey), max(2.0, 2.3 * s), (222, 150, 44), back)
        pygame.draw.lines(surface, tone(base, 0.5), False, [H(7, 7.6), H(9, 2), H(8, -6)], 1)                  # gill cover
        flap = 1.2 * math.sin(self.anim * 0.15)
        pec = [H(9, -3.5), H(1, -7.4 + flap), H(-2, -5.2), H(4, -2.8)]
        pygame.draw.polygon(surface, finc, pec)
        pygame.draw.lines(surface, fire, False, pec[1:3], 1)


class Crayfish(Predator):
    """A bottom-dweller: camouflaged at rest, creeps toward shrimp and pounces with open claws, flicks its tail to
    shoot backwards away from danger, and raises a claw toward a still cursor."""
    label = "Crayfish"
    hunts_fish = False

    def __init__(self):
        x = random.randint(150, SCREEN_WIDTH - 150)
        super().__init__(x, ground_y(x) - 24, 0.93)  # z above 0.9: drawn in front of the plants
        self.state = "rest"
        self.timer = random.randint(200, 500)
        self.cooldown = 0
        self.ink_cd = 0
        self.max_speed = 7.0
        self.col = [150.0, 64.0, 44.0]
        self.camo = 1.0
        self.face = random.choice([-1, 1])
        self.goal_x = x
        self.flee_dir = pygame.Vector2(1, 0)
        self.reach_amt = 0.0
        self.reach_pt = pygame.Vector2()
        self.claw_open = 0.0

    def scare_level(self, f):
        return 0.0

    def startle(self, pos):
        if self.pos.distance_to(pos) < 280 and self.state in ("rest", "crawl"):
            if self.ink_cd <= 0 and random.random() < 0.5:
                self.begin_flee(pos)
            else:
                self.col = [214.0, 112.0, 84.0]  # a startled flush

    def begin_flee(self, src):
        self.flee_dir = unit(self.pos - pygame.Vector2(src), (random.choice([-1, 1]), -0.3))
        self.state, self.timer = "flee", 90
        self.ink_cd = 900
        burst(self.pos, (200, 220, 240), 10, 2.5, 40, 2, -0.02)
        self.col = [214.0, 140.0, 108.0]

    def update(self):
        self.anim += 1
        self.timer -= 1
        self.cooldown -= 1
        self.ink_cd -= 1
        self.hunger = min(100.0, self.hunger + 0.03)
        if self.state != "flee" and self.ink_cd <= 0:
            for p in predators:
                if p is not self and p.hunts_fish and p.scare_level(self) > 0.45:
                    self.begin_flee(p.pos)
                    break
        mt = mouse_track
        want = (mt["inside"] and mt["still"] > 45 and self.state in ("rest", "crawl")
                and mt["pos"].distance_to(self.pos) < 240)
        self.reach_amt += ((1.0 if want else 0.0) - self.reach_amt) * 0.06
        if want:
            self.reach_pt = pygame.Vector2(mt["pos"])
        self.camo_goal = 0.0
        self.accel = 0.05
        getattr(self, "state_" + self.state)()
        self.move()
        if self.camo_goal > 0.5:
            goal = mix(mix((126, 66, 46), (96, 66, 50), 0.5 + 0.5 * math.sin(self.pos.x * 0.01)),
                       (60, 52, 80), eco.night * 0.5)
        elif self.state == "hunt":
            goal = (186, 58, 38)
        else:
            goal = (156, 62, 42)
        for i in range(3):
            self.col[i] += (goal[i] - self.col[i]) * 0.04
        self.camo += (self.camo_goal - self.camo) * 0.04

    def move(self):
        self.vel += (self.desired - self.vel) * self.accel
        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)
        self.pos += self.vel
        self.pos.x = max(40, min(SCREEN_WIDTH - 40, self.pos.x))
        self.pos.y = max(WATER_TOP + 60, min(ground_y(self.pos.x) - 20 * self.z - 2, self.pos.y))

    def rest_y(self):
        return ground_y(self.pos.x) - 20 * self.z - 4

    def state_rest(self):
        self.camo_goal = 1.0
        self.desired = pygame.Vector2()
        self.pos.y += (self.rest_y() - self.pos.y) * 0.05
        if self.timer <= 0:
            if self.hunger > 40 and shimps and self.cooldown <= 0:
                near = min(shimps, key=lambda s: self.pos.distance_squared_to(s.pos))
                if self.pos.distance_to(near.pos) < 520:
                    self.target, self.state, self.timer = near, "hunt", 700
                    return
                self.cooldown = 300
            self.goal_x = max(100, min(SCREEN_WIDTH - 100, self.pos.x + random.randint(-260, 260)))
            self.state, self.timer = "crawl", 600

    def state_crawl(self):
        self.camo_goal = 1.0
        self.pos.y += (self.rest_y() - self.pos.y) * 0.05
        dx = self.goal_x - self.pos.x
        self.desired = pygame.Vector2(math.copysign(0.7, dx), 0)
        if abs(dx) < 8 or self.timer <= 0:
            self.state, self.timer = "rest", random.randint(300, 700)

    def state_hunt(self):
        s = self.target
        if s not in shimps or self.timer <= 0:
            self.state, self.timer, self.cooldown, self.target = "rest", 300, 300, None
            return
        to = s.pos - self.pos
        d = to.length()
        if d < 26:
            shimps.remove(s)
            respawn_queue.append((eco.t + 900, "shrimp"))
            burst(s.pos, (255, 130, 110), 8, 1.8, 40, 2)
            self.hunger = max(0.0, self.hunger - 70)
            self.state, self.timer, self.cooldown, self.target = "rest", 400, 900, None
            return
        self.desired = unit(to) * (1.1 if d > 130 else 6.0)  # sneak up, then pounce
        self.accel = 0.05 if d > 130 else 0.15
        if d <= 130 and random.random() < 0.1:
            bubbles.append(Bubble(self.pos.x, self.pos.y))

    def state_flee(self):
        self.accel = 0.2
        self.desired = self.flee_dir * (6.5 if self.timer > 55 else 1.5)
        if self.timer <= 0:
            self.state, self.timer = "rest", 500

    def draw(self, surface):
        """Red swamp crayfish seen from the side: a rounded carapace with a pointed rostrum and cervical groove, six
        overlapping abdomen segments with pleura, a tail fan, stalked eyes, long antennae, four pairs of walking legs and two
        big red-tipped claws. The claws open wide while hunting, one lifts toward a still cursor, and it tucks its tail to flee."""
        self.draw_shadow(surface, 40)
        s = self.z * 1.5
        x, y = self.pos.x, self.pos.y
        t = self.anim * 0.05
        if self.state == "flee":
            self.face = -1 if self.flee_dir.x > 0 else 1
        elif self.state == "hunt" and self.target is not None:
            self.face = 1 if self.target.pos.x >= x else -1
        elif abs(self.vel.x) > 0.15:
            self.face = 1 if self.vel.x > 0 else -1
        f = self.face
        body = self.get_depth_color(tuple(int(c) for c in self.col))
        dark, light = tone(body, 0.55), tone(body, 1.28)
        under = mix(body, self.get_depth_color((226, 182, 150)), 0.5)       # pale underside
        red = mix(body, self.get_depth_color((208, 66, 38)), 0.5)           # claws run redder than the body
        speed = self.vel.length()
        walk = self.pos.x * 0.22
        fleeing = self.state == "flee"
        hunting = self.state == "hunt"
        reach = self.reach_amt

        def P(dx, dy):
            return (x + f * dx * s, y + dy * s)

        def oval(cx, cy, ang, rl, rw, n=12):
            ca, sa = math.cos(ang), math.sin(ang)
            return [(cx + math.cos(k / n * math.tau) * rl * ca - math.sin(k / n * math.tau) * rw * sa,
                     cy + math.cos(k / n * math.tau) * rl * sa + math.sin(k / n * math.tau) * rw * ca) for k in range(n)]

        # walking legs: four pairs (far side darker), the first two ending in tiny pincers
        foot_y = 21
        for far in (1, 0):
            for k in range(4):
                hx = -9 + k * 6.8
                swing = math.sin(walk + k * 1.6) * 5 * clamp(speed / 1.2) * (1 if k % 2 else -1)
                off = 3 if far else 0
                lift = 3 if swing > 1.5 else 0
                hip = P(hx + off, 8)
                knee = P(hx + 4 + swing * 0.5 + off, 12.5)
                ankle = P(hx + 7 + swing * 0.8 + off, 17.5 - lift)
                foot = P(hx + 4 + swing + off, foot_y - lift)
                col = tone(dark, 0.9) if far else tone(body, 0.8)
                pygame.draw.lines(surface, col, False, [hip, knee, ankle, foot], max(1, int(1.8 * s)))
                if k < 2:
                    pygame.draw.line(surface, col, foot, (foot[0] + f * 3 * s, foot[1] - 0.9 * s), 1)
                    pygame.draw.line(surface, col, foot, (foot[0] + f * 3 * s, foot[1] + 0.2 * s), 1)

        # abdomen: six overlapping segments, each with a pleuron flap hanging below; curls under when it flicks away
        tuck = 1.0 if fleeing else 0.0
        seg = []
        for k in range(6):
            seg.append((-17 - 6.2 * k * (1 - 0.32 * tuck), 1.0 + 0.7 * k + tuck * 0.75 * k * k, 9.4 - 0.55 * k))
        # tail fan first, so the last segment overlaps its root
        ex0, ey0 = P(seg[5][0] - 3.5, seg[5][1] + 2.0)
        for a, ln, wd in ((-0.95, 10, 3.4), (0.95, 10, 3.4), (-0.48, 12, 3.8), (0.48, 12, 3.8), (0.0, 13, 4.3)):
            ta = a * (1.0 + 0.5 * tuck) + 0.2
            dx_, dy_ = -f * math.cos(ta), math.sin(ta)
            cc = (ex0 + dx_ * ln * 0.5 * s, ey0 + dy_ * ln * 0.5 * s)
            poly = oval(cc[0], cc[1], math.atan2(dy_, dx_), ln * 0.5 * s, wd * s)
            pygame.draw.polygon(surface, mix(body, under, 0.25), poly)
            pygame.draw.polygon(surface, dark, poly, 1)
            pygame.draw.line(surface, light, (ex0, ey0), (cc[0] + dx_ * ln * 0.4 * s, cc[1] + dy_ * ln * 0.4 * s), 1)
        for k in range(5, -1, -1):
            cx_, cy_, h = seg[k]
            c = P(cx_, cy_)
            rect = (c[0] - 4.8 * s, c[1] - h * s, 9.6 * s, 2 * h * s)
            pl = [P(cx_ - 3.6, cy_ + h * 0.6), P(cx_ + 3.2, cy_ + h * 0.6), P(cx_ - 0.4, cy_ + h + 3.4)]
            pygame.draw.polygon(surface, under, pl)
            pygame.draw.polygon(surface, dark, pl, 1)
            pygame.draw.ellipse(surface, body, rect)
            pygame.draw.ellipse(surface, light, (rect[0] + 1.4 * s, rect[1] + 0.5 * s, rect[2] - 2.8 * s, h * 0.7 * s), 1)
            pygame.draw.ellipse(surface, dark, rect, 1)
        pygame.draw.lines(surface, tone(body, 0.5), False, [P(cx_, cy_ - h + 0.8) for cx_, cy_, h in seg], max(1, int(1.4 * s)))   # dark dorsal stripe

        # carapace, rostrum, cervical groove
        shell = [P(*q) for q in smooth_closed([(-18, -1), (-15, -9.5), (-6, -13.5), (6, -13), (15, -8.5), (19, -3), (16, 3.5), (8, 9),
                                                (-4, 10.5), (-14, 8.5)], 4)]
        pygame.draw.polygon(surface, body, shell)
        pygame.draw.polygon(surface, dark, shell, 1)
        pygame.draw.lines(surface, light, False, [P(-14, -9), P(-6, -12), P(6, -11.5), P(13, -7.5)], max(1, int(1.5 * s)))
        pygame.draw.lines(surface, dark, False, [P(-15, 7), P(-4, 9), P(8, 7.6), P(15, 3)], 1)   # edge of the gill cover
        pygame.draw.lines(surface, dark, False, [P(4, -13), P(1.5, -3), P(3, 4), P(0, 9)], 1)    # cervical groove
        rost = [P(13, -8.2), P(36, -3.4), P(15, -0.4)]
        pygame.draw.polygon(surface, tone(body, 1.04), rost)
        pygame.draw.polygon(surface, dark, rost, 1)
        pygame.draw.line(surface, light, P(14, -5), P(33, -3.7), 1)
        gen = random.Random(self.id)
        for _ in range(10):   # small tubercles on the cheek and shoulder
            pygame.draw.circle(surface, mix(body, light, 0.5), P(gen.uniform(-12, 12), gen.uniform(-8, 6)), max(1, int(gen.uniform(0.8, 1.6) * s)))

        # stalked eye, short antennules and long antennae
        ex, ey = P(21.5, -11.5)
        pygame.draw.line(surface, dark, P(17, -6.5), (ex, ey), max(1, int(2 * s)))
        pygame.draw.circle(surface, (12, 10, 8), (int(ex), int(ey)), max(2, int(3.1 * s)))
        pygame.draw.circle(surface, (255, 255, 255), (int(ex - 0.9 * s), int(ey - 1.0 * s)), 1)
        for dy2, sg in ((-2.0, -1), (1.0, 1)):
            pygame.draw.line(surface, tone(body, 1.1), P(28, -2.5), P(38, -2.5 + dy2 * 3), 1)
        for side, (ax, ay) in enumerate(((26, -2.5), (24, -0.5))):
            pts = []
            for k in range(8):
                u = k / 7
                pts.append(P(ax + 36 * u * (1.0 + 0.2 * side), ay - 18 * u * (1 - side * 0.6) + math.sin(t * 1.4 + k * 0.6 + side * 2) * 3 * u))
            pygame.draw.lines(surface, tone(body, 1.15), False, pts, 1)

        # the two big claws: raised and wide when hunting, one lifted toward a still cursor, otherwise held low and forward
        for which in (0, 1):
            near = which == 0
            sh = P(14 + (2 if near else 0), 3 + (2 if near else -1))
            lift = (-0.7 if hunting or fleeing else -0.38) if near else (-0.1 if hunting or fleeing else 0.22)
            reaching = reach > 0.03 and near
            if reaching:
                to = pygame.Vector2(self.reach_pt) - pygame.Vector2(sh)
                ang_goal = math.atan2(to.y, to.x)
                ang_fwd = math.atan2(math.sin(lift), math.cos(lift) * f)
                dang = (ang_goal - ang_fwd + math.pi) % math.tau - math.pi
                ang = ang_fwd + dang * reach
            else:
                ang = math.atan2(math.sin(lift) + (math.sin(t * 2 + which) * 0.05), math.cos(lift) * f)
            ln1, ln2 = 17 * s, 14 * s
            elbow = (sh[0] + math.cos(ang + 0.5 * -f) * ln1, sh[1] + math.sin(ang + 0.5 * -f) * ln1)
            wrist = (elbow[0] + math.cos(ang) * ln2, elbow[1] + math.sin(ang) * ln2)
            ccol = tone(red, 1.0 if near else 0.8)
            draw_ribbon(surface, pygame.Vector2(sh), pygame.Vector2(elbow), 6.5 * s, 5.5 * s, mix(body, ccol, 0.5))
            draw_ribbon(surface, pygame.Vector2(elbow), pygame.Vector2(wrist), 5.5 * s, 5.2 * s, ccol)
            gape = (0.5 if hunting else 0.1 + 0.08 * math.sin(t * 3 + which)) * (1.0 + (0.5 if reaching else 0.0))
            ca, sa = math.cos(ang), math.sin(ang)
            palm_c = (wrist[0] + ca * 6.5 * s, wrist[1] + sa * 6.5 * s)
            palm_end = (wrist[0] + ca * 12 * s, wrist[1] + sa * 12 * s)
            palm = oval(palm_c[0], palm_c[1], ang, 7.5 * s, 4.6 * s)
            pygame.draw.polygon(surface, ccol, palm)
            pygame.draw.polygon(surface, dark, palm, 1)
            for sgn in (-1, 1):   # long, slender fingers with pale tips
                fa = ang + sgn * gape
                fb = (palm_end[0] - ca * 3 * s + math.cos(ang + 1.57 * sgn) * 2.6 * s, palm_end[1] - sa * 3 * s + math.sin(ang + 1.57 * sgn) * 2.6 * s)
                mid = (palm_end[0] + math.cos(fa + 0.1 * sgn) * 9 * s + math.cos(ang + 1.57 * sgn) * 1.2 * s,
                       palm_end[1] + math.sin(fa + 0.1 * sgn) * 9 * s + math.sin(ang + 1.57 * sgn) * 1.2 * s)
                tip = (palm_end[0] + math.cos(fa) * 16 * s, palm_end[1] + math.sin(fa) * 16 * s)
                pygame.draw.polygon(surface, ccol, [fb, mid, tip, palm_c])
                pygame.draw.lines(surface, dark, False, [fb, mid, tip], 1)
                pygame.draw.line(surface, (236, 214, 184), mid, tip, max(1, int(1.6 * s)))
            for k in range(4):   # orange-red tubercles along the palm
                q = (palm_c[0] + ca * (k - 1.2) * 2.6 * s - sa * 1.4 * s, palm_c[1] + sa * (k - 1.2) * 2.6 * s + ca * 1.4 * s - 1.2 * s)
                pygame.draw.circle(surface, mix(ccol, (240, 130, 70), 0.55), (int(q[0]), int(q[1])), max(1, int(0.9 * s)))


# ---- water quality, disease, feeding ----
FEEDS = ["PELLET", "FLAKES", "LIVE DAPHNIA", "BLOODWORM", "ALGAE WAFER"]
eggs, visitors, crawlers, placed = [], [], [], []


SICK_RECOVERY = 0.5          # illness shed per frame even in bad water (clean water adds up to 0.9 more)
SICK_DEATH_CHANCE = 1 / 60000  # per frame: about one sick fish in twenty dies in decent water
SICK_SPREAD = 0.03           # chance per second that a sick fish infects a neighbour within 70 px


def infect(f):
    f.sick, f.sick_t = True, 2400
    f.spots = [(random.uniform(-1, 1), random.uniform(-0.6, 0.6)) for _ in range(5)]
    f.disease = pick_disease(f)
    notify(f"{f.name} the {nice_name(f)} has {DISEASES[f.disease]} (I: quarantine, U: medicine)")


def update_water():
    """Slow bookkeeping, twice a second: leftovers rot, plants and crawlers clean, dirty water breeds disease."""
    if eco.t % 30:
        return
    resting = [p for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6]
    for p in resting:
        p.rot = getattr(p, "rot", 0) + 30
        if p.rot > 1200:
            pellets.remove(p)
            eco.water -= 1.2
    gain = (0.05 + 0.0015 * len(plants) + 0.03 * len(crawlers)) * (0.45 + 0.55 * eco.filter)
    if eco.air_on and not eco.power:
        gain += 0.02
    loss = 0.003 * len(fishes) + 0.002 * len(algae) + 0.01 * len(resting) + (0.04 if eco.power else 0.0)
    eco.water = clamp(eco.water + gain - loss, 0.0, 100.0)
    if eco.t % 60:
        return
    if eco.water < 45 and random.random() < (45 - eco.water) / 45 * 0.15:
        well = [f for f in fishes if hasattr(f, "sick") and not f.sick and f.growth >= 1.0 and getattr(f, "immune", 0) <= 0]
        if well:
            infect(random.choice(well))
    for f in fishes:
        if getattr(f, "sick", False):
            for o in fishes:
                if (o is not f and hasattr(o, "sick") and not o.sick and random.random() < SICK_SPREAD
                        and not getattr(o, "qpos", None) and not getattr(f, "qpos", None) and getattr(o, "immune", 0) <= 0
                        and o.pos.distance_squared_to(f.pos) < 70 * 70):
                    infect(o)


def draw_sick(surface):
    for f in fishes:
        if getattr(f, "sick", False) and getattr(f, "disease", "ich") == "ich":
            for ox, oy in f.spots:
                pygame.draw.circle(surface, (240, 245, 255), (int(f.pos.x + ox * 38 * f.z), int(f.pos.y + oy * 38 * f.z)), 2)


class Flake(FoodPellet):
    """Fish flakes: lighter than a pellet and they hang in the water longer."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vel = pygame.Vector2(random.uniform(-0.15, 0.15), random.uniform(0.25, 0.45))
        self.bites = 1

    def draw(self, surface):
        pygame.draw.rect(surface, (235, 215, 150), (int(self.pos.x), int(self.pos.y), 3, 2))


class Bloodworm(Flake):
    """Frozen bloodworm: small red pieces that send the whole tank into a frenzy."""

    def __init__(self, x, y):
        super().__init__(x, y)
        self.bites = 2
        self.vel = pygame.Vector2(random.uniform(-0.2, 0.2), random.uniform(0.35, 0.6))

    def draw(self, surface):
        x, y = int(self.pos.x), int(self.pos.y)
        pygame.draw.line(surface, (190, 30, 40), (x, y), (x + 3, y + 2 + int(math.sin(eco.t * 0.3 + x) * 1.5)), 2)


class Wafer(FoodPellet):
    """An algae wafer: it sinks fast and only bottom feeders (corydoras, plecos, loaches) go for it."""
    bottom_only = True

    def __init__(self, x, y):
        super().__init__(x, y)
        self.vel = pygame.Vector2(0, 1.7)
        self.bites = 6

    def draw(self, surface):
        pygame.draw.ellipse(surface, (150, 190, 90), (int(self.pos.x) - 5, int(self.pos.y) - 3, 10, 6))
        pygame.draw.ellipse(surface, (200, 230, 130), (int(self.pos.x) - 4, int(self.pos.y) - 3, 6, 3))


def drop_feed(pos):
    kind = FEEDS[eco.feed_idx]
    if kind == "PELLET":
        pellets.append(FoodPellet(*pos))
    elif kind == "FLAKES":
        for _ in range(6):
            pellets.append(Flake(pos[0] + random.uniform(-22, 22), pos[1] + random.uniform(-10, 10)))
    elif kind == "BLOODWORM":
        stats["blood"] += 1
        for _ in range(9):
            pellets.append(Bloodworm(pos[0] + random.uniform(-26, 26), pos[1] + random.uniform(-10, 10)))
    elif kind == "ALGAE WAFER":
        stats["wafers"] += 1
        pellets.append(Wafer(*pos))
    else:
        for _ in range(4):
            if len(daphnia) < 110:
                k = Daphnia()
                k.pos = pygame.Vector2(pos[0] + random.uniform(-15, 15), pos[1] + random.uniform(-10, 10))
                daphnia.append(k)
    feed_record(pos)
    play_sfx("bubble", 0.3)


# ---- breeding ----
class Eggs:
    """A clutch laid by a pair. Hungry fish will eat unguarded eggs; otherwise it hatches into fry that the parents defend."""

    def __init__(self, spot, male, female):
        self.pos = pygame.Vector2(spot) + pygame.Vector2(0, 24)
        self.kind = type(male)
        self.parents = (male, female)
        self.age = 0
        self.tint = (236, 214, 150) if isinstance(male, Cichlid) else (226, 232, 214)
        self.dots = [(random.uniform(-9, 9), random.uniform(-4, 4)) for _ in range(14)]

    def guarded(self):
        return any(p.alive and p.guard_t > 0 and p.pos.distance_squared_to(self.pos) < 120 * 120 for p in self.parents)

    def update(self):
        self.age += 1
        for f in fishes:
            if (f.hunger > 75 and random.random() < 0.01 and f.pos.distance_squared_to(self.pos) < 30 * 30
                    and f not in self.parents and not self.guarded()):
                eggs.remove(self)
                notify(f"{f.name} ate a clutch of eggs")
                return
        if self.age >= 1800:
            self.hatch()

    def hatch(self):
        eggs.remove(self)
        n = random.randint(3, 5)
        while n > 0 and not has_room(self.kind, n):
            n -= 1  # only as many fry as the tank can carry
        if n == 0:
            notify("The clutch failed: the tank is too crowded")
            return
        for _ in range(n):
            kid = self.kind(self.pos.x + random.uniform(-12, 12), self.pos.y - 20)
            init_traits(kid)
            kid.growth = 0.0
            kid.age = 0
            kid.sex = random.choice("MF")
            kid.bravery = random.uniform(0.1, 0.4)
            kid.z = kid.adult_z * 0.3
            kid.hunger = 20.0
            kid.breed_cd = 4000
            kid.parents = self.parents
            inherit_line(kid, self.parents)
            kid.nest, kid.nest_t = pygame.Vector2(self.pos) + (0, -24), 2600
            fishes.append(kid)
        eco.births += n
        stats["fry"] += n
        notify(f"{n} {nice_name(self.kind)} fry hatched!")
        play_sfx("hatch")
        burst(self.pos, self.tint, 12, 1.5, 50, 2, -0.01)

    def draw(self, surface):
        ripe = self.age > 1200
        for ox, oy in self.dots:
            p = (int(self.pos.x + ox), int(self.pos.y + oy))
            pygame.draw.circle(surface, self.tint, p, 2)
            if ripe:
                pygame.draw.circle(surface, (40, 25, 10), p, 1)


def give_birth(m, f):
    """Guppies are livebearers: the pair separates and the female drops a brood of tiny fry that scatter for cover."""
    for x in (m, f):
        x.nesting, x.courting, x.breed_cd = 0, 0, 3600
    m.site = None
    unbond(m)
    n = random.randint(4, 7)
    while n > 0 and not has_room(type(m), n):
        n -= 1
    if n == 0:
        notify("The brood was lost: the tank is too crowded", log=False)
        return
    for _ in range(n):
        kid = type(m)(f.pos.x + random.uniform(-10, 10), f.pos.y + random.uniform(-6, 6))
        init_traits(kid)
        kid.growth = 0.0
        kid.age = 0
        kid.sex = random.choice("MF")
        kid.bravery = random.uniform(0.1, 0.4)
        kid.z = max(0.2, f.z - 0.05)
        kid.hunger = 20.0
        kid.breed_cd = 4000
        kid.parents = (m, f)
        if hasattr(kid, "gh"):   # inherit the colour and tail genes from both parents, with a little mutation
            kid.gh = clamp((getattr(m, "gh", 0.0) + getattr(f, "gh", 0.0)) / 2 + random.gauss(0, 0.5), -2.4, 2.4)
            kid.gt = clamp((getattr(m, "gt", 0.0) + getattr(f, "gt", 0.0)) / 2 + random.gauss(0, 0.4), -1.4, 1.4)
            kid.gen = max(getattr(m, "gen", 1), getattr(f, "gen", 1)) + 1
            inherit_extra(kid, m, f)
            record_strain(kid, True)
        if eco.nursery is not None:   # the mother was moved into the nursery net: her fry are born safe inside it
            kid.pos = pygame.Vector2(eco.nursery[0] + random.uniform(-80, 80), eco.nursery[1] + random.uniform(-45, 45))
            kid.box = True
        kid.vel = pygame.Vector2(random.uniform(-1, 1), random.uniform(-0.6, 0.2))
        fishes.append(kid)
    eco.births += n
    stats["fry"] += n
    notify(f"{f.name} gave birth to {n} {nice_name(type(m))} fry!")
    play_sfx("hatch")
    burst(f.pos, (255, 235, 200), 10, 1.2, 45, 2, -0.01)
    add_emote(f, "<3")


def lay_eggs(m, f):
    """The male and female spawn at the male's site; both stay to guard (the male longest)."""
    site = m.site
    if isinstance(m, GuppyBase):   # livebearers: no eggs, the female gives birth to free-swimming fry
        give_birth(m, f)
        return
    eggs.append(Eggs(site, m, f))
    for x in (m, f):
        x.nesting, x.courting, x.breed_cd = 0, 0, 4800
        x.guard_pos = pygame.Vector2(site) + (0, 24)
        x.guard_t = 3000 if x is m else 1800
    m.site = None
    if m.family not in PAIRING:
        unbond(m)
    burst(site + (0, 20), eggs[-1].tint, 14, 1.2, 55, 2, -0.01)
    add_emote(m, "<3")
    notify(f"{m.name} and {f.name} spawned ({nice_name(m)})", log=False)


def update_breeding():
    for e in eggs[:]:
        e.update()
    if eco.t % 30 or eco.water < 55 or len(eggs) >= 6:
        return
    for m in fishes:
        if getattr(m, "sex", None) != "M" or m.partner is None or m.nesting <= 90 or m.site is None:
            continue
        mate = m.partner
        if not mate.alive:
            continue
        if any(e.pos.distance_squared_to(m.site) < 60 * 60 for e in eggs):
            m.nesting = 0
            continue
        if not has_room(type(m), 3):
            m.nesting, m.breed_cd, mate.breed_cd = 0, 1500, 1500
            continue
        lay_eggs(m, mate)
        break


# ---- rare visitors ----
class Visitor:
    """Guests that cross the tank and leave. Not hunted, not hunting."""
    z = 0.5

    @property
    def dz(self):
        return self.z

    def __init__(self):
        self.alive = True
        self.anim = random.uniform(0, 6)

    def update(self):
        self.anim += 0.04


class Turtle(Visitor):
    """A red-eared slider paddling slowly across the tank."""

    def __init__(self):
        super().__init__()
        self.dir = random.choice([-1, 1])
        self.base_y = random.randint(190, 400)
        self.pos = pygame.Vector2(-140 if self.dir == 1 else SCREEN_WIDTH + 140, self.base_y)
        self.z = 0.8
        self.speed = random.uniform(0.7, 1.0)

    def update(self):
        super().update()
        self.pos.x += self.speed * self.dir
        self.pos.y = self.base_y + math.sin(self.anim * 0.5) * 22
        if (self.dir == 1 and self.pos.x > SCREEN_WIDTH + 160) or (self.dir == -1 and self.pos.x < -160):
            self.alive = False

    def draw(self, surface):
        u = SS
        w, h = 170 * u, 120 * u
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        a = math.sin(self.anim * 1.6)
        col = (84, 112, 62)
        # far flippers, then body, then near flippers
        pygame.draw.polygon(surf, (62, 92, 52), [(cx + 14 * u, cy - 4 * u), (cx + (26 + 8 * a) * u, cy - (30 - 14 * a) * u), (cx - 2 * u, cy - 8 * u)])
        pygame.draw.polygon(surf, (62, 92, 52), [(cx - 30 * u, cy + 6 * u), (cx - 48 * u, cy + (12 + 6 * a) * u), (cx - 26 * u, cy + 12 * u)])
        pygame.draw.polygon(surf, (110, 140, 80), [(cx - 38 * u, cy + 4 * u), (cx - 56 * u, cy + 8 * u), (cx - 38 * u, cy + 10 * u)])
        shaded_ellipse(surf, (cx - 40 * u, cy - 26 * u, 80 * u, 52 * u), (150, 134, 62), (58, 74, 38))
        pygame.draw.ellipse(surf, (60, 66, 36), (cx - 40 * u, cy - 26 * u, 80 * u, 52 * u), u)
        for k in range(-1, 2):
            pygame.draw.line(surf, (70, 76, 40), (cx + k * 22 * u, cy - 22 * u), (cx + k * 20 * u, cy + 12 * u), u)
        pygame.draw.line(surf, (70, 76, 40), (cx - 32 * u, cy - 6 * u), (cx + 34 * u, cy - 6 * u), u)
        pygame.draw.ellipse(surf, (126, 152, 92), (cx + 32 * u, cy - 14 * u, 30 * u, 20 * u))
        pygame.draw.ellipse(surf, (214, 50, 40), (cx + 42 * u, cy - 11 * u, 8 * u, 4 * u))
        pygame.draw.circle(surf, (12, 12, 12), (int(cx + 52 * u), int(cy - 9 * u)), int(2.2 * u))
        pygame.draw.polygon(surf, col, [(cx + 16 * u, cy + 12 * u), (cx + (34 + 10 * a) * u, cy + (38 - 18 * a) * u), (cx + 2 * u, cy + 20 * u)])
        surf = pygame.transform.smoothscale(surf, (w // u, h // u))
        if self.dir == -1:
            surf = pygame.transform.flip(surf, True, False)
        surface.blit(surf, surf.get_rect(center=(int(self.pos.x), int(self.pos.y))))



def spawn_rare_visitor(kind=None):
    visitors.append(Turtle())
    notify("A red-eared slider paddles through the tank")


class Frog(Visitor):
    """A little green tree frog that sticks to the front glass for a while, blinks, then hops away upwards."""

    def __init__(self):
        super().__init__()
        self.z = 1.2
        side = random.choice([(120, 360), (SCREEN_WIDTH - 360, SCREEN_WIDTH - 120)])
        self.pos = pygame.Vector2(random.randint(*side), random.randint(260, 520))
        self.life = 2000
        self.blink = 0

    def update(self):
        super().update()
        self.life -= 1
        if self.blink > 0:
            self.blink -= 1
        elif random.random() < 0.008:
            self.blink = 8
        if self.life < 0:
            self.pos.y -= 5
            if self.pos.y < -60:
                self.alive = False

    def draw(self, surface):
        u = SS
        w, h = 110 * u, 100 * u
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        skin, belly, dark = (96, 186, 84), (206, 226, 160), (52, 120, 58)
        for sx in (-1, 1):   # folded back legs and front arms with sticky toe discs
            pygame.draw.ellipse(s, dark, (cx + sx * 30 * u - 14 * u, cy + 6 * u, 28 * u, 18 * u))
            pygame.draw.ellipse(s, skin, (cx + sx * 26 * u - 8 * u, cy - 10 * u, 16 * u, 34 * u))
            for k in range(3):
                pygame.draw.circle(s, (170, 220, 120), (int(cx + sx * (24 + 5 * k - 4) * u), int(cy + 28 * u)), int(3 * u))
        pygame.draw.ellipse(s, skin, (cx - 28 * u, cy - 22 * u, 56 * u, 50 * u))
        pygame.draw.ellipse(s, belly, (cx - 18 * u, cy - 4 * u, 36 * u, 28 * u))
        pulse = 1.0 + 0.08 * math.sin(self.anim * 6)
        pygame.draw.ellipse(s, (226, 238, 190), (cx - 11 * u, cy - 8 * u, 22 * u * pulse, 9 * u))
        pygame.draw.line(s, dark, (cx - 14 * u, cy - 12 * u), (cx + 14 * u, cy - 12 * u), u)
        for sx in (-1, 1):
            ex, ey = int(cx + sx * 15 * u), int(cy - 24 * u)
            pygame.draw.circle(s, skin, (ex, ey), int(9 * u))
            if self.blink:
                pygame.draw.line(s, dark, (ex - 7 * u, ey), (ex + 7 * u, ey), int(2 * u))
            else:
                pygame.draw.circle(s, (232, 190, 70), (ex, ey), int(6.5 * u))
                pygame.draw.ellipse(s, (14, 14, 14), (ex - 2 * u, ey - 5 * u, 4 * u, 10 * u))
        s = pygame.transform.smoothscale(s, (w // u, h // u))
        surface.blit(s, s.get_rect(center=(int(self.pos.x), int(self.pos.y))))


class Kingfisher(Visitor):
    """A kingfisher that sweeps over the tank, dives in with a splash (scaring the fish) and flies off."""

    def __init__(self):
        super().__init__()
        self.z = 1.2
        self.dir = random.choice([-1, 1])
        self.pos = pygame.Vector2(-80 if self.dir == 1 else SCREEN_WIDTH + 80, 50)
        self.dive_x = random.randint(300, SCREEN_WIDTH - 300)
        self.state = "fly"
        self.t = 0

    def update(self):
        super().update()
        self.t += 1
        if self.state == "fly":
            self.pos.x += 5.5 * self.dir
            self.pos.y = 50 + math.sin(self.anim * 5) * 5
            if (self.pos.x - self.dive_x) * self.dir >= 0:
                self.state = "dive"
        elif self.state == "dive":
            self.pos.x += 3.0 * self.dir
            self.pos.y += 7.0
            if self.pos.y >= WATER_TOP + 75:
                self.state = "out"
                burst(pygame.Vector2(self.pos.x, WATER_TOP + 6), (220, 240, 255), 16, 2.4, 40, 2, 0.05)
                play_sfx("bubble", 0.6)
                eco.scare(0.3)
        else:
            self.pos.x += 4.0 * self.dir
            self.pos.y -= 7.0
            if self.pos.y < -60:
                self.alive = False

    def draw(self, surface):
        u = SS
        w, h = 110 * u, 70 * u
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        flap = math.sin(self.anim * 14)
        pygame.draw.polygon(s, (24, 100, 170), [(cx - 6 * u, cy - 2 * u), (cx - 24 * u, cy - (16 + 10 * flap) * u), (cx + 8 * u, cy - 4 * u)])
        pygame.draw.ellipse(s, (36, 140, 205), (cx - 24 * u, cy - 8 * u, 46 * u, 18 * u))
        pygame.draw.ellipse(s, (236, 134, 56), (cx - 14 * u, cy - 1 * u, 30 * u, 10 * u))
        pygame.draw.circle(s, (36, 140, 205), (int(cx + 22 * u), int(cy - 3 * u)), int(8 * u))
        pygame.draw.polygon(s, (24, 24, 28), [(cx + 28 * u, cy - 5 * u), (cx + 48 * u, cy - 2 * u), (cx + 28 * u, cy)])
        pygame.draw.circle(s, (10, 10, 10), (int(cx + 24 * u), int(cy - 5 * u)), int(1.6 * u))
        pygame.draw.polygon(s, (24, 100, 170), [(cx - 22 * u, cy), (cx - 36 * u, cy + 3 * u), (cx - 22 * u, cy + 6 * u)])
        s = pygame.transform.smoothscale(s, (w // u, h // u))
        if self.dir == -1:
            s = pygame.transform.flip(s, True, False)
        ang = {"fly": 0, "dive": -55, "out": 50}[self.state] * self.dir
        s = pygame.transform.rotate(s, ang)
        surface.blit(s, s.get_rect(center=(int(self.pos.x), int(self.pos.y))))


def spawn_guest():
    v = random.choice((Frog, Kingfisher))()
    visitors.append(v)
    X["guests"] += 1
    notify("A tree frog is clinging to the glass" if isinstance(v, Frog) else "A kingfisher is hunting over the tank")
    save_prefs()


# ---- crawlers on the sand ----
class MysterySnail:
    """Wanders the sand and tidies up leftover food, which keeps the water cleaner."""

    def __init__(self):
        self.x = random.uniform(80, SCREEN_WIDTH - 80)
        self.dir = random.choice([-1, 1])
        self.pause = random.randint(60, 300)
        self.anim = random.uniform(0, 6)
        self.shell = random.choice([(222, 176, 70), (60, 52, 70), (226, 214, 190), (170, 110, 60)])

    def update(self):
        self.pause -= 1
        if self.pause <= 0:
            self.anim += 0.12
            self.x += 0.18 * self.dir
            if random.random() < 0.004:
                self.pause = random.randint(60, 300)
                if random.random() < 0.5:
                    self.dir *= -1
        if self.x < 40 or self.x > SCREEN_WIDTH - 40:
            self.dir *= -1
            self.x = max(41, min(SCREEN_WIDTH - 41, self.x))
        if eco.t % 20 == 0:
            for p in pellets:
                if abs(p.pos.x - self.x) < 18 and p.pos.y >= ground_y(p.pos.x) - 6:
                    pellets.remove(p)
                    eco.water = clamp(eco.water + 0.8, 0.0, 100.0)
                    break

    def draw(self, surface):
        d = self.dir
        x, y = int(self.x), int(ground_y(self.x) + 12)
        body = (206, 190, 150)
        stretch = 1.0 + 0.08 * math.sin(self.anim * 2)
        pygame.draw.ellipse(surface, body, (x - 11 * stretch, y - 5, 22 * stretch, 6))
        hx = x + 10 * d * stretch
        pygame.draw.ellipse(surface, body, (hx - 4, y - 8, 9, 7))
        for k in (-1, 1):  # tentacles
            pygame.draw.line(surface, tone(body, 0.8), (hx + 2 * d, y - 7), (hx + 8 * d, y - 13 + k * 2 + math.sin(self.anim + k) * 1.5), 1)
        pygame.draw.circle(surface, (15, 15, 15), (hx + 3 * d, y - 6), 1)
        sx, sy = x - 3 * d, y - 12
        pygame.draw.circle(surface, tone(self.shell, 0.65), (sx, sy), 10)
        pygame.draw.circle(surface, self.shell, (sx, sy), 9)
        pygame.draw.circle(surface, tone(self.shell, 1.25), (sx - 2, sy - 3), 4)
        pygame.draw.arc(surface, tone(self.shell, 0.55), (sx - 6, sy - 6, 12, 12), 0.6, 5.2, 1)
        pygame.draw.arc(surface, tone(self.shell, 0.55), (sx - 3, sy - 3, 6, 6), 1.0, 5.6, 1)


class Ramshorn:
    """A small flat-coiled snail that grazes the substrate slowly."""

    def __init__(self):
        self.x = random.uniform(80, SCREEN_WIDTH - 80)
        self.dir = random.choice([-1, 1])
        self.anim = random.uniform(0, 6)
        self.shell = random.choice([(196, 60, 52), (130, 84, 52)])

    def update(self):
        self.anim += 0.03
        self.x += 0.05 * self.dir
        if self.x < 40 or self.x > SCREEN_WIDTH - 40 or random.random() < 0.001:
            self.dir *= -1
        eco.water = clamp(eco.water + 0.0004, 0.0, 100.0)

    def draw(self, surface):
        x, y = int(self.x), int(ground_y(self.x) + 10)
        d = self.dir
        pygame.draw.ellipse(surface, (120, 100, 90), (x - 7 + (2 if d > 0 else -2), y - 3, 12, 4))
        pygame.draw.circle(surface, tone(self.shell, 0.6), (x, y - 7), 7)
        pygame.draw.circle(surface, self.shell, (x, y - 7), 6)
        for r in (4, 2):
            pygame.draw.circle(surface, tone(self.shell, 0.7), (x, y - 7), r, 1)
        pygame.draw.line(surface, (140, 120, 110), (x + 5 * d, y - 3), (x + 8 * d, y - 7), 1)


# ---- building: drop decorations into the tank ----
DECOR_TOOLS = ["OFF", "ROCK", "DRIFTWOOD", "SWORD", "ROTALA", "LUDWIGIA", "DWARF", "CRYPT", "CLOVER", "MOSS", "CABOMBA", "HYGRO", "UNDO", "TRIM"]


PLANT_KINDS = {"SWORD": "Sword", "ROTALA": "Rotala", "LUDWIGIA": "Ludwigia", "DWARF": "DwarfGrass", "CRYPT": "Cryptocoryne",
               "CLOVER": "Clover", "MOSS": "MossBall", "CABOMBA": "Cabomba", "HYGRO": "Hygrophila", "VALLIS": "Vallisneria",
               "HAIR": "Hairgrass", "LOTUS": "TigerLotus", "ANUBIAS": "Anubias", "JAVAFERN": "JavaFern", "POTHOS": "Pothos"}
KIND_OF = {v: k for k, v in PLANT_KINDS.items()}


def seeded(seed, fn):
    """Run fn with its own random seed, so a decoration can be rebuilt exactly from a saved layout."""
    st = random.getstate()
    random.seed(seed)
    try:
        return fn()
    finally:
        random.setstate(st)


def make_item(kind, x, z=None, seed=None, yo=0):
    seed = seed if seed is not None else random.getrandbits(30)
    if kind in ROCK_KINDS:
        item = seeded(seed, lambda: ROCK_KINDS[kind](x=x, z=z, y_offset=yo))
    else:
        item = seeded(seed, lambda: Plant(x, PLANT_KINDS[kind]))
        if kind == "JAVAFERN":
            item.lift = 40
    item.iseed = seed
    return item


def place_decor(kind, x, z=None, yo=0):
    if kind == "UNDO":
        if placed:
            _, _, _, item = placed.pop()
            for lst in (rocks, plants):
                if item in lst:
                    lst.remove(item)
            build_cover()
        return
    z = z if z is not None else random.uniform(0.75, 1.1)
    item = make_item(kind, x, z, None, yo)
    item.mday = eco.day
    if kind in ROCK_KINDS:
        rocks.append(item)
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
    else:
        plants.append(item)
    placed.append((kind, x, z, item))
    build_cover()


# ---- following a fish ----
def pick_fish(pos):
    best, bd = None, 60
    for f in fishes + predators:
        d = f.pos.distance_to(pos) / (1.0 + 1.2 * isinstance(f, Predator))  # hunters are big: easier to click
        if d < bd and hasattr(f, "name"):
            best, bd = f, d
    eco.selected = best
    if best is None:
        eco.follow = False
    else:
        notify(f"Selected {best.name} the {nice_name(best)}", log=False)


def draw_selection(surface):
    f = eco.selected
    if f is None:
        return
    if not f.alive or (f not in fishes and f not in predators):
        eco.selected, eco.follow = None, False
        return
    pygame.draw.circle(surface, (255, 240, 120), (int(f.pos.x), int(f.pos.y)), int(34 * max(f.z, 0.5) + 10), 2)
    label = hud_font().render(f.name, True, (255, 240, 150))
    surface.blit(label, label.get_rect(midbottom=(int(f.pos.x), int(f.pos.y - 34 * max(f.z, 0.5) - 14))))


def apply_follow_cam(surface):
    f = eco.selected
    if not (eco.follow and f is not None and f.alive):
        return
    zoom = 1.8
    vw, vh = SCREEN_WIDTH / zoom, SCREEN_HEIGHT / zoom
    eco.cam += (pygame.Vector2(f.pos) - eco.cam) * 0.1
    x = clamp(eco.cam.x - vw / 2, 0, SCREEN_WIDTH - vw)
    y = clamp(eco.cam.y - vh / 2, 0, SCREEN_HEIGHT - vh)
    view = surface.subsurface(pygame.Rect(int(x), int(y), int(vw), int(vh))).copy()
    pygame.transform.scale(view, (SCREEN_WIDTH, SCREEN_HEIGHT), surface)


# ---- photo mode ----
VIGNETTE = None


PHOTO_STYLES = ("plain", "frame", "blur")
PHOTO = {"style": 0, "mask": None}


def photo_blur(surface):
    """Depth of field: the centre stays sharp, the edges are softly out of focus."""
    w, h = surface.get_size()
    if PHOTO["mask"] is None or PHOTO["mask"].get_size() != (w, h):
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(40):
            a = int(255 * (1 - i / 40) ** 1.6)
            pygame.draw.rect(m, (255, 255, 255, a), (i * w // 120, i * h // 120, w - 2 * i * w // 120, h - 2 * i * h // 120), max(2, w // 120))
        PHOTO["mask"] = m
    small = pygame.transform.smoothscale(surface, (max(1, w // 7), max(1, h // 7)))
    soft = pygame.transform.smoothscale(small, (w, h)).convert_alpha()
    soft.blit(PHOTO["mask"], (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(soft, (0, 0))


def photo_frame(shot):
    """A white polaroid border with a caption."""
    w, h = shot.get_size()
    b = max(18, w // 60)
    canvas = pygame.Surface((w + 2 * b, h + b + 4 * b))
    canvas.fill((246, 244, 238))
    canvas.blit(shot, (b, b))
    font = pygame.font.SysFont("Georgia", max(16, w // 50), italic=True)
    cap = font.render(f"Day {eco.day}  -  {len(fishes)} fish  -  {time.strftime('%d %b %Y')}", True, (70, 70, 80))
    canvas.blit(cap, cap.get_rect(center=(canvas.get_width() // 2, h + b + 2 * b)))
    return canvas


def take_photo(surface):
    global VIGNETTE, photo_flash
    if VIGNETTE is None:
        VIGNETTE = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(34):
            pygame.draw.rect(VIGNETTE, (0, 0, 0, int(120 * (1 - i / 34) ** 2)),
                             (i * 3, i * 2, SCREEN_WIDTH - i * 6, SCREEN_HEIGHT - i * 4), 3)
    surface.blit(VIGNETTE, (0, 0))
    os.makedirs("screenshots", exist_ok=True)
    name = time.strftime("screenshots/aquarium_%Y%m%d_%H%M%S.png")
    style = PHOTO_STYLES[PHOTO["style"]]
    if style == "blur":
        photo_blur(surface)
    shot = surface
    if DISPLAY_W > surface.get_width():   # save at the monitor's full resolution, not the smaller world buffer
        shot = pygame.transform.smoothscale(surface, (DISPLAY_W, DISPLAY_H))
    if style == "frame":
        shot = photo_frame(shot)
    pygame.image.save(shot, name)
    try:
        score = int(judge_layout()["overall"])
    except Exception:
        score = 0
    album_add(name, score)
    photo_flash = 14
    stats["photos"] += 1
    play_sfx("shutter", 0.7)
    notify(f"Photo saved: {name}", log=False)


# ---- save / load ----
SAVE_PATH = "aquarium_save.json"
world_seed = 0
LAYOUT = {"custom": False}   # True once the planting mode has changed the seeded layout (then the save stores every item)
PM = {"on": False, "tool": "MOVE", "sel": None, "drag": None, "ops": [], "clear_t": -99999, "rocks_dirty": False, "z": None}
FISH_CLASSES = {c.__name__: c for c in FW_CLASSES}


def rebuild_world(seed=None):
    """Build the hardscape and plants from a seed, so a saved tank can get its exact layout back."""
    global plants, rocks, pebbles, world_seed
    world_seed = seed if seed is not None else random.randrange(1 << 30)
    state = random.getstate()
    random.seed(world_seed)
    plants = create_plants()
    rocks = create_hardscape()
    plants += mounted_plants()
    plants.sort(key=PLANT_ORDER)
    pebbles = create_pebbles(400)
    random.setstate(state)
    for i, r in enumerate(rocks):   # a saved custom layout refers to the original pieces by these numbers
        r.orig = i
    for i, p in enumerate(plants):
        p.orig = i
    LAYOUT["custom"] = False


def save_game(path=None, quiet=False):
    fish_data = []
    for f in fishes:
        if not hasattr(f, "family"):
            continue
        d = {"cls": type(f).__name__, "x": f.pos.x, "y": f.pos.y, "vx": f.vel.x, "vy": f.vel.y, "z": f.z,
             "hunger": f.hunger, "health": f.health, "bravery": f.bravery, "curious": f.curious,
             "growth": f.growth, "adult_z": f.adult_z, "name": f.name, "sick": f.sick, "sick_t": f.sick_t,
             "age": f.age, "lifespan": f.lifespan, "sex": f.sex}
        if hasattr(f, "gh"):
            d.update(gh=f.gh, gt=f.gt, gen=f.gen)
        d["x21"] = fish_extra(f)
        fish_data.append(d)
    data = {"seed": world_seed, "saved_at": time.time(),
            "eco": {"clock": eco.clock, "day": eco.day, "kills": eco.kills, "births": eco.births, "water": eco.water,
                    "glass": list(eco.glass), "filter": eco.filter, "lights": eco.lights, "air": eco.air_on,
                    "realtime": eco.realtime, "temp": eco.temp, "heater": eco.heater},
            "fish": fish_data,
            "feed": dict(feed_mem),
            "shrimp": [s.gene for s in shimps],
            "hunger": {type(p).__name__: p.hunger for p in predators},
            "placed": [[k, x, z] for k, x, z, _ in placed],
            "layout": layout_snapshot() if LAYOUT["custom"] else None,
            "journal": journal[-40:], "x21": save21()}
    try:
        with open(path or SAVE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        if not quiet:
            notify(f"Tank saved ({len(fish_data)} fish, day {eco.day})", log=False)
    except OSError as err:
        if not quiet:
            notify(f"Could not save: {err}", log=False)


def load_game(path=None, away=False):
    try:
        with open(path or SAVE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        if not away:
            notify("No saved tank found (press F5 to save one)", log=False)
        return
    rebuild_world(data.get("seed"))
    lay = data.get("layout")
    if isinstance(lay, dict):
        layout_apply(lay)
    init_ecosystem()
    if not isinstance(lay, dict):
        for k, x, z in data.get("placed", []):
            place_decor(k, x, z)
    e = data.get("eco", {})
    eco.clock, eco.day = e.get("clock", eco.clock), e.get("day", 1)
    eco.kills, eco.births, eco.water = e.get("kills", 0), e.get("births", 0), e.get("water", 90.0)
    gl = e.get("glass")
    if isinstance(gl, list) and len(gl) == GLASS_COLS:
        eco.glass = [clamp(float(v)) for v in gl]
    eco.filter = clamp(float(e.get("filter", 1.0)))
    if e.get("lights") in ("SUN", "ON", "OFF"):
        eco.lights = e["lights"]
    eco.air_on = bool(e.get("air", True))
    eco.realtime = bool(e.get("realtime", False))
    eco.temp = float(e.get("temp", 25.0))
    if e.get("heater") in HEAT:
        eco.heater = e["heater"]
    fm = data.get("feed")
    if isinstance(fm, dict):
        for k in ("x", "y", "conf"):
            feed_mem[k] = float(fm.get(k, 0.0))
    n_shrimp = data.get("shrimp")
    genes = n_shrimp if isinstance(n_shrimp, list) else [0] * n_shrimp if isinstance(n_shrimp, int) else []
    if 4 <= len(genes) <= 60:
        shimps[:] = [TinyShrimp() for _ in genes]
        for sh, gn in zip(shimps, genes):
            if gn in (0, 1, 2):
                sh.gene, sh.base_color = gn, SHRIMP_COLORS[gn]
    new_fish = []
    for d in data.get("fish", []):
        cls = FISH_CLASSES.get(d["cls"])
        if cls is None:
            continue
        f = cls(d["x"], d["y"])
        init_traits(f)
        f.vel = pygame.Vector2(d["vx"], d["vy"])
        f.z, f.hunger, f.health = d["z"], d["hunger"], d["health"]
        f.bravery, f.curious, f.growth, f.adult_z = d["bravery"], d["curious"], d["growth"], d["adult_z"]
        f.name, f.sick, f.sick_t = d["name"], d["sick"], d["sick_t"]
        f.age, f.lifespan, f.sex = d.get("age", f.age), d.get("lifespan", f.lifespan), d.get("sex", f.sex)
        if hasattr(f, "gh"):
            f.gh, f.gt, f.gen = d.get("gh", f.gh), d.get("gt", f.gt), d.get("gen", 1)
        fish_extra_apply(f, d.get("x21"))
        if f.sick:
            f.spots = [(random.uniform(-1, 1), random.uniform(-0.6, 0.6)) for _ in range(5)]
        new_fish.append(f)
    fishes[:] = new_fish
    for p in predators:
        p.hunger = data.get("hunger", {}).get(type(p).__name__, p.hunger)
    journal[:] = [tuple(j) for j in data.get("journal", [])]
    load21(data.get("x21"))
    relink_friends()
    notify("Tank loaded", log=False)
    if away and isinstance(data.get("saved_at"), (int, float)):
        apply_away(time.time() - data["saved_at"])



# ---- planting mode: put the fish away and lay out every plant, rock and piece of driftwood by hand ----
PM.update(fill=False, stroke=None, edits=0, shots={"before": None, "after": None})
PM_TOOLS = [("MOVE", "Move"), ("ROCK", "Rock"), ("DRIFTWOOD", "Driftwood"), ("CAVE", "Cave"), ("POT", "Clay pot"), ("SHIP", "Shipwreck"),
            ("BRIDGE", "Bridge"), ("SWORD", "Sword"), ("ROTALA", "Rotala"), ("LUDWIGIA", "Ludwigia"), ("CABOMBA", "Cabomba"),
            ("HYGRO", "Hygrophila"), ("VALLIS", "Vallisneria"), ("HAIR", "Hairgrass"), ("LOTUS", "Tiger lotus"), ("ANUBIAS", "Anubias"),
            ("JAVAFERN", "Java fern"), ("POTHOS", "Pothos"), ("DWARF", "Carpet"), ("CRYPT", "Crypt"), ("CLOVER", "Clover"),
            ("MOSS", "Moss ball"), ("TRIM", "Prune")]
PM_LABEL = dict(PM_TOOLS, UNDO="Undo", CLEAR="Clear all", DONE="Done", FILL="Fill", MIRROR="Mirror", JUDGE="Judge")
PM_ROWS = 3
PM_BAR_BOTTOM = 10 + PM_ROWS * 34 + 6


def rock_set_x(r, x):
    r.pos_x = x
    r.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2


def item_kind(it):
    return it.kind if isinstance(it, Rock) else KIND_OF.get(it.species, "SWORD")


def layout_snapshot():
    """Every rock and plant as plain data: seeded originals by number, new pieces by kind and seed, with position, height, size and flip."""
    items = []
    for r in rocks:
        d = {"t": "r", "x": r.pos_x, "yo": r.y_offset, "sc": round(r.sc, 3), "fl": r.fl, "md": r.mday}
        if getattr(r, "orig", None) is not None:
            d["o"] = r.orig
        else:
            d.update(k=r.kind, z=r.z, s=getattr(r, "iseed", 0))
        items.append(d)
    for p in plants:
        d = {"t": "p", "x": p.pos_x, "lift": p.lift, "sz": round(p.psize, 3), "hp": round(p.hp, 2), "dp": p.depth}
        if getattr(p, "orig", None) is not None:
            d["o"] = p.orig
        else:
            d.update(k=KIND_OF.get(p.species, "SWORD"), s=getattr(p, "iseed", 0))
        items.append(d)
    return {"items": items}


def layout_apply(snap):
    orig_r = {r.orig: r for r in rocks if getattr(r, "orig", None) is not None}
    orig_p = {p.orig: p for p in plants if getattr(p, "orig", None) is not None}
    new_r, new_p = [], []
    for d in snap.get("items", []):
        try:
            if d["t"] == "r":
                if "o" in d:
                    it = orig_r.get(d["o"])
                    if it is None:
                        continue
                    rock_set_x(it, float(d["x"]))
                else:
                    it = make_item(d["k"], float(d["x"]), float(d["z"]), int(d["s"]), int(d.get("yo", 0)))
                it.y_offset = int(d.get("yo", it.y_offset))
                it.mday = int(d.get("md", 0))
                it.sc, it.fl = float(d.get("sc", 1.0)), bool(d.get("fl", False))
                if it.sc != 1.0 or it.fl:
                    rock_look(it)
                new_r.append(it)
            else:
                if "o" in d:
                    it = orig_p.get(d["o"])
                    if it is None:
                        continue
                    it.pos_x = float(d["x"])
                else:
                    it = make_item(d["k"], float(d["x"]), None, int(d["s"]))
                it.lift = d.get("lift", it.lift)
                sz = float(d.get("sz", 1.0))
                if abs(sz - it.psize) > 0.01:
                    scale_plant(it, sz / it.psize)
                it.hp = float(d.get("hp", 1.0))
                it.depth = int(clamp(int(d.get("dp", 0)), 0, 2))
                it._colc = {}
                new_p.append(it)
        except (KeyError, TypeError, ValueError):
            continue
    rocks[:] = sorted(new_r, key=lambda r: (r.z, -r.y_offset))
    plants[:] = sorted(new_p, key=PLANT_ORDER)
    LAYOUT["custom"] = True
    build_cover()


def pm_finalize():
    """After designing: rebuild the hiding places, and give the fire eel and cleaner shrimp a rock that still exists."""
    build_cover()
    if not PM["rocks_dirty"]:
        return
    PM["rocks_dirty"] = False
    had_eel = any(isinstance(p, FireEel) for p in predators)
    predators[:] = [p for p in predators if not isinstance(p, FireEel)]
    eel, chosen = build_world_extras()
    stations[:] = chosen
    if had_eel and eel is not None:
        predators.append(eel)


def pm_item_rect(it):
    if isinstance(it, Rock):
        sink = int(35 * it.z) if it.y_offset >= 0 else 0
        return it.image.get_rect(midbottom=(int(it.pos_x), int(it.base_y + it.y_offset + sink)))
    if it.hang:
        return pygame.Rect(int(it.pos_x) - 26, 0, 52, int(min(420, max(v[2] for v in it.vines) + 70)))
    base = ground_y(it.pos_x) - it.lift
    h = max(40, it.height)
    return pygame.Rect(int(it.pos_x) - 30, int(base - h), 60, int(h + 6))


def pm_pick(pos):
    best, bs = None, 1e9
    for it in list(plants) + list(rocks):
        if not pm_item_rect(it).collidepoint(pos):
            continue
        dx = abs(it.pos_x - pos[0])
        sc = dx + (10 + 0.25 * dx if isinstance(it, Rock) else 0)   # a plant wins a tie with the rock it stands beside
        if sc < bs:
            best, bs = it, sc
    return best


def pm_note_edit():
    PM["edits"] += 1
    LAYOUT["custom"] = True


def pm_enter():
    PM.update(on=True, tool="MOVE", sel=None, drag=None, stroke=None, ops=[], clear_t=-99999, edits=0)
    PM["shots"] = {"before": None, "after": None}
    CAP.update(want="before", delay=0)   # the tank as it is now, fish and all, for the before / after slider
    eco.selected, eco.follow = None, False
    notify("Planting mode: the fish are put away", log=False)


def pm_exit():
    PM.update(on=False, drag=None, sel=None, stroke=None)
    pm_finalize()
    save_prefs()
    if PM["edits"]:
        CAP.update(want="after", delay=QUALITY_SPECS[QUALITY[0]]["strips"] + 3)
    notify("Planting mode done: the fish are back", log=False)


def pm_remove(it, record=True):
    if it in rocks:
        rocks.remove(it)
        PM["rocks_dirty"] = True
    elif it in plants:
        plants.remove(it)
    else:
        return
    if PM["sel"] is it:
        PM["sel"] = None
    pm_note_edit()
    if record:
        PM["ops"].append(("del", it))
    build_cover()


def pm_insert(it):
    if isinstance(it, Rock):
        rocks.append(it)
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
        PM["rocks_dirty"] = True
    else:
        plants.append(it)
        plants.sort(key=PLANT_ORDER)
    pm_note_edit()
    build_cover()


def pm_replace(old, new):
    lst = rocks if isinstance(old, Rock) else plants
    if old in lst:
        lst[lst.index(old)] = new
    if isinstance(new, Rock):
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
        PM["rocks_dirty"] = True
    else:
        plants.sort(key=PLANT_ORDER)
    if PM["sel"] is old:
        PM["sel"] = new
    pm_note_edit()
    build_cover()


def pm_add(kind, x, record=True, z=None, yo=0):
    x = clamp(x, 8, SCREEN_WIDTH - 8)
    if kind in ROCK_KINDS:
        z = z if z is not None else PM["z"]
    place_decor(kind, x, z if kind in ROCK_KINDS else None, yo)
    it = placed[-1][3]
    plants.sort(key=PLANT_ORDER)
    if record:
        PM["ops"].append(("add", it))
    PM["sel"] = it
    PM["rocks_dirty"] = PM["rocks_dirty"] or isinstance(it, Rock)
    pm_note_edit()
    return it


def pm_stack(kind, base):
    """Drop a rock on top of another: same depth, one layer higher than whatever is already stacked there."""
    layers = sum(1 for r in rocks if abs(r.pos_x - base.pos_x) < 30 and abs(r.z - base.z) < 0.06 and r.y_offset < 0)
    yo = max(-90, -18 * (layers + 1))
    return pm_add(kind, base.pos_x + random.randint(-12, 12), z=base.z, yo=yo)


def pm_set_prop(it, **kw):
    old = {k: getattr(it, k) for k in kw}
    for k, v in kw.items():
        setattr(it, k, v)
    if isinstance(it, Rock):
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
        PM["rocks_dirty"] = True
    pm_note_edit()
    build_cover()
    return old


def pm_lift(it, up):
    if isinstance(it, Rock):
        yo = clamp(it.y_offset + (-18 if up else 18), -90, 0)
        if yo != it.y_offset:
            PM["ops"].append(("prop", it, pm_set_prop(it, y_offset=int(yo))))
    else:
        lf = clamp(it.lift + (8 if up else -8), 0, 320)
        if lf != it.lift:
            PM["ops"].append(("prop", it, pm_set_prop(it, lift=lf)))


def pm_resize(it, k):
    if isinstance(it, Rock):
        sc = clamp(it.sc * k, 0.5, 2.2)
        if sc != it.sc:
            PM["ops"].append(("prop", it, pm_set_prop(it, sc=sc)))
            rock_look(it)
    else:
        new = clamp(it.psize * k, 0.5, 2.2)
        k2 = new / it.psize
        if abs(k2 - 1.0) > 0.001:
            scale_plant(it, k2)
            PM["ops"].append(("size", it, k2))
            plants.sort(key=PLANT_ORDER)
            pm_note_edit()
            build_cover()


def pm_flip(it):
    if isinstance(it, Rock):
        it.fl = not it.fl
        rock_look(it)
        PM["ops"].append(("flip", it))
        pm_note_edit()


def pm_depth(it, dz):
    """A new depth redraws the piece (shading is baked into its picture), so it is rebuilt from a seed."""
    if not isinstance(it, Rock):   # a plant has three planes: front, middle, back
        nd = int(clamp(it.depth + (1 if dz > 0 else -1), 0, 2))
        if nd != it.depth:
            PM["ops"].append(("pdepth", it, it.depth))
            it.depth = nd
            it._colc = {}
            plants.sort(key=PLANT_ORDER)
            pm_note_edit()
        return
    z = round(clamp(it.z + dz, 0.6, 1.2), 2)
    if z == it.z:
        return
    seed = getattr(it, "iseed", None) or random.getrandbits(30)
    new = make_item(it.kind, it.pos_x, z, seed, it.y_offset)
    new.sc, new.fl = it.sc, it.fl
    rock_look(new)
    pm_replace(it, new)
    PM["ops"].append(("swap", it, new))


def pm_mirror(record=True):
    for r in rocks:
        rock_set_x(r, SCREEN_WIDTH - r.pos_x)
        r.fl = not r.fl
        rock_look(r)
    for p in plants:
        p.pos_x = SCREEN_WIDTH - p.pos_x
    rocks.sort(key=lambda r: (r.z, -r.y_offset))
    plants.sort(key=PLANT_ORDER)
    PM["rocks_dirty"] = True
    pm_note_edit()
    build_cover()
    if record:
        PM["ops"].append(("mirror",))


def pm_undo():
    if not PM["ops"]:
        return
    op = PM["ops"].pop()
    kind = op[0]
    if kind == "add":
        pm_remove(op[1], record=False)
    elif kind == "group":
        for it in op[1]:
            pm_remove(it, record=False)
    elif kind == "del":
        pm_insert(op[1])
    elif kind == "move":
        it, ox = op[1], op[2]
        if isinstance(it, Rock):
            rock_set_x(it, ox)
            PM["rocks_dirty"] = True
        else:
            it.pos_x = ox
        plants.sort(key=PLANT_ORDER)
        pm_note_edit()
        build_cover()
    elif kind == "prop":
        for k, v in op[2].items():
            setattr(op[1], k, v)
        if isinstance(op[1], Rock):
            rock_look(op[1])
            rocks.sort(key=lambda r: (r.z, -r.y_offset))
            PM["rocks_dirty"] = True
        pm_note_edit()
        build_cover()
    elif kind == "pdepth":
        op[1].depth = op[2]
        op[1]._colc = {}
        plants.sort(key=PLANT_ORDER)
        pm_note_edit()
    elif kind == "size":
        scale_plant(op[1], 1.0 / op[2])
        plants.sort(key=PLANT_ORDER)
        pm_note_edit()
        build_cover()
    elif kind == "flip":
        op[1].fl = not op[1].fl
        rock_look(op[1])
        pm_note_edit()
    elif kind == "swap":
        pm_replace(op[2], op[1])
    elif kind == "mirror":
        pm_mirror(record=False)
    elif kind == "clear":
        rocks[:] = op[1]
        plants[:] = op[2]
        PM["rocks_dirty"] = True
        pm_note_edit()
        build_cover()


def pm_clear_all():
    PM["ops"].append(("clear", list(rocks), list(plants)))
    rocks.clear()
    plants.clear()
    placed.clear()
    PM["sel"], PM["drag"], PM["stroke"] = None, None, None
    PM["rocks_dirty"] = True
    pm_note_edit()
    build_cover()
    notify("Tank cleared: start your design from scratch", log=False)


PM_ACTIONS = ("UNDO", "FILL", "MIRROR", "JUDGE", "CLEAR", "DONE")


def pm_layout():
    ids = [t[0] for t in PM_TOOLS] + list(PM_ACTIONS)
    x0, per = 380, 10
    bw = max(72, min(118, (SCREEN_WIDTH - x0 - 20) // per - 4))
    return [(pygame.Rect(x0 + (i % per) * (bw + 4), 10 + (i // per) * 34, bw, 30), b) for i, b in enumerate(ids)]


def pm_button(b):
    if b == "DONE":
        pm_exit()
    elif b == "UNDO":
        pm_undo()
    elif b == "FILL":
        PM["fill"] = not PM["fill"]
    elif b == "MIRROR":
        pm_mirror()
    elif b == "JUDGE":
        judge_run()
    elif b == "CLEAR":
        now = pygame.time.get_ticks()
        if now - PM["clear_t"] < 3000:
            PM["clear_t"] = -99999
            pm_clear_all()
        else:
            PM["clear_t"] = now
    else:
        PM["tool"] = b


def pm_event(e):
    """While planting, the mouse and a few keys belong to the mode. Returns True when the event was used."""
    if e.type == pygame.KEYDOWN:
        if e.key == pygame.K_HOME:
            if PM["on"]:
                pm_exit()
            elif not TOUR["on"]:
                pm_enter()
            return True
        if e.key == pygame.K_PAGEDOWN and not PM["on"]:
            tour_toggle()
            return True
        if e.key == pygame.K_ESCAPE and TOUR["on"]:
            tour_end()
            return True
        if e.key == pygame.K_INSERT and not PM["on"]:
            if PM["shots"]["before"] is not None and PM["shots"]["after"] is not None:
                UI21["panel"] = "ba"
            else:
                notify("Nothing to compare yet: change the layout in planting mode (Home) first", log=False)
            return True
    if not PM["on"] or UI21["panel"] is not None:
        return False
    if e.type == pygame.MOUSEBUTTONDOWN:
        pos = world_mouse(e.pos)
        if e.button == 1:
            for r, b in pm_layout():
                if r.collidepoint(pos):
                    pm_button(b)
                    return True
            if pos[0] > 370 and pos[1] < PM_BAR_BOTTOM + 80:
                return True
            tool = PM["tool"]
            if tool == "MOVE":
                it = pm_pick(pos)
                PM["sel"] = it
                PM["drag"] = (it, it.pos_x, pos[0] - it.pos_x) if it is not None else None
            elif tool == "TRIM":
                trim_plants(pos[0])
                pm_note_edit()
            elif PM["fill"] and tool != "TRIM":
                it = pm_add(tool, pos[0], record=False)
                PM["stroke"] = {"kind": tool, "x": pos[0], "gap": 18 if tool not in ROCK_KINDS else 60, "items": [it]}
            else:
                base = pm_pick(pos) if tool in ROCK_KINDS else None
                if isinstance(base, Rock):
                    pm_stack(tool, base)
                else:
                    pm_add(tool, pos[0])
        elif e.button == 3:
            it = pm_pick(pos)
            if it is not None:
                pm_remove(it)
        return True
    if e.type == pygame.MOUSEWHEEL:
        PM["z"] = clamp(round((PM["z"] or 0.9) + 0.05 * e.y, 2), 0.6, 1.2)
        return True
    if e.type == pygame.MOUSEBUTTONUP:
        d, st = PM["drag"], PM["stroke"]
        PM["drag"], PM["stroke"] = None, None
        if d is not None and abs(d[0].pos_x - d[1]) > 1:
            PM["ops"].append(("move", d[0], d[1]))
        if st is not None:
            PM["ops"].append(("group", st["items"]))
        return True
    if e.type == pygame.KEYDOWN:
        k = e.key
        it = PM["sel"]
        if k == pygame.K_ESCAPE:
            pm_exit()
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE) and it is not None:
            pm_remove(it)
        elif k == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
            pm_undo()
        elif k == pygame.K_TAB:
            ids = [t[0] for t in PM_TOOLS]
            PM["tool"] = ids[(ids.index(PM["tool"]) + 1) % len(ids)]
        elif it is not None and k in (pygame.K_LEFT, pygame.K_RIGHT):
            nx = clamp(it.pos_x + (1 if k == pygame.K_RIGHT else -1) * (20 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 4), 0, SCREEN_WIDTH)
            if isinstance(it, Rock):
                rock_set_x(it, nx)
                PM["rocks_dirty"] = True
            else:
                it.pos_x = nx
            pm_note_edit()
            build_cover()
        elif it is not None and k in (pygame.K_UP, pygame.K_DOWN):
            pm_lift(it, k == pygame.K_UP)
        elif it is not None and k in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            pm_resize(it, 1.1 if k == pygame.K_PAGEUP else 1 / 1.1)
        elif it is not None and k in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            pm_depth(it, 0.05 if k == pygame.K_RIGHTBRACKET else -0.05)
        elif it is not None and k == pygame.K_f:
            pm_flip(it)
        else:
            return False
        return True
    return False


def pm_update():
    d, st = PM["drag"], PM["stroke"]
    mx = world_mouse(pygame.mouse.get_pos())[0]
    if st is not None and abs(mx - st["x"]) >= st["gap"]:
        st["items"].append(pm_add(st["kind"], mx + random.uniform(-3, 3), record=False))
        st["x"] = mx
        st["gap"] = random.uniform(14, 26) if st["kind"] not in ROCK_KINDS else random.uniform(50, 80)
    if d is None:
        return
    it = d[0]
    nx = clamp(mx - d[2], 0, SCREEN_WIDTH)
    if abs(nx - it.pos_x) < 0.5:
        return
    if isinstance(it, Rock):
        rock_set_x(it, nx)
        PM["rocks_dirty"] = True
    else:
        it.pos_x = nx
        plants.sort(key=PLANT_ORDER)
    LAYOUT["custom"] = True


def pm_sel_text(it):
    if isinstance(it, Rock):
        return f"{PM_LABEL.get(it.kind, it.kind.title())}   depth {it.z:.2f}   size {it.sc:.2f}   height {-it.y_offset}"
    txt = f"{it.species}   health {int(it.hp * 100)}%   size {it.psize:.2f}   lift {int(it.lift)}   depth {('front', 'middle', 'back')[it.depth]}"
    if it.bloom:
        txt += "   in flower"
    if it.nib >= 2:
        txt += "   nibbled"
    return txt


def draw_plant_mode(surface):
    if not PM["on"]:
        return
    pm_update()
    mx, my = world_mouse(pygame.mouse.get_pos())
    low = PM_BAR_BOTTOM + 80
    if PM["tool"] == "MOVE" and PM["drag"] is None:
        hov = pm_pick((mx, my))
        if hov is not None and hov is not PM["sel"]:
            pygame.draw.rect(surface, (255, 255, 255), pm_item_rect(hov), 1, border_radius=4)
    if PM["sel"] is not None:
        pygame.draw.rect(surface, (255, 232, 120), pm_item_rect(PM["sel"]), 2, border_radius=4)
    if PM["tool"] not in ("MOVE", "TRIM") and my > low:
        gy = ground_y(mx)
        for y in range(int(gy) - 150, int(gy), 10):
            pygame.draw.line(surface, (255, 255, 255), (mx, y), (mx, y + 5), 1)
        lab = f21("d").render(PM_LABEL[PM["tool"]] + ("  (fill: drag)" if PM["fill"] else ""), True, (255, 255, 255))
        surface.blit(lab, lab.get_rect(midbottom=(int(mx), int(gy) - 154)))
    elif PM["tool"] == "TRIM" and my > low:
        pygame.draw.circle(surface, (255, 255, 255), (int(mx), int(my)), 75, 1)
    now = pygame.time.get_ticks()
    for r, b in pm_layout():
        on = b == PM["tool"] or (b == "FILL" and PM["fill"])
        sure = b == "CLEAR" and now - PM["clear_t"] < 3000
        col = (170, 60, 50) if b == "CLEAR" else (40, 130, 90) if b in ("DONE", "JUDGE") else (60, 130, 210) if on else (14, 30, 54)
        pygame.draw.rect(surface, col, r, border_radius=8)
        pygame.draw.rect(surface, (255, 232, 140) if on else (120, 190, 230), r, 2, border_radius=8)
        text = "Sure? click again" if sure else (("Fill: on" if PM["fill"] else "Fill: off") if b == "FILL" else PM_LABEL[b])
        t = f21("d").render(text, True, (255, 255, 255))
        surface.blit(t, t.get_rect(center=r.center))
    zt = f"{PM['z']:.2f}" if PM["z"] else "random"
    lines = ["PLANTING MODE - the fish are away.   Pick a tool, then click the tank.   Click a rock with a rock tool to stack on it.   Esc or Home when done.",
             f"MOVE: drag, arrows nudge.  Up/Down raise or lower.  PgUp/PgDn size.  [ ] depth.  F flip.  Right-click or Del removes.  Ctrl+Z undo.  Wheel: new rock depth ({zt})"]
    if PM["sel"] is not None:
        lines.append("Selected:  " + pm_sel_text(PM["sel"]))
    ts = [f21("d").render(m, True, (255, 232, 150) if i == 2 else (235, 245, 255)) for i, m in enumerate(lines)]
    bar = pygame.Surface((max(t.get_width() for t in ts) + 24, 8 + 22 * len(ts)), pygame.SRCALPHA)
    pygame.draw.rect(bar, (8, 20, 40, 210), bar.get_rect(), border_radius=8)
    for i, t in enumerate(ts):
        bar.blit(t, (12, 4 + 22 * i))
    surface.blit(bar, (380, PM_BAR_BOTTOM))


# ---------------------------------------------------------------- 6/7: plant health, nibbling, flowers, runners, growth
PT = {"day": -1}
NIBBLERS = ("Pleco", "KenyiCichlid", "AuratusCichlid", "SocolofiCichlid", "BalaShark")
RUNNERS = ("DwarfGrass", "Clover")
BLOOMERS = ("Anubias", "Cryptocoryne", "Sword")


def plant_care():
    """Every ten seconds: plants take the tank's light, food and fish into account. Once a day: nibbles heal, some bloom, carpets send runners."""
    if PM["on"] or not plants:
        return
    new_day = eco.day != PT["day"]
    PT["day"] = eco.day
    dark = eco.lights == "OFF"
    starved = CHEM["no3"] < 2.5 and FERT["t"] <= 0 and "co2" not in X["owned"]
    smothered = sum(HAIR) / len(HAIR) > 0.55
    for f in fishes:   # a few species nibble the softer plants
        if type(f).__name__ in NIBBLERS and f.growth >= 1.0 and random.random() < 0.35:
            near = [p for p in plants if not p.hang and p.species not in ("MossBall", "Anubias") and abs(p.pos_x - f.pos.x) < 70]
            if near:
                v = random.choice(near)
                v.nib = min(10, v.nib + 1)
                if v.nib == 3:
                    notify(f"{f.name} is nibbling the {v.species.lower()}", log=False)
    for p in plants:
        t = 1.0 - (0.3 if dark else 0.0) - (0.35 if starved else 0.0) - (0.2 if CHEM["no3"] > 90 else 0.0) - (0.15 if smothered else 0.0)
        t = clamp(t - min(0.4, p.nib * 0.08), 0.2, 1.0)
        p.hp += (t - p.hp) * 0.2
    if not new_day:
        return
    grown = 0
    for p in list(plants):
        p.nib = max(0, p.nib - 1)
        if p.bloom:
            p.bloom -= 1
        elif p.species in BLOOMERS and p.hp > 0.75 and random.random() < 0.012:
            p.bloom = random.randint(3, 6)
            X["blooms"] += 1
            notify(f"The {p.species.lower()} is in flower", log=False)
        if p.species in TALL_PLANTS and p.hp > 0.6:   # slow natural growth, faster with fertiliser or CO2 (see fw21_update)
            if not hasattr(p, "base_h"):
                p.base_h = p.height
            if p.height < p.base_h * 1.8:
                scale_plant(p, 1.015)
                grown += 1
        if (p.species in RUNNERS and p.hp > 0.6 and len(plants) < 260 and random.random() < 0.06
                and sum(1 for q in plants if q.species == p.species and abs(q.pos_x - p.pos_x) < 60) < 5):
            x = clamp(p.pos_x + random.choice((-1, 1)) * random.uniform(16, 30), 8, SCREEN_WIDTH - 8)
            plants.append(make_item(KIND_OF[p.species], x))
            LAYOUT["custom"] = True
            grown += 1
    if grown:
        plants.sort(key=PLANT_ORDER)
        build_cover()


# ---------------------------------------------------------------- 9: the aquascape judge
COLOR_GROUP = {"Ludwigia": "red", "TigerLotus": "red", "Rotala": "red", "Cryptocoryne": "red",
               "Hygrophila": "lime", "Hairgrass": "lime", "DwarfGrass": "lime", "Clover": "lime", "MossBall": "lime",
               "Vallisneria": "deep", "Sword": "deep", "JavaFern": "deep", "Anubias": "deep", "Cabomba": "feather", "Pothos": "feather"}
JUDGE_TIPS = {
    "Balance": "Spread the weight: keep a focal point off-centre and no empty third of the tank.",
    "Layers": "Mix carpet, mid-height and tall plants, and put rocks at more than one depth.",
    "Colour": "Add contrast: red stem plants, lime greens and deep greens side by side.",
    "Shelter": "Give the fish caves, rock faces and thick plant stands, and use more kinds of piece.",
}


def judge_layout():
    W = SCREEN_WIDTH
    mass = [0.0, 0.0, 0.0]
    com_num = 0.0
    for p in plants:
        m = max(20.0, p.height) * (0.5 if p.height < 70 else 1.0)
        mass[min(2, int(p.pos_x / W * 3))] += m
        com_num += m * p.pos_x
    for r in rocks:
        m = r.image.get_width() * r.image.get_height() / 55.0
        mass[min(2, int(r.pos_x / W * 3))] += m
        com_num += m * r.pos_x
    total = sum(mass)
    if total <= 0:
        return {"Balance": 0, "Layers": 0, "Colour": 0, "Shelter": 0, "overall": 0}
    com = com_num / total / W
    shares = [m / total for m in mass]
    bal = 100 - 220 * max(0.0, abs(com - 0.5) - 0.15) - 320 * max(0.0, 0.15 - min(shares))
    cols = set()   # open water matters: a tank packed edge to edge leaves the fish nowhere to swim
    for it in list(plants) + list(rocks):
        if isinstance(it, Rock) or it.height > 120:
            rc = pm_item_rect(it)
            cols.update(range(max(0, rc.left // 40), min(W // 40, rc.right // 40) + 1))
    open_frac = 1.0 - len(cols) / max(1, W // 40 + 1)
    bal -= 260 * max(0.0, 0.22 - open_frac) + 140 * max(0.0, open_frac - 0.7)
    n_pl = [p for p in plants if not p.hang]
    hc = sum(1 for lo, hi in ((0, 70), (70, 170), (170, 9999)) if sum(1 for p in n_pl if lo <= p.height < hi) >= 2)
    zb = len({0 if r.z < 0.8 else 1 if r.z < 0.95 else 2 for r in rocks})
    lay = (100 * (0.6 * hc / 3 + 0.4 * zb / 3)) * min(1.0, len(n_pl) / 10.0)
    groups = {}
    for p in plants:
        g = COLOR_GROUP.get(p.species)
        if g:
            groups[g] = groups.get(g, 0) + 1
    ng = sum(1 for v in groups.values() if v >= 2)
    col = (0, 35, 70, 100, 100)[min(4, ng)]
    if groups and max(groups.values()) > 0.6 * sum(groups.values()):   # one colour everywhere is dull
        col -= 30
    spots = len(rock_spots) + len(nest_spots) + len(cave_spots) * 2 + len(thicket_spots)
    need = max(3.0, len(fishes) / 6.0)
    kinds = len({item_kind(it) for it in list(plants) + list(rocks)})
    shel = 0.6 * min(100.0, 100.0 * spots / need) + 0.4 * min(100.0, kinds * 100 / 9.0)
    out = {"Balance": int(clamp(bal, 0, 100)), "Layers": int(clamp(lay, 0, 100)), "Colour": int(clamp(col, 0, 100)), "Shelter": int(clamp(shel, 0, 100))}
    out["overall"] = int(sum(out.values()) / 4)
    return out


def judge_run():
    r = judge_layout()
    gain = max(0, r["overall"] - X["best_scape"])
    pts = min(25, gain // 4)
    r["pts"] = pts
    if r["overall"] > X["best_scape"]:
        X["best_scape"] = r["overall"]
    if pts:
        X["points"] += pts
        notify(f"The judge awards {pts} points for the new design", log=True)
    save_prefs()
    UI21["judge"] = r
    UI21["panel"] = "judge"
    check_goals()


def draw_judge(surface):
    r = UI21["judge"] or judge_layout()
    panel = begin_panel(760, 410, f"Aquascape judge   {r['overall']} / 100")
    worst = min(("Balance", "Layers", "Colour", "Shelter"), key=lambda k: r[k])
    for i, name in enumerate(("Balance", "Layers", "Colour", "Shelter")):
        y = 74 + i * 52
        txt21(panel, name, 26, y, "h", (255, 232, 140))
        pygame.draw.rect(panel, (24, 44, 70), (170, y + 2, 480, 22), border_radius=6)
        v = r[name]
        col = (110, 210, 140) if v >= 70 else (235, 200, 90) if v >= 40 else (225, 110, 90)
        pygame.draw.rect(panel, col, (170, y + 2, int(480 * v / 100), 22), border_radius=6)
        txt21(panel, str(v), 668, y, "h", (235, 245, 255))
    txt21(panel, f"Best so far: {X['best_scape']}   " + (f"+{r.get('pts', 0)} points just now" if r.get("pts") else "no new points"), 26, 290, "d", HUD_DIM)
    txt21(panel, "Tip:  " + JUDGE_TIPS[worst], 26, 318, "d", (200, 215, 232))
    end_panel(surface, panel, "Esc to close   (points come only when you beat your best score)")


# ---------------------------------------------------------------- 10: before / after
CAP = {"want": None, "delay": 0}


def cap_tick(surface):
    w = CAP["want"]
    if not w:
        return
    if CAP["delay"] > 0:
        CAP["delay"] -= 1
        return
    CAP["want"] = None
    PM["shots"][w] = surface.copy()
    if w == "after":
        UI21["panel"] = "ba"


def draw_ba(surface):
    b, a = PM["shots"]["before"], PM["shots"]["after"]
    if b is None or a is None:
        return
    W, H = surface.get_size()
    mx = int(clamp(world_mouse(pygame.mouse.get_pos())[0], 0, W))
    surface.blit(a, (0, 0))
    if mx > 0:
        surface.blit(b, (0, 0), area=pygame.Rect(0, 0, mx, H))
    pygame.draw.line(surface, (255, 255, 255), (mx, 0), (mx, H), 3)
    pygame.draw.circle(surface, (255, 255, 255), (mx, H // 2), 14)
    pygame.draw.circle(surface, (40, 100, 190), (mx, H // 2), 10)
    for text, x in (("BEFORE", 40), ("AFTER", W - 160)):
        t = f21("t").render(text, True, (255, 255, 255))
        box = pygame.Surface((t.get_width() + 24, t.get_height() + 10), pygame.SRCALPHA)
        pygame.draw.rect(box, (8, 20, 40, 190), box.get_rect(), border_radius=8)
        box.blit(t, (12, 5))
        surface.blit(box, (x, 30))
    hint = f21("d").render("Slide the mouse to compare   Enter: save the picture to the album   Esc: close", True, (235, 245, 255))
    box = pygame.Surface((hint.get_width() + 24, 30), pygame.SRCALPHA)
    pygame.draw.rect(box, (8, 20, 40, 200), box.get_rect(), border_radius=8)
    box.blit(hint, (12, 6))
    surface.blit(box, box.get_rect(midbottom=(W // 2, H - 24)))


def ba_save():
    b, a = PM["shots"]["before"], PM["shots"]["after"]
    if b is None or a is None:
        return
    W, H = b.get_size()
    both = pygame.Surface((W * 2, H))
    both.blit(b, (0, 0))
    both.blit(a, (W, 0))
    os.makedirs("screenshots", exist_ok=True)
    name = time.strftime("screenshots/scape_before_after_%Y%m%d_%H%M%S.png")
    pygame.image.save(both, name)
    album_add(name)
    notify(f"Before / after saved: {name}", log=False)


# ---------------------------------------------------------------- 12: a day in the life, filmed as a camera tour
TOUR = {"on": False, "t": 0, "len": 1000, "clock0": 0.0, "hud": True}


def tour_toggle():
    if TOUR["on"]:
        tour_end()
        return
    if PM["on"] or REC["on"]:
        return
    TOUR.update(on=True, t=0, clock0=eco.clock, hud=eco.show_hud)
    eco.show_hud, eco.selected, eco.follow = False, None, False
    REC.update(on=True, frames=[], n=0, every=10)
    notify("Filming a tank tour: one whole day (Esc stops)", log=False)


def tour_end():
    TOUR["on"] = False
    eco.clock = TOUR["clock0"]
    eco.show_hud = TOUR["hud"]
    X["tours"] += 1
    rec_stop()


def apply_tour_cam(surface):
    if not TOUR["on"]:
        return
    TOUR["t"] += 1
    p = TOUR["t"] / TOUR["len"]
    ease = p * p * (3 - 2 * p)
    eco.clock = (TOUR["clock0"] + p) % 1.0
    zoom = 1.7
    vw, vh = SCREEN_WIDTH / zoom, SCREEN_HEIGHT / zoom
    x = (SCREEN_WIDTH - vw) * ease
    y = clamp(SCREEN_HEIGHT * 0.62 - vh / 2 + math.sin(p * math.tau) * SCREEN_HEIGHT * 0.07, 0, SCREEN_HEIGHT - vh)
    view = surface.subsurface(pygame.Rect(int(x), int(y), int(vw), int(vh))).copy()
    pygame.transform.scale(view, (SCREEN_WIDTH, SCREEN_HEIGHT), surface)
    if TOUR["t"] >= TOUR["len"]:
        rec_capture(surface)
        tour_end()


# ---- sprite cache: fish are drawn once per animation frame instead of every frame ----
SPRITE_CACHE = {}
ROT_CACHE = {}
ORIGINAL_DRAW = {}


def cache_fish_sprites(cls, period, shadow_w, buckets=8):
    """Wrap cls.draw so each fish renders a handful of tail-beat frames once, then just rotates and blits them."""
    original = cls.draw
    ORIGINAL_DRAW[cls] = original
    step = period / buckets

    def make_key(self, b):
        return (type(self).__name__, self.id if getattr(self, "unique", False) else 0, b, round(self.z * 20), min(30, int(self.hunger)) // 15,
                getattr(self, "mouth_open_timer", 0) > 1, round(getattr(self, "puff", 0.0) * 10),
                getattr(self, "sex", ""), int((self.vigor() + 1) * 3), int(getattr(self, "flare", 0)), getattr(self, "gene_key", 0))

    def render(self, key, b, surface):
        global _capture
        real_ticks = pygame.time.get_ticks
        pygame.time.get_ticks = lambda: int(b * step)  # render at the bucket's canonical moment
        _capture = []
        try:
            original(self, surface)
            big = _capture[0] if _capture else None
        finally:
            _capture = None
            pygame.time.get_ticks = real_ticks
        if big is None:
            return None
        big = apply_sex(self, big)
        sprite = pygame.transform.smoothscale(big, (big.get_width() // SS, big.get_height() // SS))
        if len(SPRITE_CACHE) > 2500:
            SPRITE_CACHE.clear()
        SPRITE_CACHE[key] = sprite
        return sprite

    def draw(self, surface):
        if not self.alive:
            return original(self, surface)
        b = int((pygame.time.get_ticks() % period) / step) % buckets
        key = make_key(self, b)
        sprite = SPRITE_CACHE.get(key)
        if sprite is None:
            if SPRITE_BUDGET[0] > 0:
                # A new sprite was already built this frame: borrow a near-identical one (adjacent size or beat) so the frame
                # stays fast; this fish builds its own on a later frame.
                for dz in (1, -1, 2, -2):
                    for db in (0, 1, -1):
                        sprite = SPRITE_CACHE.get(key[:2] + ((b + db) % buckets, key[3] + dz) + key[4:])
                        if sprite is not None:
                            break
                    if sprite is not None:
                        break
            if sprite is None:
                SPRITE_BUDGET[0] += 1
                sprite = render(self, key, b, surface)
                if sprite is None:
                    return
            else:
                self.draw_shadow(surface, shadow_w)
        else:
            self.draw_shadow(surface, shadow_w)
            if getattr(self, "mouth_open_timer", 0) > 0:
                self.mouth_open_timer -= 1
        facing = self.vel.x >= 0
        ab = int(round(self.angle / 3.0))  # rotations are cached per 3 degrees; flip + rotate were a big share of the frame
        rkey = (key, facing, ab)
        img = ROT_CACHE.get(rkey)
        if img is None:
            img = sprite if facing else pygame.transform.flip(sprite, True, False)
            img = pygame.transform.rotate(img, ab * 3.0 if facing else -ab * 3.0)
            if len(ROT_CACHE) > 2500:
                ROT_CACHE.clear()
            ROT_CACHE[rkey] = img
        surface.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))

    def warm(self, scratch):
        """Pre-build all tail-beat frames of this fish's current look (called while the welcome screen is up)."""
        for b in range(buckets):
            key = make_key(self, b)
            if key not in SPRITE_CACHE:
                render(self, key, b, scratch)

    cls.draw = draw
    cls.warm_sprites = warm


SPRITE_BUDGET = [0]   # new sprites built this frame; reset every frame so a burst of cache misses is spread over several frames
WARM_QUEUE = []
WARM_DONE = [False]


def warm_step(budget_ms=10.0):
    """Build cached sprites for the current fish for up to budget_ms; returns True while there is more to do."""
    global WARM_QUEUE
    if WARM_DONE[0]:
        return False
    if not WARM_QUEUE:
        seen = set()
        for f in fishes + predators:
            k = (type(f).__name__, round(f.z * 20), getattr(f, "sex", ""))
            if hasattr(f, "warm_sprites") and (k not in seen or getattr(f, "unique", False)):
                seen.add(k)
                WARM_QUEUE.append(f)
        WARM_QUEUE.append(None)   # sentinel: finished
    t0 = pygame.time.get_ticks()
    scratch = pygame.Surface((8, 8), pygame.SRCALPHA)
    while WARM_QUEUE and pygame.time.get_ticks() - t0 < budget_ms:
        f = WARM_QUEUE.pop(0)
        if f is None:
            WARM_DONE[0] = True
            return False
        f.warm_sprites(scratch)
    return True


SEX_ACCENT = {"PeacockCichlid": (255, 200, 40), "YellowPrinceCichlid": (255, 120, 20), "IceBlueCichlid": (255, 255, 255),
              "DemasoniCichlid": (190, 230, 255), "CobaltZebra": (150, 215, 255), "RedZebra": (255, 215, 150),
              "KenyiCichlid": (255, 235, 120), "AuratusCichlid": (240, 215, 90), "SocolofiCichlid": (255, 170, 170),
              "AngelFish": (255, 255, 255),
              "Pleco": (230, 200, 120), "BalaShark": (255, 255, 255), "NeonTetra": (120, 255, 255), "RummyNose": (255, 80, 80),
              "BoesemaniRainbow": (255, 200, 60), "PearlGourami": (255, 150, 70), "ClownLoach": (255, 220, 120),
              "TigerBarb": (255, 90, 40), "CardinalTetra": (120, 255, 255), "EmberTetra": (255, 200, 100),
              "BlackSkirtTetra": (255, 255, 255), "LemonTetra": (255, 255, 150)}


def apply_sex(f, big):
    """Sexual dimorphism, painted on a finished sprite: females are bigger and have a pale gravid belly,
    males are smaller with a bright nuptial streak and fin-tip dots."""
    sex = getattr(f, "sex", None)
    if sex is None:
        return big
    cls = type(f).__name__
    r = big.get_bounding_rect()
    if r.w < 8 or r.h < 8:
        return big
    accent = SEX_ACCENT.get(cls)
    mark = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    w, h = r.w, r.h
    if sex == "M" and accent:
        y = r.centery - h * 0.05
        pygame.draw.line(mark, (*accent, 185), (r.left + w * 0.30, y), (r.right - w * 0.22, y - h * 0.02), max(2, int(h * 0.05)))
        for k in range(5):
            pygame.draw.circle(mark, (*accent, 210), (int(r.left + w * (0.34 + 0.09 * k)), int(r.top + h * (0.12 + 0.02 * abs(k - 2)))),
                               max(2, int(h * 0.03)))
    elif sex == "F":
        pygame.draw.ellipse(mark, (255, 246, 228, 80), (r.left + w * 0.26, r.centery + h * 0.02, w * 0.44, h * 0.27))
    mask = big.copy()
    mask.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
    mark.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    out = big.copy()
    out.blit(mark, (0, 0))
    size = {"M": 0.94, "F": 1.08}[sex]
    return pygame.transform.smoothscale(out, (max(2, int(out.get_width() * size)), max(2, int(out.get_height() * size))))


for _cls in FW_CLASSES:
    cache_fish_sprites(_cls, 628.32 / _cls.beat, _cls.shadow)


def build_world_extras():
    """Pick the eel's lair and the shrimp stations from the freshly built hardscape."""
    build_cover()
    if not any(not isinstance(r, Driftwood) for r in rocks):   # a tank designed without a single rock has no lair and no stations
        return None, []
    cands = [r for r in rocks if not isinstance(r, Driftwood) and r.y_offset == 0 and r.z >= 0.96
             and 120 < r.pos_x < SCREEN_WIDTH - 120]
    if not cands:
        cands = [r for r in rocks if not isinstance(r, Driftwood)]
    eel = FireEel(random.choice(cands))
    spots = [r for r in rocks if not isinstance(r, Driftwood) and r is not eel.rock and r.y_offset == 0 and r.z >= 0.75]
    random.shuffle(spots)
    chosen = []
    for r in spots:
        if all(abs(r.pos_x - st.pos.x) > 250 for st in chosen):
            chosen.append(CleaningStation(r))
        if len(chosen) == 2:
            break
    return eel, chosen


def init_ecosystem():
    """(Re)build everything the ecosystem layer owns; call after the hardscape and plants exist."""
    global eco
    eco = Ecosystem()
    for lst in (fx, emotes, ripples, inks, respawn_queue, eggs, placed, journal, foam_nests):
        lst.clear()
    eel, chosen = build_world_extras()
    predators[:] = ([Channa(random.randint(150, SCREEN_WIDTH - 150), random.randint(180, 330))] + ([eel] if eel is not None else [])
                    + ([Crayfish()] if CRAY["on"] else [])) if PRED["on"] else []
    stations[:] = chosen
    visitors[:] = []
    crawlers[:] = [MysterySnail(), MysterySnail(), Ramshorn(), Ramshorn()]


pygame.display.set_caption("Pixel Aquarium")
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), 0, display)  # the world; scaled up to the display each frame
clock = pygame.time.Clock()

try:
    splash_img = pygame.transform.scale(pygame.image.load(get_path('splash.png')).convert(),
                                        (SCREEN_WIDTH, SCREEN_HEIGHT))
except:
    splash_img = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    splash_img.fill((20, 40, 80))

welcome_font = pygame.font.SysFont("Arial", 32, bold=True)
notif_font = pygame.font.SysFont("Arial", 16, italic=True)

WELCOME_BR = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 100, 240, 60)
WELCOME_SHADE = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
for _y in range(SCREEN_HEIGHT):   # the live tank shows through; a soft shade keeps the title readable
    _d = abs(_y - SCREEN_HEIGHT * 0.45) / (SCREEN_HEIGHT * 0.55)
    pygame.draw.line(WELCOME_SHADE, (4, 12, 28, int(150 - 90 * min(1.0, _d))), (0, _y), (SCREEN_WIDTH, _y))
welcome_title_font = pygame.font.SysFont("Arial", 84, bold=True)


def draw_welcome_screen():
    """The welcome screen is drawn over the running tank: the fish and plants are the live preview."""
    screen.blit(WELCOME_SHADE, (0, 0))
    title = welcome_title_font.render("PIXEL AQUARIUM", True, (236, 246, 255))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
    bw, bh = 240, 60
    bx, by = (SCREEN_WIDTH // 2) - (bw // 2), (SCREEN_HEIGHT // 2) + 100
    m_pos = world_mouse(pygame.mouse.get_pos())
    br = WELCOME_BR = pygame.Rect(bx, by, bw, bh)
    col = (60, 160, 240) if br.collidepoint(m_pos) else (40, 100, 200)
    pygame.draw.rect(screen, col, br, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), br, 2, border_radius=15)
    txt = welcome_font.render("WELCOME", True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=br.center))
    return br

music_files = ["bgmusic.mp3", "bgmusic2.mp3", "bgmusic3.mp3", "bgmusic4.mp3"]
current_music_idx = 0
try:
    pygame.mixer.music.load(get_path(music_files[current_music_idx]))
    pygame.mixer.music.play(-1)
    apply_music_volume()
except pygame.error:
    print(f"Could not load initial music: {music_files[0]}")

bg_files, bg_index = ["wallart.png", "wallart2.png", "wallart3.png", "wallart4.png","wallart5.png","wallart6.png","wallart7.png","wallart8.png","wallart9.png"], 0
BG_MARGIN = 24  # the wall art is larger than the screen so it can slide behind the glass


def load_bg(name):
    size = (SCREEN_WIDTH + 2 * BG_MARGIN, SCREEN_HEIGHT + 2 * BG_MARGIN)
    return pygame.transform.smoothscale(pygame.image.load(get_path(name)).convert(), size)


try:
    bg_image = load_bg(bg_files[bg_index])
except Exception:
    bg_image = pygame.Surface((SCREEN_WIDTH + 2 * BG_MARGIN, SCREEN_HEIGHT + 2 * BG_MARGIN))
    bg_image.fill((10, 20, 40))

fishes = []  # filled by spawn_community() once the hardscape and plants exist
daphnia = [Daphnia() for _ in range(40)]
shimps = [TinyShrimp() for _ in range(20)]
auto_feed_timer = random.randint(100, 300)
plants = create_plants()
grains = [(random.randint(0, SCREEN_WIDTH), random.randint(SCREEN_HEIGHT - 60, SCREEN_HEIGHT), random.choice([(190, 170, 110), (225, 200, 140)]))
          for _ in range(600)]
algae, pellets, bubbles, frame = [], [], [], 0
rebuild_world()
build_sfx()
init_ecosystem()
fishes[:] = spawn_community()

# Caustics: sunlight rippling through the surface, pre-rendered as a short loop of additive overlays
CAUSTIC_FRAMES = 8
CAUSTIC_SCALE = 4  # One caustic pixel covers this many screen pixels
CAUSTIC_STRENGTH = 34   # brightness of the rippling light (was 70; lower = calmer water)
CAUSTIC_SLOWNESS = 7    # frames per caustic step (was 4; higher = slower shimmer)


def build_caustic_overlays():
    cw, ch = SCREEN_WIDTH // CAUSTIC_SCALE, SCREEN_HEIGHT // CAUSTIC_SCALE
    overlays = []
    for f in range(CAUSTIC_FRAMES):
        t = f / CAUSTIC_FRAMES * math.tau
        small = pygame.Surface((cw, ch))
        for py in range(ch):
            fall = max(0.0, 1.0 - py / (ch * 0.75))  # Light is strongest near the surface
            y = py * CAUSTIC_SCALE * 0.03
            for px in range(cw):
                x = px * CAUSTIC_SCALE * 0.03
                u = x + math.sin(y * 0.7 + t) * 2.0
                v = y + math.cos(x * 0.8 - t) * 2.0
                c = (math.sin(u * 2.1 + t) + math.sin(v * 2.3 - t * 1.1) + math.sin((u + v) * 1.7 + t * 0.7)) / 3
                val = int(max(0.0, c) ** 2.5 * fall * CAUSTIC_STRENGTH)
                small.set_at((px, py), (val, val, int(val * 0.85)))
        overlays.append(pygame.transform.smoothscale(small, (SCREEN_WIDTH, SCREEN_HEIGHT)))
    return overlays


CAUSTIC_OVERLAYS = build_caustic_overlays()

# Sand is static, so its shading, ripples and grains are rendered once into a layer
sand_top_points = [(x, SCREEN_HEIGHT - 60 + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2) for x in range(0, SCREEN_WIDTH + 11, 10)]
sand_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
shaded_polygon(sand_layer, sand_top_points + [(SCREEN_WIDTH, SCREEN_HEIGHT), (0, SCREEN_HEIGHT)],
               (200, 184, 144), (118, 106, 86))
for row in range(4):  # Wind/current ripples across the sand
    y0 = SCREEN_HEIGHT - 44 + row * 11
    ripple = [(x, y0 + math.sin(x * 0.07 + row * 2) * 1.5) for x in range(0, SCREEN_WIDTH + 9, 8)]
    pygame.draw.aalines(sand_layer, (120, 104, 80, 150), False, ripple)
for gx, gy, col in grains:
    if gy > SCREEN_HEIGHT - 60 + math.sin(gx * 0.02) * 5 + math.cos(gx * 0.05) * 2:
        pygame.draw.rect(sand_layer, col, (gx, gy, 2, 2))


class Detritus:
    """Slow drifting detritus that makes the water feel alive and gives depth."""

    def __init__(self):
        self.reset(random.uniform(WATER_TOP, SCREEN_HEIGHT - SAND_HEIGHT))

    def reset(self, y):
        self.pos = pygame.Vector2(random.uniform(0, SCREEN_WIDTH), y)
        self.speed = random.uniform(0.15, 0.45)
        self.phase = random.uniform(0, math.tau)
        self.size = random.choice([1, 1, 1, 2])
        self.col = random.choice([(230, 235, 240), (210, 225, 235)])

    def update(self):
        self.phase += 0.02
        self.pos.y += self.speed
        self.pos.x = (self.pos.x + math.sin(self.phase) * 0.25 + eco.current * 14) % SCREEN_WIDTH
        if self.pos.y > SCREEN_HEIGHT - SAND_HEIGHT:
            self.reset(WATER_TOP)

    def draw(self, surface):
        ox, oy = poff("snow_near" if self.size > 1 else "snow_far")  # big flakes are close to the glass
        pygame.draw.circle(surface, self.col, (int(self.pos.x + ox), int(self.pos.y + oy)), self.size)


snow = [Detritus() for _ in range(90)]
LOG_INTERVAL = 180

# Static layers and reusable surfaces, built once instead of every frame
water_gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
for y in range(SCREEN_HEIGHT):
    t = y / SCREEN_HEIGHT
    col = [int(top * (1 - t) + bottom * t) for top, bottom in zip(CLR_WATER_TOP, CLR_WATER_BOTTOM)]
    pygame.draw.line(water_gradient, (*col, 150), (0, y), (SCREEN_WIDTH, y))

surface_haze = pygame.Surface((SCREEN_WIDTH, 120), pygame.SRCALPHA)
for y in range(120):
    pygame.draw.line(surface_haze, (255, 255, 220, max(0, 100 - y)), (0, y), (SCREEN_WIDTH, y))

light_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# ---- 2.5D: the tank is drawn as depth layers that slide against each other (parallax) ----
# The mid layer is the focal plane where the fish live and food is eaten, so it never moves; layers behind it drift with
# the viewpoint and layers in front drift against it. Fish are assigned to a layer by their z.
PARALLAX_ON = True
PARALLAX = {"bg": 15.0, "hang_bg": 12.0, "hang_fg": -32.0, "far": 8.0, "mid": 0.0, "plants": -8.0, "near": -20.0, "snow_far": 4.0, "snow_near": -40.0, "fore": -95.0}
par = pygame.Vector2()   # smoothed viewpoint in -1..1 (mouse position, plus a slow idle sway so it never looks frozen)
plant_tick = 0
LAYER_FAR, LAYER_MID = 0.5, 0.9   # z cut-offs between the far, mid and near layers
layer_surfs = {name: pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA) for name in ("far", "mid", "plants", "near", "hang_bg", "hang_fg")}
layer_surfs["far"].set_alpha(205)   # distance haze: the far layer is a little washed out into the water


def blit_edges(dest, layer, off, width=520):
    """The hanging vines only live in the left and right edge bands, so only those bands are composited."""
    h = layer.get_height()
    for x in (0, layer.get_width() - width):
        dest.blit(layer, (x + off[0], off[1]), pygame.Rect(x, 0, width, h))


HELP_COLUMNS = [
    ("TANK", [("1 - 5", "Choose feed type"), ("Left click", "Drop food / place tool"), ("Shift-click", "Select a fish"),
              ("Right click", "Tap the glass"), ("Z", "Follow selected fish"), ("W", "Water change"), ("E", "Random event"),
              ("D", "Cycle build tool"), ("F5 / F9", "Save / load tank"), ("R", "Reset tank, reload config")]),
    ("VIEW", [("H", "Show / hide HUD"), ("J", "Show / hide journal"), ("P", "Take a photo"), ("N", "Cycle lighting mode"),
              ("T", "Pause day / night"), ("B", "Cycle background art"), ("X", "Parallax on / off"), ("M", "Next music track"),
              ("V", "Mute / unmute")]),
    ("SYSTEM", [("F1", "This help"), ("Esc", "Close help / ask to quit"), ("F3", "FPS counter"), ("Q", "Quality: Low / Med / High"),
                ("F11", "Fullscreen / window"), ("F10", "Screensaver mode"), ("- / =", "Master volume"), ("[ / ]", "Effects volume")]),
    ("CARE & CAMERA", [("C", "Wipe the glass"), ("F", "Rinse the filter"), ("L", "Lights: Sun / On / Off"), ("A", "Air stone on / off"),
                       ("G", "Goals"), ("K", "Cinema camera"), ("O", "Real-time clock"), ("Del", "Hub: gear, line, upkeep"), ("Ctrl+drag", "Lift a fish"), ("Hold click", "Drip food")]),
    ("HEALTH & HOME", [("U", "Medicine (cure)"), ("I", "Quarantine selected fish"), ("S", "Nursery net on / off"),
                       ("Y", "Heater Off / Low / High"), ("Tab", "Strain book"), ("\\ (hold)", "Timelapse"), ("D > TRIM", "Prune plants"), ("Shift+D", "Trim all plants"), ("9", "Methylene blue"), ("0", "Vitamins"), ("7", "Sell bred fish"), ("8", "Chores & challenges"), ("Ctrl+S", "Settings and save slots")]),
    ("MORE", [("F2", "Social web"), ("F4", "Genetic show"), ("F6", "Rename fish"), ("F7", "Star a favourite"), ("F8", "Story / memorial"), 
              (",", "Equipment shop"), (".", "Aquascapes"), ("/", "Dashboard"), (";", "Water test kit"), ("'", "Fertiliser"),
              ("`", "Soundscape on / off"), ("PgUp", "Photo album"), ("F12", "Record timelapse"), ("Home", "Planting mode"),
              ("PgDn", "Record a tank tour"), ("Ins", "Before / after")]),
]
show_help = False
show_goals = False
show_strains = False
show_fps = False
frame_times = deque(maxlen=120)
photo_flash = 0
FLASH_SURF = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
FLASH_SURF.fill((255, 255, 255))
screensaver = False
saved_hud = True
is_full = True


def set_display(full):
    """F11: switch between the full-screen tank and a window of the same proportions."""
    global display, DISPLAY_W, DISPLAY_H, is_full
    try:
        if full:
            display = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            w = int(info.current_w * 0.72)
            display = pygame.display.set_mode((w, int(w * SCREEN_HEIGHT / SCREEN_WIDTH)))
        is_full = full
    except pygame.error:
        return
    DISPLAY_W, DISPLAY_H = display.get_size()


_help_surf = [None]
confirm_quit = False
QUIT_BTNS = {}


def draw_quit_modal(surface):
    """Esc asks first: Y / Enter quits, N / Esc (or the buttons) keeps watching."""
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 130))
    surface.blit(dim, (0, 0))
    w, h = 460, 190
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 20, 40, 238), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
    title_f = pygame.font.SysFont("Arial", 26, bold=True)
    txt_f = pygame.font.SysFont("Arial", 17)
    btn_f = pygame.font.SysFont("Arial", 18, bold=True)
    t = title_f.render("Leave the aquarium?", True, (235, 245, 255))
    panel.blit(t, ((w - t.get_width()) // 2, 26))
    sub = txt_f.render("Your tank is not saved unless you pressed F5.", True, (190, 210, 228))
    panel.blit(sub, ((w - sub.get_width()) // 2, 70))
    rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    mx, my = world_mouse(pygame.mouse.get_pos())
    for name, label, x, base in (("quit", "Quit  (Y)", 40, (150, 52, 52)), ("keep", "Keep watching  (N)", 250, (36, 96, 140))):
        br = pygame.Rect(x, 112, 170, 46)
        hover = br.move(rect.topleft).collidepoint(mx, my)
        pygame.draw.rect(panel, tuple(min(255, c + (40 if hover else 0)) for c in base), br, border_radius=10)
        pygame.draw.rect(panel, (230, 240, 250), br, 1, border_radius=10)
        lt = btn_f.render(label, True, (255, 255, 255))
        panel.blit(lt, lt.get_rect(center=br.center))
        QUIT_BTNS[name] = br.move(rect.topleft)
    surface.blit(panel, rect)


def draw_help(surface):
    """A modal listing every control (F1). Built once and cached."""
    if _help_surf[0] is None:
        title_f = pygame.font.SysFont("Arial", 26, bold=True)
        head_f = pygame.font.SysFont("Arial", 17, bold=True)
        key_f = pygame.font.SysFont("Consolas", 16, bold=True)
        txt_f = pygame.font.SysFont("Arial", 16)
        row_h, col_w, pad = 24, 316, 26
        per_row = max(1, min(len(HELP_COLUMNS), (SCREEN_WIDTH - 2 * pad - 40) // col_w))   # wrap the columns to fit the screen
        bands = [HELP_COLUMNS[i:i + per_row] for i in range(0, len(HELP_COLUMNS), per_row)]
        band_h = [34 + max(len(c[1]) for c in band) * row_h + 10 for band in bands]
        w, h = pad * 2 + col_w * per_row, pad * 2 + 40 + sum(band_h) + 22
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (8, 20, 40, 238), (0, 0, w, h), border_radius=14)
        pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
        panel.blit(title_f.render("Keyboard & mouse", True, (235, 245, 255)), (pad, pad - 4))
        y0 = pad + 40
        for band, bh in zip(bands, band_h):
            for ci, (head, items) in enumerate(band):
                x = pad + ci * col_w
                panel.blit(head_f.render(head, True, (120, 200, 240)), (x, y0))
                for ri, (key, desc) in enumerate(items):
                    y = y0 + 30 + ri * row_h
                    panel.blit(key_f.render(key, True, (255, 214, 120)), (x, y))
                    panel.blit(txt_f.render(desc, True, (214, 226, 238)), (x + 128, y + 1))
            y0 += bh
        panel.blit(txt_f.render("Press F1 or Esc to close", True, (150, 175, 200)), (pad, h - pad - 2))
        _help_surf[0] = panel
    panel = _help_surf[0]
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    surface.blit(dim, (0, 0))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))


def update_parallax():
    t = pygame.time.get_ticks() * 0.001
    idle = pygame.Vector2(math.sin(t * 0.23), math.sin(t * 0.31 + 1.3) * 0.6) * 0.55
    if mouse_track["inside"]:
        mx, my = mouse_track["pos"]
        goal = pygame.Vector2((mx / SCREEN_WIDTH - 0.5) * 2, (my / SCREEN_HEIGHT - 0.5) * 2) * 0.95 + idle * 0.25
    else:
        goal = idle
    par.update(par + (goal - par) * 0.05 if PARALLAX_ON else par * 0.9)


def poff(name):
    f = PARALLAX[name]
    return (int(par.x * f), int(par.y * f * 0.3))


def build_far_ridge():
    """A dim silhouette of distant gravel hills and driftwood along the back wall, sitting behind everything else."""
    w, h = SCREEN_WIDTH + 80, SCREEN_HEIGHT
    ridge = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = random.Random(77)
    base = h - SAND_HEIGHT - 50
    pts = [(x, base - (40 + 26 * math.sin(x * 0.011 + 1.0) + 18 * math.sin(x * 0.027 + 2.0)
                       + 12 * math.sin(x * 0.061)) * VS) for x in range(0, w + 16, 16)]
    pygame.draw.polygon(ridge, (14, 44, 96, 120), pts + [(w, h), (0, h)])
    for _ in range(max(5, w // 170)):  # distant snags of driftwood standing on the hills
        x = rng.randint(0, w)
        y = base - (40 + 26 * math.sin(x * 0.011 + 1.0) + 18 * math.sin(x * 0.027 + 2.0)) * VS
        ln = rng.randint(40, 90) * VS
        lean = rng.randint(-26, 26)
        pygame.draw.line(ridge, (16, 52, 108, 120), (x, y + 6), (x + lean, y - ln), rng.randint(4, 7))
        for k in range(rng.randint(1, 3)):
            t = rng.uniform(0.35, 0.8)
            bx, by = x + lean * t, y - ln * t
            pygame.draw.line(ridge, (16, 52, 108, 120), (bx, by), (bx + rng.choice((-1, 1)) * rng.randint(14, 30), by - rng.randint(10, 26)), 3)
    return ridge


far_ridge = build_far_ridge()
FORE_W = 320
fore_strip = pygame.Surface((FORE_W, SCREEN_HEIGHT), pygame.SRCALPHA)
fore_strip.set_alpha(165)
FORE_BLADES = [(random.randint(60, FORE_W - 40), random.randint(int(0.22 * SCREEN_HEIGHT), int(0.5 * SCREEN_HEIGHT)),
                random.randint(26, 46), random.uniform(0, math.tau), random.randint(-8, 8)) for _ in range(6)]


def draw_foreground(surface, frame):
    """Big dark vallisneria blades hugging the glass at both edges. They sit furthest forward, so they slide the most."""
    fore_strip.fill((0, 0, 0, 0))
    for bx, height, width, phase, tint in FORE_BLADES:
        pts_l, pts_r = [], []
        steps = 14
        for i in range(steps + 1):
            u = i / steps
            sway = math.sin(frame * 0.012 + phase + u * 2.2) * 30 * u * u
            x = bx + sway + 60 * math.sin(phase) * u * u
            y = SCREEN_HEIGHT - u * height
            wd = width * 0.5 * (1 - u) ** 0.8 + 1
            pts_l.append((x - wd, y))
            pts_r.append((x + wd, y))
        col = (10 + tint, 38 + tint, 44 + tint)
        pygame.draw.polygon(fore_strip, col, pts_l + pts_r[::-1])
        pygame.draw.lines(fore_strip, (col[0] + 18, col[1] + 30, col[2] + 28), False, pts_l, 2)
    ox, oy = poff("fore")
    surface.blit(fore_strip, (-110 + ox, oy))
    surface.blit(pygame.transform.flip(fore_strip, True, False), (SCREEN_WIDTH - FORE_W + 110 + ox, oy))


# ---- doodads: extra scenery in the back and front layers, so the parallax has plenty to slide against ----
PARALLAX.update({"deep": 11.0, "deep2": 6.0, "fg1": -85.0, "fg2": -68.0, "fg3": -115.0})
_doodad_rng = random.Random(4242)


def soft_blur(surf, factor=4):
    """Cheap depth-of-field: shrink then enlarge with smoothing."""
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


# --- distant plant tufts: dim silhouettes that sway slowly, deep behind everything ---
def build_deep_stalk(h, seed):
    """A tuft of long thin grass blades that lean and curl, dim and out of focus."""
    rng = random.Random(seed)
    w = 96
    surf = pygame.Surface((w, int(h) + 12), pygame.SRCALPHA)
    col = (14, 50, 102, 255)
    for b in range(rng.randint(4, 6)):
        lean = rng.uniform(-0.5, 0.5)
        ln = h * rng.uniform(0.55, 1.0)
        wd = rng.uniform(3.5, 6.0)
        left, right = [], []
        for i in range(13):
            u = i / 12
            cx = w / 2 + (b - 2) * 5 + lean * ln * u * u * 0.5 + math.sin(u * 3.2 + seed + b) * 4 * u
            cy = h + 6 - ln * u
            half = wd * 0.5 * (1 - u ** 1.6) + 0.4
            left.append((cx - half, cy))
            right.append((cx + half, cy))
        pygame.draw.polygon(surf, col, left + right[::-1])
    return surf


DEEP_SHAPES = [(build_deep_stalk(random.Random(i).uniform(230, 520) * VS ** 0.8, i)) for i in range(4)]
DEEP_ROT = {}
DEEP_STALKS = [(_doodad_rng.uniform(-40, SCREEN_WIDTH + 40), _doodad_rng.randrange(4), _doodad_rng.uniform(0, math.tau))
               for _ in range(max(14, SCREEN_WIDTH // 80))]


def deep_sprite(shape, step):
    key = (shape, step)
    spr = DEEP_ROT.get(key)
    if spr is None:
        spr = pygame.transform.rotate(DEEP_SHAPES[shape], step * 1.6)
        spr.set_alpha(62)
        DEEP_ROT[key] = spr
    return spr


# --- (jellyfish removed for freshwater; the list stays empty) ---
def build_jelly(size, frame_i):
    w, h = int(size * 1.4), int(size * 3.2)
    spr = pygame.Surface((w, h), pygame.SRCALPHA)
    pulse = math.sin(frame_i / 6 * math.tau)
    bw, bh = size * (1.0 + 0.1 * pulse), size * (0.72 - 0.12 * pulse)
    cx = w / 2
    for k in range(6):
        tx = cx + (k - 2.5) * size * 0.16
        pts = [(tx + math.sin(k + j * 0.7 + frame_i * 0.5) * size * 0.08, bh * 0.6 + j * size * 0.3) for j in range(8)]
        pygame.draw.lines(spr, (170, 205, 245, 130), False, pts, 1)
    shaded_ellipse(spr, (cx - bw / 2, 2, bw, bh), (196, 220, 255), (110, 150, 225), 8)
    pygame.draw.ellipse(spr, (225, 240, 255, 150), (cx - bw * 0.28, 5, bw * 0.56, bh * 0.35))
    pygame.draw.arc(spr, (230, 240, 255, 200), (cx - bw / 2, 2, bw, bh * 1.5), 0.15, math.pi - 0.15, 1)
    spr.set_alpha(120)
    return spr


JELLY_FRAMES = {s: [build_jelly(s, i) for i in range(6)] for s in (30, 44, 58)}
JELLIES = [[_doodad_rng.uniform(0, SCREEN_WIDTH), _doodad_rng.uniform(WATER_TOP + 60, SCREEN_HEIGHT - 200),
            _doodad_rng.choice([30, 44, 58]), _doodad_rng.uniform(0, 6), _doodad_rng.uniform(-0.18, 0.18)] for _ in range(0)]


# --- a distant school of tiny fish crossing the back of the tank ---
def build_micro_fish():
    spr = pygame.Surface((26, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(spr, (28, 74, 132, 255), (6, 2, 18, 8))
    pygame.draw.polygon(spr, (28, 74, 132, 255), [(8, 6), (0, 1), (0, 11)])
    spr.set_alpha(120)
    return spr


MICRO_FISH = build_micro_fish()
MICRO_FLIP = pygame.transform.flip(MICRO_FISH, True, False)
SCHOOL = {"x": SCREEN_WIDTH * 0.3, "y": WATER_TOP + 220 * VS, "dir": 1,
          "members": [(_doodad_rng.uniform(-90, 90), _doodad_rng.uniform(-40, 40), _doodad_rng.uniform(0, math.tau)) for _ in range(14)]}


def draw_deep_doodads(surface, clock):
    ox, oy = poff("deep")
    base_y = SCREEN_HEIGHT - SAND_HEIGHT - 50 + oy
    for x, shape, ph in DEEP_STALKS:
        step = max(-3, min(3, round((math.sin(clock * 0.011 + ph + x * 0.004) * 2.4 + eco.current * 20) / 1.6)))
        spr = deep_sprite(shape, step)
        r = DEEP_SHAPES[shape].get_height() / 2 - 6
        a = math.radians(step * 1.6)
        cxs, cys = x + ox - r * math.sin(a), base_y - r * math.cos(a)
        surface.blit(spr, spr.get_rect(center=(int(cxs), int(cys))))
    ox2, oy2 = poff("deep2")
    for j in JELLIES:
        j[1] -= 0.18
        j[0] += j[4] + math.sin(clock * 0.01 + j[3]) * 0.12
        if j[1] < WATER_TOP + 20:
            j[1] = SCREEN_HEIGHT - 150
            j[0] = _doodad_rng.uniform(0, SCREEN_WIDTH)
        frames = JELLY_FRAMES[j[2]]
        spr = frames[int(clock / 7 + j[3]) % 6]
        surface.blit(spr, (int(j[0] % SCREEN_WIDTH) + ox2, int(j[1]) + oy2))
    SCHOOL["x"] += 0.35 * SCHOOL["dir"]
    SCHOOL["y"] += math.sin(clock * 0.004) * 0.15
    if SCHOOL["x"] > SCREEN_WIDTH + 140 or SCHOOL["x"] < -140:
        SCHOOL["dir"] *= -1
        SCHOOL["y"] = WATER_TOP + _doodad_rng.uniform(120, 360) * VS
    spr = MICRO_FISH if SCHOOL["dir"] > 0 else MICRO_FLIP
    for mx, my, ph in SCHOOL["members"]:
        surface.blit(spr, (int(SCHOOL["x"] + mx + math.sin(clock * 0.02 + ph) * 12) + ox2, int(SCHOOL["y"] + my + math.cos(clock * 0.017 + ph) * 8) + oy2))


# --- foreground: big out-of-focus rocks, driftwood and leaves at the bottom corners, bokeh, bubbles and a passing silhouette ---
def build_fg_corner(seed, flip):
    rng = random.Random(seed)
    w, h = 230, 190   # drawn at half size, then blown up and blurred
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for k in range(4):  # rounded rock mounds that fall away from the corner
        rw, rh = rng.randint(60, 110), rng.randint(40, 80)
        rx, ry = rng.randint(0, w - rw - 30), h - rh - rng.randint(0, 30)
        pts = smooth_closed([(rx, h + 4), (rx + 4, ry + rh * 0.5), (rx + rw * 0.3, ry + 6), (rx + rw * 0.7, ry), (rx + rw, ry + rh * 0.6), (rx + rw + 8, h + 4)], 5)
        shaded_polygon(surf, pts, (70, 104, 110), (20, 40, 54))
    cx = rng.randint(70, w - 100)
    bark = (84, 58, 38)
    for k in range(3):  # a driftwood branch with forks, lying across the corner
        bx = rng.randint(10, w - 90)
        by = h - rng.randint(8, 26)
        pts = [(bx, by), (bx + 26, by - 14), (bx + 56, by - 10), (bx + 84, by - 30)]
        pygame.draw.lines(surf, bark, False, pts, 8 - k)
        pygame.draw.lines(surf, (118, 86, 58), False, [(x, y - 2) for x, y in pts], 2)
        fx, fy = pts[2]
        pygame.draw.lines(surf, bark, False, [(fx, fy), (fx + 10, fy - 26), (fx + 4, fy - 46)], 5)
    for k in range(5):  # broad sword-plant leaves arching out of the corner
        sx = rng.randint(14, w - 24)
        lean = rng.uniform(-1, 1)
        ln = rng.randint(70, 140)
        left, right = [], []
        for i in range(10):
            u = i / 9
            cx = sx + lean * ln * u * 0.55 + math.sin(u * 2.6 + k) * 6
            cy = h - ln * u
            half = 11 * math.sin(math.pi * min(1.0, u * 1.05)) ** 0.7 + 0.5
            left.append((cx - half, cy))
            right.append((cx + half, cy))
        pygame.draw.polygon(surf, mix((58, 124, 62), (28, 80, 46), k / 5), left + right[::-1])
        pygame.draw.lines(surf, (110, 168, 96), False, [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(left, right)], 1)
    big = pygame.transform.smoothscale(surf, (w * 2, h * 2))
    big = soft_blur(big, 5)
    big.fill((150, 172, 196, 255), special_flags=pygame.BLEND_RGBA_MULT)
    big.set_alpha(215)
    return pygame.transform.flip(big, True, False) if flip else big


FG_CORNER_L = build_fg_corner(11, False)
FG_CORNER_R = build_fg_corner(23, True)


def build_bokeh(r):
    spr = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    for k in range(r, 0, -1):
        pygame.draw.circle(spr, (210, 235, 255, int(46 * (1 - k / r) ** 0.5 + 8)), (r + 1, r + 1), k)
    return spr


BOKEH = {r: build_bokeh(r) for r in (7, 11, 16)}
BOKEH_LIST = [[_doodad_rng.uniform(0, SCREEN_WIDTH), _doodad_rng.uniform(WATER_TOP, SCREEN_HEIGHT), _doodad_rng.choice([7, 11, 16]),
               _doodad_rng.uniform(0.12, 0.38), _doodad_rng.uniform(0, math.tau)] for _ in range(16)]


def build_big_bubble(r):
    spr = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(spr, (210, 235, 255, 40), (r + 2, r + 2), r)
    pygame.draw.circle(spr, (235, 248, 255, 190), (r + 2, r + 2), r, 2)
    pygame.draw.ellipse(spr, (255, 255, 255, 220), (r * 0.5, r * 0.45, r * 0.5, r * 0.3))
    return spr


BIG_BUBBLES = {r: build_big_bubble(r) for r in (6, 9, 13)}
FG_BUBBLES = []


def build_passing_fish():
    w, h = 300, 130
    spr = pygame.Surface((w, h), pygame.SRCALPHA)
    col = (8, 30, 70, 255)
    pygame.draw.ellipse(spr, col, (60, 24, 210, 82))
    pygame.draw.polygon(spr, col, [(76, 64), (10, 14), (30, 64), (10, 114)])
    pygame.draw.polygon(spr, col, [(150, 26), (190, 0), (225, 30)])
    spr = soft_blur(spr, 4)
    spr.set_alpha(110)
    return spr


PASSING_FISH = build_passing_fish()
PASSING = {"x": -400.0, "y": 300.0, "dir": 1, "wait": 900}


def draw_fore_doodads(surface, clock):
    # passing, very out-of-focus fish
    p = PASSING
    if p["wait"] > 0:
        p["wait"] -= 1
        if p["wait"] == 0:
            p["dir"] = random.choice([-1, 1])
            p["x"] = -340 if p["dir"] > 0 else SCREEN_WIDTH + 340
            p["y"] = random.uniform(WATER_TOP + 120, SCREEN_HEIGHT - 260)
    else:
        p["x"] += 1.1 * p["dir"]
        spr = PASSING_FISH if p["dir"] > 0 else pygame.transform.flip(PASSING_FISH, True, False)
        ox, oy = poff("fg3")
        surface.blit(spr, (int(p["x"]) + ox, int(p["y"] + math.sin(clock * 0.01) * 14) + oy))
        if p["x"] < -420 or p["x"] > SCREEN_WIDTH + 420:
            p["wait"] = random.randint(1500, 3600)
    ox, oy = poff("fg2")
    for b in BOKEH_LIST:
        b[1] -= b[3]
        b[0] += math.sin(clock * 0.01 + b[4]) * 0.2
        if b[1] < WATER_TOP - 20:
            b[1] = SCREEN_HEIGHT + 20
            b[0] = random.uniform(0, SCREEN_WIDTH)
        spr = BOKEH[b[2]]
        surface.blit(spr, (int(b[0]) + ox - b[2], int(b[1]) + oy - b[2]))
    if clock % 140 == 0 and len(FG_BUBBLES) < 7:
        FG_BUBBLES.append([random.uniform(40, SCREEN_WIDTH - 40), SCREEN_HEIGHT + 10, random.choice([6, 9, 13]), random.uniform(1.0, 2.2), random.uniform(0, 6)])
    for b in FG_BUBBLES[:]:
        b[1] -= b[3]
        b[0] += math.sin(clock * 0.05 + b[4]) * 0.6
        if b[1] < WATER_TOP - 20:
            FG_BUBBLES.remove(b)
            continue
        spr = BIG_BUBBLES[b[2]]
        surface.blit(spr, (int(b[0]) + ox - b[2], int(b[1]) + oy - b[2]))
    fx, fy = poff("fg1")
    surface.blit(FG_CORNER_L, (-200 + fx, SCREEN_HEIGHT - FG_CORNER_L.get_height() + 90 + fy))
    surface.blit(FG_CORNER_R, (SCREEN_WIDTH - FG_CORNER_R.get_width() + 200 + fx, SCREEN_HEIGHT - FG_CORNER_R.get_height() + 90 + fy))


start_hum()
if AWAY["on"]:
    try_autoload()

while True:
    SPRITE_BUDGET[0] = 0
    WELCOME_LIVE = current_state == STATE_WELCOME
    if WELCOME_LIVE:
        warm_step(10.0)   # the welcome screen is idle time: build the fish sprites now so the tank never hitches later
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                quit_game()
            if e.type == pygame.MOUSEBUTTONDOWN and WELCOME_BR.collidepoint(world_mouse(e.pos)):
                current_state = STATE_AQUARIUM
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    current_state = STATE_AQUARIUM
    else:
        warm_step(3.0)   # finish any sprites the welcome screen didn't get to, a few ms at a time
    if True:   # the tank runs behind the welcome screen too, so the menu is a live preview
        frame += 1
        if frame % LOG_INTERVAL == 0:
            starving_count = 0
            log_output = ""
            fish_counts = {}

            for f in fishes:
                fish_type = f.__class__.__name__
                fish_counts[fish_type] = fish_counts.get(fish_type, 0) + 1
                if f.hunger > 70:
                    log_output += f"[{fish_type} #{getattr(f, 'id', '???')}] "
                    starving_count += 1

            print("--- Current Tank Population ---")
            sorted_fish = sorted(fish_counts.items(), key=lambda item: item[1], reverse=True)
            for species, count in sorted_fish:
                print(f"{species}: {count}")

            if starving_count > 0:
                print(f"\n--- ALERT: STARVING FISH DETECTED ({starving_count}) ---")
                print(log_output.strip())
                print("---------------------------------------------------\n")
            if starving_count > 10:
                print("!!! CRITICAL STARVATION: MASSIVE ALGAE BLOOM TRIGGERED !!!")
                for _ in range(50):
                    new_algae = (
                        random.randint(20, SCREEN_WIDTH - 20),
                        random.randint(int(WATER_TOP + 220 * VS), SCREEN_HEIGHT - SAND_HEIGHT)
                    )
                    algae.append(new_algae)

        update_parallax()
        bgx, bgy = poff("bg")
        screen.blit(bg_image, (bgx - BG_MARGIN, bgy - BG_MARGIN))
        screen.blit(water_gradient, (0, 0))
        screen.blit(far_ridge, (-40 + poff("far")[0], poff("far")[1]))
        draw_deep_doodads(screen, PLANT_CLOCK)

        auto_feed_timer -= 1
        if auto_feed_timer <= 0:
            if len(pellets) < 15:
                pellets.append(FoodPellet(random.randint(50, SCREEN_WIDTH - 50), WATER_TOP))
            auto_feed_timer = 100

        update_mouse_track()
        eco.update()
        process_respawns()
        fw21_update()
        for p in (() if PM["on"] else predators[:]):
            p.update()
            if not p.alive:
                predators.remove(p)
        for v in (() if PM["on"] else visitors[:]):
            v.update()
            if not v.alive:
                visitors.remove(v)

        for f in (() if PM["on"] else fishes[:]):   # planting mode: the fish are put away, nothing swims or ages
            if not f.alive:  # eaten this frame; a newcomer swims in later
                record_death(f, "eaten")
                fishes.remove(f)
                respawn_queue.append((eco.t + random.randint(300, 800), "fish"))
                continue
            f.behavior(fishes)
            prey_social(f)
            feed_learning(f)
            fish_life(f)
            f.update(pellets, algae)
            if not f.alive:  # starved
                record_death(f)
                fishes.remove(f)
                respawn_queue.append((eco.t + random.randint(120, 360), "fish"))
        eco.refresh_moods()
        update_plants()

        plant_tick += 1
        # Plants sway slowly and are the costliest layer, so each frame redraws only one third-width strip of the tank
        # (rotating), which keeps the load identical every frame instead of one heavy frame in three.
        n_strips = QUALITY_SPECS[QUALITY[0]]["strips"]
        strip_w = SCREEN_WIDTH // n_strips + 1
        strip = pygame.Rect((plant_tick % n_strips) * strip_w, 0, strip_w, SCREEN_HEIGHT)
        for name, layer in layer_surfs.items():
            if name in ("plants", "hang_bg", "hang_fg"):
                layer.fill((0, 0, 0, 0), strip)
            else:
                layer.fill((0, 0, 0, 0))
        L_far, L_mid, L_plants, L_near = (layer_surfs[k] for k in ("far", "mid", "plants", "near"))
        entities = [] if PM["on"] else sorted(fishes + predators + visitors, key=lambda e: e.z)
        for e in entities:
            if e.dz <= LAYER_FAR:
                e.draw(L_far)
        for r in rocks:
            if r.z < LAYER_FAR:
                r.draw(L_far)
        for e in entities:
            if LAYER_FAR < e.dz <= LAYER_MID:
                e.draw(L_mid)
        for r in rocks:
            if LAYER_FAR <= r.z < 0.95:
                r.draw(L_mid)
        draw_stations(L_mid, False)
        L_hbg, L_hfg = layer_surfs["hang_bg"], layer_surfs["hang_fg"]
        for lay in (L_plants, L_hbg, L_hfg):
            lay.set_clip(strip)
        hang_target = {"bg": L_hbg, "mid": L_plants, "fg": L_hfg}
        for p in plants:
            if strip.left - 90 < p.pos_x < strip.right + 90:
                p.draw(hang_target[p.layer] if p.hang else L_plants, frame)
        for lay in (L_plants, L_hbg, L_hfg):
            lay.set_clip(None)
        for e in entities:
            if e.dz > LAYER_MID:
                e.draw(L_near)
        for r in rocks:
            if r.z >= 0.95:
                r.draw(L_near)
        draw_stations(L_near, True)
        for egg in eggs:
            egg.draw(L_near)
        for p in pebbles:
            p.draw(L_near)
        for c in (() if PM["on"] else crawlers):
            c.update()
            c.draw(L_near)

        blit_edges(screen, L_hbg, poff("hang_bg"))   # pothos behind the fish
        screen.blit(L_far, poff("far"))
        screen.blit(sand_layer, (0, SCREEN_HEIGHT - 120), area=pygame.Rect(0, SCREEN_HEIGHT - 120, SCREEN_WIDTH, 120))
        screen.blit(L_mid, (0, 0))
        screen.blit(L_plants, poff("plants"))
        screen.blit(L_near, poff("near"))
        blit_edges(screen, L_hfg, poff("hang_fg"))   # pothos in front of everything in the tank

        draw_sick(screen)
        draw_world21(screen)
        draw_world6(screen)
        for nst in foam_nests[:]:
            if nst.update():
                nst.draw(screen)
            else:
                foam_nests.remove(nst)
        for s in (() if PM["on"] else shimps):
            s.update(algae)
            shrimp_flee(s)
            s.draw(screen)
        draw_air_stone(screen)
        draw_nets(screen)
        draw_shells(screen)
        if eco.bag is not None:
            eco.bag.draw(screen)
        for k in (() if PM["on"] else daphnia):
            update_daphnia(k)
            k.draw(screen)

        for s in snow:
            s.update()
            s.draw(screen)

        screen.blit(CAUSTIC_OVERLAYS[(frame // CAUSTIC_SLOWNESS) % CAUSTIC_FRAMES], (poff('bg')[0] // 2, 0), special_flags=pygame.BLEND_RGB_ADD)

        for e in (() if WELCOME_LIVE else pygame.event.get()):
            if e.type == pygame.QUIT:
                quit_game()
            if screensaver:   # any key or click wakes the tank back up
                if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    screensaver = False
                    eco.show_hud = saved_hud
                    pygame.mouse.set_visible(True)
                continue
            if confirm_quit:   # the quit dialog swallows all other input
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                        quit_game()
                    if e.key in (pygame.K_n, pygame.K_ESCAPE):
                        confirm_quit = False
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    pos = world_mouse(e.pos)
                    if QUIT_BTNS.get("quit") and QUIT_BTNS["quit"].collidepoint(pos):
                        quit_game()
                    if QUIT_BTNS.get("keep") and QUIT_BTNS["keep"].collidepoint(pos):
                        confirm_quit = False
                continue
            if pm_event(e):
                continue
            if fw21_event(e):
                continue
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F1:
                    show_help = not show_help
                elif e.key == pygame.K_ESCAPE and show_help:
                    show_help = False
                elif e.key == pygame.K_ESCAPE and show_goals:
                    show_goals = False
                elif e.key == pygame.K_ESCAPE and show_strains:
                    show_strains = False
                elif e.key == pygame.K_ESCAPE:
                    confirm_quit = True
                if e.key == pygame.K_F3:
                    show_fps = not show_fps
                if e.key == pygame.K_q:
                    names = list(QUALITY_SPECS)
                    QUALITY[0] = names[(names.index(QUALITY[0]) + 1) % len(names)]
                    GOV["base"] = QUALITY[0]
                    save_prefs()
                    light_notif_text = "Quality: " + QUALITY[0]
                    light_notif_alpha = 255
                if e.key == pygame.K_F11:
                    set_display(not is_full)
                    light_notif_text = "Fullscreen" if is_full else "Windowed"
                    light_notif_alpha = 255
                if e.key == pygame.K_F10:
                    screensaver, saved_hud = True, eco.show_hud
                    eco.show_hud, eco.show_journal, show_help = False, False, False
                    light_notif_alpha = 0
                    if not is_full:
                        set_display(True)
                    pygame.mouse.set_visible(False)
                if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    step = -0.1 if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS) else 0.1
                    VOL["master"] = clamp(round(VOL["master"] + step, 2))
                    apply_music_volume()
                    save_prefs()
                    play_sfx("bubble")
                    light_notif_text = f"Volume {round(VOL['master'] * 100)}%"
                    light_notif_alpha = 255
                if e.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    VOL["fx"] = clamp(round(VOL["fx"] + (-0.1 if e.key == pygame.K_LEFTBRACKET else 0.1), 2))
                    save_prefs()
                    play_sfx("chime")
                    light_notif_text = f"Effects volume {round(VOL['fx'] * 100)}%"
                    light_notif_alpha = 255
                if e.key == pygame.K_9:
                    pour_methylene_blue()
                if e.key == pygame.K_0:
                    pour_vitamins()
                if e.key == pygame.K_u:
                    dose_medicine()
                if e.key == pygame.K_i:
                    toggle_quarantine()
                if e.key == pygame.K_s:
                    toggle_nursery()
                if e.key == pygame.K_y:
                    eco.heater = {"OFF": "LOW", "LOW": "HIGH", "HIGH": "OFF"}[eco.heater]
                    notify("Heater: " + eco.heater, log=False)
                if e.key == pygame.K_TAB:
                    show_strains = not show_strains
                if e.key == pygame.K_c:
                    start_wipe()
                if e.key == pygame.K_f:
                    rinse_filter()
                    chem_rinse()
                if e.key == pygame.K_l:
                    eco.lights = {"SUN": "ON", "ON": "OFF", "OFF": "SUN"}[eco.lights]
                    notify("Lights: " + eco.lights, log=False)
                if e.key == pygame.K_a:
                    eco.air_on = not eco.air_on
                    notify("Air stone: " + ("ON" if eco.air_on else "OFF"), log=False)
                if e.key == pygame.K_g:
                    show_goals = not show_goals
                if e.key == pygame.K_k:
                    eco.cinema = not eco.cinema
                    eco.cin_t = 0
                    if not eco.cinema:
                        eco.follow = False
                    notify("Cinema camera: " + ("ON" if eco.cinema else "OFF"), log=False)
                if e.key == pygame.K_o:
                    eco.realtime = not eco.realtime
                    notify("Clock: " + ("REAL TIME" if eco.realtime else "TANK TIME"), log=False)
                if e.key == pygame.K_x:
                    PARALLAX_ON = not PARALLAX_ON
                    light_notif_text = "Parallax: " + ("ON" if PARALLAX_ON else "OFF")
                    light_notif_alpha = 255
                if e.key == pygame.K_v:
                    is_muted = not is_muted
                    apply_music_volume()
                    light_notif_text = "Audio: MUTED" if is_muted else "Audio: ON"
                    light_notif_alpha = 255
                if e.key == pygame.K_m:
                    current_music_idx = (current_music_idx + 1) % len(music_files)
                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(get_path(music_files[current_music_idx]))
                        apply_music_volume()
                        pygame.mixer.music.play(-1)
                        light_notif_text = f"NOW PLAYING: {music_files[current_music_idx]}"
                        light_notif_alpha = 255
                    except pygame.error:
                        print(f"Error loading: {music_files[current_music_idx]}")
                if e.key == pygame.K_n:
                    current_light_idx = (current_light_idx + 1) % len(LIGHT_MODES)
                    light_notif_text = f"Mode: {LIGHT_MODES[current_light_idx]['name']}"
                    light_notif_alpha = 255
                if e.key == pygame.K_b:
                    bg_index = (bg_index + 1) % len(bg_files)
                    light_notif_text = f"ART CHANGED TO: {bg_files[bg_index]}"
                    light_notif_alpha = 255
                    try:
                        bg_image = load_bg(bg_files[bg_index])
                    except Exception:
                        pass
                if e.key == pygame.K_r:
                    current_state, frame = STATE_WELCOME, 0
                    fishes = []
                    shimps = [TinyShrimp() for _ in range(20)]
                    daphnia = [Daphnia() for _ in range(40)]
                    rebuild_world()
                    algae.clear()
                    pellets.clear()
                    bubbles.clear()
                    init_ecosystem()
                    load_fish_config()
                    fishes[:] = spawn_community()
                if e.key == pygame.K_h:
                    eco.show_hud = not eco.show_hud
                if e.key == pygame.K_t:
                    eco.cycle_on = not eco.cycle_on
                    notify("Day/night cycle: " + ("RUNNING" if eco.cycle_on else "PAUSED"))
                if e.key == pygame.K_e:
                    eco.start_event()
                if e.key == pygame.K_j:
                    eco.show_journal = not eco.show_journal
                if e.key == pygame.K_p and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    PHOTO["style"] = (PHOTO["style"] + 1) % len(PHOTO_STYLES)
                    notify("Photo style: " + PHOTO_STYLES[PHOTO["style"]], log=False)
                elif e.key == pygame.K_p:
                    eco.photo = True
                if e.key == pygame.K_z and eco.selected is not None:
                    eco.follow = not eco.follow
                if e.key == pygame.K_w:
                    eco.water = min(100.0, eco.water + 35)
                    play_sfx("bubble")
                    notify("Water change: the tank is fresher", log=True)
                    chem_water_change()
                if e.key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    trim_plants()
                elif e.key == pygame.K_d:
                    eco.decor_idx = (eco.decor_idx + 1) % len(DECOR_TOOLS)
                    notify("Build tool: " + DECOR_TOOLS[eco.decor_idx] + (" (click to place)" if eco.decor_idx else ""), log=False)
                if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    eco.feed_idx = e.key - pygame.K_1
                    notify("Feed: " + FEEDS[eco.feed_idx], log=False)
                if e.key == pygame.K_F5:
                    save_game()
                if e.key == pygame.K_F9:
                    backup_current()
                    load_game()
            if e.type == pygame.MOUSEBUTTONDOWN:
                tool = DECOR_TOOLS[eco.decor_idx]
                if e.button == 2 or (e.button == 1 and pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    pick_fish(pygame.Vector2(world_mouse(e.pos)))
                elif e.button == 1 and tool == "TRIM":
                    trim_plants(world_mouse(e.pos)[0])
                elif e.button == 1 and tool != "OFF":
                    place_decor(tool, world_mouse(e.pos)[0])
                elif e.button == 1:
                    if eco.selected is not None and eco.follow is False and not any(
                            f.pos.distance_to(pygame.Vector2(world_mouse(e.pos))) < 60 for f in fishes):
                        eco.selected = None
                    drop_feed(world_mouse(e.pos))
                elif e.button == 3:
                    eco.tap(world_mouse(e.pos))

        if frame % ALGAE_SPAWN_RATE == 0 and len(algae) < 35:
            algae.append((random.randint(10, SCREEN_WIDTH - 10), random.randint(WATER_TOP + 20, SCREEN_HEIGHT - SAND_HEIGHT - 60)))

        for a in algae:
            pygame.draw.circle(screen, CLR_ALGAE, a, 3)

        for p in pellets[:]:
            p.update()
            p.draw(screen)

        for b in bubbles[:]:
            b.update()
            b.draw(screen)
            if b.pos.y < 80:
                bubbles.remove(b)

        draw_fx(screen)
        draw_fore_doodads(screen, PLANT_CLOCK)
        draw_foreground(screen, frame)
        draw_algae_world(screen)
        screen.blit(surface_haze, (0, 0))
        draw_daylight(screen)
        draw_glass(screen)
        draw_moon(screen)
        draw_rain(screen)

        mode = LIGHT_MODES[current_light_idx]

        if mode["name"] == "RGB STROBE":
            t = pygame.time.get_ticks() * 0.0005
            r = int(127 + 127 * math.sin(t))
            g = int(127 + 127 * math.sin(t + 2))
            b = int(127 + 127 * math.sin(t + 4))
            light_surf.fill((r, g, b, 40))
        else:
            light_surf.fill(mode["color"])

        screen.blit(light_surf, (0, 0))
        draw_emotes(screen)
        draw_selection(screen)
        apply_follow_cam(screen)
        apply_tour_cam(screen)
        cap_tick(screen)
        if eco.photo:  # captured before the HUD goes on, so the picture is clean
            eco.photo = False
            take_photo(screen)
        rec_capture(screen)
        draw_ui(screen)
        draw_care_status(screen)
        draw_hud21(screen)
        draw_card21(screen)
        draw_hud6(screen)
        draw_plant_mode(screen)
        if show_goals:
            draw_goals(screen)
        if show_strains:
            draw_strains(screen)
        if show_help:
            draw_help(screen)
        draw_panel21(screen)
        if confirm_quit:
            draw_quit_modal(screen)
        if photo_flash > 0:   # the camera flash after a photo
            FLASH_SURF.set_alpha(photo_flash * 17)
            screen.blit(FLASH_SURF, (0, 0))
            photo_flash -= 1
        if show_fps:
            frame_times.append(clock.get_time())
            fps = clock.get_fps()
            txt = hud_font().render(f"FPS {fps:4.1f}   worst {max(frame_times)} ms", True,
                                    (120, 255, 150) if fps >= 58 else (255, 200, 90) if fps >= 45 else (255, 90, 90))
            screen.blit(txt, (SCREEN_WIDTH - txt.get_width() - 14, SCREEN_HEIGHT - 26))
        if screensaver:
            light_notif_alpha = 0
    if WELCOME_LIVE:
        draw_welcome_screen()
    if light_notif_alpha > 0:
        text_surf = notif_font.render(light_notif_text, True, (220, 220, 220))
        notif_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        notif_surf.blit(text_surf, (0, 0))
        notif_surf.set_alpha(light_notif_alpha)
        padding = 20
        screen.blit(notif_surf, (SCREEN_WIDTH - text_surf.get_width() - padding, padding))
        light_notif_alpha = max(0, light_notif_alpha - 2)

    try:
        if QUALITY_SPECS[QUALITY[0]]["smooth"]:
            pygame.transform.smoothscale(screen, (DISPLAY_W, DISPLAY_H), display)
        else:
            pygame.transform.scale(screen, (DISPLAY_W, DISPLAY_H), display)
    except (ValueError, pygame.error):
        display.blit(pygame.transform.scale(screen, (DISPLAY_W, DISPLAY_H)), (0, 0))
    pygame.display.flip()
    quality_governor()
    clock.tick(60)
    frame += 1