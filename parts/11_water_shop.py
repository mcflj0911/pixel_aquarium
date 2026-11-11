# ---------------------------------------------------------------- 14: water chemistry and the nitrogen cycle
def chem_tick():
    c = CHEM
    n = sum(1 for f in fishes if hasattr(f, "family"))
    resting = sum(1 for p in pellets if p.pos.y >= ground_y(p.pos.x) - 6)
    c["nh3"] += 0.00015 * n + 0.0004 * resting
    fl = 0.4 + 0.6 * eco.filter + (0.3 if "filter" in X["owned"] else 0.0)
    if eco.power:
        fl *= 0.8 if "ups" in X["gear"] else 0.3
    fl *= 0.6 + 0.4 * EQ["media"]
    floor = 0.55 if c["done"] else 0.02
    c["b1"] = clamp(c["b1"] * (1.002 if c["nh3"] > 0.05 else 0.99995), floor, 1.0)
    c["b2"] = clamp(c["b2"] * (1.002 if c["no2"] > 0.05 else 0.99995), floor, 1.0)
    k1 = min(c["nh3"], 0.012 * c["b1"] * fl)
    c["nh3"] -= k1
    c["no2"] += k1
    k2 = min(c["no2"], 0.012 * c["b2"] * fl)
    c["no2"] -= k2
    c["no3"] += k2 * 15
    green = sum(1 for p in plants if p.species != "MossBall")
    c["no3"] = max(0.0, c["no3"] - 0.0004 * green * (1.6 if FERT["t"] > 0 else 1.0))
    c["nh3"] = min(8.0, c["nh3"])
    c["no2"] = min(8.0, c["no2"])
    c["no3"] = min(200.0, c["no3"])
    target = 7.3 - 0.006 * c["no3"] - (0.3 if "co2" in X["owned"] else 0.0)
    c["ph"] += (target - c["ph"]) * 0.02
    c["age"] += 1
    if not c["done"]:
        # cycled = both colonies exist and have kept ammonia and nitrite near zero for two minutes
        c["ok"] = c["ok"] + 1 if (c["b1"] > 0.1 and c["b2"] > 0.1 and c["nh3"] < 0.1 and c["no2"] < 0.2) else 0
    if not c["done"] and c["ok"] >= 120:
        c["done"], c["won"] = True, True
        c["b1"], c["b2"] = max(c["b1"], 0.6), max(c["b2"], 0.6)
        X["points"] += 10
        notify("The tank has cycled: both bacteria colonies are established! +10 points")
        play_sfx("chime", 0.6)
        save_prefs()
    tox = max(0.0, c["nh3"] - 0.4) + 0.8 * max(0.0, c["no2"] - 0.5) + 0.01 * max(0.0, c["no3"] - 80)
    if tox > 0:
        eco.water = clamp(eco.water - 0.12 * tox, 0.0, 100.0)
        for f in fishes:
            if hasattr(f, "stress"):
                f.stress = min(100.0, f.stress + 0.3 * tox)
        if "tox" not in eco.warned:
            eco.warned.add("tox")
            notify("Ammonia / nitrite / nitrate is high: do a water change (W), check the kit (;)", log=False)
    elif c["nh3"] < 0.2 and c["no2"] < 0.3:
        eco.warned.discard("tox")


def chem_water_change():
    WCOUNT[0] += 1
    for k, v in (("nh3", 0.6), ("no2", 0.6), ("no3", 0.65)):
        CHEM[k] *= v
    CHEM["ph"] += (7.2 - CHEM["ph"]) * 0.4
    CHEM["kh"] += (float(scape("water", "tap_kh", 6.0)) - CHEM["kh"]) * 0.4      # fresh tap water: KH 6, GH 8 (a scape can set its own)
    CHEM["gh"] += (float(scape("water", "tap_gh", 8.0)) - CHEM["gh"]) * 0.4
    del DEB[:]
    DEBS[0] = int(DEBS[0] * 0.4)
    for i in range(GLASS_COLS):
        HAIR[i] *= 0.9


def chem_rinse():
    CHEM["b1"] = max(0.55 if CHEM["done"] else 0.02, CHEM["b1"] * 0.8)
    CHEM["b2"] = max(0.55 if CHEM["done"] else 0.02, CHEM["b2"] * 0.8)


# ---------------------------------------------------------------- 12-13: fertiliser, hair algae, diatoms
def dose_fert():
    if FERT["t"] > 0:
        notify("Fertiliser is still in the water", log=False)
        return
    FERT["t"] = 7200
    CHEM["no3"] += 8
    X["ferts"] += 1
    play_sfx("bubble")
    notify("Fertiliser dosed: plants grow faster" + ("" if "co2" in X["owned"] else ", but algae will love it too"), log=True)


def algae_tick():
    lit = 0.0 if (eco.lights == "OFF" or eco.power) else ((1.0 - eco.night) if eco.lights == "SUN" else 1.0)
    co2 = "co2" in X["owned"]
    feed = 0.25 + clamp(CHEM["no3"] / 40.0, 0.0, 2.0) + (1.5 if FERT["t"] > 0 and not co2 else 0.0)
    rate = 0.004 * lit * feed
    for _ in range(2):
        i = random.randrange(GLASS_COLS)
        HAIR[i] = min(1.0, HAIR[i] + rate * random.random() * 3)
        if HAIR[i] > 0.4:
            j = i + random.choice((-1, 1))
            if 0 <= j < GLASS_COLS:
                HAIR[j] = min(1.0, HAIR[j] + 0.01)
    if lit == 0.0:
        for i in range(GLASS_COLS):
            HAIR[i] *= 0.998

    def col(x):
        return max(0, min(GLASS_COLS - 1, int(x / SCREEN_WIDTH * GLASS_COLS)))
    low = SCREEN_HEIGHT - SAND_HEIGHT - 90
    for s in shimps:
        if s.pos.y > low:
            HAIR[col(s.pos.x)] = max(0.0, HAIR[col(s.pos.x)] - 0.01)
    for sn in crawlers:
        HAIR[col(sn.x)] = max(0.0, HAIR[col(sn.x)] - 0.02)
    clean = 0.0006 * len(crawlers)
    for f in fishes:
        if isinstance(f, Otocinclus):
            HAIR[col(f.pos.x)] = max(0.0, HAIR[col(f.pos.x)] - 0.02)
            clean += 0.003
    if not CHEM["done"]:
        DIA[0] = min(1.0, DIA[0] + 0.0015 * (0.3 + lit))
    DIA[0] = max(0.0, DIA[0] - clean - (0.0015 if CHEM["done"] else 0.0))
    avg = sum(HAIR) / GLASS_COLS
    if avg > 0.3 and "hair" not in eco.warned:
        eco.warned.add("hair")
        notify("Hair algae is spreading: add shrimp, snails or otos, cut the lights, ease off the fertiliser", log=False)
    elif avg < 0.12:
        eco.warned.discard("hair")


def draw_algae_world(surface):
    if DIA[0] > 0.03:
        h = 150
        if F21.get("dia") is None:
            s = pygame.Surface((SCREEN_WIDTH, h), pygame.SRCALPHA)
            for i in range(h):
                pygame.draw.line(s, (122, 90, 38, int(120 * (i / h) ** 1.6)), (0, i), (SCREEN_WIDTH, i))
            F21["dia"] = s
        F21["dia"].set_alpha(int(255 * DIA[0]))
        surface.blit(F21["dia"], (0, SCREEN_HEIGHT - SAND_HEIGHT - h + 30))
    clk = eco.t * 0.03
    for i in range(GLASS_COLS):
        hv = HAIR[i]
        if hv < 0.12:
            continue
        x = (i + 0.5) * SCREEN_WIDTH / GLASS_COLS
        y = ground_y(x)
        for k in range(int(hv * 6) + 2):
            h = 22 + hv * 70 + k * 5
            bx = x + (k - 2) * 6
            pts = [(bx + math.sin(clk + i + k + j * 0.7) * j * 2.0, y + 4 - h * j / 5) for j in range(6)]
            pygame.draw.lines(surface, (126 + 24 * (k % 2), 176, 70), False, pts, 3)
            pygame.draw.lines(surface, (170, 206, 96), False, pts, 1)


# ---------------------------------------------------------------- 10: shop
def buy_item(i):
    if not 0 <= i < len(SHOP):
        return
    iid, name, cost, _ = SHOP[i]
    if iid != "oto" and iid in X["owned"]:
        notify(f"You already own the {name}", log=False)
        return
    if X["points"] < cost:
        notify(f"The {name} costs {cost} points (you have {X['points']})", log=False)
        return
    if iid == "oto":
        if len(fishes) >= FRAME_BUDGET - 3:
            notify("The tank is too full for more fish", log=False)
            return
        for _ in range(2):
            fishes.append(Otocinclus(random.randint(120, SCREEN_WIDTH - 120), SCREEN_HEIGHT - SAND_HEIGHT - 80))
    else:
        X["owned"].append(iid)
    X["points"] -= cost
    play_sfx("chime", 0.6)
    notify(f"Bought: {name}", log=True)
    save_prefs()


def shop_tick():
    own = X["owned"]
    if "filter" in own:
        eco.filter = min(1.0, eco.filter + 0.0008)
    if "magnet" in own:
        for i in range(GLASS_COLS):
            eco.glass[i] = max(0.0, eco.glass[i] - 0.0008)
    if "thermo" in own and not eco.power:
        eco.temp += (25.0 - eco.temp) * 0.05


# ---------------------------------------------------------------- 11: aquascapes
def load_user_scapes():
    try:
        with open(SCAPES_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return [s for s in data if isinstance(s, dict) and "name" in s and "seed" in s and isinstance(s.get("placed"), list)]
    except (OSError, ValueError):
        return []


def all_scapes():
    out = []
    for name, seed, items in SCAPE_BUILTIN:
        out.append({"name": name, "seed": seed, "placed": [[k, int(fr * SCREEN_WIDTH), 0.9] for k, fr in items]})
    return out + load_user_scapes()[-5:]


def apply_scape(sc):
    rebuild_world(int(sc["seed"]))
    placed.clear()
    if isinstance(sc.get("layout"), dict):
        layout_apply(sc["layout"])
        PM["rocks_dirty"] = True
        pm_finalize()
    for k, x, z in ([] if isinstance(sc.get("layout"), dict) else sc["placed"]):
        if k in ("ROCK", "DRIFTWOOD", "SWORD", "ROTALA", "LUDWIGIA", "DWARF", "CRYPT", "CLOVER", "MOSS", "CABOMBA", "HYGRO"):
            place_decor(k, float(x), float(z))
    build_cover()
    X["scapes"] += 1
    notify(f"Aquascape: {sc['name']}", log=True)
    save_prefs()


def save_scape():
    mine = load_user_scapes()
    mine.append({"name": f"My scape {len(mine) + 1}", "seed": world_seed, "placed": [[k, x, z] for k, x, z, _ in placed]})
    if LAYOUT["custom"]:
        mine[-1]["layout"] = layout_snapshot()
    try:
        with open(SCAPES_PATH, "w", encoding="utf-8") as fh:
            json.dump(mine[-20:], fh)
        notify(f"Saved as {mine[-1]['name']}", log=False)
    except OSError as err:
        notify(f"Could not save the scape: {err}", log=False)


# ---------------------------------------------------------------- 18: album and timelapse recorder
def album_load():
    try:
        with open(ALB_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return [a for a in data if isinstance(a, dict) and "file" in a]
    except (OSError, ValueError):
        return []


def album_add(name, score=0):
    items = album_load()
    items.append({"score": score, "file": name, "day": eco.day, "season": SEASONS[eco.season], "fish": len(fishes), "water": int(eco.water),
                  "when": time.strftime("%Y-%m-%d %H:%M")})
    try:
        with open(ALB_PATH, "w", encoding="utf-8") as fh:
            json.dump(items[-400:], fh)
    except OSError:
        pass


def rec_toggle():
    if REC["on"]:
        rec_stop()
    else:
        REC.update(on=True, frames=[], n=0, every=20)
        notify("Recording a timelapse clip (F12 to stop)", log=False)


def rec_capture(surface):
    if not REC["on"]:
        return
    REC["n"] += 1
    if REC["n"] % REC.get("every", 20):
        return
    w = 480
    h = int(w * SCREEN_HEIGHT / SCREEN_WIDTH)
    small = pygame.transform.smoothscale(surface, (w, h))
    REC["frames"].append((small.get_size(), pygame.image.tostring(small, "RGB")))
    if len(REC["frames"]) >= 400:
        rec_stop()


def _rec_save(name, frames):
    try:
        from PIL import Image
        ims = [Image.frombytes("RGB", sz, raw) for sz, raw in frames]
        ims[0].save(name, save_all=True, append_images=ims[1:], duration=100, loop=0)
    except Exception as err:   # no Pillow, disk full...: the game carries on
        print("timelapse clip not saved:", err)


def rec_stop():
    frames = REC["frames"]
    REC.update(on=False, frames=[], n=0)
    if len(frames) < 4:
        notify("Clip too short to save", log=False)
        return
    import threading
    os.makedirs("screenshots", exist_ok=True)
    name = time.strftime("screenshots/timelapse_%Y%m%d_%H%M%S.gif")
    threading.Thread(target=_rec_save, args=(name, frames), daemon=True).start()
    X["clips"] += 1
    notify(f"Timelapse clip saved: {name}", log=True)
    save_prefs()


# ---------------------------------------------------------------- 19: soundscapes
def build_soundscape():
    SND21["ready"] = True
    if pygame.mixer.get_init() is None:
        return
    try:
        import numpy as np
        freq, _, chans = pygame.mixer.get_init()
        n = freq * 4
        t = np.arange(n) / freq
        rng = np.random.default_rng(5)

        def mk(a):
            a = (np.clip(a, -1, 1) * 9000).astype(np.int16)
            if chans > 1:
                a = np.repeat(a[:, None], chans, axis=1)
            return pygame.mixer.Sound(buffer=np.ascontiguousarray(a).tobytes())
        rain = np.convolve(rng.standard_normal(n), np.ones(5) / 5, "same") * 0.9
        gate = ((t * 2) % 1.0 < 0.4) & (np.sin(2 * np.pi * 28 * t) > 0)
        crick = np.sin(2 * np.pi * 4300 * t) * gate * 0.5 + np.sin(2 * np.pi * 4700 * t) * (np.roll(gate, freq // 3)) * 0.35
        room = np.convolve(rng.standard_normal(n), np.ones(160) / 160, "same") * 9 + np.sin(2 * np.pi * 60 * t) * 0.12 + np.sin(2 * np.pi * 120 * t) * 0.05
        pygame.mixer.set_reserved(3)
        SND21["snd"] = [mk(rain), mk(crick), mk(room)]
        SND21["chan"] = [pygame.mixer.Channel(i) for i in range(3)]
        for ch, snd in zip(SND21["chan"], SND21["snd"]):
            ch.set_volume(0.0)
            ch.play(snd, loops=-1)
    except Exception as err:
        print("soundscape unavailable:", err)
        SND21["chan"] = []


def sound_tick():
    on = X["sound"] == "AUTO"
    if on and not SND21["ready"]:
        build_soundscape()
    if not SND21["chan"]:
        return
    storm = eco.event == "THUNDERSTORM"
    night = clamp((eco.night - 0.2) / 0.6)
    target = [0.5 if storm else 0.0, 0.0 if storm else 0.3 * night, 0.14 * (1.0 - 0.3 * night)]
    master = 0.0 if (is_muted or not on) else VOL["master"] * VOL["fx"]
    for i, ch in enumerate(SND21["chan"]):
        SND21["cur"][i] += (target[i] * master - SND21["cur"][i]) * 0.15
        try:
            ch.set_volume(max(0.0, SND21["cur"][i]))
        except pygame.error:
            pass


def cycle_sound():
    X["sound"] = "OFF" if X["sound"] == "AUTO" else "AUTO"
    notify("Soundscape: " + X["sound"] + ("  (rain in storms, crickets at night, room hum)" if X["sound"] == "AUTO" else ""), log=False)
    save_prefs()



# ---------------------------------------------------------------- care: carriers, sales, weekly chores, challenges, raids
CH = {"day": None, "wipes": 0, "rinses": 0, "wc": 0, "kit": False}
WCOUNT = [0]
RAID = {"t": -1, "kills": 0, "warned": False}
CHALLENGES = [
    ("mix", "Community", "Keep 6 or more species together for 8 days in a row", 30, 15),
    ("hands", "Hands off", "No water change for 10 days, and the water still 60+ at the end", 10, 12),
    ("line", "Master breeder", "Raise a third-generation fish within 25 days", 25, 18),
    ("boom", "Fry boom", "Have 12 fish hatch within 20 days", 20, 14),
]


def carrier_tick(f):
    """A recovered fish still carries the sickness for a while: stress and foul water can bring it back, and it can pass it on."""
    c = getattr(f, "carrier", 0)
    if c <= 0:
        return
    f.carrier = c - 1
    if f.sick or getattr(f, "immune", 0) > 0 or getattr(f, "qpos", None) is not None:
        return
    if f.stress > 55 and eco.water < 65 and random.random() < 0.0004:
        infect(f)
        X["relapses"] += 1
        story(f, "The sickness came back")
        return
    if eco.water < 70 and eco.t % 120 == 0 and random.random() < 0.02:
        for o in fishes:
            if (o is not f and hasattr(o, "sick") and not o.sick and getattr(o, "immune", 0) <= 0 and not getattr(o, "qpos", None)
                    and o.pos.distance_squared_to(f.pos) < 70 * 70):
                infect(o)
                break


def sale_price(f):
    gk = f.gene_key
    p = 3 + 5 * abs(gk[0]) + 3 * (getattr(f, "gen", 1) - 1)
    if hasattr(f, "lace") and f.lace_on():
        p += 6
    rec = strains.get(f"{type(f).__name__}|{gk[0]}|{gk[1]}")
    if rec is not None and rec[1] <= 2:
        p += 4      # a rare strain
    return int(max(2, p))


def sellable():
    out = [f for f in fishes if hasattr(f, "persona") and f.growth >= 1.0 and f.alive and not f.sick and not f.fav
           and not isinstance(f, Predator) and getattr(f, "gen", 1) >= 2]
    out.sort(key=sale_price, reverse=True)
    return out[:9]


def sell_fish(i):
    lst = sellable()
    if not 0 <= i < len(lst):
        return
    f = lst[i]
    price = sale_price(f)
    story(f, f"Sold for {price} points")
    fishes.remove(f)
    if eco.selected is f:
        eco.selected = None
    X["points"] += price
    X["cash"] += price
    X["sold"] += 1
    play_sfx("chime", 0.5)
    notify(f"Sold {f.name} the {nice_name(f)} for {price} points", log=True)
    save_prefs()


def chore_status():
    return [("Water change (W)", WCOUNT[0] > CH["wc"]), ("Rinse the filter (F)", stats["rinses"] > CH["rinses"]),
            ("Wipe the glass (C)", stats["wipes"] > CH["wipes"]), ("Check the test kit (;)", CH["kit"])]


def chore_tick():
    if CH["day"] is None:
        CH.update(day=eco.day, wipes=stats["wipes"], rinses=stats["rinses"], wc=WCOUNT[0], kit=False)
        return
    if eco.day - CH["day"] < 7:
        return
    if all(ok for _, ok in chore_status()):
        X["streak"] += 1
        pts = 4 + min(X["streak"], 6)
        X["points"] += pts
        notify(f"Weekly chores done: {X['streak']} week streak, +{pts} points", log=True)
        play_sfx("chime", 0.5)
    else:
        if X["streak"]:
            notify("A chore was missed this week: the streak is over", log=False)
        X["streak"] = 0
    CH.update(day=eco.day, wipes=stats["wipes"], rinses=stats["rinses"], wc=WCOUNT[0], kit=False)
    save_prefs()


def chal_start(i):
    if not 0 <= i < len(CHALLENGES):
        return
    if X["chal"]:
        notify("Finish or abandon the current challenge first (press its number again to abandon)", log=False)
        return
    cid = CHALLENGES[i][0]
    X["chal"] = {"id": cid, "start": eco.day, "wc": WCOUNT[0], "births": eco.births, "since": eco.day}
    notify(f"Challenge started: {CHALLENGES[i][1]}", log=True)
    save_prefs()


def chal_info(cid):
    return next(c for c in CHALLENGES if c[0] == cid)


def chal_progress(st):
    """(state, text): state is 'run', 'won' or 'lost'."""
    cid, day = st["id"], eco.day
    left = chal_info(cid)[3] - (day - st["start"])
    if cid == "mix":
        species = len({type(f) for f in fishes if hasattr(f, "persona") and not isinstance(f, Predator)})
        held = day - st["since"]
        if held >= 8:
            return "won", "done"
        if left < 0:
            return "lost", "time ran out"
        return "run", f"{species} species now, held {held}/8 days, {left} days left"
    if cid == "hands":
        if WCOUNT[0] > st["wc"]:
            return "lost", "you changed the water"
        if day - st["start"] >= 10:
            return ("won", "done") if eco.water >= 60 else ("lost", "the water went bad")
        return "run", f"{10 - (day - st['start'])} days to go, water {int(eco.water)}%"
    if cid == "line":
        best = max([getattr(f, "gen", 1) for f in fishes] + [1])
        if best >= 3:
            return "won", "done"
        if left < 0:
            return "lost", "time ran out"
        return "run", f"best generation {best}/3, {left} days left"
    n = eco.births - st["births"]
    if n >= 12:
        return "won", "done"
    if left < 0:
        return "lost", "time ran out"
    return "run", f"{n}/12 hatched, {left} days left"


def chal_tick():
    st = X["chal"]
    if not st:
        return
    if st["id"] == "mix":
        species = len({type(f) for f in fishes if hasattr(f, "persona") and not isinstance(f, Predator)})
        if species < 6:
            st["since"] = eco.day
    state, _ = chal_progress(st)
    if state == "run":
        return
    c = chal_info(st["id"])
    if state == "won":
        X["points"] += c[4]
        X["chal_won"].append(c[0])
        notify(f"Challenge won: {c[1]}! +{c[4]} points", log=True)
        play_sfx("chime", 0.6)
    else:
        notify(f"Challenge failed: {c[1]}", log=True)
    X["chal"] = {}
    save_prefs()


def raid_tick():
    """With predators enabled, a raid now and then: a warning, then the hunters get hungry. Hiding places decide how it goes."""
    if not PRED["on"] or not predators or eco.day < 3 or unattended():
        RAID["t"] = -1
        return
    if RAID["t"] < 0:
        if eco.t % 600 == 0 and random.random() < 0.02:
            RAID["t"] = eco.t + 1200
            RAID["kills"] = eco.kills
            RAID["warned"] = True
            notify("Shadows are circling the tank: the hunters are about to get hungry. Hiding places (Home) help.", log=True)
        return
    if eco.t == RAID["t"] or (eco.t > RAID["t"] and RAID["warned"]):
        for p in predators:
            p.hunger = max(p.hunger, 88.0)
        RAID["warned"] = False
        RAID["end"] = eco.t + 3000
    if eco.t > RAID.get("end", 10 ** 9):
        lost = eco.kills - RAID["kills"]
        X["raids"] += 1
        if lost == 0:
            X["points"] += 8
            notify("The raid is over and nobody was caught! +8 points", log=True)
            play_sfx("chime", 0.5)
        else:
            notify(f"The raid is over: {lost} fish lost", log=True)
        RAID["t"] = -1
        RAID.pop("end", None)


def draw_care_panels(surface):
    p = UI21["panel"]
    if p == "sell":
        lst = sellable()
        panel = begin_panel(860, 130 + 34 * max(1, len(lst)), f"Sell fish   {X['points']} points")
        if not lst:
            txt21(panel, "Nothing to sell yet: bred fish (generation 2+) that are grown, healthy and not starred.", 26, 70)
        for i, f in enumerate(lst):
            y = 70 + 34 * i
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, f"{f.name} the {nice_name(f)}", 62, y + 4, "h", (255, 232, 140))
            txt21(panel, f"gen {getattr(f, 'gen', 1)}   {gene_text(f)}", 380, y + 6, "d", HUD_DIM)
            txt21(panel, f"{sale_price(f)} pts", 760, y + 4, "h", (235, 245, 255))
        end_panel(surface, panel, "1-9 sell   Esc to close   (rare and well-bred strains sell for more; starred fish are never listed)")
    elif p == "care":
        panel = begin_panel(900, 150 + 40 * len(CHALLENGES) + 120, f"Care and challenges   streak {X['streak']}")
        txt21(panel, "This week's chores", 26, 64, "h", (255, 232, 140))
        for i, (name, ok) in enumerate(chore_status()):
            x = 26 + (i % 2) * 420
            y = 92 + (i // 2) * 26
            pygame.draw.rect(panel, (90, 210, 140) if ok else (70, 90, 120), (x, y + 2, 16, 16), 0 if ok else 2, border_radius=3)
            txt21(panel, name, x + 26, y, "d", (200, 215, 232))
        days = 7 - (eco.day - (CH["day"] if CH["day"] is not None else eco.day))
        txt21(panel, f"{days} days left this week. Finish all four for streak points.", 26, 148, "d", HUD_DIM)
        txt21(panel, "Challenges", 26, 184, "h", (255, 232, 140))
        st = X["chal"]
        for i, (cid, title, desc, _d, reward) in enumerate(CHALLENGES):
            y = 212 + 40 * i
            active = bool(st) and st["id"] == cid
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, title + (f"   (won x{X['chal_won'].count(cid)})" if cid in X["chal_won"] else ""), 62, y, "h",
                  (150, 230, 170) if active else (200, 215, 232))
            txt21(panel, chal_progress(st)[1] if active else desc, 62, y + 20, "d", (150, 230, 170) if active else HUD_DIM)
            txt21(panel, f"+{reward} pts", 800, y + 4, "h", (235, 245, 255))
        end_panel(surface, panel, "1-4 start a challenge (again to abandon)   Esc to close")
