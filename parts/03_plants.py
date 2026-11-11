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
    if isinstance(SCAPE.get("plants"), dict):
        return create_plants_scape(SCAPE["plants"])
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


def create_plants_scape(cfg):
    """A sparse planting for a rock-and-sand scape: a few hardy clumps at the foot of the flank rocks and next to the arch,
    nothing in the open front, and (unless asked for) no ground cover."""
    width = SCREEN_WIDTH
    species = cfg.get("species") or ["Anubias", "Sword"]
    dens = max(0.0, min(1.0, float(cfg.get("density", 0.1))))
    new_plants = []
    for lo, hi in ((0.02, 0.24), (0.76, 0.98), (0.4, 0.6)):
        x = width * lo
        while x < width * hi:
            if random.random() < dens * (2.5 if (hi - lo) > 0.2 else 1.2):
                new_plants.append(Plant(x + random.randint(-10, 10), random.choice(species)))
            x += random.randint(34, 70)
    if cfg.get("ground_cover"):
        x = random.randint(4, 18)
        while x < width - 4:
            if random.random() < 0.5:
                new_plants.append(Plant(x + random.randint(-6, 6), random.choices(["DwarfGrass", "Cryptocoryne", "Clover", "MossBall"], [5, 3, 3, 1])[0]))
            x += random.randint(16, 34)
    new_plants.sort(key=PLANT_ORDER)
    return new_plants


PLANT_ORDER = lambda p: (-p.depth, p.height < 70, p.pos_x)


def mounted_plants():
    """Mid-height planting that needs the hardscape: java fern tied to the driftwood, and pothos vines hanging from the surface.
    Added after the original layout so a saved tank's seed still gives the same rocks and plants."""
    extra = []
    if isinstance(SCAPE.get("plants"), dict) and not SCAPE["plants"].get("mounted", False):
        return extra
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
