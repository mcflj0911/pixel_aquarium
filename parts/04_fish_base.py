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
        elif getattr(self, "burster", False):
            self.burst_glide(chasing)

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
