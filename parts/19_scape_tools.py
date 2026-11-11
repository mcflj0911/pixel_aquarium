# ---------------------------------------------------------------- 6/7: plant health, nibbling, flowers, runners, growth
PT = {"day": -1}
NIBBLERS = ("Pleco", "KenyiCichlid", "AuratusCichlid", "SocolofiCichlid", "BalaShark")
RUNNERS = ("DwarfGrass", "Clover")
BLOOMERS = ("Anubias", "Cryptocoryne", "Sword")


def plant_care():
    """Every ten seconds: plants take the tank's light, food and fish into account. Once a day: nibbles heal, some bloom, carpets send runners."""
    if PM["on"] or not plants:
        return
    new_day = eco.day != PT["day"]
    PT["day"] = eco.day
    dark = eco.lights == "OFF"
    starved = CHEM["no3"] < 2.5 and FERT["t"] <= 0 and "co2" not in X["owned"]
    smothered = sum(HAIR) / len(HAIR) > 0.55
    for f in fishes:   # a few species nibble the softer plants
        if type(f).__name__ in NIBBLERS and f.growth >= 1.0 and random.random() < 0.35:
            near = [p for p in plants if not p.hang and p.species not in ("MossBall", "Anubias") and abs(p.pos_x - f.pos.x) < 70]
            if near:
                v = random.choice(near)
                v.nib = min(10, v.nib + 1)
                if v.nib == 3:
                    notify(f"{f.name} is nibbling the {v.species.lower()}", log=False)
    for p in plants:
        t = 1.0 - (0.3 if dark else 0.0) - (0.35 if starved else 0.0) - (0.2 if CHEM["no3"] > 90 else 0.0) - (0.15 if smothered else 0.0)
        t = clamp(t - min(0.4, p.nib * 0.08), 0.2, 1.0)
        p.hp += (t - p.hp) * 0.2
    if not new_day:
        return
    grown = 0
    for p in list(plants):
        p.nib = max(0, p.nib - 1)
        if p.bloom:
            p.bloom -= 1
        elif p.species in BLOOMERS and p.hp > 0.75 and random.random() < 0.012:
            p.bloom = random.randint(3, 6)
            X["blooms"] += 1
            notify(f"The {p.species.lower()} is in flower", log=False)
        if p.species in TALL_PLANTS and p.hp > 0.6:   # slow natural growth, faster with fertiliser or CO2 (see fw21_update)
            if not hasattr(p, "base_h"):
                p.base_h = p.height
            if p.height < p.base_h * 1.8:
                scale_plant(p, 1.015)
                grown += 1
        if (p.species in RUNNERS and p.hp > 0.6 and len(plants) < 260 and random.random() < 0.06
                and sum(1 for q in plants if q.species == p.species and abs(q.pos_x - p.pos_x) < 60) < 5):
            x = clamp(p.pos_x + random.choice((-1, 1)) * random.uniform(16, 30), 8, SCREEN_WIDTH - 8)
            plants.append(make_item(KIND_OF[p.species], x))
            LAYOUT["custom"] = True
            grown += 1
    if grown:
        plants.sort(key=PLANT_ORDER)
        build_cover()


# ---------------------------------------------------------------- 9: the aquascape judge
COLOR_GROUP = {"Ludwigia": "red", "TigerLotus": "red", "Rotala": "red", "Cryptocoryne": "red",
               "Hygrophila": "lime", "Hairgrass": "lime", "DwarfGrass": "lime", "Clover": "lime", "MossBall": "lime",
               "Vallisneria": "deep", "Sword": "deep", "JavaFern": "deep", "Anubias": "deep", "Cabomba": "feather", "Pothos": "feather"}
JUDGE_TIPS = {
    "Balance": "Spread the weight: keep a focal point off-centre and no empty third of the tank.",
    "Layers": "Mix carpet, mid-height and tall plants, and put rocks at more than one depth.",
    "Colour": "Add contrast: red stem plants, lime greens and deep greens side by side.",
    "Shelter": "Give the fish caves, rock faces and thick plant stands, and use more kinds of piece.",
}


def judge_layout():
    W = SCREEN_WIDTH
    mass = [0.0, 0.0, 0.0]
    com_num = 0.0
    for p in plants:
        m = max(20.0, p.height) * (0.5 if p.height < 70 else 1.0)
        mass[min(2, int(p.pos_x / W * 3))] += m
        com_num += m * p.pos_x
    for r in rocks:
        m = r.image.get_width() * r.image.get_height() / 55.0
        mass[min(2, int(r.pos_x / W * 3))] += m
        com_num += m * r.pos_x
    total = sum(mass)
    if total <= 0:
        return {"Balance": 0, "Layers": 0, "Colour": 0, "Shelter": 0, "overall": 0}
    com = com_num / total / W
    shares = [m / total for m in mass]
    bal = 100 - 220 * max(0.0, abs(com - 0.5) - 0.15) - 320 * max(0.0, 0.15 - min(shares))
    cols = set()   # open water matters: a tank packed edge to edge leaves the fish nowhere to swim
    for it in list(plants) + list(rocks):
        if isinstance(it, Rock) or it.height > 120:
            rc = pm_item_rect(it)
            cols.update(range(max(0, rc.left // 40), min(W // 40, rc.right // 40) + 1))
    open_frac = 1.0 - len(cols) / max(1, W // 40 + 1)
    bal -= 260 * max(0.0, 0.22 - open_frac) + 140 * max(0.0, open_frac - 0.7)
    n_pl = [p for p in plants if not p.hang]
    hc = sum(1 for lo, hi in ((0, 70), (70, 170), (170, 9999)) if sum(1 for p in n_pl if lo <= p.height < hi) >= 2)
    zb = len({0 if r.z < 0.8 else 1 if r.z < 0.95 else 2 for r in rocks})
    lay = (100 * (0.6 * hc / 3 + 0.4 * zb / 3)) * min(1.0, len(n_pl) / 10.0)
    groups = {}
    for p in plants:
        g = COLOR_GROUP.get(p.species)
        if g:
            groups[g] = groups.get(g, 0) + 1
    ng = sum(1 for v in groups.values() if v >= 2)
    col = (0, 35, 70, 100, 100)[min(4, ng)]
    if groups and max(groups.values()) > 0.6 * sum(groups.values()):   # one colour everywhere is dull
        col -= 30
    spots = len(rock_spots) + len(nest_spots) + len(cave_spots) * 2 + len(thicket_spots)
    need = max(3.0, len(fishes) / 6.0)
    kinds = len({item_kind(it) for it in list(plants) + list(rocks)})
    shel = 0.6 * min(100.0, 100.0 * spots / need) + 0.4 * min(100.0, kinds * 100 / 9.0)
    out = {"Balance": int(clamp(bal, 0, 100)), "Layers": int(clamp(lay, 0, 100)), "Colour": int(clamp(col, 0, 100)), "Shelter": int(clamp(shel, 0, 100))}
    out["overall"] = int(sum(out.values()) / 4)
    return out


def judge_run():
    r = judge_layout()
    gain = max(0, r["overall"] - X["best_scape"])
    pts = min(25, gain // 4)
    r["pts"] = pts
    if r["overall"] > X["best_scape"]:
        X["best_scape"] = r["overall"]
    if pts:
        X["points"] += pts
        notify(f"The judge awards {pts} points for the new design", log=True)
    save_prefs()
    UI21["judge"] = r
    UI21["panel"] = "judge"
    check_goals()


def draw_judge(surface):
    r = UI21["judge"] or judge_layout()
    panel = begin_panel(760, 410, f"Aquascape judge   {r['overall']} / 100")
    worst = min(("Balance", "Layers", "Colour", "Shelter"), key=lambda k: r[k])
    for i, name in enumerate(("Balance", "Layers", "Colour", "Shelter")):
        y = 74 + i * 52
        txt21(panel, name, 26, y, "h", (255, 232, 140))
        pygame.draw.rect(panel, (24, 44, 70), (170, y + 2, 480, 22), border_radius=6)
        v = r[name]
        col = (110, 210, 140) if v >= 70 else (235, 200, 90) if v >= 40 else (225, 110, 90)
        pygame.draw.rect(panel, col, (170, y + 2, int(480 * v / 100), 22), border_radius=6)
        txt21(panel, str(v), 668, y, "h", (235, 245, 255))
    txt21(panel, f"Best so far: {X['best_scape']}   " + (f"+{r.get('pts', 0)} points just now" if r.get("pts") else "no new points"), 26, 290, "d", HUD_DIM)
    txt21(panel, "Tip:  " + JUDGE_TIPS[worst], 26, 318, "d", (200, 215, 232))
    end_panel(surface, panel, "Esc to close   (points come only when you beat your best score)")


# ---------------------------------------------------------------- 10: before / after
CAP = {"want": None, "delay": 0}


def cap_tick(surface):
    w = CAP["want"]
    if not w:
        return
    if CAP["delay"] > 0:
        CAP["delay"] -= 1
        return
    CAP["want"] = None
    PM["shots"][w] = surface.copy()
    if w == "after":
        UI21["panel"] = "ba"


def draw_ba(surface):
    b, a = PM["shots"]["before"], PM["shots"]["after"]
    if b is None or a is None:
        return
    W, H = surface.get_size()
    mx = int(clamp(world_mouse(pygame.mouse.get_pos())[0], 0, W))
    surface.blit(a, (0, 0))
    if mx > 0:
        surface.blit(b, (0, 0), area=pygame.Rect(0, 0, mx, H))
    pygame.draw.line(surface, (255, 255, 255), (mx, 0), (mx, H), 3)
    pygame.draw.circle(surface, (255, 255, 255), (mx, H // 2), 14)
    pygame.draw.circle(surface, (40, 100, 190), (mx, H // 2), 10)
    for text, x in (("BEFORE", 40), ("AFTER", W - 160)):
        t = f21("t").render(text, True, (255, 255, 255))
        box = pygame.Surface((t.get_width() + 24, t.get_height() + 10), pygame.SRCALPHA)
        pygame.draw.rect(box, (8, 20, 40, 190), box.get_rect(), border_radius=8)
        box.blit(t, (12, 5))
        surface.blit(box, (x, 30))
    hint = f21("d").render("Slide the mouse to compare   Enter: save the picture to the album   Esc: close", True, (235, 245, 255))
    box = pygame.Surface((hint.get_width() + 24, 30), pygame.SRCALPHA)
    pygame.draw.rect(box, (8, 20, 40, 200), box.get_rect(), border_radius=8)
    box.blit(hint, (12, 6))
    surface.blit(box, box.get_rect(midbottom=(W // 2, H - 24)))


def ba_save():
    b, a = PM["shots"]["before"], PM["shots"]["after"]
    if b is None or a is None:
        return
    W, H = b.get_size()
    both = pygame.Surface((W * 2, H))
    both.blit(b, (0, 0))
    both.blit(a, (W, 0))
    os.makedirs("screenshots", exist_ok=True)
    name = time.strftime("screenshots/scape_before_after_%Y%m%d_%H%M%S.png")
    pygame.image.save(both, name)
    album_add(name)
    notify(f"Before / after saved: {name}", log=False)


# ---------------------------------------------------------------- 12: a day in the life, filmed as a camera tour
TOUR = {"on": False, "t": 0, "len": 1000, "clock0": 0.0, "hud": True}


def tour_toggle():
    if TOUR["on"]:
        tour_end()
        return
    if PM["on"] or REC["on"]:
        return
    TOUR.update(on=True, t=0, clock0=eco.clock, hud=eco.show_hud)
    eco.show_hud, eco.selected, eco.follow = False, None, False
    REC.update(on=True, frames=[], n=0, every=10)
    notify("Filming a tank tour: one whole day (Esc stops)", log=False)


def tour_end():
    TOUR["on"] = False
    eco.clock = TOUR["clock0"]
    eco.show_hud = TOUR["hud"]
    X["tours"] += 1
    rec_stop()


def apply_tour_cam(surface):
    if not TOUR["on"]:
        return
    TOUR["t"] += 1
    p = TOUR["t"] / TOUR["len"]
    ease = p * p * (3 - 2 * p)
    eco.clock = (TOUR["clock0"] + p) % 1.0
    zoom = 1.7
    vw, vh = SCREEN_WIDTH / zoom, SCREEN_HEIGHT / zoom
    x = (SCREEN_WIDTH - vw) * ease
    y = clamp(SCREEN_HEIGHT * 0.62 - vh / 2 + math.sin(p * math.tau) * SCREEN_HEIGHT * 0.07, 0, SCREEN_HEIGHT - vh)
    view = surface.subsurface(pygame.Rect(int(x), int(y), int(vw), int(vh))).copy()
    pygame.transform.scale(view, (SCREEN_WIDTH, SCREEN_HEIGHT), surface)
    if TOUR["t"] >= TOUR["len"]:
        rec_capture(surface)
        tour_end()
