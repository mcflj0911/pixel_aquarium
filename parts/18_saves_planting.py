# ---- save / load ----
SAVE_PATH = "aquarium_save.json"
world_seed = 0
LAYOUT = {"custom": False}   # True once the planting mode has changed the seeded layout (then the save stores every item)
PM = {"on": False, "tool": "MOVE", "sel": None, "drag": None, "ops": [], "clear_t": -99999, "rocks_dirty": False, "z": None}
FISH_CLASSES = {c.__name__: c for c in FW_CLASSES}


def rebuild_world(seed=None):
    """Build the hardscape and plants from a seed, so a saved tank can get its exact layout back."""
    global plants, rocks, pebbles, world_seed
    world_seed = seed if seed is not None else random.randrange(1 << 30)
    state = random.getstate()
    random.seed(world_seed)
    plants = create_plants()
    rocks = create_hardscape()
    plants += mounted_plants()
    plants.sort(key=PLANT_ORDER)
    pebbles = create_pebbles(400)
    random.setstate(state)
    for i, r in enumerate(rocks):   # a saved custom layout refers to the original pieces by these numbers
        r.orig = i
    for i, p in enumerate(plants):
        p.orig = i
    LAYOUT["custom"] = False


def save_game(path=None, quiet=False):
    fish_data = []
    for f in fishes:
        if not hasattr(f, "family"):
            continue
        d = {"cls": type(f).__name__, "x": f.pos.x, "y": f.pos.y, "vx": f.vel.x, "vy": f.vel.y, "z": f.z,
             "hunger": f.hunger, "health": f.health, "bravery": f.bravery, "curious": f.curious,
             "growth": f.growth, "adult_z": f.adult_z, "name": f.name, "sick": f.sick, "sick_t": f.sick_t,
             "age": f.age, "lifespan": f.lifespan, "sex": f.sex}
        if hasattr(f, "gh"):
            d.update(gh=f.gh, gt=f.gt, gen=f.gen)
        d["x21"] = fish_extra(f)
        fish_data.append(d)
    data = {"seed": world_seed, "saved_at": time.time(), "set": ACTIVE_SET,
            "eco": {"clock": eco.clock, "day": eco.day, "kills": eco.kills, "births": eco.births, "water": eco.water,
                    "glass": list(eco.glass), "filter": eco.filter, "lights": eco.lights, "air": eco.air_on,
                    "realtime": eco.realtime, "temp": eco.temp, "heater": eco.heater},
            "fish": fish_data,
            "feed": dict(feed_mem),
            "shrimp": [s.gene for s in shimps],
            "hunger": {type(p).__name__: p.hunger for p in predators},
            "placed": [[k, x, z] for k, x, z, _ in placed],
            "layout": layout_snapshot() if LAYOUT["custom"] else None,
            "journal": journal[-40:], "x21": save21()}
    try:
        with open(path or SAVE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        if not quiet:
            notify(f"Tank saved ({len(fish_data)} fish, day {eco.day})", log=False)
    except OSError as err:
        if not quiet:
            notify(f"Could not save: {err}", log=False)


def load_game(path=None, away=False):
    try:
        with open(path or SAVE_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        if not away:
            notify("No saved tank found (press F5 to save one)", log=False)
        return
    if data.get("set") in SET_NAMES and data["set"] != ACTIVE_SET:
        use_set(data["set"], save=False)       # the saved tank was built for another set: bring its scape back first
    rebuild_world(data.get("seed"))
    lay = data.get("layout")
    if isinstance(lay, dict):
        layout_apply(lay)
    init_ecosystem()
    if not isinstance(lay, dict):
        for k, x, z in data.get("placed", []):
            place_decor(k, x, z)
    e = data.get("eco", {})
    eco.clock, eco.day = e.get("clock", eco.clock), e.get("day", 1)
    eco.kills, eco.births, eco.water = e.get("kills", 0), e.get("births", 0), e.get("water", 90.0)
    gl = e.get("glass")
    if isinstance(gl, list) and len(gl) == GLASS_COLS:
        eco.glass = [clamp(float(v)) for v in gl]
    eco.filter = clamp(float(e.get("filter", 1.0)))
    if e.get("lights") in ("SUN", "ON", "OFF"):
        eco.lights = e["lights"]
    eco.air_on = bool(e.get("air", True))
    eco.realtime = bool(e.get("realtime", False))
    eco.temp = float(e.get("temp", 25.0))
    if e.get("heater") in HEAT:
        eco.heater = e["heater"]
    fm = data.get("feed")
    if isinstance(fm, dict):
        for k in ("x", "y", "conf"):
            feed_mem[k] = float(fm.get(k, 0.0))
    n_shrimp = data.get("shrimp")
    genes = n_shrimp if isinstance(n_shrimp, list) else [0] * n_shrimp if isinstance(n_shrimp, int) else []
    if 4 <= len(genes) <= 60:
        shimps[:] = [TinyShrimp() for _ in genes]
        for sh, gn in zip(shimps, genes):
            if gn in (0, 1, 2):
                sh.gene, sh.base_color = gn, SHRIMP_COLORS[gn]
    new_fish = []
    for d in data.get("fish", []):
        cls = FISH_CLASSES.get(d["cls"])
        if cls is None:
            continue
        f = cls(d["x"], d["y"])
        init_traits(f)
        f.vel = pygame.Vector2(d["vx"], d["vy"])
        f.z, f.hunger, f.health = d["z"], d["hunger"], d["health"]
        f.bravery, f.curious, f.growth, f.adult_z = d["bravery"], d["curious"], d["growth"], d["adult_z"]
        f.name, f.sick, f.sick_t = d["name"], d["sick"], d["sick_t"]
        f.age, f.lifespan, f.sex = d.get("age", f.age), d.get("lifespan", f.lifespan), d.get("sex", f.sex)
        if hasattr(f, "gh"):
            f.gh, f.gt, f.gen = d.get("gh", f.gh), d.get("gt", f.gt), d.get("gen", 1)
        fish_extra_apply(f, d.get("x21"))
        if f.sick:
            f.spots = [(random.uniform(-1, 1), random.uniform(-0.6, 0.6)) for _ in range(5)]
        new_fish.append(f)
    fishes[:] = new_fish
    for p in predators:
        p.hunger = data.get("hunger", {}).get(type(p).__name__, p.hunger)
    journal[:] = [tuple(j) for j in data.get("journal", [])]
    load21(data.get("x21"))
    relink_friends()
    notify("Tank loaded", log=False)
    if away and isinstance(data.get("saved_at"), (int, float)):
        apply_away(time.time() - data["saved_at"])



# ---- planting mode: put the fish away and lay out every plant, rock and piece of driftwood by hand ----
PM.update(fill=False, stroke=None, edits=0, shots={"before": None, "after": None})
PM_TOOLS = [("MOVE", "Move"), ("ROCK", "Rock"), ("DRIFTWOOD", "Driftwood"), ("CAVE", "Cave"), ("POT", "Clay pot"), ("SHIP", "Shipwreck"),
            ("BRIDGE", "Bridge"), ("SWORD", "Sword"), ("ROTALA", "Rotala"), ("LUDWIGIA", "Ludwigia"), ("CABOMBA", "Cabomba"),
            ("HYGRO", "Hygrophila"), ("VALLIS", "Vallisneria"), ("HAIR", "Hairgrass"), ("LOTUS", "Tiger lotus"), ("ANUBIAS", "Anubias"),
            ("JAVAFERN", "Java fern"), ("POTHOS", "Pothos"), ("DWARF", "Carpet"), ("CRYPT", "Crypt"), ("CLOVER", "Clover"),
            ("MOSS", "Moss ball"), ("TRIM", "Prune")]
PM_LABEL = dict(PM_TOOLS, UNDO="Undo", CLEAR="Clear all", DONE="Done", FILL="Fill", MIRROR="Mirror", JUDGE="Judge")
PM_ROWS = 3
PM_BAR_BOTTOM = 10 + PM_ROWS * 34 + 6


def rock_set_x(r, x):
    r.pos_x = x
    r.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2


def item_kind(it):
    return it.kind if isinstance(it, Rock) else KIND_OF.get(it.species, "SWORD")


def layout_snapshot():
    """Every rock and plant as plain data: seeded originals by number, new pieces by kind and seed, with position, height, size and flip."""
    items = []
    for r in rocks:
        d = {"t": "r", "x": r.pos_x, "yo": r.y_offset, "sc": round(r.sc, 3), "fl": r.fl, "md": r.mday}
        if getattr(r, "orig", None) is not None:
            d["o"] = r.orig
        else:
            d.update(k=r.kind, z=r.z, s=getattr(r, "iseed", 0))
        items.append(d)
    for p in plants:
        d = {"t": "p", "x": p.pos_x, "lift": p.lift, "sz": round(p.psize, 3), "hp": round(p.hp, 2), "dp": p.depth}
        if getattr(p, "orig", None) is not None:
            d["o"] = p.orig
        else:
            d.update(k=KIND_OF.get(p.species, "SWORD"), s=getattr(p, "iseed", 0))
        items.append(d)
    return {"items": items}


def layout_apply(snap):
    orig_r = {r.orig: r for r in rocks if getattr(r, "orig", None) is not None}
    orig_p = {p.orig: p for p in plants if getattr(p, "orig", None) is not None}
    new_r, new_p = [], []
    for d in snap.get("items", []):
        try:
            if d["t"] == "r":
                if "o" in d:
                    it = orig_r.get(d["o"])
                    if it is None:
                        continue
                    rock_set_x(it, float(d["x"]))
                else:
                    it = make_item(d["k"], float(d["x"]), float(d["z"]), int(d["s"]), int(d.get("yo", 0)))
                it.y_offset = int(d.get("yo", it.y_offset))
                it.mday = int(d.get("md", 0))
                it.sc, it.fl = float(d.get("sc", 1.0)), bool(d.get("fl", False))
                if it.sc != 1.0 or it.fl:
                    rock_look(it)
                new_r.append(it)
            else:
                if "o" in d:
                    it = orig_p.get(d["o"])
                    if it is None:
                        continue
                    it.pos_x = float(d["x"])
                else:
                    it = make_item(d["k"], float(d["x"]), None, int(d["s"]))
                it.lift = d.get("lift", it.lift)
                sz = float(d.get("sz", 1.0))
                if abs(sz - it.psize) > 0.01:
                    scale_plant(it, sz / it.psize)
                it.hp = float(d.get("hp", 1.0))
                it.depth = int(clamp(int(d.get("dp", 0)), 0, 2))
                it._colc = {}
                new_p.append(it)
        except (KeyError, TypeError, ValueError):
            continue
    rocks[:] = sorted(new_r, key=lambda r: (r.z, -r.y_offset))
    plants[:] = sorted(new_p, key=PLANT_ORDER)
    LAYOUT["custom"] = True
    build_cover()


def pm_finalize():
    """After designing: rebuild the hiding places, and give the fire eel and cleaner shrimp a rock that still exists."""
    build_cover()
    if not PM["rocks_dirty"]:
        return
    PM["rocks_dirty"] = False
    had_eel = any(isinstance(p, FireEel) for p in predators)
    predators[:] = [p for p in predators if not isinstance(p, FireEel)]
    eel, chosen = build_world_extras()
    stations[:] = chosen
    if had_eel and eel is not None:
        predators.append(eel)


def pm_item_rect(it):
    if isinstance(it, Rock):
        sink = int(35 * it.z) if it.y_offset >= 0 else 0
        return it.image.get_rect(midbottom=(int(it.pos_x), int(it.base_y + it.y_offset + sink)))
    if it.hang:
        return pygame.Rect(int(it.pos_x) - 26, 0, 52, int(min(420, max(v[2] for v in it.vines) + 70)))
    base = ground_y(it.pos_x) - it.lift
    h = max(40, it.height)
    return pygame.Rect(int(it.pos_x) - 30, int(base - h), 60, int(h + 6))


def pm_pick(pos):
    best, bs = None, 1e9
    for it in list(plants) + list(rocks):
        if not pm_item_rect(it).collidepoint(pos):
            continue
        dx = abs(it.pos_x - pos[0])
        sc = dx + (10 + 0.25 * dx if isinstance(it, Rock) else 0)   # a plant wins a tie with the rock it stands beside
        if sc < bs:
            best, bs = it, sc
    return best


def pm_note_edit():
    PM["edits"] += 1
    LAYOUT["custom"] = True


def pm_enter():
    PM.update(on=True, tool="MOVE", sel=None, drag=None, stroke=None, ops=[], clear_t=-99999, edits=0)
    PM["shots"] = {"before": None, "after": None}
    CAP.update(want="before", delay=0)   # the tank as it is now, fish and all, for the before / after slider
    eco.selected, eco.follow = None, False
    notify("Planting mode: the fish are put away", log=False)


def pm_exit():
    PM.update(on=False, drag=None, sel=None, stroke=None)
    pm_finalize()
    save_prefs()
    if PM["edits"]:
        CAP.update(want="after", delay=QUALITY_SPECS[QUALITY[0]]["strips"] + 3)
    notify("Planting mode done: the fish are back", log=False)


def pm_remove(it, record=True):
    if it in rocks:
        rocks.remove(it)
        PM["rocks_dirty"] = True
    elif it in plants:
        plants.remove(it)
    else:
        return
    if PM["sel"] is it:
        PM["sel"] = None
    pm_note_edit()
    if record:
        PM["ops"].append(("del", it))
    build_cover()


def pm_insert(it):
    if isinstance(it, Rock):
        rocks.append(it)
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
        PM["rocks_dirty"] = True
    else:
        plants.append(it)
        plants.sort(key=PLANT_ORDER)
    pm_note_edit()
    build_cover()


def pm_replace(old, new):
    lst = rocks if isinstance(old, Rock) else plants
    if old in lst:
        lst[lst.index(old)] = new
    if isinstance(new, Rock):
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
        PM["rocks_dirty"] = True
    else:
        plants.sort(key=PLANT_ORDER)
    if PM["sel"] is old:
        PM["sel"] = new
    pm_note_edit()
    build_cover()


def pm_add(kind, x, record=True, z=None, yo=0):
    x = clamp(x, 8, SCREEN_WIDTH - 8)
    if kind in ROCK_KINDS:
        z = z if z is not None else PM["z"]
    place_decor(kind, x, z if kind in ROCK_KINDS else None, yo)
    it = placed[-1][3]
    plants.sort(key=PLANT_ORDER)
    if record:
        PM["ops"].append(("add", it))
    PM["sel"] = it
    PM["rocks_dirty"] = PM["rocks_dirty"] or isinstance(it, Rock)
    pm_note_edit()
    return it


def pm_stack(kind, base):
    """Drop a rock on top of another: same depth, one layer higher than whatever is already stacked there."""
    layers = sum(1 for r in rocks if abs(r.pos_x - base.pos_x) < 30 and abs(r.z - base.z) < 0.06 and r.y_offset < 0)
    yo = max(-90, -18 * (layers + 1))
    return pm_add(kind, base.pos_x + random.randint(-12, 12), z=base.z, yo=yo)


def pm_set_prop(it, **kw):
    old = {k: getattr(it, k) for k in kw}
    for k, v in kw.items():
        setattr(it, k, v)
    if isinstance(it, Rock):
        rocks.sort(key=lambda r: (r.z, -r.y_offset))
        PM["rocks_dirty"] = True
    pm_note_edit()
    build_cover()
    return old


def pm_lift(it, up):
    if isinstance(it, Rock):
        yo = clamp(it.y_offset + (-18 if up else 18), -90, 0)
        if yo != it.y_offset:
            PM["ops"].append(("prop", it, pm_set_prop(it, y_offset=int(yo))))
    else:
        lf = clamp(it.lift + (8 if up else -8), 0, 320)
        if lf != it.lift:
            PM["ops"].append(("prop", it, pm_set_prop(it, lift=lf)))


def pm_resize(it, k):
    if isinstance(it, Rock):
        sc = clamp(it.sc * k, 0.5, 2.2)
        if sc != it.sc:
            PM["ops"].append(("prop", it, pm_set_prop(it, sc=sc)))
            rock_look(it)
    else:
        new = clamp(it.psize * k, 0.5, 2.2)
        k2 = new / it.psize
        if abs(k2 - 1.0) > 0.001:
            scale_plant(it, k2)
            PM["ops"].append(("size", it, k2))
            plants.sort(key=PLANT_ORDER)
            pm_note_edit()
            build_cover()


def pm_flip(it):
    if isinstance(it, Rock):
        it.fl = not it.fl
        rock_look(it)
        PM["ops"].append(("flip", it))
        pm_note_edit()


def pm_depth(it, dz):
    """A new depth redraws the piece (shading is baked into its picture), so it is rebuilt from a seed."""
    if not isinstance(it, Rock):   # a plant has three planes: front, middle, back
        nd = int(clamp(it.depth + (1 if dz > 0 else -1), 0, 2))
        if nd != it.depth:
            PM["ops"].append(("pdepth", it, it.depth))
            it.depth = nd
            it._colc = {}
            plants.sort(key=PLANT_ORDER)
            pm_note_edit()
        return
    z = round(clamp(it.z + dz, 0.6, 1.2), 2)
    if z == it.z:
        return
    seed = getattr(it, "iseed", None) or random.getrandbits(30)
    new = make_item(it.kind, it.pos_x, z, seed, it.y_offset)
    new.sc, new.fl = it.sc, it.fl
    rock_look(new)
    pm_replace(it, new)
    PM["ops"].append(("swap", it, new))


def pm_mirror(record=True):
    for r in rocks:
        rock_set_x(r, SCREEN_WIDTH - r.pos_x)
        r.fl = not r.fl
        rock_look(r)
    for p in plants:
        p.pos_x = SCREEN_WIDTH - p.pos_x
    rocks.sort(key=lambda r: (r.z, -r.y_offset))
    plants.sort(key=PLANT_ORDER)
    PM["rocks_dirty"] = True
    pm_note_edit()
    build_cover()
    if record:
        PM["ops"].append(("mirror",))


def pm_undo():
    if not PM["ops"]:
        return
    op = PM["ops"].pop()
    kind = op[0]
    if kind == "add":
        pm_remove(op[1], record=False)
    elif kind == "group":
        for it in op[1]:
            pm_remove(it, record=False)
    elif kind == "del":
        pm_insert(op[1])
    elif kind == "move":
        it, ox = op[1], op[2]
        if isinstance(it, Rock):
            rock_set_x(it, ox)
            PM["rocks_dirty"] = True
        else:
            it.pos_x = ox
        plants.sort(key=PLANT_ORDER)
        pm_note_edit()
        build_cover()
    elif kind == "prop":
        for k, v in op[2].items():
            setattr(op[1], k, v)
        if isinstance(op[1], Rock):
            rock_look(op[1])
            rocks.sort(key=lambda r: (r.z, -r.y_offset))
            PM["rocks_dirty"] = True
        pm_note_edit()
        build_cover()
    elif kind == "pdepth":
        op[1].depth = op[2]
        op[1]._colc = {}
        plants.sort(key=PLANT_ORDER)
        pm_note_edit()
    elif kind == "size":
        scale_plant(op[1], 1.0 / op[2])
        plants.sort(key=PLANT_ORDER)
        pm_note_edit()
        build_cover()
    elif kind == "flip":
        op[1].fl = not op[1].fl
        rock_look(op[1])
        pm_note_edit()
    elif kind == "swap":
        pm_replace(op[2], op[1])
    elif kind == "mirror":
        pm_mirror(record=False)
    elif kind == "clear":
        rocks[:] = op[1]
        plants[:] = op[2]
        PM["rocks_dirty"] = True
        pm_note_edit()
        build_cover()


def pm_clear_all():
    PM["ops"].append(("clear", list(rocks), list(plants)))
    rocks.clear()
    plants.clear()
    placed.clear()
    PM["sel"], PM["drag"], PM["stroke"] = None, None, None
    PM["rocks_dirty"] = True
    pm_note_edit()
    build_cover()
    notify("Tank cleared: start your design from scratch", log=False)


PM_ACTIONS = ("UNDO", "FILL", "MIRROR", "JUDGE", "CLEAR", "DONE")


def pm_layout():
    ids = [t[0] for t in PM_TOOLS] + list(PM_ACTIONS)
    x0, per = 380, 10
    bw = max(72, min(118, (SCREEN_WIDTH - x0 - 20) // per - 4))
    return [(pygame.Rect(x0 + (i % per) * (bw + 4), 10 + (i // per) * 34, bw, 30), b) for i, b in enumerate(ids)]


def pm_button(b):
    if b == "DONE":
        pm_exit()
    elif b == "UNDO":
        pm_undo()
    elif b == "FILL":
        PM["fill"] = not PM["fill"]
    elif b == "MIRROR":
        pm_mirror()
    elif b == "JUDGE":
        judge_run()
    elif b == "CLEAR":
        now = pygame.time.get_ticks()
        if now - PM["clear_t"] < 3000:
            PM["clear_t"] = -99999
            pm_clear_all()
        else:
            PM["clear_t"] = now
    else:
        PM["tool"] = b


def pm_event(e):
    """While planting, the mouse and a few keys belong to the mode. Returns True when the event was used."""
    if e.type == pygame.KEYDOWN:
        if e.key == pygame.K_HOME:
            if PM["on"]:
                pm_exit()
            elif not TOUR["on"]:
                pm_enter()
            return True
        if e.key == pygame.K_PAGEDOWN and not PM["on"]:
            tour_toggle()
            return True
        if e.key == pygame.K_ESCAPE and TOUR["on"]:
            tour_end()
            return True
        if e.key == pygame.K_INSERT and not PM["on"]:
            if PM["shots"]["before"] is not None and PM["shots"]["after"] is not None:
                UI21["panel"] = "ba"
            else:
                notify("Nothing to compare yet: change the layout in planting mode (Home) first", log=False)
            return True
    if not PM["on"] or UI21["panel"] is not None:
        return False
    if e.type == pygame.MOUSEBUTTONDOWN:
        pos = world_mouse(e.pos)
        if e.button == 1:
            for r, b in pm_layout():
                if r.collidepoint(pos):
                    pm_button(b)
                    return True
            if pos[0] > 370 and pos[1] < PM_BAR_BOTTOM + 80:
                return True
            tool = PM["tool"]
            if tool == "MOVE":
                it = pm_pick(pos)
                PM["sel"] = it
                PM["drag"] = (it, it.pos_x, pos[0] - it.pos_x) if it is not None else None
            elif tool == "TRIM":
                trim_plants(pos[0])
                pm_note_edit()
            elif PM["fill"] and tool != "TRIM":
                it = pm_add(tool, pos[0], record=False)
                PM["stroke"] = {"kind": tool, "x": pos[0], "gap": 18 if tool not in ROCK_KINDS else 60, "items": [it]}
            else:
                base = pm_pick(pos) if tool in ROCK_KINDS else None
                if isinstance(base, Rock):
                    pm_stack(tool, base)
                else:
                    pm_add(tool, pos[0])
        elif e.button == 3:
            it = pm_pick(pos)
            if it is not None:
                pm_remove(it)
        return True
    if e.type == pygame.MOUSEWHEEL:
        PM["z"] = clamp(round((PM["z"] or 0.9) + 0.05 * e.y, 2), 0.6, 1.2)
        return True
    if e.type == pygame.MOUSEBUTTONUP:
        d, st = PM["drag"], PM["stroke"]
        PM["drag"], PM["stroke"] = None, None
        if d is not None and abs(d[0].pos_x - d[1]) > 1:
            PM["ops"].append(("move", d[0], d[1]))
        if st is not None:
            PM["ops"].append(("group", st["items"]))
        return True
    if e.type == pygame.KEYDOWN:
        k = e.key
        it = PM["sel"]
        if k == pygame.K_ESCAPE:
            pm_exit()
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE) and it is not None:
            pm_remove(it)
        elif k == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
            pm_undo()
        elif k == pygame.K_TAB:
            ids = [t[0] for t in PM_TOOLS]
            PM["tool"] = ids[(ids.index(PM["tool"]) + 1) % len(ids)]
        elif it is not None and k in (pygame.K_LEFT, pygame.K_RIGHT):
            nx = clamp(it.pos_x + (1 if k == pygame.K_RIGHT else -1) * (20 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 4), 0, SCREEN_WIDTH)
            if isinstance(it, Rock):
                rock_set_x(it, nx)
                PM["rocks_dirty"] = True
            else:
                it.pos_x = nx
            pm_note_edit()
            build_cover()
        elif it is not None and k in (pygame.K_UP, pygame.K_DOWN):
            pm_lift(it, k == pygame.K_UP)
        elif it is not None and k in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            pm_resize(it, 1.1 if k == pygame.K_PAGEUP else 1 / 1.1)
        elif it is not None and k in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            pm_depth(it, 0.05 if k == pygame.K_RIGHTBRACKET else -0.05)
        elif it is not None and k == pygame.K_f:
            pm_flip(it)
        else:
            return False
        return True
    return False


def pm_update():
    d, st = PM["drag"], PM["stroke"]
    mx = world_mouse(pygame.mouse.get_pos())[0]
    if st is not None and abs(mx - st["x"]) >= st["gap"]:
        st["items"].append(pm_add(st["kind"], mx + random.uniform(-3, 3), record=False))
        st["x"] = mx
        st["gap"] = random.uniform(14, 26) if st["kind"] not in ROCK_KINDS else random.uniform(50, 80)
    if d is None:
        return
    it = d[0]
    nx = clamp(mx - d[2], 0, SCREEN_WIDTH)
    if abs(nx - it.pos_x) < 0.5:
        return
    if isinstance(it, Rock):
        rock_set_x(it, nx)
        PM["rocks_dirty"] = True
    else:
        it.pos_x = nx
        plants.sort(key=PLANT_ORDER)
    LAYOUT["custom"] = True


def pm_sel_text(it):
    if isinstance(it, Rock):
        return f"{PM_LABEL.get(it.kind, it.kind.title())}   depth {it.z:.2f}   size {it.sc:.2f}   height {-it.y_offset}"
    txt = f"{it.species}   health {int(it.hp * 100)}%   size {it.psize:.2f}   lift {int(it.lift)}   depth {('front', 'middle', 'back')[it.depth]}"
    if it.bloom:
        txt += "   in flower"
    if it.nib >= 2:
        txt += "   nibbled"
    return txt


def draw_plant_mode(surface):
    if not PM["on"]:
        return
    pm_update()
    mx, my = world_mouse(pygame.mouse.get_pos())
    low = PM_BAR_BOTTOM + 80
    if PM["tool"] == "MOVE" and PM["drag"] is None:
        hov = pm_pick((mx, my))
        if hov is not None and hov is not PM["sel"]:
            pygame.draw.rect(surface, (255, 255, 255), pm_item_rect(hov), 1, border_radius=4)
    if PM["sel"] is not None:
        pygame.draw.rect(surface, (255, 232, 120), pm_item_rect(PM["sel"]), 2, border_radius=4)
    if PM["tool"] not in ("MOVE", "TRIM") and my > low:
        gy = ground_y(mx)
        for y in range(int(gy) - 150, int(gy), 10):
            pygame.draw.line(surface, (255, 255, 255), (mx, y), (mx, y + 5), 1)
        lab = f21("d").render(PM_LABEL[PM["tool"]] + ("  (fill: drag)" if PM["fill"] else ""), True, (255, 255, 255))
        surface.blit(lab, lab.get_rect(midbottom=(int(mx), int(gy) - 154)))
    elif PM["tool"] == "TRIM" and my > low:
        pygame.draw.circle(surface, (255, 255, 255), (int(mx), int(my)), 75, 1)
    now = pygame.time.get_ticks()
    for r, b in pm_layout():
        on = b == PM["tool"] or (b == "FILL" and PM["fill"])
        sure = b == "CLEAR" and now - PM["clear_t"] < 3000
        col = (170, 60, 50) if b == "CLEAR" else (40, 130, 90) if b in ("DONE", "JUDGE") else (60, 130, 210) if on else (14, 30, 54)
        pygame.draw.rect(surface, col, r, border_radius=8)
        pygame.draw.rect(surface, (255, 232, 140) if on else (120, 190, 230), r, 2, border_radius=8)
        text = "Sure? click again" if sure else (("Fill: on" if PM["fill"] else "Fill: off") if b == "FILL" else PM_LABEL[b])
        t = f21("d").render(text, True, (255, 255, 255))
        surface.blit(t, t.get_rect(center=r.center))
    zt = f"{PM['z']:.2f}" if PM["z"] else "random"
    lines = ["PLANTING MODE - the fish are away.   Pick a tool, then click the tank.   Click a rock with a rock tool to stack on it.   Esc or Home when done.",
             f"MOVE: drag, arrows nudge.  Up/Down raise or lower.  PgUp/PgDn size.  [ ] depth.  F flip.  Right-click or Del removes.  Ctrl+Z undo.  Wheel: new rock depth ({zt})"]
    if PM["sel"] is not None:
        lines.append("Selected:  " + pm_sel_text(PM["sel"]))
    ts = [f21("d").render(m, True, (255, 232, 150) if i == 2 else (235, 245, 255)) for i, m in enumerate(lines)]
    bar = pygame.Surface((max(t.get_width() for t in ts) + 24, 8 + 22 * len(ts)), pygame.SRCALPHA)
    pygame.draw.rect(bar, (8, 20, 40, 210), bar.get_rect(), border_radius=8)
    for i, t in enumerate(ts):
        bar.blit(t, (12, 4 + 22 * i))
    surface.blit(bar, (380, PM_BAR_BOTTOM))
