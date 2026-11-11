# ---- carrying capacity: how many fish the tank can hold, worked out from geometry, water chemistry and frame budget ----
# Space:  every species claims "personal water" = (its drawn body area) x (how much room that lifestyle wants).
#         Schooling fish tolerate crowding (small factor); lone roamers and territorial fish need far more.
#         The tank's usable water area, times the number of depth lanes the z-sorting gives us, is the supply.
# Water:  update_water() adds  0.05 + 0.0015/plant + 0.03/crawler  per tick-pair and each fish costs 0.003, so the
#         filter can carry (gain * WATER_MARGIN) / 0.003 fish before quality starts to fall; the margin leaves room for
#         algae and uneaten food.
# Speed:  a hard ceiling so the sim stays smooth.
SPACE_FACTOR = {"tetra": 5.0, "barb": 6.0, "rainbow": 7.0, "bala": 8.0, "loach": 8.0, "gourami": 12.0, "pleco": 14.0,
                "cichlid": 14.0, "cory": 5.0, "oto": 4.0,
                "betta": 14.0, "discus": 13.0, "killi": 6.0}
DEPTH_LANES = 2.2        # fish at different z overlap on screen without actually crowding each other
WATER_MARGIN = 0.7       # use at most 70% of the water-cleaning budget for fish
FRAME_BUDGET = 45        # most fish the frame time will tolerate (was 56: too slow on busy frames)
FRY_START_SETS = ("cichlid_set",)   # sets that are stocked as fry instead of adults
FILL_TARGET = 0.85       # seed the tank at this share of its capacity; the rest is headroom for breeding
FOOTPRINTS = {}
# Q cycles these. strips = how many slices the plant layer is spread over (more = lighter frames), smooth = smoothscale to the
# display (off = faster nearest scaling), fish = share of the fish cap that can be stocked.
QUALITY_SPECS = {"LOW": dict(strips=4, smooth=False, fish=0.7), "MED": dict(strips=3, smooth=True, fish=1.0),
                 "HIGH": dict(strips=2, smooth=True, fish=1.0)}
QUALITY = ["MED"]
VOL = {"master": 1.0, "fx": 1.0}
GOV = {"on": True, "base": None, "n": 0, "sum": 0.0, "cool": 0}   # "auto_quality" in aquarium_config.json
_Q_ORDER = ["HIGH", "MED", "LOW"]    # most to least work per frame


def quality_governor():
    """Every three seconds: if frames take longer than 17 ms of real work, drop one quality step; if there is plenty of room, climb back
    toward the quality the player chose. The player's own choice (Q key or config) is always the ceiling."""
    if not GOV["on"] or PM["on"] or pygame.display.get_surface() is None:
        return
    if GOV["base"] is None:
        GOV["base"] = QUALITY[0]
    GOV["n"] += 1
    GOV["sum"] += clock.get_rawtime()
    GOV["cool"] = max(0, GOV["cool"] - 1)
    if GOV["n"] < 180:
        return
    avg = GOV["sum"] / GOV["n"]
    GOV["n"], GOV["sum"] = 0, 0.0
    i = _Q_ORDER.index(QUALITY[0])
    if avg > 17.0 and i < len(_Q_ORDER) - 1:
        QUALITY[0] = _Q_ORDER[i + 1]
        GOV["cool"] = 3600
        notify(f"Quality lowered to {QUALITY[0]} for smoother play (frames took {avg:.0f} ms; 'auto_quality': false turns this off)", log=False)
    elif avg < 9.0 and GOV["cool"] == 0 and i > _Q_ORDER.index(GOV["base"]):
        QUALITY[0] = _Q_ORDER[i - 1]
        GOV["cool"] = 1800
        notify(f"Quality raised to {QUALITY[0]}", log=False)

# ---- fish sets: pick the community from aquarium_config.json ("active_set": cichlid_set / tetra_set / mixed_set) ----
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aquarium_config.json")
DEFAULT_SETS = {
    "cichlid_set": {"AulonocaraOB": [3, 2, 3], "GermanRedPeacock": [3, 2, 3], "SunshinePeacock": [3, 2, 3], "CopadichromisBorleyi": [3, 2, 3], "ElectricBlueHap": [3, 2, 3], "PeacockCichlid": [3, 2, 3], "YellowPrinceCichlid": [3, 2, 3], "IceBlueCichlid": [3, 2, 3], "DemasoniCichlid": [3, 2, 3], "CobaltZebra": [3, 2, 3], "RedZebra": [3, 2, 3], "KenyiCichlid": [3, 2, 3], "AuratusCichlid": [3, 2, 3], "SocolofiCichlid": [3, 2, 3], "SynodontisCatfish": [3, 2, 3], "BristlenosePleco": [3, 2, 3]},
    "tetra_set": {"NeonTetra": [10, 8, 11], "RummyNose": [6, 5, 7], "CardinalTetra": [8, 6, 9], "EmberTetra": [9, 7, 10],
                  "BlackSkirtTetra": [4, 3, 4], "LemonTetra": [5, 4, 5], "MosaicGuppy": [4, 3, 5], "TuxedoGuppy": [4, 3, 5],
                  "SunsetGuppy": [4, 3, 5], "MoscowGuppy": [4, 3, 5], "Corydoras": [6, 4, 6], "Otocinclus": [5, 3, 5],
                  "BristlenosePleco": [2, 1, 2]},
    "mixed_set": {"DemasoniCichlid": [4, 3, 4], "YellowPrinceCichlid": [2, 2, 2], "CobaltZebra": [2, 2, 2], "PeacockCichlid": [2, 2, 2],
                  "AngelFish": [2, 2, 2], "NeonTetra": [5, 4, 5], "RummyNose": [4, 3, 4], "CardinalTetra": [5, 4, 5],
                  "EmberTetra": [4, 4, 4], "BlackSkirtTetra": [2, 2, 2], "MosaicGuppy": [3, 3, 3],
                  "SunsetGuppy": [3, 3, 3], "BalaShark": [2, 2, 2], "BoesemaniRainbow": [3, 3, 3],
                  "TigerBarb": [3, 3, 3], "ClownLoach": [3, 3, 3], "Pleco": [2, 1, 2], "PearlGourami": [2, 2, 2]},
    "showcase_set": {"Betta": [2, 1, 2], "Discus": [4, 2, 4], "Killifish": [6, 4, 6], "MosaicGuppy": [4, 3, 5],
                     "SunsetGuppy": [4, 3, 5], "Corydoras": [5, 4, 5], "Otocinclus": [4, 3, 4], "NeonTetra": [8, 6, 9]},
}
# Aquascape properties per fish set (aquarium_config.json -> "scapes": {set name: {...}}). A set with no entry keeps the
# default random layout. Every key is optional:
#   layout        "random" (default) or "dual_anchor": two tall rock pillars on the far flanks, a low arch in the middle,
#                 and a clear swimming runway in front
#   rock_style    "rock" | "smooth" | "river" | "lace"      pillar_height 0-1 of the water depth      arch true/false
#   plants        {"species": [...], "density": 0-1, "ground_cover": bool, "mounted": bool}   (omit for the usual planting)
#   substrate     {"color": [r, g, b], "buffer": true}      buffer = aragonite: holds KH and pH up
#   water         {"ph", "kh", "gh", "tap_kh", "tap_gh", "kh_range": [lo, hi], "gh_range": [lo, hi]}
#   background    {"darken": 0-0.9, "tint": [r, g, b], "ridge": bool, "doodads": bool}
#   light         {"kelvin": 5000-12000, "shafts": 0-1}
DEFAULT_SCAPES = {
    "cichlid_set": {
        "layout": "dual_anchor", "rock_style": "lace", "pillar_height": 0.8, "arch": True,
        "plants": {"species": ["Anubias", "Sword"], "density": 0.1, "ground_cover": False, "mounted": False},
        "substrate": {"color": [232, 222, 196], "buffer": True},
        "water": {"ph": 8.2, "kh": 12.0, "gh": 14.0, "tap_kh": 12.0, "tap_gh": 14.0, "kh_range": [8, 16], "gh_range": [8, 18]},
        "background": {"darken": 0.62, "tint": [0, 8, 34], "ridge": False, "doodads": False},
        "light": {"kelvin": 9000, "shafts": 0.5},
        "max_fish": 70, "caves": 2,
    },
}
SCAPE = {}      # the active set's aquascape (filled by load_fish_config)


def scape(section, key, default=None):
    v = SCAPE.get(section)
    return v.get(key, default) if isinstance(v, dict) else default


CONFIG_HELP = ("active_set picks which set of fish is stocked (cichlid_set, tetra_set, mixed_set, or any set you add under 'sets'). "
               "Each set maps a species class name to [share, smallest_group, largest_group]. max_fish caps the number of fish "
               "(lower it if the frame rate drops). 'scapes' sets the aquascape per set (layout, rocks, plants, sand, water, background, light). "
               "Press R in game to reload this file. Species: "
               + ", ".join(c.__name__ for c in FW_CLASSES))
DEFAULT_SET = "tetra_set"
ACTIVE_SET = DEFAULT_SET


SET_NAMES = []


def load_fish_config(force=None):
    """Read aquarium_config.json (creating it with the default sets the first time) and apply the active set
    (or the set named by force, for the start menu)."""
    global FRAME_BUDGET, ACTIVE_SET
    cfg = {"_help": CONFIG_HELP, "active_set": DEFAULT_SET, "max_fish": FRAME_BUDGET, "sets": DEFAULT_SETS, "scapes": DEFAULT_SCAPES}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            user = json.load(fh)
        cfg["active_set"] = user.get("active_set", cfg["active_set"])
        cfg["max_fish"] = user.get("max_fish", cfg["max_fish"])
        cfg["sets"] = dict(DEFAULT_SETS)
        cfg["sets"].update(user.get("sets", {}))
        cfg["scapes"] = {k: dict(v) for k, v in DEFAULT_SCAPES.items()}
        for k, v in (user.get("scapes") or {}).items():
            cfg["scapes"].setdefault(k, {}).update(v if isinstance(v, dict) else {})
    except FileNotFoundError:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except OSError:
            pass
    except (OSError, ValueError) as err:
        print(f"aquarium_config.json could not be read ({err}); using the defaults")
    sets = cfg["sets"]
    SET_NAMES[:] = list(sets)
    name = force if force in sets else cfg["active_set"]
    if name not in sets:
        print(f"unknown fish set '{name}', using {DEFAULT_SET} (available: {', '.join(sets)})")
        name = DEFAULT_SET if DEFAULT_SET in sets else next(iter(sets))
    by_name = {c.__name__: c for c in FW_CLASSES}
    target, group = {}, {}
    for cname, spec in sets[name].items():
        cls = by_name.get(cname)
        if cls is None:
            print(f"fish set '{name}': unknown species '{cname}' skipped")
            continue
        try:
            share = max(1, int(spec[0]))
            lo = max(1, int(spec[1])) if len(spec) > 1 else 1
            hi = max(lo, int(spec[2])) if len(spec) > 2 else lo
        except (TypeError, ValueError, IndexError):
            print(f"fish set '{name}': bad entry for {cname}, expected [share, smallest, largest]")
            continue
        target[cls], group[cls] = share, (lo, hi)
    if not target:
        print(f"fish set '{name}' is empty; using {DEFAULT_SET}")
        name = DEFAULT_SET
        target = {by_name[c]: v[0] for c, v in DEFAULT_SETS[name].items()}
        group = {by_name[c]: (v[1], v[2]) for c, v in DEFAULT_SETS[name].items()}
    COMMUNITY_TARGET.clear()
    COMMUNITY_TARGET.update(target)
    COMMUNITY_GROUP.clear()
    COMMUNITY_GROUP.update(group)
    try:
        FRAME_BUDGET = max(6, int(cfg["max_fish"]))
    except (TypeError, ValueError):
        pass
    ACTIVE_SET = name
    SCAPE.clear()
    SCAPE.update(cfg["scapes"].get(name) or {})
    if SCAPE.get("max_fish"):       # a set can have its own fish budget (cichlids need a lot of room each)
        try:
            FRAME_BUDGET = max(6, int(SCAPE["max_fish"]))
        except (TypeError, ValueError):
            pass
    print(f"fish set: {name} ({len(target)} species, up to {FRAME_BUDGET} fish)")


load_fish_config()


def family_of(cls):
    return getattr(cls, "family_name", None) or "cichlid"


def footprint(cls):
    """Average on-screen body area (px^2) of an adult of this species, measured by drawing it and taking the
    bounding box of the pixels (clipped so the sand shadow is ignored)."""
    if cls not in FOOTPRINTS:
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60
        window = pygame.Rect(cx - 220, cy - 150, 440, 300)
        draw = ORIGINAL_DRAW.get(cls, cls.draw)
        areas = []
        for _ in range(4):
            canvas.fill((0, 0, 0, 0))
            canvas.set_clip(window)
            probe = cls(cx, cy)
            probe.vel = pygame.Vector2(1, 0)
            draw(probe, canvas)
            r = canvas.subsurface(window).get_bounding_rect()
            areas.append(0.72 * r.w * r.h)  # a fish fills about 72% of its bounding box
        FOOTPRINTS[cls] = sum(areas) / len(areas)
    return FOOTPRINTS[cls]


def demand(cls):
    """Square pixels of water one fish of this species needs to live comfortably."""
    return footprint(cls) * (getattr(cls, "space", None) or SPACE_FACTOR[family_of(cls)])


def tank_budget():
    """Total 'personal water' the tank can supply, as the lower of the space and water-quality limits."""
    area = SCREEN_WIDTH * (SCREEN_HEIGHT - WATER_TOP - SAND_HEIGHT) * DEPTH_LANES
    water_fish = (0.05 + 0.0015 * len(plants) + 0.03 * len(crawlers)) * WATER_MARGIN / 0.003
    mean_demand = sum(demand(c) * s for c, s in COMMUNITY_TARGET.items()) / sum(COMMUNITY_TARGET.values())
    return min(area, water_fish * mean_demand, FRAME_BUDGET * QUALITY_SPECS[QUALITY[0]]["fish"] * mean_demand)


def tank_load(extra=()):
    return sum(demand(type(f)) for f in fishes if f.alive) + sum(demand(c) for c in extra)


def tank_capacity():
    """How many fish of the community mix fit."""
    mean_demand = sum(demand(c) * s for c, s in COMMUNITY_TARGET.items()) / sum(COMMUNITY_TARGET.values())
    return int(tank_budget() / mean_demand)


def has_room(cls, count=1):
    return tank_load([cls] * count) <= tank_budget()


def spawn_community(total=None):
    """A starting community in the community's proportions, placed in species groups at their habitats and sized so
    the stocked load stays at FILL_TARGET of the tank's budget."""
    if total is None:
        total = int(tank_capacity() * FILL_TARGET)
    scale = total / sum(COMMUNITY_TARGET.values())
    population = []
    for fish_class, share in COMMUNITY_TARGET.items():
        quota = max(1, round(share * scale))
        while quota > 0:
            lo, hi = COMMUNITY_GROUP[fish_class]
            size = min(quota, random.randint(lo, hi))
            population += spawn_group(fish_class, size)
            quota -= size
    while len(population) > 1 and sum(demand(type(f)) for f in population) > tank_budget() * FILL_TARGET:
        population.pop()  # rounding pushed us over: drop the last arrivals
    if ACTIVE_SET in FRY_START_SETS:   # a nursery start: everyone begins as a tiny fry and grows up in the tank
        for f in population:
            init_traits(f)
            f.growth, f.age = 0.0, 0
            f.z = f.adult_z * 0.3
            f.bravery = random.uniform(0.1, 0.4)
            f.hunger = 20.0
    groups = {}
    for f in population:
        groups.setdefault(type(f), []).append(f)
    for grp in groups.values():       # every species that has two or more fish gets at least one male and one female
        sexes = [getattr(f, "sex", None) for f in grp]
        if len(grp) >= 2 and None not in sexes and len(set(sexes)) == 1:
            grp[-1].sex = "F" if sexes[0] == "M" else "M"
    return population


def spawn_random_fish(fishes=None):
    """One replacement fish, favouring whichever species is furthest below its share of the community."""
    current = globals().get("fishes") or []
    counts = {cls: 0 for cls in COMMUNITY_TARGET}
    for f in current:
        if type(f) in counts:
            counts[type(f)] += 1
    total = max(len(current), 1)
    weights = [max(0.4, share * total / 30 - counts[cls] + 0.5) for cls, share in COMMUNITY_TARGET.items()]
    fish_class = random.choices(list(COMMUNITY_TARGET), weights)[0]
    return spawn_group(fish_class, 1)[0]
