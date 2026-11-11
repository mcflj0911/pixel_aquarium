# ---------------- cichlids: territorial, pair up, dig and guard nests ----------------
class Cichlid(FWFish):
    """Base for every fish in the tank. Mbuna and friends: they patrol a territory, dig the sand, squabble with other
    species (and males of their own kind), pair up, spawn at a sword plant and guard the clutch."""
    family_name = "cichlid"
    beat = 1.6
    L, HT, HB = 92, 27, 23
    shape = dict(peak=0.52, pt=0.6, pn=0.9, ped=0.17)
    eye_r, eye_u = 5.4, 0.8
    aggr = 0.4              # how readily it picks fights with other species (0..1)
    social_base = 0.25      # how strongly it keeps to its own kind (0..1); the demasoni live in colonies
    bold_floor = 0.5        # minimum bravery
    hunts = False           # piscivores that pick off other species' fry
    open_water = False      # swims in the open instead of keeping to rocks and plants
    space = None            # personal-water multiplier override (see SPACE_FACTOR)
    common = "cichlid"
    burster = True          # swims in kicks and glides instead of at a steady speed
    unique = False          # True when its markings are random per fish, so each needs its own sprites

    @property
    def gene_key(self):
        k = FWFish.gene_key.fget(self)
        h = getattr(self, "hyb", None)      # a hybrid's colour blend is part of its look, so part of its sprite key
        return k + ((h["from"], round(h["w"] * 10)),) if h else k

    def __init__(self, x, y):
        super().__init__(x, lane(random.uniform(0.35, 0.8)))
        self.z = random.uniform(0.55, 0.85)
        self.territory = pygame.Vector2(x, self.pos.y)
        self.max_speed = 2.8
        self.state, self.target_rival, self.sift_timer = "PATROL", None, 0
        self.might, self.wins, self.dom, self.claim = random.uniform(0.3, 0.7), 0.0, False, None
        self.flee_t, self.flee_src, self.brood, self.display = 0, None, None, 0
        self.fold, self.kicking, self.kick_t = 0.0, False, random.randint(0, 60)   # fin folding and burst-and-glide swimming
        self.pit, self.dig_t, self.dig_n = None, 0, 0
        self.egg_spots = random.randint(1, 3)                 # egg spots on the male's anal fin (heritable): the more, the more the females like him
        self.sneaker_gene, self.sneaker = random.random() < 0.25, False    # some low-rank males pose as females and steal fertilisations
        self.lat_t, self.fry_in, self.recall_t, self.fry_t = 0, [], 0, 0      # fry_t: how long she still tends her fry
        self.mother, self.in_mouth = None, False
        self.carry, self.carry_t, self.carry_ph = None, 0, 0
        self.snap_to = None
        self.sleep_pose = random.choice((-40, -12, 0, 22))     # how it rests at night: head-down, leaning, level or tail-down

    @property
    def hidden(self):
        """Fry held in the mother's mouth count as hidden: nothing hunts them."""
        return self.__dict__.get("_hid", False) or self.__dict__.get("in_mouth", False)

    @hidden.setter
    def hidden(self, v):
        self.__dict__["_hid"] = v

    @property
    def fighting(self):
        return 1 if (self.state in ("DEFEND", "LATERAL") or getattr(self, "flare", 0) == 2) else 0

    @property
    def look(self):
        """Everything that changes how it is painted besides its genes: stress, rank, age, a mouthful of eggs, a courting display.
        Part of the sprite cache key, so each combination is drawn once."""
        male = getattr(self, "sex", "M") == "M"
        rank = 2 if self.dom else (0 if (male and self.flee_t > 0) else 1)
        gr = getattr(self, "growth", 1.0)
        return (int(clamp(getattr(self, "stress", 0.0) / 100.0) * 3), rank, int(min(1.0, gr) * 5) if gr < 1.0 else 5,
                1 if (self.brood is not None or self.fry_in) else 0, 1 if self.display > 0 else 0, int(round(clamp(self.fold) * 2)),
                self.fighting, self.egg_spots, 1 if self.sneaker else 0)

    def burst_glide(self, busy):
        """Cichlids do not cruise: a quick kick of the tail, then a long glide. Kicks are lazy on patrol and hard when fleeing,
        chasing or lunging at a rival; hovering, digging, sifting and resting fish do not kick. While kicking or fleeing the
        pelvic, dorsal and anal fins fold flat (self.fold, 0..1); at rest and in the glide they open again."""
        sp = self.vel.length()
        fear = getattr(self, "fear", 0.0)
        flee = fear > 0.35 or self.flee_t > 0
        chase = busy or self.state == "DEFEND"
        target = 0.0 if self.flare else clamp(sp / max(self.max_speed, 0.1) * 1.1)
        if (self.kicking or flee) and not self.flare:
            target = max(target, 0.9)
        self.fold += (target - self.fold) * (0.3 if target > self.fold else 0.07)
        if (self.state in ("SIFT", "PECK", "DIG", "LATERAL", "CARRY") or getattr(self, "hover", 0) > 0 or getattr(self, "sleepy", 0.0) > 0.4
                or self.brood is not None or (getattr(self, "refuge", None) is not None and getattr(self, "settled", False))):
            self.kicking = False
            return
        self.kick_t -= 1
        if self.kick_t <= 0:
            self.kicking = not self.kicking
            hard = flee or chase
            if self.kicking:
                self.kick_t = random.randint(9, 16) if hard else random.randint(7, 12)
            else:
                self.kick_t = random.randint(8, 22) if hard else random.randint(34, 85)
        if self.kicking:
            d = unit(self.vel) if sp > 0.05 else unit(pygame.Vector2(random.uniform(-1, 1), random.uniform(-0.3, 0.3)))
            self.acc += d * 0.2 * (1.9 if flee else 1.5 if chase else 1.0)
        else:
            self.vel *= 0.985 if (flee or chase) else 0.973

    feed_w = (0.0025, 0.0035, 0.0, 0.0006)     # chance per frame to sift the sand, graze a rock, snap at plankton, move a pebble

    def start_carry(self):
        c = self.claim
        cand = [p for p in pebbles if 50 < abs(p.pos_x - c.x) < 170 and p.z > 0.7]
        if not cand:
            return False
        self.carry, self.carry_t, self.carry_ph, self.state = random.choice(cand[:60]), 0, 0, "CARRY"
        return True

    def can_dig(self):
        return (getattr(self, "sex", "M") == "M" and getattr(self, "growth", 0.0) >= 1.0 and (self.dom or getattr(self, "partner", None) is not None) and self.hunger < 60
                and getattr(self, "fear", 0.0) < 0.2 and self.brood is None and self.flee_t == 0 and getattr(self, "sleepy", 0.0) < 0.3)

    def start_dig(self):
        pit = self.pit if self.pit in PITS else None
        if pit is None:
            x = clamp((self.claim.x if self.claim is not None else self.pos.x) + random.uniform(-40, 40), 120, SCREEN_WIDTH - 120)
            if len(PITS) >= 6 or any(abs(p["x"] - x) < 100 for p in PITS):
                return False
            pit = {"x": x, "depth": 0.0, "mound": 0.0, "side": random.choice((-1, 1)), "owner": self.id}
            PITS.append(pit)
        self.pit, self.state, self.dig_t, self.dig_n, self.target_rival = pit, "DIG", 0, random.randint(3, 5), None
        return True

    def pick_rival(self, fishes):
        """Another species that wanders into its space, or a rival male of its own kind, draws a flaring chase. A dominant
        male also drives every lesser male out of the territory he holds."""
        if self.brood is not None or self.flee_t > 0:
            return None
        pers = getattr(self, "persona", "")
        k = 1.5 if pers == "bossy" else 0.6 if pers == "calm" else 1.0
        if random.random() > (0.05 * self.aggr + 0.004 + (0.05 if self.dom else 0.0)) * CROWD["aggr"] * k:
            return None
        for o in fishes:
            if (o is self or not isinstance(o, Cichlid) or o is getattr(self, "partner", None) or not o.alive
                    or getattr(o, "sneaker", False) or getattr(o, "in_mouth", False)):
                continue
            d2 = self.pos.distance_squared_to(o.pos)
            if (self.dom and not o.dom and getattr(o, "sex", "F") == "M" and getattr(o, "growth", 1.0) >= 1.0
                    and o.pos.distance_squared_to(self.territory) < 150 * 150):
                return o
            if type(o) is type(self):
                if d2 < 62 * 62 and getattr(self, "sex", "M") == "M" == getattr(o, "sex", "F") and getattr(o, "growth", 1.0) >= 1.0:
                    return o
            elif d2 < 90 * 90 and getattr(o, "growth", 1.0) >= 0.7:
                return o
        return None

    def behavior(self, fishes):
        m = self.mother
        if m is not None:       # a fry of a mouthbrooder: it dives back into her mouth when she is alarmed
            if (not m.alive) or self.growth >= 0.3:
                self.mother, self.in_mouth = None, False
            elif self.in_mouth:
                if self not in m.fry_in:
                    self.in_mouth = False
                else:
                    self.pos.update(m.pos.x, m.pos.y)
                    self.vel.update(0, 0)
                    return
            elif m.recall_t > 0:
                d = m.pos - self.pos
                if d.length() < 26:
                    self.in_mouth = True
                    m.fry_in.append(self)
                    return
                self.apply_force(unit(d) * 0.6)
        self.tilt(25)
        self.eat_daphnia(180)
        pers = getattr(self, "persona", "")
        if self.fry_t > 0:
            self.fry_t -= 1
        if self.fry_in or self.brood is not None or self.fry_t > 0:
            alarm = (getattr(self, "fear", 0.0) > 0.35 or self.flee_t > 0
                     or any(p.pos.distance_squared_to(self.pos) < 260 * 260 for p in predators))
            if alarm:
                self.recall_t = 180
            elif self.recall_t > 0:
                self.recall_t -= 1
            if self.fry_in and self.recall_t <= 0 and getattr(self, "fear", 0.0) < 0.15:     # all clear: spit the fry out
                for k in self.fry_in:
                    k.in_mouth = False
                    k.pos.update(self.pos.x + random.uniform(-14, 14), self.pos.y + random.uniform(-8, 8))
                    k.vel.update(random.uniform(-0.8, 0.8), random.uniform(-0.5, 0.2))
                burst(self.pos, (236, 214, 150), 8, 0.8, 30, 2, -0.01)
                self.fry_in = []
        if getattr(self, "sleepy", 0.0) > 0.6 and self.vel.length() < 0.3 and self.state == "PATROL":   # resting posture
            self.angle += (self.sleep_pose - self.angle) * 0.04
        if pers == "greedy" and pellets and (eco.t + self.id) % 3 == 0 and self.hunger > 20:
            q = min(pellets, key=lambda p: self.pos.distance_squared_to(p.pos))
            if self.pos.distance_squared_to(q.pos) < 220 * 220:
                self.apply_force(unit(q.pos - self.pos) * 0.05)
        if self.sneaker and (eco.t + self.id) % 30 == 0:      # sneakers drift toward a courting pair
            cand = [o for o in fishes if isinstance(o, Cichlid) and o is not self and o.display > 0
                    and o.pos.distance_squared_to(self.pos) < 280 * 280]
            self.snk = min(cand, key=lambda o: self.pos.distance_squared_to(o.pos)) if cand else None
        snk = getattr(self, "snk", None)
        if self.sneaker and snk is not None and snk.alive and snk.display > 0 and self.pos.distance_to(snk.pos) > 90:
            self.apply_force(unit(snk.pos - self.pos) * 0.05)
        if self.display > 0:
            self.display -= 1
        if self.brood is not None:       # a mouthbrooding female moves slowly, keeps out of fights and retreats to a cave
            self.vel *= 0.985
            if getattr(self, "refuge", 0) is None and self.refuge_cd <= 0 and cave_spots and (eco.t + self.id) % 60 == 0:
                cave = find_cave(self)
                if cave is not None:
                    self.refuge, self.refuge_covered, self.settled, self.safe = cave, True, False, 0
        if self.flee_t > 0:              # beaten: slink away from the winner
            self.flee_t -= 1
            if self.flee_src is not None and self.flee_src.alive:
                self.apply_force(unit(self.pos - self.flee_src.pos) * 0.1)
            self.state, self.target_rival = "PATROL", None
        if self.state == "PATROL":
            if pers == "explorer" and not self.dom and random.random() < 0.0015:     # explorers wander the whole tank
                self.territory = pygame.Vector2(random.uniform(150, SCREEN_WIDTH - 150), lane(random.uniform(0.3, 0.8)))
            if self.pos.distance_to(self.territory) > (110 if self.dom else 90 if pers == "shy" else 150):
                self.apply_force((self.territory - self.pos) * 0.01)
            rival = self.pick_rival(fishes)
            if rival is not None:
                if (isinstance(rival, Cichlid) and self.brood is None and getattr(self, "sex", "F") == "M" == getattr(rival, "sex", "F")
                        and rival.state == "PATROL" and getattr(rival, "growth", 0) >= 1.0 and getattr(self, "growth", 0) >= 1.0 and random.random() < 0.6):
                    # rivals first size each other up side by side, fins flared; the smaller usually backs down without a blow
                    self.state, self.target_rival, self.lat_t = "LATERAL", rival, 0
                    rival.state, rival.target_rival, rival.lat_t = "LATERAL", self, 0
                else:
                    self.target_rival, self.state, self.sift_timer = rival, "DEFEND", 0
                return
            r = random.random()
            if r < 0.0015 and self.can_dig() and self.start_dig():
                return
            sw, pw, nw, cw = self.feed_w        # sifting, grazing, plankton snaps, moving pebbles
            x = r - 0.0015
            if 0 <= x < sw:
                self.state, self.sift_timer = "SIFT", 120
            elif 0 <= x - sw < pw and rock_spots:   # mbuna pick the algae film off the rocks
                self.state, self.sift_timer = "PECK", 240
                self.peck_spot = min(rock_spots, key=lambda rs: rs[0].distance_squared_to(self.territory))[0].copy()
            elif 0 <= x - sw - pw < nw:    # open-water species snap at drifting plankton
                self.state, self.sift_timer = "SNAP", 40
                self.snap_to = self.pos + pygame.Vector2(random.choice((-1, 1)) * random.uniform(50, 100), random.uniform(-40, 30))
            elif 0 <= x - sw - pw - nw < cw and self.dom and self.claim is not None and self.start_carry():
                return
            self.wobble(0.3, 0.03)
        elif self.state == "LATERAL":
            o = self.target_rival
            if (o is None or not o.alive or o.state != "LATERAL" or o.target_rival is not self
                    or self.pos.distance_to(o.pos) > 220 or self.flee_t > 0):
                self.state, self.target_rival, self.lat_t = "PATROL", None, 0
            else:
                self.lat_t += 1
                side = 1 if self.id < o.id else -1
                spot = o.pos + pygame.Vector2(0, 26 * side * self.z)
                self.apply_force(unit(spot - self.pos) * min(0.12, 0.004 * (spot - self.pos).length()))
                self.vel *= 0.9
                self.set_flare(2, 6)
                self.display = 8
                self.apply_force(pygame.Vector2(0, math.sin(eco.t * 0.8 + self.id) * 0.12))
                self.angle += (0 - self.angle) * 0.1
                if self.lat_t >= 100 and self.id < o.id:
                    resolve_lateral(self, o)
        elif self.state == "SNAP":
            self.sift_timer -= 1
            to = self.snap_to - self.pos
            if self.sift_timer > 20 and to.length() > 14:
                self.apply_force(unit(to) * 0.16)
            elif self.sift_timer == 20:
                self.mouth_open_timer = 8
                self.vel *= 0.3
                self.hunger = max(0.0, self.hunger - 4)
            if self.sift_timer <= 0:
                self.state, self.sift_timer = "PATROL", 0
        elif self.state == "CARRY":
            self.carry_t += 1
            p = self.carry
            c = self.claim
            if p is None or c is None or self.carry_t > 500 or getattr(self, "fear", 0.0) > 0.4:
                if p is not None:
                    p.base_y = ground_y(p.pos_x)
                self.carry, self.state, self.carry_t, self.carry_ph = None, "PATROL", 0, 0
            elif self.carry_ph == 0:       # go to the pebble and pick it up
                to = pygame.Vector2(p.pos_x, p.base_y - 8) - self.pos
                self.apply_force(unit(to) * min(0.14, 0.004 * to.length()))
                self.vel *= 0.94
                if to.length() < 22:
                    self.carry_ph = 1
                    self.mouth_open_timer = 6
                    self.drop_to = pygame.Vector2(c.x + random.choice((-1, 1)) * random.uniform(25, 75), 0)
            else:                          # carry it home and set it down by the cave
                p.pos_x, p.base_y = self.pos.x, self.pos.y + 8 * self.z
                to = pygame.Vector2(self.drop_to.x, ground_y(self.drop_to.x) - 22) - self.pos
                self.apply_force(unit(to) * min(0.14, 0.004 * to.length()))
                self.vel *= 0.94
                if to.length() < 22:
                    p.pos_x, p.base_y = self.drop_to.x, ground_y(self.drop_to.x)
                    self.mouth_open_timer = 6
                    self.carry, self.state, self.carry_t, self.carry_ph = None, "PATROL", 0, 0
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
                    if isinstance(self.target_rival, Cichlid) and random.random() < 0.02:
                        contest(self, self.target_rival)
        elif self.state == "DIG":
            pit = self.pit
            self.dig_t += 1
            if pit not in PITS or getattr(self, "fear", 0.0) > 0.4 or self.dig_t >= 80 * self.dig_n or self.hunger > 80:
                self.state, self.dig_t = "PATROL", 0
            else:
                gy = ground_y(pit["x"])
                mx = pit["x"] + pit["side"] * (30 + 46 * pit["depth"])
                ph = self.dig_t % 80
                if ph < 30:          # mouth down in the pit: scoop up a mouthful of sand
                    to = pygame.Vector2(pit["x"], gy - 12 * self.z) - self.pos
                    self.apply_force(unit(to) * min(0.14, 0.004 * to.length()))
                    if to.length() < 24:
                        self.vel *= 0.8
                        self.angle += (-55 - self.angle) * 0.15
                        if 14 < ph < 28:
                            self.mouth_open_timer = 4
                elif ph < 56:        # carry it off to the rim
                    to = pygame.Vector2(mx, gy - 22 * self.z) - self.pos
                    self.apply_force(unit(to) * min(0.14, 0.004 * to.length()))
                elif ph == 56:       # and spit it out: the pit gets deeper, the mound higher
                    self.mouth_open_timer = 10
                    burst(pygame.Vector2(mx, gy - 6), SAND_TOP, 7, 0.9, 26, 1, 0.03)
                    pit["depth"] = min(1.0, pit["depth"] + 0.12)
                    pit["mound"] = min(1.0, pit["mound"] + 0.12)
                self.vel *= 0.93
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
        return [fin_tail(g, "round", 13, 21, rays=9), fin_on_top(g, 0.84, 0.1, 13, -7, 0.55, rays=20),
                fin_on_belly(g, 0.56, 0.2, 9, -4, rays=8), fin_pelvic(g, 0.62, 16, 9)]

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


# ---------------- Lake Malawi peacocks and haps: the open-sand showpieces ----------------
def pick_sex(fish):
    """Most species are 50/50; the Malawi show fish are stocked mostly male, because the males are the colourful ones."""
    return "M" if random.random() < getattr(fish, "male_share", 0.5) else "F"


class MalawiShow(Cichlid):
    """Base for the Aulonocara peacocks and the open-water Haplochromis. Males are the colourful ones; females stay a plain
    silvery-brown. Peacocks hover over the sand sifting for food; the open-water haps cruise the middle of the tank."""
    aggr, social_base, bold_floor = 0.3, 0.3, 0.45
    unique = True
    male_share = 0.65
    male_color = (60, 120, 220)
    female_color = (156, 146, 124)
    male_fin = (230, 180, 60)
    female_fin = (176, 166, 146)
    hovers = True

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed, self.hover = 2.1, 0
        if self.open_water:
            self.territory = pygame.Vector2(x, lane(random.uniform(0.22, 0.55)))
            self.pos.y = self.territory.y

    @property
    def base_color(self):
        return self.dimorphic(self.male_color, self.female_color)

    def is_female(self):
        return getattr(self, "sex", "M") == "F"

    def behavior(self, fishes):
        if self.hovers and self.state == "PATROL" and random.random() < 0.01:
            self.hover = 100
        if self.hover > 0:   # hangs over the sand, looking for tiny food
            self.hover -= 1
            self.vel *= 0.82
            self.tilt(25)
            self.eat_daphnia(180)
            return
        super().behavior(fishes)
        if self.open_water:
            self.prefer_depth(lane(0.15), lane(0.62), 0.004)

    def palette(self):
        top, mid, belly, fin = super().palette()
        fin = self.get_depth_color(self.female_fin if self.is_female() else self.male_fin)
        return top, mid, mix(belly, (255, 236, 200), 0.25), fin

    def blotches(self, g, layer, colors, count, alpha, size=0.9, span=(0.18, 0.88)):
        rng = random.Random(self.id * 5 + 11)
        for _ in range(count):
            c = rng.choice(colors)
            u, y = rng.uniform(*span), g.cy + rng.uniform(-0.75, 0.7) * g.ht
            w, h = g.L * rng.uniform(0.04, 0.09) * size, g.ht * rng.uniform(0.25, 0.55) * size
            pygame.draw.ellipse(layer, (*self.get_depth_color(c), alpha), (g.rx + u * g.L, y, max(2, w), max(2, h)))

    def head_glow(self, g, layer, color, alpha=120):
        pygame.draw.ellipse(layer, (*color, alpha), (g.rx + 0.66 * g.L, g.cy - g.ht * 0.85, g.L * 0.36, g.ht * 1.6))
        rng = random.Random(self.id)
        for _ in range(14):   # iridescent speckle
            u = rng.uniform(0.68, 0.94)
            y = g.cy + rng.uniform(-0.7, 0.55) * g.ht
            pygame.draw.circle(layer, (200, 235, 255, 160), (int(g.rx + u * g.L), int(y)), max(1, int(g.z * 0.9)))

    def back_fins(self, g):
        return [fin_tail(g, "round", 12, 20, rays=9), fin_on_top(g, 0.84, 0.1, 13, -7, 0.55, rays=20),
                fin_on_belly(g, 0.56, 0.2, 9, -4, rays=8), fin_pelvic(g, 0.62, 16, 9)]


class AulonocaraOB(MalawiShow):
    """OB peacock: a calico marble of orange, blue and black blotches, different on every fish."""
    common = "OB peacock"
    male_color = (214, 168, 120)
    female_color = (170, 150, 124)
    male_fin = (232, 150, 70)
    L, HT, HB = 92, 26, 22

    def decorate(self, g, layer):
        if self.is_female():
            self.blotches(g, layer, [(90, 70, 56), (200, 170, 130)], 6, 90, 0.8)
            return
        self.blotches(g, layer, [(238, 120, 40), (232, 140, 60)], 9, 190)
        self.blotches(g, layer, [(60, 130, 225), (90, 160, 235)], 7, 185)
        self.blotches(g, layer, [(18, 18, 24)], 9, 215, 0.7)
        self.blotches(g, layer, [(250, 235, 215)], 4, 150, 0.8)
        self.head_glow(g, layer, (70, 150, 240), 70)


class GermanRedPeacock(MalawiShow):
    """German red / rubin red peacock: blood-orange body, iridescent blue face."""
    common = "German red peacock"
    male_color = (216, 62, 30)
    female_color = (178, 168, 146)
    male_fin = (226, 76, 34)
    L, HT, HB = 94, 26, 22

    def decorate(self, g, layer):
        if self.is_female():
            bars(g, layer, [0.3, 0.42, 0.54, 0.66], 0.03, (110, 96, 80), 90, 0.015)
            return
        for k in range(18):   # the red deepens towards the back, a paler wash on the belly
            u = 0.1 + 0.55 * k / 17
            pygame.draw.line(layer, (150, 24, 18, int(70 * (1 - k / 17))), (g.rx + u * g.L, g.cy - g.ht * 1.3),
                             (g.rx + u * g.L, g.cy + g.hb * 1.3), max(2, int(g.L * 0.022)))
        bars(g, layer, [0.2 + 0.085 * i for i in range(7)], 0.034, (84, 70, 210), 175, 0.015)
        self.head_glow(g, layer, (60, 140, 255), 150)
        pygame.draw.line(layer, (255, 170, 120, 100), (g.rx + 0.15 * g.L, g.cy - g.ht * 0.6), (g.rx + 0.7 * g.L, g.cy - g.ht * 0.75), max(1, int(g.z * 1.3)))


class SunshinePeacock(MalawiShow):
    """Blue neon / sunshine peacock: bright yellow with a neon-blue head, back stripe and dorsal edge."""
    common = "Sunshine peacock"
    male_color = (252, 208, 40)
    female_color = (200, 188, 150)
    male_fin = (250, 214, 70)
    L, HT, HB = 90, 25, 21

    def decorate(self, g, layer):
        if self.is_female():
            pygame.draw.line(layer, (140, 120, 80, 90), (g.rx + 0.15 * g.L, g.cy - g.ht * 0.1), (g.rx + 0.85 * g.L, g.cy - g.ht * 0.2), max(1, int(g.z * 1.4)))
            return
        bars(g, layer, [0.22 + 0.09 * i for i in range(6)], 0.03, (120, 90, 10), 90, 0.015)
        self.head_glow(g, layer, (50, 140, 255), 150)
        pygame.draw.line(layer, (60, 160, 255, 210), (g.rx + 0.12 * g.L, g.cy - g.ht * 0.82), (g.rx + 0.72 * g.L, g.cy - g.ht * 0.92), max(2, int(g.z * 2.4)))
        pygame.draw.line(layer, (255, 250, 200, 120), (g.rx + 0.2 * g.L, g.cy - g.ht * 0.3), (g.rx + 0.7 * g.L, g.cy - g.ht * 0.38), max(1, int(g.z * 1.3)))

    def back_fins(self, g):
        edge = (70, 160, 255) if not self.is_female() else (200, 190, 160)
        return [fin_tail(g, "round", 12, 20, rays=9), fin_on_top(g, 0.84, 0.1, 13, -7, 0.55, rays=20, edge=edge, width=SS),
                fin_on_belly(g, 0.56, 0.2, 9, -4, rays=8, edge=edge, width=SS), fin_pelvic(g, 0.62, 18, 10, color=(90, 170, 255) if not self.is_female() else g.fin)]


class CopadichromisBorleyi(MalawiShow):
    """Red fin borleyi: an open-water hap, deep metallic blue with orange-red fins."""
    common = "Red fin borleyi"
    open_water, hovers = True, False
    male_color = (30, 70, 188)
    female_color = (150, 160, 172)
    male_fin = (240, 100, 40)
    female_fin = (206, 168, 120)
    L, HT, HB = 98, 23, 20
    shape = dict(peak=0.52, pt=0.62, pn=0.9, ped=0.16)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.5

    def decorate(self, g, layer):
        if self.is_female():
            bars(g, layer, [0.26 + 0.09 * i for i in range(6)], 0.03, (90, 100, 112), 80, 0.015)
            return
        for k in range(5):   # a metallic sheen along the back and a darker head
            pygame.draw.line(layer, (130, 190, 255, 70 - 10 * k), (g.rx + 0.1 * g.L, g.cy - g.ht * (0.8 - 0.22 * k)),
                             (g.rx + 0.85 * g.L, g.cy - g.ht * (0.95 - 0.22 * k)), max(1, int(g.z * 1.5)))
        pygame.draw.ellipse(layer, (10, 20, 80, 90), (g.rx + 0.7 * g.L, g.cy - g.ht * 0.8, g.L * 0.3, g.ht * 1.5))
        bars(g, layer, [0.2 + 0.082 * i for i in range(8)], 0.036, (6, 14, 66), 190, 0.015)

    def back_fins(self, g):
        edge = (255, 140, 60) if not self.is_female() else (200, 170, 130)
        return [fin_tail(g, "round", 13, 22, rays=9, edge=edge, width=SS), fin_on_top(g, 0.85, 0.08, 14, -8, 0.55, rays=20, edge=edge, width=SS),
                fin_on_belly(g, 0.56, 0.2, 9, -4, rays=8, edge=edge, width=SS), fin_pelvic(g, 0.62, 18, 10, color=(236, 110, 50) if not self.is_female() else g.fin)]


class ElectricBlueHap(MalawiShow):
    """Electric blue hap (Sciaenochromis fryeri): a sleek, metallic royal-blue predator that cruises open water and picks off fry."""
    common = "Electric blue hap"
    open_water, hovers, hunts = True, False, True
    aggr, bold_floor = 0.5, 0.6
    male_color = (28, 108, 255)
    female_color = (150, 156, 168)
    male_fin = (60, 150, 255)
    female_fin = (180, 172, 160)
    L, HT, HB = 106, 21, 18
    shape = dict(peak=0.52, pt=0.62, pn=0.95, ped=0.15)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.8

    def decorate(self, g, layer):
        if self.is_female():
            bars(g, layer, [0.24 + 0.09 * i for i in range(7)], 0.028, (80, 88, 104), 70, 0.015)
            return
        for k in range(6):
            pygame.draw.line(layer, (170, 225, 255, 90 - 12 * k), (g.rx + 0.08 * g.L, g.cy - g.ht * (0.85 - 0.2 * k)),
                             (g.rx + 0.9 * g.L, g.cy - g.ht * (0.98 - 0.2 * k)), max(1, int(g.z * 1.4)))
        bars(g, layer, [0.2 + 0.075 * i for i in range(9)], 0.032, (8, 30, 120), 165, 0.015)
        pygame.draw.circle(layer, (255, 170, 60, 220), (int(g.rx + 0.5 * g.L), int(g.cy + g.hb * 0.62)), max(1, int(g.z * 1.8)))   # egg spot on the anal fin

    def back_fins(self, g):
        edge = (200, 235, 255) if not self.is_female() else (210, 205, 195)
        return [fin_tail(g, "round", 12, 22, rays=9, edge=edge, width=SS), fin_on_top(g, 0.86, 0.07, 14, -8, 0.55, rays=20, edge=edge, width=SS),
                fin_on_belly(g, 0.52, 0.2, 9, -4, rays=8), fin_pelvic(g, 0.62, 18, 10, color=(150, 200, 255) if not self.is_female() else g.fin)]


def _slim_cichlids():
    """The cichlids read as long torpedoes, not discs: slim each species' own body proportions once, here."""
    todo, seen = [Cichlid], set()
    while todo:
        c = todo.pop()
        if c in seen:
            continue
        seen.add(c)
        todo.extend(c.__subclasses__())
        if c is AngelFish:
            continue
        if "HT" in c.__dict__:
            c.HT = max(11, round(c.HT * 0.64))
            c.HB = max(10, round(c.HB * 0.64))
        if "L" in c.__dict__:
            c.L = round(c.L * 0.95)
        if "eye_r" in c.__dict__ or c is Cichlid:
            c.eye_r = round(c.eye_r * 0.8, 1)


_slim_cichlids()


def cichlid_cols(p):
    """A cichlid's colours as it would show them: (male body, female body, male fin, female fin), its own species' colours
    blended with the other species it carries when it is a hybrid."""
    base = getattr(p, "male_color", None) or tuple(p.base_color)
    fem = getattr(p, "female_color", None) or base
    fin = tuple(p.fin_color or base)
    cols = {"m": tuple(base), "f": tuple(fem), "fm": tuple(getattr(p, "male_fin", None) or fin), "ff": tuple(getattr(p, "female_fin", None) or fin)}
    h = getattr(p, "hyb", None)
    if h:
        for k in cols:
            cols[k] = mix(cols[k], tuple(h[k]), h["w"])
    return cols


CROWD = {"aggr": 1.0}      # how quarrelsome the tank is: sparse stocking focuses the aggression, a crowd is nasty and stressed


def contest(a, b):
    """A shoving match between two cichlids: the stronger one (size, health, past wins) takes rank from the other."""
    pa, pb = a.might + random.gauss(0, 0.1), b.might + random.gauss(0, 0.1)
    w, l = (a, b) if pa >= pb else (b, a)
    w.wins = clamp(w.wins + 0.03, -0.3, 0.3)
    l.wins = clamp(l.wins - 0.03, -0.3, 0.3)
    l.flee_t, l.flee_src = 150, w
    l.stress = min(100.0, getattr(l, "stress", 0.0) + 4.0)


PITS = []      # sand pits dug by the males: {"x", "depth", "mound", "side", "owner"}


def draw_pits(surface):
    """The spawning pits the males dig: a dark scoop in the sand with a mound of the sand they carried out."""
    for p in PITS:
        if p["depth"] < 0.04 and p["mound"] < 0.04:
            continue
        gy = ground_y(p["x"])
        w, h = int(40 + 52 * p["depth"]), int(8 + 12 * p["depth"])
        mr = int(10 + 15 * p["mound"])
        s = pygame.Surface((w + 190, 70), pygame.SRCALPHA)
        cx0 = s.get_width() // 2
        mx = cx0 + p["side"] * (w // 2 + int(mr * 0.9))
        # the mound: a pale heap with a shaded foot
        pygame.draw.ellipse(s, (*tone(SAND_BOT, 0.8), int(110 + 110 * p["mound"])), (mx - mr, 36 - int(mr * 0.2), mr * 2, int(mr * 0.9)))
        pygame.draw.ellipse(s, (*tone(SAND_TOP, 1.05), int(150 + 90 * p["mound"])), (mx - mr, 30 - int(mr * 0.35), mr * 2, int(mr * 0.9)))
        # the pit: dark floor, a pale lip along the far edge
        pygame.draw.ellipse(s, (*tone(SAND_BOT, 0.55), int(120 + 120 * p["depth"])), (cx0 - w // 2, 30, w, h))
        pygame.draw.ellipse(s, (*tone(SAND_BOT, 0.4), int(100 + 100 * p["depth"])), (cx0 - w // 2 + 6, 33, w - 12, max(3, h - 7)))
        pygame.draw.arc(s, (*tone(SAND_TOP, 1.1), 220), (cx0 - w // 2, 30, w, h), 0.2, math.pi - 0.2, 2)
        surface.blit(s, (int(p["x"]) - cx0, int(gy) - 28))


def find_cave(f, panic=False):
    """A cave for a cichlid to shelter in: its own (a dominant male's claim), or one that is not full or another boss's."""
    best, bd = None, 900.0
    for s in cave_spots:
        occ = sum(1 for o in fishes if o is not f and getattr(o, "refuge", None) is s)
        own = f.claim is not None and f.claim.distance_squared_to(s) < 70 * 70
        boss = any(getattr(o, "dom", False) and getattr(o, "claim", None) is not None and o.claim.distance_squared_to(s) < 70 * 70 for o in fishes
                   if o is not f and isinstance(o, Cichlid))
        if not own and not panic and (occ >= 3 or boss):
            continue
        d = f.pos.distance_to(s) - (250 if own else 0) + occ * 60
        if d < bd:
            best, bd = s, d
    return best


def resolve_lateral(a, b):
    """The end of a lateral display: the weaker male usually backs off without a blow; a close match escalates to a chase."""
    pa, pb = a.might + random.gauss(0, 0.08), b.might + random.gauss(0, 0.08)
    w, l = (a, b) if pa >= pb else (b, a)
    a.lat_t = b.lat_t = 0
    if abs(pa - pb) > 0.08 or random.random() < 0.35:
        w.wins = clamp(w.wins + 0.015, -0.3, 0.3)
        l.wins = clamp(l.wins - 0.015, -0.3, 0.3)
        l.flee_t, l.flee_src = 150, w
        a.state = b.state = "PATROL"
        a.target_rival = b.target_rival = None
    else:
        a.state, a.target_rival, a.sift_timer = "DEFEND", b, 0
        b.state, b.target_rival, b.sift_timer = "DEFEND", a, 0


def attract(m):
    """How much a female likes a male: rank, egg spots and a blazing display, with a penalty for a sneaker."""
    return (0.6 * getattr(m, "might", 0.5) + 0.12 * getattr(m, "egg_spots", 2) + (0.2 if getattr(m, "dom", False) else 0.0)
            + 0.3 * min(1.0, getattr(m, "display", 0) / 12.0) - (0.35 if getattr(m, "sneaker", False) else 0.0))


def rank_tick():
    """Every couple of seconds: who is the boss. The strongest adult males become dominant and each claims a cave, nest or rock
    as a territory; lesser males are chased off it (see pick_rival). Also sets how quarrelsome the tank is from its stocking."""
    cich = [f for f in fishes if isinstance(f, Cichlid) and f.alive and hasattr(f, "growth") and hasattr(f, "adult_z")]   # newcomers are not set up until their first update
    males = [f for f in cich if getattr(f, "sex", "M") == "M" and f.growth >= 1.0]
    for f in males:
        f.might = f.adult_z * 0.6 + f.aggr * 0.5 + getattr(f, "health", 100.0) / 300.0 - getattr(f, "stress", 0.0) / 300.0 + f.wins
    males.sort(key=lambda f: -f.might)
    ndom = 0 if len(males) < 2 else max(1, len(males) // 4)
    for p in PITS[:]:                  # the pits slowly fill in unless they are kept up
        p["depth"] = max(0.0, p["depth"] - 0.004)
        p["mound"] = max(0.0, p["mound"] - 0.003)
        if p["depth"] < 0.03 and p["mound"] < 0.03:
            PITS.remove(p)
    spots = [pygame.Vector2(p) for p in list(nest_spots) + list(cave_spots)] + [pygame.Vector2(r[0]) for r in rock_spots]
    taken = [f.claim for f in males[:ndom] if f.claim is not None]
    for i, f in enumerate(males):
        f.dom = i < ndom
        if f.dom and f.claim is None and spots:
            free = [p for p in spots if all(p.distance_squared_to(t) > 140 * 140 for t in taken)]
            if free:
                f.claim = min(free, key=lambda p: p.distance_to(f.pos) - (250 if any(p.distance_squared_to(c) < 4 for c in cave_spots) else 0)).copy()
                taken.append(f.claim)
                f.territory = f.claim.copy()
        elif not f.dom:
            f.claim = None
    for f in cich:
        if f not in males:
            f.dom = False
        f.sneaker = bool(f.sneaker_gene) and f in males and not f.dom
    load = tank_load() / max(1.0, tank_budget())
    if load < 0.45:
        CROWD["aggr"] = 1.5
    elif load <= 0.95:
        CROWD["aggr"] = 1.2 - 0.5 * (load - 0.45) / 0.5
    else:
        CROWD["aggr"] = 1.4
        for f in cich:
            f.stress = min(100.0, getattr(f, "stress", 0.0) + 1.5 * (load - 0.95) * 4)


JUV_COL = (150, 146, 128)
_CICHLID_NAMES = {}


def cichlid_by_name(n):
    if not _CICHLID_NAMES:
        todo = [Cichlid]
        while todo:
            c = todo.pop()
            _CICHLID_NAMES[c.__name__] = c
            todo.extend(c.__subclasses__())
    return _CICHLID_NAMES.get(n)


def _grey(c, k):
    g = int(0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
    return mix(c, (g, g, g), k)


def self_fold(fish, g, fins):
    """Fin folding: the dorsal, anal, pelvic and pectoral fins are pulled flat against the body while the fish kicks or flees
    (fish.fold, in three steps so each is cached once); the tail spreads wider on the kick."""
    k = int(round(clamp(getattr(fish, "fold", 0.0)) * 2)) / 2.0
    if k <= 0.0:
        return fins
    out = []
    for fin in fins:
        shape = fin[0]
        if len(shape) >= 3 and min(x for x, _ in shape) < g.rx - 2:      # the tail: wider on the kick
            ay = (shape[0][1] + shape[-1][1]) / 2
            sc = 0.92 + 0.22 * k
            shape = [shape[0]] + [(x, ay + (y - ay) * sc) for x, y in shape[1:-1]] + [shape[-1]]
            out.append((shape,) + tuple(fin[1:]))
        else:
            out.append(flare_fin(fin, 1.0 - 0.6 * k))
    return out


def _paint_wrappers():
    """Every cichlid class's palette and decorate are wrapped once. The outermost call (type(self) is cls) adds, on top of the
    species' own look: the colours of a hybrid's other parent and its markings, a juvenile's plain colouring, stress that
    drains the colour, a dominant male's richer colour and a courting male's display, and the bulge of a mouthful of eggs."""
    todo, seen = [Cichlid], set()
    while todo:
        c = todo.pop()
        if c in seen:
            continue
        seen.add(c)
        todo.extend(c.__subclasses__())

        def wrap(cls, orig_pal, orig_dec, orig_bf, orig_ff, orig_fn):
            def palette(self):
                res = orig_pal(self)
                if type(self) is not cls:     # blend once, in the outermost call
                    return res
                top, mid, belly, fin = res
                h = getattr(self, "hyb", None)
                if h is not None:
                    fem = getattr(self, "sex", "M") == "F"
                    col = self.get_depth_color(h["f"] if fem else h["m"])
                    fc = self.get_depth_color(h["ff"] if fem else h["fm"])
                    w = h["w"]
                    top, mid, belly, fin = (mix(top, tone(col, 0.82), w), mix(mid, tone(col, 1.05), w),
                                            mix(belly, mix(col, (255, 238, 205), 0.4), w), mix(fin, fc, w))
                gr = getattr(self, "growth", 1.0)
                if gr < 1.0:       # fry are plain silvery-brown and colour up as they grow
                    w = clamp(1.0 - (gr - 0.15) / 0.7) * 0.75
                    top, mid, belly, fin = (mix(top, tone(JUV_COL, 0.8), w), mix(mid, JUV_COL, w),
                                            mix(belly, (196, 190, 170), w), mix(fin, (176, 172, 156), w))
                if self.sneaker:      # he looks like a female so the bosses leave him alone
                    fc = getattr(self, "female_color", None) or JUV_COL
                    top, mid, belly, fin = (mix(top, tone(fc, 0.8), 0.7), mix(mid, fc, 0.7), mix(belly, (210, 200, 180), 0.7),
                                            mix(fin, getattr(self, "female_fin", None) or (176, 166, 146), 0.7))
                sk = clamp((getattr(self, "stress", 0.0) - 30.0) / 70.0) * 0.4
                male = getattr(self, "sex", "M") == "M"
                if male and self.flee_t > 0:
                    sk = max(sk, 0.3)
                if sk > 0.02:      # stressed or beaten: the colour drains
                    top, mid, belly, fin = _grey(top, sk), _grey(mid, sk), _grey(belly, sk), _grey(fin, sk)
                elif self.dom or self.display > 0:      # a dominant or courting male is at his richest
                    k = 0.1 + (0.06 if self.display > 0 else 0.0)
                    top, mid, belly, fin = tone(top, 1.0 + k * 0.6), tone(mid, 1.0 + k), tone(belly, 1.0 + k * 0.5), tone(fin, 1.0 + k)
                return top, mid, belly, fin

            def decorate(self, g, layer):
                orig_dec(self, g, layer)
                if type(self) is not cls:
                    return
                h = getattr(self, "hyb", None)
                oc = cichlid_by_name(h.get("cls")) if h and h.get("cls") else None
                if oc is not None and oc is not type(self):    # a hybrid also wears the other parent's markings, as faint
                    tmp = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
                    try:
                        oc.decorate(self, g, tmp)
                        tmp.set_alpha(int(50 + 190 * h["w"]))
                        layer.blit(tmp, (0, 0))
                    except Exception:
                        pass
                if self.fighting:      # fighting bars: dark vertical stripes across the body while it fights
                    for i in range(6):
                        pygame.draw.rect(layer, (8, 8, 20, 105), (g.rx + (0.2 + 0.11 * i) * g.L, g.cy - g.ht * 0.9, max(2, 0.032 * g.L), (g.ht + g.hb) * 0.9))
                if getattr(self, "brood", None) is not None or self.fry_in:     # the cheeks bulge with eggs or fry
                    z = g.z
                    pygame.draw.ellipse(layer, (*mix(g.belly, (236, 214, 150), 0.35), 235),
                                        (g.rx + 0.6 * g.L, g.cy - 0.02 * g.ht, 0.34 * g.L, 0.95 * g.hb))
                    rng = random.Random(self.id)
                    for _ in range(7):
                        pygame.draw.circle(layer, (236, 214, 150, 230), (int(g.rx + rng.uniform(0.64, 0.9) * g.L),
                                           int(g.cy + rng.uniform(0.15, 0.7) * g.hb)), max(1, int(1.2 * z)))
            def finish(self, g):
                orig_fn(self, g)
                if (type(self) is cls and isinstance(self, Cichlid) and getattr(self, "mouthbrooder", True)
                        and getattr(self, "sex", "M") == "M" and getattr(self, "growth", 1.0) >= 0.8 and not self.sneaker):
                    n = max(0, min(4, self.egg_spots))      # egg spots on the anal fin: dummy eggs the female snaps at
                    x0 = g.rx + 0.34 * g.L
                    y0 = edge_y(g.outline, x0, False) + 3.5 * g.z
                    for i in range(n):
                        px, py = x0 + (i - (n - 1) / 2) * 5.5 * g.z, y0 + (i % 2) * 2.2 * g.z
                        pygame.draw.circle(g.fs, (255, 206, 110), (px, py), max(1.5, 2.3 * g.z))
                        pygame.draw.circle(g.fs, (240, 130, 40), (px, py), max(1.5, 2.3 * g.z), 1)

            def back_fins(self, g):
                fins = orig_bf(self, g)
                return self_fold(self, g, fins) if type(self) is cls else fins

            def front_fins(self, g):
                fins = orig_ff(self, g)
                return self_fold(self, g, fins) if type(self) is cls else fins
            return palette, decorate, back_fins, front_fins, finish
        c.palette, c.decorate, c.back_fins, c.front_fins, c.finish = wrap(c, c.palette, c.decorate, c.back_fins, c.front_fins, c.finish)


_paint_wrappers()
AngelFish.mouthbrooder = False

GRAZERS = ("DemasoniCichlid", "CobaltZebra", "RedZebra", "KenyiCichlid", "AuratusCichlid", "YellowPrinceCichlid", "IceBlueCichlid")
SIFTERS = ("AulonocaraOB", "GermanRedPeacock", "SunshinePeacock", "SocolofiCichlid", "PeacockCichlid")
PELAGIC = ("ElectricBlueHap", "CopadichromisBorleyi")
for _n in GRAZERS:       # mbuna graze the algae film off the rocks all day
    cichlid_by_name(_n).feed_w = (0.001, 0.009, 0.0, 0.0006)
for _n in SIFTERS:       # peacocks sift the sand for small food
    cichlid_by_name(_n).feed_w = (0.008, 0.0015, 0.0, 0.0006)
for _n in PELAGIC:       # open-water haps snap at plankton in mid-water
    cichlid_by_name(_n).feed_w = (0.001, 0.0005, 0.008, 0.0004)

AngelFish.burster = False       # angelfish glide smoothly


def cross_ok(f):
    """Who can take part in cichlid cross-breeding: every Malawi and Central American cichlid except the angelfish."""
    return isinstance(f, Cichlid) and not isinstance(f, AngelFish)


def cross_id(p):
    """Which cross a hybrid is: the pair of species it descends from (the same for both sides of the cross)."""
    h = getattr(p, "hyb", None)
    return frozenset((type(p).__name__, h["cls"])) if h and h.get("cls") else None


def cross_traits(kid, m, f):
    """Pass the parents' colours on. Two different species: the fry is one parent's species wearing a blend of both (and its
    own colour line gene). Two hybrids of the same cross breed true: the blend is kept, and after three generations it is a
    named, stable strain. A hybrid with a pure fish: the blend thins out (a fixed strain only a little)."""
    if not isinstance(kid, Cichlid):
        return
    mi, fi = cross_id(m), cross_id(f)
    if mi is not None and mi == fi:
        own = m if type(m) is type(kid) else f
        h = dict(own.hyb)
        h["w"] = clamp((m.hyb["w"] + f.hyb["w"]) / 2 + random.gauss(0, 0.03), 0.1, 0.9)
        h["gen"] = min(m.hyb.get("gen", 1), f.hyb.get("gen", 1)) + 1
        if h["gen"] >= 3:
            h["fixed"] = True
            record_hybrid_strain(kid, h)
        kid.hyb = h
    elif type(m) is not type(f):
        other = f if type(kid) is type(m) else m
        oc = cichlid_cols(other)
        kid.hyb = {"from": nice_name(other), "cls": type(other).__name__, "gen": 1, "fixed": False,
                   "w": clamp(0.5 + random.gauss(0, 0.12), 0.25, 0.75), **{k: list(v) for k, v in oc.items()}}
    else:
        carriers = [p.hyb for p in (m, f) if getattr(p, "hyb", None)]
        if carriers:
            h = dict(carriers[0])
            h["w"] = clamp(h["w"] * (0.85 if h.get("fixed") else 0.6) + random.gauss(0, 0.05), 0.0, 0.8)
            if h["w"] > 0.08:
                kid.hyb = h


def record_hybrid_strain(kid, h):
    key = f"{nice_name(kid)} + {h['from']}"
    new = key not in X["hybrids"]
    rec = X["hybrids"].setdefault(key, [h["gen"], 0])
    rec[0] = max(rec[0], h["gen"])
    rec[1] += 1
    if new:
        notify(f"New hybrid strain: {key} (gen {h['gen']}, now breeding true)", log=True)
        save_prefs()


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


class SynodontisCatfish(Pleco):
    """Synodontis: a mottled, tan-and-black catfish with three pairs of barbels and a tall, forked fin set; shy by day,
    it scavenges the sand and rocks and is hardy among the Malawi cichlids."""
    common = "Synodontis"
    W, H = 200, 140
    L, HT, HB = 100, 21, 14
    shape = dict(peak=0.42, pt=0.66, pn=0.7, ped=0.1)
    base_color = (128, 104, 70)
    shadow = 22

    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.55, 0.78)
        self.max_speed = 3.2

    def back_fins(self, g):
        c = tone(g.mid, 0.95)
        return [fin_tail(g, "fork", 20, 30, 0.6, color=c, rays=10, alpha=215),
                fin_on_top(g, 0.62, 0.38, 40, -12, 0.35, color=c, rays=14, edge=tone(g.top, 0.7), width=SS),
                fin_on_belly(g, 0.4, 0.2, 10, -3, rays=6, color=tone(g.mid, 0.9)), fin_pelvic(g, 0.58, 14, 12, color=c)]

    def decorate(self, g, layer):
        rng = random.Random(self.id)
        for _ in range(26):   # big dark blotches on a tan flank
            u = rng.uniform(0.12, 0.86)
            y = g.cy + rng.uniform(-0.8, 0.5) * g.ht
            r = max(1.0, rng.uniform(1.2, 2.8) * g.z)
            pygame.draw.circle(layer, (24, 18, 14, 215), (int(g.rx + u * g.L), int(y)), int(r))
        pygame.draw.ellipse(layer, (30, 22, 16, 140), (g.rx + 0.7 * g.L, g.cy - g.ht * 0.9, g.L * 0.3, g.ht * 1.2))

    def finish(self, g):
        z, nose = g.z, g.cx + g.L / 2
        for k, (dy, ln) in enumerate(((0.05, 22), (0.25, 17), (0.42, 12))):   # three pairs of barbels
            pygame.draw.line(g.fs, tone(g.mid, 1.5), (nose - 2 * z, g.cy + g.ht * dy), (nose + ln * z * 0.5, g.cy + g.ht * dy + (6 + 3 * k) * z), max(1, int(z * 1.1)))
        pygame.draw.ellipse(g.fs, tone(g.belly, 0.95), (nose - 15 * z, g.cy + g.hb * 0.05, 15 * z, 9 * z))
