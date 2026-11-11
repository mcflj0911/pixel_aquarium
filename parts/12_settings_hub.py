# ---------------------------------------------------------------- settings, save slots, backups, progress reset
SLOT_DIR = os.path.dirname(CONFIG_FILE)
PREV_PATH = os.path.join(SLOT_DIR, "aquarium_prev.json")
N_SLOTS = 5
SET = {"mode": None, "slots": None, "reset": 0}
QUAL_NAMES = ("LOW", "MED", "HIGH")


def slot_path(i):
    return os.path.join(SLOT_DIR, f"aquarium_slot{i + 1}.json")


def slot_meta():
    out = []
    for i in range(N_SLOTS):
        try:
            with open(slot_path(i), encoding="utf-8") as fh:
                d = json.load(fh)
            e = d.get("eco", {})
            when = time.strftime("%d %b %H:%M", time.localtime(d["saved_at"])) if isinstance(d.get("saved_at"), (int, float)) else "?"
            out.append(f"day {e.get('day', '?')}, {len(d.get('fish', []))} fish, saved {when}")
        except (OSError, ValueError, KeyError, TypeError):
            out.append(None)
    return out


def backup_current():
    """Called before any load, so a load can be taken back (R in the settings panel)."""
    try:
        save_game(PREV_PATH, quiet=True)
    except Exception:
        pass


def restore_previous():
    if not os.path.exists(PREV_PATH):
        notify("There is no earlier state to restore", log=False)
        return
    load_game(PREV_PATH)
    notify("Restored the tank from before the last load", log=True)


def reset_progress():
    for k in X:
        X[k] = json.loads(json.dumps(X_DEFAULT[k]))
    GOALS_DONE.clear()
    strains.clear()
    save_prefs()
    notify("Progress reset: points, goals, strains, memorial and purchases are cleared (fish sets and options are kept)", log=True)


SETTING_ROWS = [
    ("Predators", lambda: PRED["on"], "predators", "channa, fire eel and crayfish hunt the fish"),
    ("Crayfish", lambda: CRAY["on"], "crayfish", "show the crayfish"),
    ("Turtle", lambda: TURTLE["on"], "turtle", "rare turtle visitor"),
    ("Visitors", lambda: VISIT["on"], "visitors", "frog and kingfisher guests"),
    ("Away mode", lambda: AWAY["on"], "away", "the tank keeps going while the game is closed"),
    ("Auto quality", lambda: GOV["on"], "auto", "drop the plant detail automatically when frames are slow"),
    ("Quality", lambda: QUALITY[0], "quality", "LOW / MED / HIGH (also Q)"),
    ("New tank mode", lambda: NEWTANK["on"], "newtank", "start the next game with an uncycled tank"),
    ("Soundscape", lambda: X["sound"], "sound", "ambient rain, crickets and room hum (also backquote)"),
]


def setting_toggle(i):
    key = SETTING_ROWS[i][2]
    if key == "predators":
        PRED["on"] = not PRED["on"]
    elif key == "crayfish":
        CRAY["on"] = not CRAY["on"]
    elif key == "turtle":
        TURTLE["on"] = not TURTLE["on"]
    elif key == "visitors":
        VISIT["on"] = not VISIT["on"]
    elif key == "away":
        AWAY["on"] = not AWAY["on"]
    elif key == "auto":
        GOV["on"] = not GOV["on"]
    elif key == "quality":
        QUALITY[0] = QUAL_NAMES[(QUAL_NAMES.index(QUALITY[0]) + 1) % 3]
        GOV["base"] = QUALITY[0]
    elif key == "newtank":
        NEWTANK["on"] = not NEWTANK["on"]
    elif key == "sound":
        cycle_sound()
    save_prefs()
    if key in ("predators", "crayfish", "turtle", "visitors"):
        notify("Changed: it takes effect the next time the tank is started", log=False)


def settings_key(k):
    """Digits 1-9 change a setting. S then 1-5 saves to a slot, L then 1-5 loads one, R restores the state before the last load,
    Z twice resets progress."""
    if SET["mode"] in ("save", "load") and pygame.K_1 <= k <= pygame.K_5:
        i = k - pygame.K_1
        if SET["mode"] == "save":
            save_game(slot_path(i))
            notify(f"Saved to slot {i + 1}", log=False)
        elif os.path.exists(slot_path(i)):
            backup_current()
            load_game(slot_path(i))
        else:
            notify(f"Slot {i + 1} is empty", log=False)
        SET["mode"], SET["slots"] = None, None
        return True
    if pygame.K_1 <= k <= pygame.K_9:
        setting_toggle(k - pygame.K_1)
        return True
    if k == pygame.K_s:
        SET["mode"] = None if SET["mode"] == "save" else "save"
        SET["slots"] = None
        return True
    if k == pygame.K_l:
        SET["mode"] = None if SET["mode"] == "load" else "load"
        SET["slots"] = None
        return True
    if k == pygame.K_r:
        backup = os.path.exists(PREV_PATH)
        restore_previous() if backup else notify("There is no earlier state to restore", log=False)
        return True
    if k == pygame.K_z:
        SET["reset"] += 1
        if SET["reset"] >= 2:
            SET["reset"] = 0
            reset_progress()
        else:
            notify("Press Z again to reset all progress (points, goals, strains, memorial, purchases)", log=False)
        return True
    return False


def draw_settings(surface):
    if SET["slots"] is None:
        SET["slots"] = slot_meta()
    panel = begin_panel(1000, 600, "Settings and saves")
    for i, (name, getter, _k, desc) in enumerate(SETTING_ROWS):
        y = 66 + 34 * i
        v = getter()
        on = v is True or (isinstance(v, str) and v not in ("OFF",))
        txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
        txt21(panel, name, 62, y + 2, "h", (200, 215, 232))
        txt21(panel, ("ON" if v is True else "OFF" if v is False else str(v)), 230, y + 2, "h", (150, 230, 170) if on else (160, 170, 185))
        txt21(panel, desc, 320, y + 4, "d", HUD_DIM)
    y0 = 66 + 34 * len(SETTING_ROWS) + 14
    txt21(panel, "Save slots", 26, y0, "h", (255, 232, 140))
    mode = SET["mode"]
    txt21(panel, ("Press 1-5 to " + mode + "...") if mode else "S then 1-5 saves   L then 1-5 loads   R restores the state before the last load", 150, y0 + 2, "d", (255, 232, 150) if mode else HUD_DIM)
    for i, m in enumerate(SET["slots"]):
        txt21(panel, f"{i + 1}", 26, y0 + 28 + 24 * i, "h", (130, 190, 235))
        txt21(panel, m or "empty", 62, y0 + 28 + 24 * i, "d", (200, 215, 232) if m else (110, 125, 145))
    txt21(panel, "Z twice: reset progress (points, goals, strains, memorial, purchases). Fish sets, audio and options stay.", 26, 600 - 52, "d", (240, 170, 150))
    end_panel(surface, panel, "Esc to close   (Ctrl+S opens this panel)")



# ---------------------------------------------------------------- hub: gear and cash, breeding line, upkeep, history, life, guide
# Also here: water hardness, equipment wear, snail and shrimp colonies, weather events, debris, night life, the hand, the gamepad.
EQ = {"drift": 0.0, "stone": 1.0, "media": 1.0, "sd": -9}
EV = {"name": None, "until": 0, "dt": 0.0, "start": -9, "b0": 0}
DEB = []
DEBS = [0]
HUB = {"tab": 0}
HUB_TABS = ("Gear", "Line", "Upkeep", "History", "Life", "Guide")
HAND = {"f": None, "held": 0, "drip": 0}
TUTF = set()
TUTP = {"t": 0}
PAD = {"js": None, "btn": {}, "next": 0}
CAT = {"t": 0}
P6 = {"day": None, "init": False, "tour": 0, "last_event": ""}
SOFT_FISH = ("NeonTetra", "CardinalTetra", "RummyNose", "LemonTetra", "BlackSkirtTetra", "Otocinclus", "Corydoras")
HARD_FISH = ("Killifish", "MosaicGuppy", "MoscowGuppy", "TuxedoGuppy", "SunsetGuppy", "KenyiCichlid", "AuratusCichlid", "SocolofiCichlid",
              "AulonocaraOB", "GermanRedPeacock", "SunshinePeacock", "CopadichromisBorleyi", "ElectricBlueHap", "SynodontisCatfish")
GEAR = [("filter2", "Filter upgrade II", 40, "Sponge clogs even slower and the flow stays strong"),
        ("led", "LED rack", 60, "Tall plants grow a little faster every day"),
        ("ups", "Battery backup", 50, "A power cut no longer stops the filter or the water quality"),
        ("autofeed", "Auto feeder", 70, "Drops a pinch of flakes twice a day (watch the waste)"),
        ("heater_pro", "Smart heater", 45, "The heater never drifts off its setting"),
        ("mineral", "Mineral kit", 30, "Lets you raise or lower hardness from the Upkeep tab")]
TUT = [("Click the water to drop food. Hold the button to drip it. Keys 1-6 change the food.", "click"),
       ("Press F1 to see every key.", pygame.K_F1),
       ("Press , to open the equipment shop.", pygame.K_COMMA),
       ("Press ; for the water test kit (now with KH and GH).", pygame.K_SEMICOLON),
       ("Press / for the dashboard and the week summary.", pygame.K_SLASH),
       ("Press Del for the hub: gear, breeding line, upkeep, history, life.", pygame.K_DELETE),
       ("Hold Ctrl and drag a fish to lift it. Right-click taps the glass.", "hand"),
       ("That is the tour. Ctrl+S opens settings and save slots.", None)]


def buy_gear(i):
    if not 0 <= i < len(GEAR):
        return
    gid, name, cost, _ = GEAR[i]
    if gid in X["gear"]:
        notify(f"You already own the {name}", log=False)
    elif X["cash"] < cost:
        notify(f"The {name} costs {cost} cash (you have {X['cash']}). Sell bred fish and keep a good scape to earn it", log=False)
    else:
        X["cash"] -= cost
        X["gear"].append(gid)
        play_sfx("chime", 0.6)
        notify(f"Bought: {name}", log=True)
        save_prefs()


# ---- hardness
KH_OK = tuple(scape("water", "kh_range", (3, 10)))     # the "good" band shown in the kit and in Upkeep
GH_OK = tuple(scape("water", "gh_range", (4, 12)))


def hardness_range(f):
    n = type(f).__name__
    return (2.0, 8.0) if n in SOFT_FISH else (8.0, 16.0) if n in HARD_FISH else (4.0, 12.0)


def hardness_off(f):
    lo, hi = hardness_range(f)
    return max(lo - CHEM["gh"], CHEM["gh"] - hi, 0.0)


def hardness_tick():
    bad = 0
    for f in fishes:
        if hasattr(f, "stress") and hasattr(f, "family"):
            off = hardness_off(f)
            if off > 1.5:
                f.stress = min(100.0, f.stress + 0.35 * off)
                bad += 1
    if bad >= 4 and "gh" not in eco.warned:
        eco.warned.add("gh")
        notify(f"The water hardness (GH {CHEM['gh']:.0f}) does not suit {bad} fish: see Upkeep (Del)", log=False)
    elif bad == 0:
        eco.warned.discard("gh")


def chem6_tick():
    c = CHEM
    green = sum(1 for p in plants if p.species != "MossBall")
    buf = bool(scape("substrate", "buffer", False))     # aragonite sand keeps releasing carbonate, calcium and magnesium
    c["kh"] = clamp(c["kh"] - 0.0012 * (0.25 if buf else 1.0) * (1.0 + c["no3"] / 60.0), 0.5, 25.0)
    if buf:
        c["kh"] += (float(scape("water", "kh", 10.0)) - c["kh"]) * 0.002
    c["gh"] = clamp(c["gh"] + 0.0003 * len(rocks) - 0.00006 * green, 0.5, 25.0)
    c["ph"] += ((6.9 + 0.12 * (c["kh"] - 4.0) + (0.3 if buf else 0.0)) - c["ph"]) * 0.01
    if c["kh"] < 2.0 and c["ph"] < 6.4 and "khlow" not in eco.warned:
        eco.warned.add("khlow")
        notify("KH is nearly gone: the pH can crash. Do a water change (W)", log=False)
    elif c["kh"] > 3.0:
        eco.warned.discard("khlow")
    if "filter2" in X["gear"]:
        eco.filter = min(1.0, eco.filter + 0.0004)
    if DEBS[0] > 20:
        HAIR[random.randrange(GLASS_COLS)] += 0.002 * DEBS[0] / 30.0
        c["no3"] = min(200.0, c["no3"] + 0.004 * DEBS[0])
    if eco.power and "ups" in X["gear"]:
        eco.water = clamp(eco.water + 0.08, 0.0, 100.0)
    if EQ["stone"] < 0.3 and eco.air_on:
        eco.water = clamp(eco.water - 0.03 * (0.3 - EQ["stone"]) / 0.3, 0.0, 100.0)


# ---- debris on the sand
def debris_spawn():
    resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
    rate = 0.12 + 0.012 * len(fishes) + 0.04 * resting + (0.15 if EV["name"] == "leaf fall" else 0.0)
    rate *= 1.3 - 0.6 * eco.filter
    if len(DEB) < 70 and random.random() < min(0.9, rate):
        DEB.append([random.uniform(30, SCREEN_WIDTH - 30), random.uniform(WATER_TOP + 40, SCREEN_HEIGHT * 0.65),
                    random.uniform(-0.12, 0.12), random.uniform(0.06, 0.22), random.uniform(0, 6)])


def debris_update():
    if not DEB:
        return
    cur = eco.current * 6
    pull = 0.0 if eco.power else eco.filter * 0.0006
    for d in DEB[:]:
        d[0] += d[2] + cur + math.sin(eco.t * 0.03 + d[4]) * 0.15
        d[1] += d[3]
        if random.random() < pull:
            DEB.remove(d)
        elif d[1] >= ground_y(d[0]) - 4:
            DEB.remove(d)
            DEBS[0] = min(60, DEBS[0] + 1)


def siphon():
    if eco.day - EQ["sd"] < 1:
        notify("The sand was already siphoned today", log=False)
        return
    EQ["sd"] = eco.day
    del DEB[:]
    DEBS[0] = 0
    CHEM["nh3"] *= 0.8
    CHEM["no3"] *= 0.85
    eco.water = clamp(eco.water + 3.0, 0.0, 100.0)
    play_sfx("bubble")
    notify("Siphoned the sand: the mulm is gone", log=True)


# ---- colonies
def colony_tick():
    resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
    fed = CHEM["no3"] > 12 or resting > 3 or sum(HAIR) / GLASS_COLS > 0.15
    snails = [c for c in crawlers if isinstance(c, (MysterySnail, Ramshorn))]
    n = len(snails)
    if fed and n < 22 and random.random() < 0.55:
        crawlers.append(Ramshorn() if random.random() < 0.7 else MysterySnail())
        if n + 1 == 15:
            notify("A snail boom: too much food is feeding them. Feed less", log=False)
    elif not fed and n > 4 and random.random() < 0.4:
        crawlers.remove(snails[-1])
    moss = sum(1 for p in plants if p.species in ("MossBall", "DwarfGrass", "Clover"))
    if moss >= 2 and CHEM["no3"] < 70 and CHEM["nh3"] < 0.5 and len(shimps) < 40 and random.random() < 0.5:
        shimps.append(TinyShrimp())
    elif (CHEM["no3"] > 90 or CHEM["nh3"] > 1.0) and len(shimps) > 6 and random.random() < 0.5:
        shimps.pop()
        notify("A shrimp died in the dirty water", log=False)


# ---- weather and seasonal events
def event_end():
    name = EV["name"]
    ok = True
    if name in ("cold snap", "heat wave"):
        st = [f.stress for f in fishes if hasattr(f, "stress")]
        ok = (sum(st) / len(st) < 40) if st else True
    elif name == "spawning season":
        ok = eco.births - EV["b0"] >= 3
    elif name == "leaf fall":
        ok = CHEM["nh3"] < 0.3 and CHEM["no3"] < 40
    EV.update(name=None, dt=0.0)
    if ok:
        X["points"] += 6
        X["cash"] += 6
        X["evok"] += 1
        notify(f"You came through the {name}: +6 points, +6 cash", log=True)
        play_sfx("chime", 0.5)
    else:
        notify(f"The {name} is over; it left the tank a little worse for wear", log=True)
    save_prefs()


def events_tick():
    if EV["name"]:
        if eco.day >= EV["until"]:
            event_end()
        return
    if eco.day - EV["start"] < 6 or random.random() > 0.16 or eco.event or unattended():
        return
    name = ("spawning season", "heat wave", "leaf fall", "cold snap")[eco.season % 4]
    EV.update(name=name, start=eco.day, until=eco.day + 2, b0=eco.births)
    if name == "cold snap":
        EV["dt"] = -4.0
        notify("Cold snap! The room is cooling: raise the heater (Y)", log=True)
    elif name == "heat wave":
        EV["dt"] = 4.0
        notify("Heat wave! Heater off (Y), lights off (L) and keep the water clean", log=True)
    elif name == "spawning season":
        eco.start_event("MOON SPAWNING")
        notify("Spawning season: the fish are in the mood. Keep cover and clean water for the fry", log=True)
    else:
        for _ in range(30):
            debris_spawn()
        CHEM["no3"] = min(200.0, CHEM["no3"] + 5)
        notify("Leaf fall: debris is raining into the tank. Siphon the sand and change water", log=True)


# ---- breeding line
def line_state():
    L = X["line"]
    if L.get("cls") and not any(type(f).__name__ == L["cls"] for f in fishes):
        L.clear()      # the saved species is not in this tank (new set or tank): choose again
    if not L.get("cls"):
        pool = {}
        for f in fishes:
            if hasattr(f, "hl") and hasattr(f, "family"):
                pool[type(f).__name__] = pool.get(type(f).__name__, 0) + 1
        if pool:
            L["cls"] = max(pool, key=pool.get)
            L["target"] = round(random.choice((-1, 1)) * random.uniform(0.35, 0.7), 2)
            L["need"] = 2
            L["done"] = 0
    return L


def line_score(f, target):
    return int(100 * max(0.0, 1.0 - abs(f.hl - target) / 0.8))


def line_candidates():
    L = line_state()
    if not L.get("cls"):
        return []
    out = [(line_score(f, L["target"]), f) for f in fishes if type(f).__name__ == L["cls"] and hasattr(f, "hl")]
    out.sort(key=lambda a: -a[0])
    return out


def line_check():
    L = line_state()
    if not L.get("cls"):
        return
    for sc, f in line_candidates():
        if sc >= 80 and f.growth >= 1.0 and getattr(f, "gen", 1) >= L["need"]:
            L["done"] += 1
            X["points"] += 15
            X["cash"] += 10
            story(f, f"Met the {L['cls']} line standard (generation {f.gen})")
            notify(f"{f.name} meets the {nice_name(type(f))} line standard! +15 points, +10 cash", log=True)
            play_sfx("chime", 0.6)
            L["need"] = int(f.gen) + 2
            L["target"] = round(clamp(L["target"] + random.choice((-1, 1)) * random.uniform(0.3, 0.6), -1.0, 1.0), 2)
            save_prefs()
            return


def line_cycle(retarget):
    L = line_state()
    names = sorted({type(f).__name__ for f in fishes if hasattr(f, "hl") and hasattr(f, "family")})
    if not names:
        return
    if not retarget:
        i = (names.index(L["cls"]) + 1) % len(names) if L.get("cls") in names else 0
        L["cls"] = names[i]
    L["target"] = round(random.choice((-1, 1)) * random.uniform(0.3, 0.7), 2)
    L["need"] = max((getattr(f, "gen", 1) for f in fishes if type(f).__name__ == L["cls"]), default=1) + 1
    notify(f"New {nice_name(type(next(f for f in fishes if type(f).__name__ == L['cls'])))} line target set", log=False)


# ---- per-day work
def day6():
    P6["day"] = eco.day
    EQ["stone"] = max(0.0, EQ["stone"] - 0.04)
    EQ["media"] = max(0.0, EQ["media"] - 0.03)
    if "heater_pro" in X["gear"]:
        EQ["drift"] = 0.0
    else:
        EQ["drift"] = clamp(EQ["drift"] + random.gauss(0.0, 0.25), -3.0, 3.0)
        if abs(EQ["drift"]) > 1.5 and "drift" not in eco.warned:
            eco.warned.add("drift")
            notify("The heater is drifting off its setting: recalibrate it in Upkeep (Del)", log=False)
        elif abs(EQ["drift"]) < 0.8:
            eco.warned.discard("drift")
    if EQ["media"] < 0.3 and "media" not in eco.warned:
        eco.warned.add("media")
        notify("The filter media is worn out: replace it in Upkeep (Del)", log=False)
    elif EQ["media"] > 0.5:
        eco.warned.discard("media")
    if EQ["stone"] < 0.3 and "stone" not in eco.warned:
        eco.warned.add("stone")
        notify("The air stone is clogged: replace it in Upkeep (Del)", log=False)
    elif EQ["stone"] > 0.5:
        eco.warned.discard("stone")
    colony_tick()
    events_tick()
    if "led" in X["gear"]:
        for p in plants:
            if p.species in TALL_PLANTS and p.hp > 0.6 and hasattr(p, "base_h") and p.height < p.base_h * 1.8:
                scale_plant(p, 1.008)
    try:
        score = int(judge_layout()["overall"])
    except Exception:
        score = 0
    inc = max(0, (score - 35) // 10)
    P6["tour"] = inc
    if inc:
        X["cash"] += inc
        notify(f"Tank tour: visitors admired the scape and paid {inc} cash", log=False)
    if eco.day % 7 == 0:
        pool = [f for f in fishes if hasattr(f, "persona") and f.alive]
        if pool:
            best = max(pool, key=lambda f: (f.fav, len(f.bio), f.age))
            X["fow"] = best.name
            notify(f"Fish of the week: {best.name} the {nice_name(best)} ({best.persona})", log=True)
    if eco.overgrown > 0.6:    # a dense canopy shades the carpet: it fades until you prune
        for p in plants:
            if p.species in ("DwarfGrass", "Clover") and random.random() < 0.15:
                p.hp = max(0.2, p.hp - 0.1)
    line_check()
    if random.random() < 0.25 and CAT["t"] <= 0:
        CAT["t"] = 900
    save_prefs()


def fw6_update():
    pad_poll()
    if current_state != STATE_AQUARIUM or PM["on"]:
        return
    t = eco.t
    if not P6["init"]:
        P6["init"] = True
        P6["day"] = eco.day
        dash_sample()
        dash_sample()
        if X["tut_on"] and (eco.day > 5 or X["points"] > 20):
            X["tut_on"] = False      # a tank that is already running does not need the tour
    elif P6["day"] != eco.day:
        day6()
    hand_update()
    debris_update()
    if t % 30 == 0:
        debris_spawn()
        hardness_tick()
    if t % 60 == 0:
        chem6_tick()
    if "autofeed" in X["gear"] and t % (DAY_LENGTH // 2) == 0 and len(pellets) < 30:
        for _ in range(3):
            pellets.append(Flake(random.randint(80, SCREEN_WIDTH - 80), WATER_TOP))
    if CAT["t"] > 0:
        CAT["t"] -= 1
        for f in fishes:
            if hasattr(f, "fear") and f.pos.x < SCREEN_WIDTH * 0.35:
                f.fear = max(f.fear, 0.12)
    if X["tut_on"]:
        while X["tut"] < len(TUT) - 1 and TUT[X["tut"]][1] in TUTF:
            X["tut"] += 1
        if X["tut"] >= len(TUT) - 1:
            TUTP["t"] += 1
            if TUTP["t"] > 600:
                X["tut_on"] = False
                save_prefs()


# ---- the hand: lift a fish with Ctrl+drag, drip food by holding the button
def hand_event(e):
    if current_state != STATE_AQUARIUM or PM["on"] or UI21["panel"] is not None:
        return False
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and pygame.key.get_mods() & pygame.KMOD_CTRL:
        pos = pygame.Vector2(world_mouse(e.pos))
        best, bd = None, 70
        for f in fishes:
            d = f.pos.distance_to(pos)
            if d < bd and hasattr(f, "stress"):
                best, bd = f, d
        if best is not None:
            HAND["f"], HAND["held"] = best, 0
            TUTF.add("hand")
            return True
    if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and HAND["f"] is not None:
        f = HAND["f"]
        HAND["f"] = None
        f.fear = max(f.fear, 0.4)
        if HAND["held"] > 240 and hasattr(f, "bio"):
            story(f, "Was held in a hand for far too long")
        return True
    return False


def hand_update():
    f = HAND["f"]
    if f is not None:
        if not f.alive or f not in fishes:
            HAND["f"] = None
        else:
            mx, my = world_mouse(pygame.mouse.get_pos())
            f.pos.update(clamp(mx, 24, SCREEN_WIDTH - 24), clamp(my, WATER_TOP + 12, SCREEN_HEIGHT - SAND_HEIGHT - 12))
            f.vel.update(0, 0)
            HAND["held"] += 1
            if HAND["held"] % 30 == 0:
                f.stress = min(100.0, f.stress + 0.5)
    mods = pygame.key.get_mods()
    pressed = pygame.mouse.get_pressed()[0] and f is None and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT))
    ok = (pressed and UI21["panel"] is None and not show_help and not confirm_quit and not screensaver
          and DECOR_TOOLS[eco.decor_idx] == "OFF")
    HAND["drip"] = HAND["drip"] + 1 if ok else 0
    if HAND["drip"] > 25 and HAND["drip"] % 10 == 0 and len(pellets) < 40:
        drop_feed(world_mouse(pygame.mouse.get_pos()))


# ---- gamepad: the stick moves the pointer, A clicks, the other buttons press the main keys
PAD_KEYS = {1: pygame.K_ESCAPE, 2: pygame.K_F1, 3: pygame.K_DELETE, 4: pygame.K_COMMA, 5: pygame.K_SEMICOLON,
            6: pygame.K_TAB, 7: pygame.K_p}
PAD_HAT = {(-1, 0): pygame.K_LEFT, (1, 0): pygame.K_RIGHT, (0, 1): pygame.K_UP, (0, -1): pygame.K_DOWN}


def _pad_key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


def pad_poll():
    if eco.t >= PAD["next"]:
        PAD["next"] = eco.t + 180
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            n = pygame.joystick.get_count()
            if PAD["js"] is None and n > 0:
                PAD["js"] = pygame.joystick.Joystick(0)
                notify("Controller connected: stick = pointer, A = click, B = back, X = help, Y = hub", log=False)
            elif PAD["js"] is not None and n == 0:
                PAD["js"] = None
        except pygame.error:
            PAD["js"] = None
    js = PAD["js"]
    if js is None:
        return
    try:
        ax, ay = js.get_axis(0), js.get_axis(1)
        x, y = pygame.mouse.get_pos()
        if abs(ax) > 0.2 or abs(ay) > 0.2:
            pygame.mouse.set_pos((int(clamp(x + ax * 20, 0, DISPLAY_W - 1)), int(clamp(y + ay * 20, 0, DISPLAY_H - 1))))
            x, y = pygame.mouse.get_pos()
        now = {i: js.get_button(i) for i in range(min(js.get_numbuttons(), 8))}
        if js.get_numaxes() > 5:
            now["rt"] = js.get_axis(5) > 0.5
        hat = js.get_hat(0) if js.get_numhats() else (0, 0)
    except pygame.error:
        PAD["js"] = None
        return
    old = PAD["btn"]
    for i, v in now.items():
        if v and not old.get(i):
            if i == 0:
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
            elif i == "rt":
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=3))
            elif i in PAD_KEYS:
                _pad_key(PAD_KEYS[i])
        elif old.get(i) and not v and i == 0:
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))
    if hat != old.get("hat") and hat in PAD_HAT:
        _pad_key(PAD_HAT[hat])
    now["hat"] = hat
    PAD["btn"] = now


# ---- keys inside the hub
def hub_key(k):
    if k in (pygame.K_LEFT, pygame.K_RIGHT):
        HUB["tab"] = (HUB["tab"] + (1 if k == pygame.K_RIGHT else -1)) % len(HUB_TABS)
        return True
    if pygame.K_1 <= k < pygame.K_1 + len(HUB_TABS):
        HUB["tab"] = k - pygame.K_1
        return True
    tab = HUB["tab"]
    if tab == 0 and pygame.K_a <= k < pygame.K_a + len(GEAR):
        buy_gear(k - pygame.K_a)
    elif tab == 1 and k == pygame.K_n:
        line_cycle(False)
    elif tab == 1 and k == pygame.K_t:
        line_cycle(True)
    elif tab == 2:
        if k == pygame.K_r:
            EQ["media"] = 1.0
            chem_rinse()
            notify("New filter media fitted (the bacteria take a small knock)", log=True)
        elif k == pygame.K_a:
            EQ["stone"] = 1.0
            notify("New air stone fitted", log=True)
        elif k == pygame.K_h:
            EQ["drift"] = 0.0
            notify("Heater recalibrated", log=True)
        elif k == pygame.K_v:
            siphon()
        elif k == pygame.K_t:
            trim_plants()
        elif k in (pygame.K_m, pygame.K_p):
            if "mineral" not in X["gear"]:
                notify("You need the Mineral kit (Gear tab) to change hardness", log=False)
            elif k == pygame.K_m:
                CHEM["kh"] = min(25.0, CHEM["kh"] + 2.0)
                CHEM["gh"] = min(25.0, CHEM["gh"] + 2.0)
                notify("Minerals added: harder water", log=False)
            else:
                CHEM["kh"] = max(0.5, CHEM["kh"] - 1.0)
                CHEM["gh"] = max(0.5, CHEM["gh"] - 2.0)
                notify("Peat added: softer water", log=False)
    elif tab == 4 and k == pygame.K_w:
        X["wx"] = not X.get("wx", True)
        if X["wx"]:
            WX["next"] = 0.0
        save_prefs()
        notify("Live weather " + ("on (needs the real-time clock, O)" if X["wx"] else "off"), log=False)
    elif tab == 5 and k == pygame.K_t:
        X["tut_on"] = not X["tut_on"]
        if X["tut_on"]:
            X["tut"], TUTP["t"] = 0, 0
            TUTF.clear()
        save_prefs()
    return True


def _hub_gear(panel, y0):
    txt21(panel, f"Cash {X['cash']}   (earned from selling bred fish, line standards, weathering events and tank tours: last tour paid {P6['tour']})", 26, y0, "d", HUD_DIM)
    for i, (gid, name, cost, desc) in enumerate(GEAR):
        y = y0 + 40 + 56 * i
        own = gid in X["gear"]
        txt21(panel, chr(65 + i), 26, y, "t", (130, 190, 235))
        txt21(panel, name, 62, y, "h", (150, 230, 170) if own else (255, 232, 140) if X["cash"] >= cost else (200, 215, 232))
        txt21(panel, desc, 62, y + 22, "d", HUD_DIM)
        txt21(panel, "OWNED" if own else f"{cost} cash", 960, y + 4, "h", (150, 230, 170) if own else (235, 245, 255))
    txt21(panel, "Press the letter to buy", 26, y0 + 40 + 56 * len(GEAR), "d", HUD_DIM)


def _hub_line(panel, y0):
    L = line_state()
    if not L.get("cls"):
        txt21(panel, "No fish with a colour line yet.", 26, y0)
        return
    txt21(panel, f"Breeding line: {nice_name(type(next(f for f in fishes if type(f).__name__ == L['cls'])))}    standards met {L['done']}", 26, y0, "h", (255, 232, 140))
    txt21(panel, f"Breed an adult of generation {L['need']} or later whose colour line is near the target. A score of 80 meets the standard.", 26, y0 + 28, "d", HUD_DIM)
    bx, bw = 26, 700
    pygame.draw.rect(panel, (24, 44, 74), (bx, y0 + 76, bw, 18), border_radius=6)
    for v in (-1, -0.5, 0, 0.5, 1):
        pygame.draw.line(panel, (70, 100, 140), (bx + bw * (v + 1) / 2, y0 + 72), (bx + bw * (v + 1) / 2, y0 + 98), 1)
    tx = bx + bw * (L["target"] + 1) / 2
    pygame.draw.polygon(panel, (255, 220, 90), [(tx, y0 + 70), (tx - 8, y0 + 56), (tx + 8, y0 + 56)])
    txt21(panel, f"target {L['target']:+.2f}", tx + 12, y0 + 52, "h", (255, 232, 140))
    cands = line_candidates()
    for sc, f in cands[:12]:
        px = bx + bw * (clamp(f.hl, -1.0, 1.0) + 1) / 2
        pygame.draw.circle(panel, (120, 215, 160) if sc >= 80 else (120, 170, 220), (int(px), y0 + 85), 5)
    txt21(panel, "Closest fish (name, generation, score):", 26, y0 + 112, "h")
    for i, (sc, f) in enumerate(cands[:8]):
        y = y0 + 142 + 26 * i
        txt21(panel, f"{f.name}", 26, y, "d", (200, 215, 232))
        txt21(panel, f"gen {getattr(f, 'gen', 1)}   {'adult' if f.growth >= 1.0 else 'young'}", 220, y, "d", HUD_DIM)
        pygame.draw.rect(panel, (24, 44, 74), (420, y + 3, 260, 12), border_radius=4)
        pygame.draw.rect(panel, (110, 215, 140) if sc >= 80 else (120, 170, 220), (420, y + 3, max(3, int(2.6 * sc)), 12), border_radius=4)
        txt21(panel, str(sc), 690, y, "d")
    txt21(panel, "N: next species      T: new target", 26, 640 - 60, "d", HUD_DIM)


def _hub_upkeep(panel, y0):
    c = CHEM
    bar21(panel, 26, y0, 340, EQ["media"], (110, 215, 140) if EQ["media"] > 0.4 else (240, 90, 80), "Filter media", f"{int(EQ['media'] * 100)}%   R replace")
    bar21(panel, 26, y0 + 36, 340, EQ["stone"], (110, 215, 140) if EQ["stone"] > 0.4 else (240, 90, 80), "Air stone", f"{int(EQ['stone'] * 100)}%   A replace")
    bar21(panel, 26, y0 + 72, 340, (EQ["drift"] + 3) / 6.0, (110, 215, 140) if abs(EQ["drift"]) < 1.2 else (240, 200, 90), "Heater drift", f"{EQ['drift']:+.1f} C   H recalibrate")
    bar21(panel, 26, y0 + 108, 340, DEBS[0] / 60.0, (110, 215, 140) if DEBS[0] < 25 else (240, 200, 90), "Mulm on the sand", f"{DEBS[0]}   V siphon")
    txt21(panel, f"Canopy {int(eco.overgrown * 100)}% overgrown   T trim all plants", 400, y0 + 4, "h", (255, 232, 140) if eco.overgrown > 0.5 else (200, 215, 232))
    bar21(panel, 26, y0 + 160, 340, c["kh"] / 20.0, (110, 215, 140) if KH_OK[0] <= c["kh"] <= KH_OK[1] else (240, 200, 90), "Carbonate KH", f"{c['kh']:.1f}")
    bar21(panel, 26, y0 + 196, 340, c["gh"] / 20.0, (110, 215, 140) if GH_OK[0] <= c["gh"] <= GH_OK[1] else (240, 200, 90), "General GH", f"{c['gh']:.1f}   M harder, P softer")
    soft = [f for f in fishes if hardness_off(f) > 1.5]
    txt21(panel, f"{len(soft)} fish are outside their hardness range" if soft else "Every fish is happy with the hardness", 26, y0 + 240, "h", (255, 160, 130) if soft else (150, 230, 170))
    txt21(panel, "Soft-water fish: tetras, rummynose, otos, corydoras.  Hard-water fish: guppies, killifish, cichlids.  Water changes pull GH and KH toward the tap (8 / 6).", 26, y0 + 268, "d", HUD_DIM)
    txt21(panel, "Heater (Y), filter sponge (F) and the glass (C) are still done from the tank.  M and P need the Mineral kit.", 26, y0 + 292, "d", HUD_DIM)


def _hub_history(panel, y0):
    spec = [("pop", (120, 200, 255), "Fish", "{:.0f}"), ("water", (110, 215, 140), "Water quality", "{:.0f}"),
            ("no3", (240, 200, 90), "Nitrate", "{:.0f}"), ("ph", (200, 150, 255), "pH", "{:.2f}"),
            ("gh", (255, 150, 150), "GH", "{:.1f}"), ("points", (255, 232, 140), "Points", "{:.0f}")]
    for i, (k, col, title, fmt) in enumerate(spec):
        chart21(panel, (26 + (i % 3) * 360, y0 + (i // 3) * 220, 340, 200), DASH[k], col, title, fmt)
    txt21(panel, "History covers this session and fills in about every ten seconds.", 26, y0 + 446, "d", HUD_DIM)


def live_weather_text():
    if not eco.realtime:
        return "turn on the real-time clock (O) to copy the weather outside"
    if not X.get("wx", True):
        return "off  (W switches it on)"
    if wx_ok():
        return f"{WX['place'] or 'your area'}: {WX['label']}, {WX['temp']:.0f}C, cloud {int(WX['cloud'] * 100)}%   (W switches it off)"
    return "offline: " + WX["err"] if WX["err"] and not WX["busy"] else "looking up the weather..."


def _hub_life(panel, y0):
    snails = sum(1 for c in crawlers if isinstance(c, (MysterySnail, Ramshorn)))
    rows = [("Snails", f"{snails}   (they boom when there is spare food)"), ("Shrimp", f"{len(shimps)}   (they breed in moss and carpets)"),
            ("Algae eaters", f"{sum(1 for f in fishes if isinstance(f, (Otocinclus, Pleco)))} fish"),
            ("Canopy", f"{int(eco.overgrown * 100)}% overgrown   (trim with D > TRIM)"),
            ("Weather", (f"{EV['name']}  until day {EV['until']}" if EV["name"] else "quiet")),
            ("Weathered", f"{X['evok']} events survived"), ("Fish of the week", X["fow"] or "chosen every 7th day"),
            ("Cat", "watching the tank tonight" if CAT["t"] > 0 else "asleep"),
            ("Live weather", live_weather_text())]
    for i, (a, b) in enumerate(rows):
        txt21(panel, a, 26, y0 + 34 * i, "h", (255, 232, 140))
        txt21(panel, b, 260, y0 + 34 * i + 2, "d")
    txt21(panel, "Events follow the season: spawning in spring, heat in summer, leaf fall in autumn, cold snaps in winter.", 26, y0 + 34 * len(rows) + 10, "d", HUD_DIM)


def _hub_guide(panel, y0):
    txt21(panel, "Tour: " + ("ON" if X["tut_on"] else "OFF") + "     T switches it " + ("off" if X["tut_on"] else "on and restarts it"), 26, y0, "h", (150, 230, 170) if X["tut_on"] else (200, 215, 232))
    for i, (text, key) in enumerate(TUT):
        done = key is None and not X["tut_on"] or (key is not None and key in TUTF) or (X["tut_on"] and i < X["tut"])
        txt21(panel, ("[x] " if done else "[ ] ") + text, 26, y0 + 40 + 30 * i, "d", (150, 230, 170) if done else (200, 215, 232))
    txt21(panel, "Controller: stick moves the pointer, A clicks, B back, X help, Y hub, LB shop, RB test kit, D-pad moves in panels, right trigger taps the glass.", 26, y0 + 40 + 30 * len(TUT) + 12, "d", HUD_DIM)
    txt21(panel, "Touch screens work as a mouse: tap to feed, long-press for the glass tap needs a right button, so use a controller or mouse for that.", 26, y0 + 40 + 30 * len(TUT) + 36, "d", HUD_DIM)


def draw_hub(surface):
    panel = begin_panel(1120, 640, f"Tank hub     cash {X['cash']}     points {X['points']}")
    x = 26
    for i, name in enumerate(HUB_TABS):
        on = i == HUB["tab"]
        r = pygame.Rect(x, 56, 150, 28)
        pygame.draw.rect(panel, (40, 90, 150) if on else (20, 40, 70), r, border_radius=8)
        txt21(panel, f"{i + 1} {name}", r.x + 14, r.y + 4, "h", (255, 255, 255) if on else (150, 175, 205))
        x += 160
    (_hub_gear, _hub_line, _hub_upkeep, _hub_history, _hub_life, _hub_guide)[HUB["tab"]](panel, 104)
    end_panel(surface, panel, "Left/Right or 1-6: tabs   Esc: close   (Del opens the hub)")


# ---- the world overlay: light shafts, debris, the moth, sleepers, the cat
SHAFT = {"surf": None}
TXT6 = {}


def _shaft_surface():
    h = int(SCREEN_HEIGHT * 0.85)
    sf = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
    for x0, w in ((0.10, 70), (0.30, 120), (0.55, 90), (0.78, 60)):
        for k, a in ((2.0, 10), (1.4, 12), (0.9, 14)):
            top = int(SCREEN_WIDTH * x0)
            ww = int(w * k)
            pygame.draw.polygon(sf, (190, 225, 255, a), [(top - ww // 2, 0), (top + ww // 2, 0), (top + ww // 2 + int(h * 0.3), h), (top - ww // 2 + int(h * 0.3), h)])
    return sf


def draw_world6(surface):
    if QUALITY[0] != "LOW":
        a = eco.daylight * (1.0 - eco.night) * (0.0 if (eco.lights == "OFF" or eco.power) else 1.0)
        if a > 0.08:
            if SHAFT["surf"] is None:
                SHAFT["surf"] = _shaft_surface()
            sf = SHAFT["surf"]
            sf.set_alpha(int(255 * a * (0.6 + 0.4 * math.sin(eco.t * 0.008)) * float(scape("light", "shafts", 1.0))))
            surface.blit(sf, (int((eco.clock - 0.5) * SCREEN_WIDTH * 0.35), WATER_TOP))
    for d in DEB:
        pygame.draw.circle(surface, (140, 124, 98), (int(d[0]), int(d[1])), 2 if d[4] > 3 else 1)
    n = min(DEBS[0], 60)
    for i in range(n):
        x = 30 + (i * 97 + 13 * (i % 7)) % (SCREEN_WIDTH - 60)
        pygame.draw.circle(surface, (112, 98, 76), (x, ground_y(x) - 1), 2)
    if eco.night > 0.45 and not PM["on"]:
        mx = SCREEN_WIDTH * 0.5 + math.sin(eco.t * 0.011) * SCREEN_WIDTH * 0.3
        my = WATER_TOP - 22 + math.sin(eco.t * 0.07) * 9
        wing = 2 + abs(math.sin(eco.t * 0.5)) * 6
        pygame.draw.ellipse(surface, (232, 228, 205), (mx - wing - 2, my - 3, wing, 6))
        pygame.draw.ellipse(surface, (232, 228, 205), (mx + 2, my - 3, wing, 6))
        pygame.draw.circle(surface, (120, 110, 90), (int(mx), int(my)), 2)
        if eco.t % 240 == 0:
            ripples.append([pygame.Vector2(mx, WATER_TOP + 2), 2.0, 30])
    if eco.night > 0.6 and not PM["on"]:
        z = TXT6.get("z")
        if z is None:
            z = TXT6["z"] = f21("s").render("z", True, (200, 220, 255))
        for f in fishes:
            if getattr(f, "sleepy", 0) > 0.55:
                surface.blit(z, (int(f.pos.x) + 10, int(f.pos.y) - 22 - (eco.t // 2 + f.id) % 24))


def draw_cat(surface):
    t = CAT["t"]
    if t <= 0 or PM["on"] or screensaver:
        return
    up = min(1.0, (900 - t) / 90.0, t / 90.0)
    dy = int((1.0 - up) * 220)
    base = SCREEN_HEIGHT - 10 + dy
    ink = (9, 10, 16)
    pygame.draw.ellipse(surface, ink, (-40, base - 90, 330, 200))
    pygame.draw.circle(surface, ink, (130, base - 110), 52)
    pygame.draw.polygon(surface, ink, [(90, base - 145), (96, base - 205), (128, base - 156)])
    pygame.draw.polygon(surface, ink, [(138, base - 156), (170, base - 205), (176, base - 140)])
    blink = (t // 7) % 40 == 0
    for ex in (112, 150):
        if blink:
            pygame.draw.line(surface, (230, 200, 90), (ex - 7, base - 112), (ex + 7, base - 112), 2)
        else:
            pygame.draw.ellipse(surface, (236, 206, 80), (ex - 8, base - 124, 16, 20))
            pygame.draw.ellipse(surface, ink, (ex - 2, base - 122, 4, 16))
    tail = [(250, base - 30 + int(math.sin(eco.t * 0.05 + i * 0.7) * 10), ) for i in range(1)]
    pygame.draw.lines(surface, ink, False, [(260 + i * 14, base - 20 - i * 8 + int(math.sin(eco.t * 0.06 + i * 0.6) * 10)) for i in range(6)], 12)


def draw_hud6(surface):
    if screensaver or current_state != STATE_AQUARIUM:
        return
    draw_cat(surface)
    if X["tut_on"] and UI21["panel"] is None and not PM["on"]:
        i = min(X["tut"], len(TUT) - 1)
        font = f21("h")
        img = font.render(f"Tour {i + 1}/{len(TUT)}:  {TUT[i][0]}", True, (235, 245, 255))
        box = pygame.Rect(0, 0, img.get_width() + 40, 40)
        box.midtop = (SCREEN_WIDTH // 2, 14)
        pygame.draw.rect(surface, (8, 20, 40), box, border_radius=10)
        pygame.draw.rect(surface, (120, 190, 230), box, 2, border_radius=10)
        surface.blit(img, img.get_rect(center=box.center))
    if HAND["f"] is not None:
        f = HAND["f"]
        pygame.draw.circle(surface, (255, 235, 160), (int(f.pos.x), int(f.pos.y)), int(34 * f.z) + 6, 2)
    if UI21["panel"] is not None or not eco.show_hud or PM["on"] or show_help or confirm_quit:
        return
    mp = pygame.Vector2(world_mouse(pygame.mouse.get_pos()))
    best, bd = None, 9999
    for f in fishes:
        if hasattr(f, "persona"):
            d = f.pos.distance_to(mp) - 30 * f.z
            if d < 14 and d < bd:
                best, bd = f, d
    if best is None:
        return
    f = best
    lines = [(f"{f.name} the {nice_name(f)}" + ("   FISH OF THE WEEK" if X["fow"] == f.name else ""), (255, 232, 140)),
             (f"{f.persona}: {PERSONA_TXT[f.persona]}", (210, 225, 240))]
    if f.friend is not None:
        lines.append((f"friend: {f.friend.name}", (130, 235, 160)))
    if f.rival is not None:
        lines.append((f"rival: {f.rival.name}", (255, 130, 120)))
    off = hardness_off(f)
    if off > 1.5:
        lines.append((f"unhappy with the hardness (GH {CHEM['gh']:.0f})", (255, 180, 130)))
    if f.sick:
        lines.append((DISEASES.get(getattr(f, "disease", "ich"), "sick"), (255, 160, 130)))
    font = hud_font()
    w = max(font.size(t)[0] for t, _ in lines) + 20
    box = make_panel(w, 12 + 17 * len(lines))
    for i, (txt, col) in enumerate(lines):
        box.blit(font.render(txt, True, col), (10, 6 + 17 * i))
    x = int(clamp(mp.x + 16, 4, SCREEN_WIDTH - w - 4))
    y = int(clamp(mp.y + 16, 4, SCREEN_HEIGHT - box.get_height() - 4))
    surface.blit(box, (x, y))
