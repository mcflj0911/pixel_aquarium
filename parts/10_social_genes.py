# ======================================================================================================================
# fw21: the long-term tank - personalities, friendships, life stories, more genes, requests, a genetic show,
# water chemistry, algae kinds, fertiliser, disease kinds, an equipment shop, aquascapes, album and timelapse,
# soundscapes and a statistics dashboard.
# ======================================================================================================================
F21 = {}


def f21(kind):
    if "t" not in F21:
        F21["t"] = pygame.font.SysFont("Arial", 26, bold=True)
        F21["h"] = pygame.font.SysFont("Arial", 17, bold=True)
        F21["d"] = pygame.font.SysFont("Arial", 14)
        F21["s"] = pygame.font.SysFont("Arial", 12)
    return F21[kind]


UI21 = {"panel": None, "web": False, "rename": None, "mem": False, "page": 0, "judge": None}
PERSONAS = ("greedy", "shy", "bossy", "explorer", "calm")
PERSONA_TXT = {"greedy": "first to every meal", "shy": "hides, stays low", "bossy": "shoves other fish about",
               "explorer": "roams the whole tank", "calm": "hard to rattle"}
DISEASES = {"ich": "white spot (ich)", "finrot": "fin rot", "swim": "swim bladder trouble"}
FIN_NAMES = ("round", "delta", "long")
CHEM = {"nh3": 0.0, "no2": 0.0, "no3": 6.0, "ph": 7.1, "b1": 0.04 if NEWTANK["on"] else 1.0,
        "b2": 0.04 if NEWTANK["on"] else 1.0, "done": not NEWTANK["on"], "won": False, "age": 0, "ok": 0,
        "kh": 6.0, "gh": 8.0}
for _k in ("ph", "kh", "gh"):    # a scape can start the tank at its own water values
    if scape("water", _k) is not None:
        CHEM[_k] = float(scape("water", _k))
HAIR = [0.0] * GLASS_COLS
DIA = [0.0]
FERT = {"t": 0}
REQ = {"cur": None, "next": 2}
SHOWR = {"rows": [], "day": 0}
DASH = {k: deque(maxlen=240) for k in ("pop", "water", "births", "deaths", "no3", "temp", "ph", "gh", "kh", "points", "cash")}
WEEK = {"day": 1, "births": 0, "deaths": 0, "reqs": 0, "water": []}
REC = {"on": False, "frames": [], "n": 0}
ALB_PATH = os.path.join("screenshots", "album.json")
ALB_THUMBS = {}
SCAPES_PATH = "aquarium_scapes.json"
SND21 = {"ready": False, "chan": [], "snd": [], "cur": [0.0, 0.0, 0.0]}

SHOP = [("filter", "Canister filter", 30, "The filter clogs far slower and cleans harder"),
        ("magnet", "Glass magnet", 25, "Algae film on the glass grows about half as fast"),
        ("thermo", "Thermostat", 20, "Holds the water close to 25C whatever the room does"),
        ("co2", "CO2 diffuser", 35, "Plants grow faster, and fertiliser stops feeding algae"),
        ("uv", "UV steriliser", 40, "Disease spreads far less and sick fish recover sooner"),
        ("oto", "Otocinclus pair", 15, "Two algae eaters join the tank (repeatable)"),
        ("hospital", "Hospital tank", 25, "Fish in quarantine (I) recover twice as fast")]

SCAPE_BUILTIN = [
    ("Jungle", 11, [("CABOMBA", .10), ("LUDWIGIA", .22), ("SWORD", .34), ("HYGRO", .50), ("ROTALA", .62), ("CRYPT", .74), ("CABOMBA", .88), ("DRIFTWOOD", .45)]),
    ("Zen rocks", 23, [("ROCK", .20), ("ROCK", .34), ("DRIFTWOOD", .62), ("ROCK", .78), ("MOSS", .27), ("MOSS", .70), ("DWARF", .48), ("DWARF", .54)]),
    ("Meadow", 37, [("DWARF", .12), ("DWARF", .22), ("DWARF", .32), ("DWARF", .55), ("DWARF", .66), ("CLOVER", .42), ("CLOVER", .80), ("MOSS", .90)]),
    ("Open water", 53, [("SWORD", .08), ("CRYPT", .16), ("ROCK", .30), ("SWORD", .92), ("CRYPT", .84), ("HYGRO", .96)])]


# ---------------------------------------------------------------- panels, fonts
def set_panel(name):
    global show_help, show_goals, show_strains
    UI21["panel"] = None if UI21["panel"] == name else name
    if UI21["panel"]:
        show_help = show_goals = show_strains = False
    UI21["page"] = 0
    if UI21["panel"] == "test":
        CH["kit"] = True


def begin_panel(w, h, title):
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 20, 40, 240), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
    panel.blit(f21("t").render(title, True, (235, 245, 255)), (26, 18))
    return panel


def end_panel(surface, panel, hint="Esc to close"):
    panel.blit(f21("d").render(hint, True, (150, 175, 200)), (26, panel.get_height() - 26))
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    surface.blit(dim, (0, 0))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))


def txt21(panel, text, x, y, kind="d", col=(200, 215, 232)):
    panel.blit(f21(kind).render(text, True, col), (x, y))


# ---------------------------------------------------------------- 1-5: personalities, friends, names, stories
def story(f, text):
    bio = getattr(f, "bio", None)
    if bio is None:
        return
    if len(bio) >= 16:
        del bio[2]
    bio.append((eco.day, text))


def ensure_life(f):
    if hasattr(f, "persona"):
        return
    f.persona = random.choice(PERSONAS)
    if f.persona == "shy":
        f.bravery = min(f.bravery, 0.3)
    elif f.persona == "bossy":
        f.bravery = max(f.bravery, 0.7)
    f.fav = False
    f.friend = f.rival = None
    f.meet = f.mourn = f.rival_t = f.fav_cd = 0
    f.xt, f.xt_t = None, 0
    f.bio = []
    f.born_day = eco.day - int(f.age // DAY_LENGTH)
    f._sk = f.sick
    f._elder = False
    if not hasattr(f, "gh") and not hasattr(f, "hl"):
        f.hl = random.gauss(0.0, 0.35)    # a colour line gene for every species that is not a guppy
    if not hasattr(f, "gen"):
        f.gen = 1
    story(f, f"Hatched on day {eco.day}" if f.age < 900 else "Joined the tank")


def pick_disease(f):
    w = {"ich": 6 if eco.temp < 24.5 else 1,
         "finrot": 6 if (eco.water < 55 or CHEM["nh3"] > 0.4) else 1,
         "swim": 6 if (eco.cloud > 0.35 or f.hunger < 8) else 1}
    return random.choices(list(w), list(w.values()))[0]


def disease_effects(f):
    d = getattr(f, "disease", "ich")
    if "uv" in X["owned"]:
        f.sick_t -= 0.25
    if d == "ich":
        if eco.temp >= 28.0:
            f.sick_t -= 0.7      # heat speeds up the parasite's life cycle: it drops off sooner
        elif eco.temp < 24.0:
            f.sick_t += 0.15
    elif d == "finrot":
        if eco.water >= 80 and CHEM["nh3"] < 0.3:
            f.sick_t -= 0.6      # clean water lets the fins regrow
        elif eco.water < 50:
            f.sick_t += 0.25
    elif d == "swim":
        f.apply_force(pygame.Vector2(0, 0.025))     # it can't hold its depth
        if 25 < f.hunger < 70:
            f.sick_t -= 0.6      # a short fast lets the bladder settle
        elif f.hunger < 12:
            f.sick_t += 0.2


def fish_life(f):
    """Per-fish extras, run right after prey_social: ageing, personality, friends, rivals, grief, disease."""
    if not hasattr(f, "family") or not f.alive:
        return
    ensure_life(f)
    carrier_tick(f)
    t, pos, pers = eco.t, f.pos, f.persona
    key = (t + f.id) % 30
    lf = f.life_frac()
    if lf > 0.8:
        f.max_speed *= 0.82                 # elders slow down (and their colours are already washed out)
        if not f._elder:
            f._elder = True
            story(f, "Grew old and slow")
    if f.mourn > 0:
        f.mourn -= 1
        f.max_speed *= 0.6
        f.stress = min(100.0, f.stress + 0.01)
    if f.sick != f._sk:
        f._sk = f.sick
        story(f, f"Fell ill: {DISEASES.get(getattr(f, 'disease', 'ich'), 'a sickness')}" if f.sick else "Recovered")
    if f.sick:
        disease_effects(f)
    if f.growth < 1.0:
        return
    if pers == "greedy" and f.hunger > 20 and t % 3 == 0 and pellets:
        best, bd = None, 380 * 380
        for p in pellets:
            d2 = pos.distance_squared_to(p.pos)
            if d2 < bd:
                best, bd = p, d2
        if best is not None:
            f.apply_force(unit(best.pos - pos) * 0.12)
        f.hunger = min(100.0, f.hunger + 0.012)
    elif pers == "shy" and hasattr(f, "prefer_depth"):
        f.prefer_depth(lane(0.5), lane(0.92), 0.002)
    elif pers == "calm":
        f.fear *= 0.985
        f.stress = max(0.0, f.stress - 0.02)
    elif pers == "explorer":
        if f.xt is None or f.xt_t <= 0:
            if random.random() < 0.004:
                f.xt = pygame.Vector2(random.uniform(80, SCREEN_WIDTH - 80), random.uniform(WATER_TOP + 60, SCREEN_HEIGHT - SAND_HEIGHT - 40))
                f.xt_t = 420
        else:
            f.xt_t -= 1
            d = f.xt - pos
            if d.length_squared() < 3600:
                f.xt_t = 0
            else:
                f.apply_force(unit(d) * 0.03)
    if pers == "bossy" and key == 0:
        for o in fishes:
            if o is f or not hasattr(o, "persona") or o.growth < 1.0:
                continue
            if pos.distance_squared_to(o.pos) < 6400:
                if o.persona == "bossy" and o is not f.partner and f.rival is None and o.rival is None and random.random() < 0.25:
                    f.rival, o.rival = o, f
                    f.rival_t = o.rival_t = 3600
                    story(f, f"Fell out with {o.name}")
                    story(o, f"Fell out with {f.name}")
                elif o is not f.friend and o is not f.partner and o.persona != "bossy":
                    o.apply_force(unit(o.pos - pos) * 0.5)
                    o.stress = min(100.0, o.stress + 0.8)
                break
    r = f.rival
    if r is not None:
        f.rival_t -= 1
        if f.rival_t <= 0 or not r.alive or r.rival is not f:
            f.rival = None
        else:
            d = r.pos - pos
            if d.length_squared() < 180 * 180:
                f.apply_force(unit(d) * 0.03 * (1 if f.bravery >= r.bravery else -1))
                f.stress = min(100.0, f.stress + 0.01)
    fr = f.friend
    if fr is not None:
        if not fr.alive:
            f.friend = None
        else:
            d = fr.pos - pos
            dist = d.length()
            if dist > 120:
                f.apply_force(d / dist * min(0.02, 0.0001 * (dist - 120)))
    elif key == 1:
        near = None
        for o in fishes:
            if (o is not f and type(o) is type(f) and getattr(o, "friend", 1) is None and o.growth >= 1.0 and o is not f.rival
                    and o is not f.partner and pos.distance_squared_to(o.pos) < 8100):
                near = o
                break
        if near is not None:
            f.meet += 30
            if f.meet >= 1200:
                f.friend, near.friend = near, f
                f.meet = near.meet = 0
                story(f, f"Became friends with {near.name}")
                story(near, f"Became friends with {f.name}")
                notify(f"{f.name} and {near.name} have become friends", log=False)
        else:
            f.meet = max(0, f.meet - 15)


def record_death(f, cause=None):
    if not hasattr(f, "persona"):
        return
    stats["deaths"] = stats.get("deaths", 0) + 1
    if cause is None:
        if f.sick:
            cause = "illness"
        elif f.age >= f.lifespan * 0.95:
            cause = "old age"
        elif f.hunger >= 98:
            cause = "hunger"
        elif eco.water < 40:
            cause = "poor water"
        else:
            cause = "unknown causes"
    if f.growth < 1.0 and not f.fav:
        return    # fry come and go; the memorial is for grown fish
    story(f, f"Died: {cause}")
    X["memorial"].append({"name": f.name, "cls": nice_name(f), "days": max(1, int(f.age // DAY_LENGTH)), "cause": cause,
                          "day": eco.day, "persona": f.persona, "gen": getattr(f, "gen", 1),
                          "note": f.bio[-2][1] if len(f.bio) > 1 else ""})
    del X["memorial"][:-80]
    fr = f.friend
    if fr is not None and fr.alive and fr is not f:
        fr.friend = None
        fr.mourn = 2400
        story(fr, f"Mourned {f.name}")
        add_emote(fr, "..")
        notify(f"{fr.name} is mourning {f.name}", log=False)
    if f.rival is not None:
        f.rival.rival = None
    save_prefs()


def fish_extra(f):
    ensure_life(f)
    d = {"persona": f.persona, "fav": f.fav, "bio": f.bio[-16:], "born": f.born_day, "gen": getattr(f, "gen", 1),
         "friend": f.friend.name if f.friend is not None else None, "disease": getattr(f, "disease", "ich")}
    if hasattr(f, "hl"):
        d["hl"] = f.hl
    if getattr(f, "hyb", None):
        d["hyb"] = f.hyb
    if hasattr(f, "lace"):
        d.update(lace=list(f.lace), sheen=f.sheen, fin=f.fin)
    return d


def fish_extra_apply(f, d):
    if not isinstance(d, dict):
        return
    try:
        ensure_life(f)
        if d.get("persona") in PERSONAS:
            f.persona = d["persona"]
        bio = [tuple(b) for b in d.get("bio", []) if isinstance(b, (list, tuple)) and len(b) == 2]
        if bio:
            f.bio = bio
        f.fav = bool(d.get("fav"))
        f.born_day = int(d.get("born", f.born_day))
        if d.get("disease") in DISEASES:
            f.disease = d["disease"]
        f._friend_name = d.get("friend")
        if not hasattr(f, "gh"):
            f.gen = int(d.get("gen", 1))
            if "hl" in d:
                f.hl = clamp(float(d["hl"]), -2.4, 2.4)
        h = d.get("hyb")
        if isinstance(h, dict) and all(k in h for k in ("from", "w", "m", "f", "fm", "ff")):
            f.hyb = {"from": str(h["from"]), "w": clamp(float(h["w"]), 0.0, 0.9), "cls": h.get("cls"),
                     "gen": int(h.get("gen", 1)), "fixed": bool(h.get("fixed", False)),
                     **{k: [int(v) for v in h[k]][:3] for k in ("m", "f", "fm", "ff")}}
        if hasattr(f, "lace"):
            lc = d.get("lace")
            if isinstance(lc, list) and len(lc) == 2:
                f.lace = [bool(lc[0]), bool(lc[1])]
            f.sheen = clamp(float(d.get("sheen", f.sheen)))
            f.fin = int(d.get("fin", f.fin)) % 3
    except (TypeError, ValueError):
        pass


def relink_friends():
    by = {f.name: f for f in fishes if hasattr(f, "persona")}
    for f in fishes:
        nm = getattr(f, "_friend_name", None)
        if nm and nm in by and by[nm] is not f:
            f.friend = by[nm]


# ---------------------------------------------------------------- 6-7: genes
def inherit_extra(kid, m, f):
    """Guppy lace is recessive (two copies needed, so it can skip generations); sheen blends; fin shape is picked from a parent."""
    pm, pf = getattr(m, "lace", [False, False]), getattr(f, "lace", [False, False])
    kid.lace = [random.choice(pm), random.choice(pf)]
    for i in (0, 1):
        if random.random() < 0.015:
            kid.lace[i] = not kid.lace[i]
    kid.sheen = clamp((getattr(m, "sheen", 0.5) + getattr(f, "sheen", 0.5)) / 2 + random.gauss(0, 0.18))
    kid.fin = random.choice((getattr(m, "fin", 0), getattr(f, "fin", 0))) if random.random() > 0.08 else random.choice((0, 1, 2))


def inherit_line(kid, parents):
    """Egg-layers (tetras, cichlids, bettas...) pass a colour line down; breeding the same shift again builds a strain."""
    try:
        m, f = parents
    except (TypeError, ValueError):
        return
    kid.hl = clamp((getattr(m, "hl", 0.0) + getattr(f, "hl", 0.0)) / 2 + random.gauss(0, 0.45), -2.4, 2.4)
    kid.gen = max(getattr(m, "gen", 1), getattr(f, "gen", 1)) + 1
    record_strain(kid, True)


def gene_text(f):
    if hasattr(f, "lace"):
        lace = "lace" if f.lace_on() else ("lace carrier" if any(f.lace) else "no lace")
        gk = f.gene_key
        return f"hue {gk[0]:+d}  tail {gk[1]:+d}  {lace}  sheen {int(f.sheen * 100)}%  {FIN_NAMES[f.fin]} fins"
    if hasattr(f, "hl"):
        hy = getattr(f, "hyb", None)
        return (f"colour line {f.gene_key[0]:+d}   gen {getattr(f, 'gen', 1)}"
                + (f"   hybrid: {int(hy['w'] * 100)}% {hy['from']}" + (" (stable strain)" if hy.get("fixed") else "") if hy else "")
                + (f"   {'boss' if f.dom else ''}" if getattr(f, "dom", False) else "")
                + ("   holding eggs" if getattr(f, "brood", None) is not None else ""))
    return ""


# ---------------------------------------------------------------- 8: breeding requests
def hue_word(h):
    return ("much " if abs(h) > 1 else "") + ("greener/bluer" if h > 0 else "redder")


def new_request():
    gup = sorted({type(f) for f in fishes if isinstance(f, GuppyBase)}, key=lambda c: c.__name__)
    oth = sorted({type(f) for f in fishes if hasattr(f, "hl") and not isinstance(f, Predator)
                  and sum(1 for g in fishes if type(g) is type(f)) >= 2}, key=lambda c: c.__name__)
    r = None
    if gup and (not oth or random.random() < 0.75):
        c = random.choice(gup)
        kind = random.choice(("hue", "hue", "tail", "both", "lace", "fin"))
        h = random.choice((-1, 1, -1, 1, 2, -2))
        r = {"cls": c.__name__, "hue": 0, "tail": 0, "lace": 0, "fin": 0}
        if kind == "hue":
            r.update(hue=h, text=f"{nice_name(c)} shifted {hue_word(h)}", reward=6 * abs(h))
        elif kind == "tail":
            r.update(tail=1, text=f"{nice_name(c)} with a long fan tail", reward=7)
        elif kind == "both":
            r.update(hue=h, tail=1, text=f"{nice_name(c)} {hue_word(h)} with a long fan tail", reward=8 + 6 * abs(h))
        elif kind == "lace":
            r.update(lace=1, text=f"Lace-pattern {nice_name(c)} (breed two carriers)", reward=16)
        else:
            fn = random.choice((1, 2))
            r.update(fin=fn, text=f"{nice_name(c)} with {FIN_NAMES[fn]} fins", reward=9)
        r["swatch"] = hue_shift(getattr(c, "male_color", (120, 170, 210)), r["hue"])
    elif oth:
        c = random.choice(oth)
        h = random.choice((-1, 1))
        r = {"cls": c.__name__, "hue": h, "tail": 0, "lace": 0, "fin": 0, "reward": 8, "text": f"{nice_name(c)} line shifted {hue_word(h)}",
             "swatch": hue_shift(getattr(c, "male_color", (120, 170, 210)), h)}
    if r:
        r["due"] = eco.day + 10
    return r


def req_match(r):
    for f in fishes:
        if (type(f).__name__ != r["cls"] or not hasattr(f, "persona") or f.growth < 1.0 or getattr(f, "gen", 1) < 2
                or f.sick or not f.alive):
            continue
        gk = f.gene_key
        if r["hue"] and gk[0] * (1 if r["hue"] > 0 else -1) < abs(r["hue"]):
            continue
        if r["tail"] and gk[1] < 1:
            continue
        if r["lace"] and not (hasattr(f, "lace") and f.lace_on()):
            continue
        if r["fin"] and getattr(f, "fin", 0) != r["fin"]:
            continue
        return f
    return None


def request_tick():
    r = REQ["cur"]
    if r is None:
        if eco.day >= REQ["next"] and eco.t % 300 == 0:
            REQ["cur"] = new_request()
            if REQ["cur"]:
                notify("New breeding request: " + REQ["cur"]["text"], log=False)
            else:
                REQ["next"] = eco.day + 1
        return
    if eco.t % 120:
        return
    f = req_match(r)
    if f is not None:
        X["points"] += r["reward"]
        X["reqs"] += 1
        WEEK["reqs"] += 1
        story(f, f"Filled a breeding request (+{r['reward']} points)")
        notify(f"Request done with {f.name}! +{r['reward']} points", log=True)
        play_sfx("chime", 0.6)
        REQ["cur"], REQ["next"] = None, eco.day + 1
        save_prefs()
    elif eco.day > r["due"]:
        notify("The breeding request expired", log=False)
        REQ["cur"], REQ["next"] = None, eco.day + 2


# ---------------------------------------------------------------- 9: genetic show
def show_score(f):
    gk = f.gene_key
    s = 8.0 * abs(gk[0])
    if hasattr(f, "lace"):
        s += 6.0 * max(0, gk[1]) + 10.0 * f.sheen + (14.0 if f.lace_on() else 0.0) + (5.0 if f.fin else 0.0)
    s += 0.12 * f.health + 0.06 * max(0.0, 100.0 - f.hunger) - 0.05 * f.stress
    if f.sick:
        s -= 10.0
    return max(0.0, s)


def run_show():
    if eco.day - X["show_day"] < 3:
        notify(f"The next genetic show is in {3 - (eco.day - X['show_day'])} day(s)", log=False)
        return False
    mine = sorted((f for f in fishes if hasattr(f, "persona") and f.growth >= 1.0 and not f.sick and f.alive and not isinstance(f, Predator)),
                  key=show_score, reverse=True)[:3]
    if not mine:
        notify("No healthy adult fish to enter", log=False)
        return False
    pool = [(show_score(f), f.name, f) for f in mine]
    lvl = 18 + 4 * min(X["wins"], 6)
    for i in range(3):
        pool.append((random.uniform(lvl - 10, lvl + 14), "Rival " + random.choice(FISH_NAMES), None))
    pool.sort(key=lambda r: r[0], reverse=True)
    SHOWR["rows"] = [(sc, nm, f is not None) for sc, nm, f in pool]
    SHOWR["day"] = eco.day
    X["show_day"] = eco.day
    X["shows"] += 1
    prize = {0: 25, 1: 15, 2: 8}
    won = 0
    for rank, (sc, nm, f) in enumerate(pool[:3]):
        if f is not None:
            won += prize[rank]
            story(f, f"Placed #{rank + 1} at the genetic show")
            if rank == 0:
                X["wins"] += 1
    X["points"] += won
    notify(f"Genetic show: {won} points won" if won else "Genetic show: no placings this time", log=True)
    play_sfx("chime", 0.6)
    save_prefs()
    return True
