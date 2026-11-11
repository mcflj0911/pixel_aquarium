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
                        and random.random() < chance and not unattended()):
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
