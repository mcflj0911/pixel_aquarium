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
    if isinstance(f, Cichlid) and f.growth >= 0.7 and cave_spots:     # cichlids shelter in caves, not just behind any rock
        cave = find_cave(f, panic=f.fear > 0.5)
        if cave is not None:
            return cave
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
    f.sex = pick_sex(f)
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
    pit = getattr(m, "pit", None)
    if pit is not None and pit in PITS and pit["depth"] > 0.1:        # he leads her to the pit he dug
        return pygame.Vector2(pit["x"], ground_y(pit["x"]) - 22)
    if m.family == "cichlid" and (nest_spots or cave_spots):
        sites = [(sp, 0.0) for sp in nest_spots] + [(sp, 800.0) for sp in cave_spots]   # a cave is worth almost any swim
        return pygame.Vector2(min(sites, key=lambda t: m.pos.distance_to(t[0]) - t[1])[0])
    x = clamp(m.pos.x, 110, SCREEN_WIDTH - 110)
    return pygame.Vector2(x, ground_y(x) - 38)


def find_mate(f, need_ready):
    """The nearest free partner of the right kind. Cichlid females choose: the best male (rank, egg spots, display) within reach
    wins over a nearer, plainer one, and a male is turned down more often the less attractive he is."""
    best, bscore = None, -1e9
    f_cich = isinstance(f, Cichlid)
    for o in fishes:
        sex = getattr(o, "sex", None)
        if (o is f or sex is None or sex == f.sex or o.partner is not None
                or o.growth < 1.0 or o.age < GROW_FRAMES * 1.3 or not o.alive or getattr(o, "in_mouth", False)):
            continue
        same = type(o) is type(f)
        if not same and not (CROSS["on"] and cross_ok(f) and cross_ok(o)):
            continue
        if need_ready and (o.breed_cd > 0 or o.hunger > 50 or o.guard_t > 0):
            continue
        d = o.pos.distance_squared_to(f.pos) * (1.0 if same else 6.0)    # they prefer their own kind, but will cross when they must
        if d > 330 * 330:
            continue
        score = -math.sqrt(d)
        if f_cich and isinstance(o, Cichlid):
            if f.sex == "F":
                score += 260.0 * attract(o)
            elif random.random() > clamp(0.3 + attract(f)):      # she turns him down
                continue
        if score > bscore:
            best, bscore = o, score
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
    elif f.age > f.lifespan and random.random() < 1 / 2400 and not unattended():
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
    if ((f.fear > (0.35 if (isinstance(f, Cichlid) and getattr(f, "persona", "") == "shy") else 0.5) or f.sleepy > 0.55)
            and f.refuge is None and f.refuge_cd <= 0 and f.cleaning <= 0):
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
            if (f.safe > 150 and getattr(f, "brood", None) is None) or (f.hunger > 75 and threat < 0.5 and f.sleepy < 0.5):  # starving fish take risks
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
                        if dl < 170 and isinstance(f, Cichlid):     # fins up, colours blazing, quivering in front of her
                            f.display = 20
                            f.set_flare(1, 12)
                            if dl < 80:
                                f.apply_force(pygame.Vector2(math.sin(eco.t * 0.9 + f.id) * 0.22, 0))
                        if dl < 170:
                            f.apply_force(unit(pygame.Vector2(-off.y, off.x)) * math.sin(eco.t * 0.18 + f.id) * 0.34)
                            f.apply_force(unit(off) * (0.07 if dl > 55 else -0.04))
                        if random.random() < 0.012:
                            add_emote(f, "<3")
                    elif dl < 60:
                        f.apply_force(unit(-off) * 0.04)
                        if isinstance(f, Cichlid) and getattr(mate, "display", 0) > 0 and random.random() < 0.05:
                            f.mouth_open_timer = 8        # she snaps at the egg spots on his fin
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
