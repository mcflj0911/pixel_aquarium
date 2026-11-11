# ---- water quality, disease, feeding ----
FEEDS = ["PELLET", "FLAKES", "LIVE DAPHNIA", "BLOODWORM", "ALGAE WAFER"]
eggs, visitors, crawlers, placed = [], [], [], []


SICK_RECOVERY = 0.5          # illness shed per frame even in bad water (clean water adds up to 0.9 more)
SICK_DEATH_CHANCE = 1 / 60000  # per frame: about one sick fish in twenty dies in decent water
SICK_SPREAD = 0.03           # chance per second that a sick fish infects a neighbour within 70 px


def infect(f):
    if unattended():
        return
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
        self.carrier, self.hatch_at = None, 1800      # a mouthbrooder carries the clutch in her mouth
        self.sneaker = None                           # a sneaker male that darted in and fertilised some of the eggs
        self.tint = (236, 214, 150) if isinstance(male, Cichlid) else (226, 232, 214)
        self.dots = [(random.uniform(-9, 9), random.uniform(-4, 4)) for _ in range(14)]

    def guarded(self):
        return any(p.alive and p.guard_t > 0 and p.pos.distance_squared_to(self.pos) < 120 * 120 for p in self.parents)

    def update(self):
        self.age += 1
        c = self.carrier
        if c is not None:
            if not c.alive or c.brood is not self:
                eggs.remove(self)
                notify("The brood was lost with the mother", log=False)
                return
            self.pos.update(c.pos.x + (14 if c.vel.x >= 0 else -14) * c.z, c.pos.y + 4)
            c.hunger = min(100.0, c.hunger + 0.012)      # she cannot eat while her mouth is full
            if self.age >= self.hatch_at:
                self.hatch()
            return
        for f in fishes:
            if (f.hunger > 75 and random.random() < 0.01 and f.pos.distance_squared_to(self.pos) < 30 * 30
                    and f not in self.parents and not self.guarded()):
                eggs.remove(self)
                notify(f"{f.name} ate a clutch of eggs")
                return
        if self.age >= self.hatch_at:
            self.hatch()

    def hatch(self):
        eggs.remove(self)
        if self.carrier is not None:
            self.carrier.brood = None
            self.carrier.breed_cd = 5000
        n = random.randint(3, 5) + (1 if getattr(self.parents[0], "egg_spots", 0) >= 3 else 0)     # more egg spots, bigger clutch
        while n > 0 and not has_room(self.kind, n):
            n -= 1  # only as many fry as the tank can carry
        if n == 0:
            notify("The clutch failed: the tank is too crowded")
            return
        hybrids = sneaked = 0
        for _ in range(n):
            sn = self.sneaker
            fa = sn if (sn is not None and sn.alive and random.random() < 0.35) else self.parents[0]
            mo = self.parents[1]
            sneaked += fa is not self.parents[0]
            kid = random.choice((type(fa), type(mo)))(self.pos.x + random.uniform(-12, 12), self.pos.y - 20)
            init_traits(kid)
            kid.growth = 0.0
            kid.age = 0
            kid.sex = pick_sex(kid)
            kid.bravery = random.uniform(0.1, 0.4)
            kid.z = kid.adult_z * 0.3
            kid.hunger = 20.0
            kid.breed_cd = 4000
            kid.parents = (fa, mo)
            inherit_line(kid, (fa, mo))
            cross_traits(kid, fa, mo)
            if isinstance(kid, Cichlid):
                kid.egg_spots = int(clamp(round((getattr(fa, "egg_spots", 2) + getattr(mo, "egg_spots", 2)) / 2 + random.gauss(0, 0.7)), 0, 4))
                kid.sneaker_gene = random.choice((getattr(fa, "sneaker_gene", False), getattr(mo, "sneaker_gene", False))) or random.random() < 0.04
                if self.carrier is not None:
                    kid.mother = self.carrier
                    self.carrier.fry_t = 3000
            hybrids += hasattr(kid, "hyb")
            kid.nest, kid.nest_t = pygame.Vector2(self.pos) + (0, -24), 2600
            fishes.append(kid)
        eco.births += n
        stats["fry"] += n
        if sneaked:
            notify("A sneaker male fathered some of the fry", log=False)
        if type(self.parents[0]) is not type(self.parents[1]):
            notify(f"{n} hybrid fry hatched: {nice_name(self.parents[0])} x {nice_name(self.parents[1])}!")
        else:
            notify(f"{n} {nice_name(self.kind)} fry hatched!")
        play_sfx("hatch")
        burst(self.pos, self.tint, 12, 1.5, 50, 2, -0.01)

    def draw(self, surface):
        if self.carrier is not None:
            return
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
        kid.sex = pick_sex(kid)
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
    if isinstance(f, Cichlid) and getattr(f, "mouthbrooder", True):     # the Malawi way: she takes the eggs into her mouth
        e = eggs[-1]
        sn = [o for o in fishes if isinstance(o, Cichlid) and getattr(o, "sneaker", False) and o is not m and o.alive
              and o.pos.distance_squared_to(site) < 170 * 170 and (type(o) is type(f) or (CROSS["on"] and cross_ok(o)))]
        if sn:      # a low-rank male darts in during the spawning and fertilises some of the eggs
            e.sneaker = random.choice(sn)
            e.sneaker.display = 14
        e.carrier, e.hatch_at, f.brood = f, 2700, e
        m.guard_t = f.guard_t = 0
        m.breed_cd, f.breed_cd = 2400, 7000
        notify(f"{f.name} took the eggs into her mouth", log=False)
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
