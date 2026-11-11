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
