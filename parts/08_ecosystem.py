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


def unattended():
    """Wallpaper mode (F10) is unattended: nothing in the tank is allowed to hurt the fish while it is on."""
    return bool(globals().get("screensaver", False))


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
CROSS = {"on": True}       # "cichlid_crossbreed": different cichlid species may pair and breed hybrids
VISIT = {"on": False}      # "show_visitors": the frog and kingfisher guests
NEWTANK = {"on": False}    # "new_tank": start with an uncycled tank (nitrogen-cycle game)
X = {"points": 0, "owned": [], "memorial": [], "reqs": 0, "shows": 0, "wins": 0, "show_day": -9, "scapes": 0, "clips": 0,
     "guests": 0, "ferts": 0, "sound": "AUTO", "weeks": [], "best_scape": 0, "tours": 0, "blooms": 0,
     "sold": 0, "streak": 0, "chal": {}, "chal_won": [], "raids": 0, "relapses": 0,
     "cash": 0, "gear": [], "line": {}, "fow": "", "tut": 0, "tut_on": True, "evok": 0, "wx": True, "hybrids": {}}
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
    CROSS["on"] = bool(data.get("cichlid_crossbreed", True))
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
    data["cichlid_crossbreed"] = CROSS["on"]
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
        if unattended():      # unattended: only the friendly events
            options = ["CURRENT SURGE", "DAPHNIA BLOOM"]
        if self.bag is None and len(fishes) < FRAME_BUDGET - 5:
            options.append("NEW ARRIVALS")
        if PRED["on"] and not unattended() and sum(isinstance(p, Channa) for p in predators) < 2:
            options.append("CHANNA VISITOR")
        if TURTLE["on"] and not any(isinstance(v, Turtle) for v in visitors):
            options.append("RARE VISITOR")
        if VISIT["on"] and not any(isinstance(v, (Frog, Kingfisher)) for v in visitors):
            options.append("GUEST VISITOR")
        if name not in options and name != "MOON SPAWNING":
            name = None
        if name is None:
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
