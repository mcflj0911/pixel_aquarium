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
              AulonocaraOB, GermanRedPeacock, SunshinePeacock, CopadichromisBorleyi, ElectricBlueHap, SynodontisCatfish,
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
