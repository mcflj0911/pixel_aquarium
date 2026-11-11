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


def render_rock(width, height, rng, style="rock"):
    """Draw a lumpy, faceted stone at SS times its size, then scale it down. Styles: "rock" (the default, faceted and cracked),
    "smooth" (rounded boulders), "river" (blue-grey river stones) and "lace" (pale, porous lace rock)."""
    w, h = int(width * SS), int(height * SS)
    soft = style != "rock"
    pts = []
    for k in range(20):
        a = math.tau * k / 20
        r = 1 + rng.uniform(-0.035, 0.035) if soft else 1 + rng.uniform(-0.1, 0.1)
        flat = (0.85 if soft else 0.7) if math.sin(a) > 0 else 1.0  # Flatter underside, rounder top
        pts.append((w / 2 + math.cos(a) * w / 2 * 0.92 * r,
                    h / 2 + math.sin(a) * h / 2 * 0.92 * r * flat))

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    if style == "smooth":
        stone = (rng.randint(150, 172), rng.randint(138, 158), rng.randint(112, 130))
    elif style == "river":
        stone = (rng.randint(112, 132), rng.randint(120, 138), rng.randint(130, 148))
    elif style == "lace":
        stone = (rng.randint(196, 214), rng.randint(190, 206), rng.randint(172, 190))
    else:
        grey = rng.randint(115, 145)
        stone = (grey, grey - 4, grey - 10)
    shaded_polygon(surf, pts, tone(stone, 1.3), tone(stone, 0.55))
    if style == "lace":   # the pits and holes of lace rock
        for _ in range(rng.randint(5, 9)):
            hx, hy = rng.uniform(0.26, 0.74) * w, rng.uniform(0.32, 0.68) * h
            hw, hh = rng.uniform(0.07, 0.15) * w, rng.uniform(0.1, 0.22) * h
            pygame.draw.ellipse(surf, tone(stone, 0.36), (hx - hw / 2, hy - hh / 2, hw, hh))
            pygame.draw.ellipse(surf, tone(stone, 0.7), (hx - hw / 2 + hw * 0.1, hy - hh / 2 + hh * 0.18, hw * 0.8, hh * 0.7))

    # A lighter facet on the upper left catches the light
    facet = [(w / 2 + (px - w / 2) * 0.5 - w * 0.1, h / 2 + (py - h / 2) * 0.45 - h * 0.12) for px, py in pts]
    pygame.draw.polygon(surf, tone(stone, 1.45), facet)

    # Fractures across the stone
    for _ in range(3 if style == "rock" else 0):
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
    def __init__(self, x=None, z=None, y_offset=0, style="rock", scale=1.0):
        self.z = z if z is not None else random.uniform(0.7, 1.2)
        self.pos_x = x if x is not None else random.randint(0, SCREEN_WIDTH)

        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2
        self.y_offset = y_offset

        # Rocks are rendered once and cached as sprites
        width = random.uniform(55, 80) * self.z * (1.0 if y_offset == 0 else 0.8) * scale
        height = width * random.uniform(0.5, 0.7)
        if y_offset < -20:
            height *= 0.7
        self.image = shade_for_depth(render_rock(width, height, random.Random(random.random()), style), self.z)
        if random.random() > 0.5:
            self.image = pygame.transform.flip(self.image, True, False)
        self.img0, self.sc, self.fl = self.image, 1.0, False

    kind = "ROCK"
    mday = 0        # the tank day this piece was put in: moss grows with its age

    def moss_level(self):
        if self.kind not in ("ROCK", "DRIFTWOOD", "STACK"):
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


class RockStack(_Hard):
    """A tall mass of stacked, rounded boulders that tapers towards the top: the big rock structures of an aquascape."""
    kind = "STACK"
    STONE = {"lace": (205, 198, 181), "smooth": (160, 148, 122), "river": (122, 129, 139), "rock": (130, 126, 120)}

    def __init__(self, x=None, z=None, y_offset=0, height=None, style=None):
        depth = SCREEN_HEIGHT - SAND_HEIGHT - WATER_TOP
        self.stack_h = height if height is not None else random.uniform(0.35, 0.7) * depth
        self.style = style or SCAPE.get("rock_style", "smooth")
        self.z = z if z is not None else random.uniform(0.8, 1.1)
        self.pos_x = x if x is not None else random.randint(100, SCREEN_WIDTH - 100)
        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2
        self.y_offset = y_offset
        rng = random.Random(random.random())
        self.image = shade_for_depth(self.paint(rng, self.z), 1.1)     # pale rock stays readable even at the back of the tank
        if rng.random() < 0.5:
            self.image = pygame.transform.flip(self.image, True, False)
        self.img0, self.sc, self.fl = self.image, 1.0, False

    def paint(self, rng, z):
        base_w = rng.uniform(110, 135) * z * 1.35
        H = int(self.stack_h) + 40
        W = int(base_w * 1.4)
        sf = pygame.Surface((W, H), pygame.SRCALPHA)
        stone = self.STONE.get(self.style, self.STONE["smooth"])
        # a dark, tapering core so the gaps between the boulders read as shadow, not as holes
        left = [(W / 2 - base_w * (0.3 - 0.1 * (1 - k / 8.0)) + rng.uniform(-4, 4), H - k * (H - 24) / 8.0) for k in range(9)]
        right = [(W / 2 + base_w * (0.3 - 0.1 * (1 - k / 8.0)) + rng.uniform(-4, 4), H - k * (H - 24) / 8.0) for k in range(9)]
        pygame.draw.polygon(sf, tone(stone, 0.55), left + right[::-1])
        y = H
        while y > 36:
            frac = 1.0 - (H - y) / max(1.0, H)            # 1 at the foot, 0 at the top
            bw = base_w * (0.7 + 0.4 * frac) * rng.uniform(0.85, 1.2)
            bh = bw * rng.uniform(0.68, 0.92)
            cx = W / 2 + rng.uniform(-0.3, 0.3) * base_w * (0.4 + 0.6 * (1.0 - frac))
            sf.blit(render_rock(bw, bh, rng, self.style), (cx - bw / 2, y - bh))
            y -= bh * 0.5
        return sf


ROCK_KINDS = {"STACK": RockStack, "ROCK": Rock, "DRIFTWOOD": Driftwood, "CAVE": Cave, "POT": ClayPot, "SHIP": Shipwreck, "BRIDGE": StoneBridge}


def rock_look(r):
    """Rebuild a piece's picture from its original sprite, its scale and its flip."""
    img = r.img0
    if abs(r.sc - 1.0) > 0.01:
        img = pygame.transform.smoothscale(img, (max(4, int(img.get_width() * r.sc)), max(4, int(img.get_height() * r.sc))))
    if r.fl:
        img = pygame.transform.flip(img, True, False)
    r.image = img


def create_hardscape_dual():
    """Dual-anchor layout: a tall rock pillar (with a lower partner and a few boulders at its foot) on each far flank, a low arch
    in the middle, and nothing else, so the front of the tank is an open swimming runway."""
    W = SCREEN_WIDTH
    style = SCAPE.get("rock_style", "lace")
    depth = SCREEN_HEIGHT - SAND_HEIGHT - WATER_TOP - 20
    frac = max(0.3, min(0.95, float(SCAPE.get("pillar_height", 0.8))))
    out = []
    for xs, mirror in (((0.055, 0.125, 0.185, 0.02), 1), ((0.945, 0.875, 0.815, 0.98), 1)):
        out.append(RockStack(W * xs[0], 0.93, 0, height=depth * frac, style=style))
        out.append(RockStack(W * xs[1], 0.92, 0, height=depth * frac * 0.55, style=style))
        out.append(Rock(W * xs[2], 0.93, 0, style=style, scale=1.05))
        out.append(Rock(W * xs[3], 0.93, 0, style=style, scale=1.0))
        out.append(Rock(W * (xs[2] + xs[1]) / 2, 0.92, -16, style=style, scale=0.8))
    if SCAPE.get("arch", True):
        out.append(StoneBridge(x=W * 0.5, z=0.93))
        out.append(Rock(W * 0.5 - 150, 0.93, 0, style=style, scale=0.75))
        out.append(Rock(W * 0.5 + 150, 0.93, 0, style=style, scale=0.7))
    for cx in (0.29, 0.71)[:int(SCAPE.get("caves", 0))]:    # caves between the pillars and the arch: shelters and spawning homes
        out.append(Cave(x=W * cx, z=0.93))
    return sorted(out, key=lambda r: (r.z, -r.y_offset))


def create_hardscape():
    if SCAPE.get("layout") == "dual_anchor":
        return create_hardscape_dual()
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
