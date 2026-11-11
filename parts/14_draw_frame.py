# ---------------------------------------------------------------- drawing
def draw_world21(surface):
    """Under the glass: sick-fish marks, favourite stars, the social web."""
    for f in fishes:
        if not hasattr(f, "persona"):
            continue
        d = getattr(f, "disease", "ich")
        x, y = int(f.pos.x), int(f.pos.y)
        if f.sick and d == "finrot":
            ang = math.atan2(f.vel.y, f.vel.x) + math.pi if f.vel.length_squared() > 0.01 else math.pi
            for k in range(4):
                a = ang + (k - 1.5) * 0.35
                r0, r1 = 24 * f.z, 36 * f.z
                pygame.draw.line(surface, (150, 40, 44), (x + math.cos(a) * r0, y + math.sin(a) * r0 * 0.6),
                                 (x + math.cos(a) * r1, y + math.sin(a) * r1 * 0.6), 2)
        elif f.sick and d == "swim" and eco.t % 90 < 6:
            pygame.draw.circle(surface, (200, 230, 255), (x + 10, y - int(30 * f.z)), 3, 1)
        if f.fav:
            sx, sy = x, y - int(38 * max(f.z, 0.5)) - 22
            pts = []
            for i in range(10):
                r = 7 if i % 2 == 0 else 3
                a = -math.pi / 2 + i * math.pi / 5
                pts.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
            pygame.draw.polygon(surface, (255, 220, 90), pts)
    if UI21["web"]:
        for f in fishes:
            if not hasattr(f, "persona"):
                continue
            if f.friend is not None and f.friend.alive and id(f) < id(f.friend):
                pygame.draw.line(surface, (110, 235, 150), f.pos, f.friend.pos, 2)
            if f.rival is not None and f.rival.alive and id(f) < id(f.rival):
                pygame.draw.line(surface, (255, 100, 90), f.pos, f.rival.pos, 2)
            if f.mourn > 0:
                pygame.draw.circle(surface, (150, 160, 230), (int(f.pos.x), int(f.pos.y)), int(30 * f.z) + 6, 1)
            if f.friend is not None or f.rival is not None or f.fav or f is eco.selected:
                lab = f21("s").render(f"{f.name} - {f.persona}", True, (235, 245, 255))
                surface.blit(lab, lab.get_rect(midtop=(int(f.pos.x), int(f.pos.y + 26 * max(f.z, 0.5)))))


def draw_card21(surface):
    f = eco.selected
    if f is None or not eco.show_hud or not hasattr(f, "persona") or isinstance(f, Predator):
        return
    lines = [(("* " if f.fav else "") + f.persona.upper() + ": " + PERSONA_TXT[f.persona], (255, 232, 140))]
    if f.friend is not None:
        lines.append((f"friend: {f.friend.name}", (130, 235, 160)))
    if f.rival is not None:
        lines.append((f"rival: {f.rival.name}", (255, 130, 120)))
    if f.mourn > 0:
        lines.append(("grieving a lost friend", (170, 180, 240)))
    if f.life_frac() > 0.8:
        lines.append(("elder: slower, paler", (200, 200, 205)))
    if f.sick:
        lines.append((DISEASES.get(getattr(f, "disease", "ich"), "sick"), (255, 160, 130)))
    g = gene_text(f)
    if g:
        lines.append((g, HUD_DIM))
    lines.append(("F6 rename  F7 star  F8 story", HUD_DIM))
    font = hud_font()
    panel = make_panel(250, 14 + 16 * len(lines))
    for i, (txt, col) in enumerate(lines):
        panel.blit(font.render(txt[:40], True, col), (10, 7 + 16 * i))
    surface.blit(panel, (12, 188 + 246 + 6))


def draw_hud21(surface):
    if screensaver:
        return
    if UI21["rename"] is not None and eco.selected is not None:
        s = f21("h").render(f"Rename {eco.selected.name}:  {UI21['rename']}_", True, (255, 240, 150))
        box = pygame.Rect(0, 0, max(380, s.get_width() + 40), 44)
        box.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120)
        pygame.draw.rect(surface, (8, 20, 40), box, border_radius=10)
        pygame.draw.rect(surface, (120, 190, 230), box, 2, border_radius=10)
        surface.blit(s, s.get_rect(center=box.center))
    if REC["on"] and eco.t % 60 < 40:
        pygame.draw.circle(surface, (235, 50, 50), (SCREEN_WIDTH - 26, 26), 7)
        surface.blit(hud_font().render(f"REC {len(REC['frames'])}", True, (255, 200, 200)), (SCREEN_WIDTH - 90, 20))
    if not eco.show_hud:
        return
    r = REQ["cur"]
    key = (X["points"], r["text"] if r else None, max(0, r["due"] - eco.day) if r else 0)
    cache = F21.get("hud")
    if cache is None or cache[0] != key:
        font = hud_font()
        h = 52 if r else 24
        panel = make_panel(430, h)
        panel.blit(font.render(f"POINTS {X['points']}   (, shop  / dashboard  ; test kit)", True, (255, 232, 140)), (10, 5))
        if r:
            pygame.draw.circle(panel, r.get("swatch", (150, 190, 220)), (20, 36), 7)
            panel.blit(font.render(("REQUEST: " + r["text"])[:56], True, (210, 225, 240)), (34, 22))
            panel.blit(font.render(f"+{r['reward']} pts   {key[2]} days left", True, HUD_DIM), (34, 36))
        cache = F21["hud"] = (key, panel)
    surface.blit(cache[1], (14, SCREEN_HEIGHT - 30 - cache[1].get_height()))


def bar21(panel, x, y, w, frac, col, label, val):
    txt21(panel, label, x, y - 2, "h")
    pygame.draw.rect(panel, (24, 44, 74), (x + 150, y, w, 14), border_radius=5)
    pygame.draw.rect(panel, col, (x + 150, y, max(3, int(w * clamp(frac))), 14), border_radius=5)
    txt21(panel, val, x + 160 + w, y - 1, "d", (210, 225, 240))


def chart21(panel, rect, data, color, title, fmt="{:.0f}"):
    x, y, w, h = rect
    pygame.draw.rect(panel, (14, 34, 60), rect, border_radius=6)
    txt21(panel, title, x + 8, y + 4, "d", (200, 215, 232))
    d = list(data)
    if len(d) >= 2:
        lo, hi = min(d), max(d)
        if hi - lo < 1e-6:
            hi = lo + 1.0
        pts = [(x + 8 + (w - 16) * i / (len(d) - 1), y + h - 10 - (h - 44) * (v - lo) / (hi - lo)) for i, v in enumerate(d)]
        pygame.draw.lines(panel, color, False, pts, 2)
        txt21(panel, fmt.format(d[-1]), x + w - 70, y + 4, "h", color)
        txt21(panel, f"{fmt.format(lo)} - {fmt.format(hi)}", x + 8, y + h - 18, "s", (130, 155, 185))
    else:
        txt21(panel, "collecting data...", x + 8, y + 40, "s", (130, 155, 185))


def draw_panel21(surface):
    p = UI21["panel"]
    if p is None:
        return
    if p == "ba":
        draw_ba(surface)
        return
    if p == "judge":
        draw_judge(surface)
        return
    if p == "story":
        f = eco.selected if (eco.selected is not None and hasattr(eco.selected, "persona")) else None
        if f is not None and not UI21["mem"]:
            panel = begin_panel(760, 130 + 24 * max(1, len(f.bio)), f"{f.name} the {nice_name(f)}")
            txt21(panel, f"{f.persona}  -  {PERSONA_TXT[f.persona]}  -  {f.life_stage()}  -  born day {f.born_day}", 26, 56)
            g = gene_text(f)
            if g:
                txt21(panel, g, 26, 76, "d", HUD_DIM)
            for i, (day, text) in enumerate(f.bio):
                txt21(panel, f"Day {day}", 26, 104 + 24 * i, "h", (255, 232, 140))
                txt21(panel, text, 110, 106 + 24 * i)
            end_panel(surface, panel, "Esc to close   M: memorial of lost fish")
        else:
            mem = X["memorial"][-14:][::-1]
            panel = begin_panel(860, 110 + 30 * max(1, len(mem)), f"Memorial   {len(X['memorial'])} remembered")
            if not mem:
                txt21(panel, "Nobody has been lost yet.", 26, 70)
            for i, m in enumerate(mem):
                y = 70 + 30 * i
                txt21(panel, f"{m['name']} the {m['cls']}", 26, y, "h", (255, 232, 140))
                txt21(panel, f"lived {m['days']} days, {m['persona']}, gen {m['gen']}  -  {m['cause']} (day {m['day']})", 300, y + 2)
            end_panel(surface, panel, "Esc to close   (select a fish and press F8 for its story)")
    elif p in ("sell", "care"):
        draw_care_panels(surface)
    elif p == "settings":
        draw_settings(surface)
    elif p == "hub":
        draw_hub(surface)
    elif p == "shop":
        panel = begin_panel(820, 120 + 52 * len(SHOP), f"Equipment shop   {X['points']} points")
        for i, (iid, name, cost, desc) in enumerate(SHOP):
            y = 70 + 52 * i
            own = iid != "oto" and iid in X["owned"]
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, name, 62, y, "h", (150, 230, 170) if own else (255, 232, 140) if X["points"] >= cost else (200, 215, 232))
            txt21(panel, desc, 62, y + 22, "d", HUD_DIM)
            txt21(panel, "OWNED" if own else f"{cost} pts", 700, y + 4, "h", (150, 230, 170) if own else (235, 245, 255))
        end_panel(surface, panel, "Press 1-7 to buy   Esc to close   (earn points from requests, shows, goals and the cycle)")
    elif p == "scape":
        sc = all_scapes()
        panel = begin_panel(720, 130 + 36 * len(sc), "Aquascapes")
        for i, s in enumerate(sc):
            y = 70 + 36 * i
            txt21(panel, f"{i + 1}", 26, y, "t", (130, 190, 235))
            txt21(panel, s["name"], 62, y + 2, "h", (255, 232, 140))
            txt21(panel, f"{len(s['layout']['items']) if isinstance(s.get('layout'), dict) else len(s['placed'])} pieces" + ("  (yours)" if i >= len(SCAPE_BUILTIN) else "  (preset)"), 260, y + 4, "d", HUD_DIM)
        end_panel(surface, panel, "1-9: replace the layout (your fish stay)   N: save the current layout   Esc: close")
    elif p == "test":
        c = CHEM
        panel = begin_panel(760, 540, "Water test kit")
        rows = [("Ammonia NH3", c["nh3"] / 2.0, c["nh3"] < 0.25, c["nh3"] < 0.6, f"{c['nh3']:.2f} ppm"),
                ("Nitrite NO2", c["no2"] / 2.0, c["no2"] < 0.25, c["no2"] < 0.8, f"{c['no2']:.2f} ppm"),
                ("Nitrate NO3", c["no3"] / 120.0, c["no3"] < 30, c["no3"] < 60, f"{c['no3']:.0f} ppm"),
                ("pH", (c["ph"] - 5.5) / 3.0, 6.6 <= c["ph"] <= 7.6, 6.2 <= c["ph"] <= 8.0, f"{c['ph']:.1f}"),
                ("Carbonate KH", c["kh"] / 20.0, KH_OK[0] <= c["kh"] <= KH_OK[1], KH_OK[0] - 1.5 <= c["kh"] <= KH_OK[1] + 4, f"{c['kh']:.1f} dKH"),
                ("General GH", c["gh"] / 20.0, GH_OK[0] <= c["gh"] <= GH_OK[1], GH_OK[0] - 2 <= c["gh"] <= GH_OK[1] + 4, f"{c['gh']:.1f} dGH")]
        for i, (lab, fr, good, ok, val) in enumerate(rows):
            bar21(panel, 26, 76 + 34 * i, 340, fr, (110, 215, 140) if good else (240, 200, 90) if ok else (240, 90, 80), lab, val)
        y = 294
        bar21(panel, 26, y, 340, c["b1"], (120, 190, 235), "Bacteria: ammonia", f"{int(c['b1'] * 100)}%")
        bar21(panel, 26, y + 34, 340, c["b2"], (120, 190, 235), "Bacteria: nitrite", f"{int(c['b2'] * 100)}%")
        status = "CYCLED" if c["done"] else "CYCLING: keep ammonia low with water changes (W) while the colonies grow"
        txt21(panel, status, 26, y + 72, "h", (150, 230, 170) if c["done"] else (255, 200, 120))
        hair = sum(HAIR) / GLASS_COLS
        glass = sum(eco.glass) / GLASS_COLS
        txt21(panel, f"Algae   hair {int(hair * 100)}%    diatom film {int(DIA[0] * 100)}%    glass film {int(glass * 100)}%", 26, y + 108, "h")
        txt21(panel, "Hair algae: shrimp, snails, otos, lights off, less nitrate.   Diatoms: they fade as the tank matures.   Glass: C to wipe.", 26, y + 132, "d", HUD_DIM)
        txt21(panel, "Fertiliser (')" + (f" active for {FERT['t'] // 60}s: plants grow, algae too" if FERT["t"] > 0 else " is not in the water")
              + "      CO2 diffuser: " + ("fitted" if "co2" in X["owned"] else "not fitted"), 26, y + 158, "d", HUD_DIM)
        end_panel(surface, panel, "Esc to close   (set \"new_tank\": true in aquarium_config.json to start with an uncycled tank)")
    elif p == "dash":
        panel = begin_panel(980, 640, "Tank dashboard")
        cw, ch = 460, 150
        specs = [("pop", (120, 200, 255), "Fish in the tank"), ("water", (110, 215, 140), "Water quality"),
                 ("births", (255, 200, 110), "Births (total)"), ("deaths", (255, 120, 110), "Deaths (total)"),
                 ("no3", (190, 150, 240), "Nitrate ppm"), ("temp", (255, 160, 90), "Temperature C")]
        for i, (k, col, title) in enumerate(specs):
            chart21(panel, (26 + (i % 2) * (cw + 20), 64 + (i // 2) * (ch + 12), cw, ch), DASH[k], col, title,
                    "{:.1f}" if k == "temp" else "{:.0f}")
        wk = X["weeks"][-1] if X["weeks"] else None
        if wk:
            txt21(panel, f"Week {wk['week']} summary (day {wk['day']}):  {wk['fish']} fish,  {wk['births']} born,  {wk['deaths']} lost,  "
                         f"water {wk['water']}%,  {wk['reqs']} requests filled", 26, 560, "h", (255, 232, 140))
        else:
            txt21(panel, "The first weekly summary appears after seven tank days.", 26, 560, "d", HUD_DIM)
        end_panel(surface, panel, "Esc to close   (a sample every ten seconds)")
    elif p == "album":
        items = album_load()[::-1]
        if UI21.get("best"):
            items = sorted(items, key=lambda a: -a.get("score", 0))
        per = 6
        pages = max(1, (len(items) + per - 1) // per)
        UI21["page"] = min(UI21["page"], pages - 1)
        panel = begin_panel(1040, 600, f"Photo album   {len(items)} photos   page {UI21['page'] + 1}/{pages}" + ("   BEST OF" if UI21.get("best") else ""))
        if not items:
            txt21(panel, "Press P to take a photo; it will be filed here with the day and the tank stats.", 26, 80)
        for i, a in enumerate(items[UI21["page"] * per:(UI21["page"] + 1) * per]):
            x, y = 26 + (i % 3) * 330, 70 + (i // 3) * 250
            th = ALB_THUMBS.get(a["file"])
            if th is None:
                try:
                    th = pygame.transform.smoothscale(pygame.image.load(a["file"]).convert(), (300, 169))
                except (pygame.error, OSError, FileNotFoundError):
                    th = pygame.Surface((300, 169))
                    th.fill((30, 40, 60))
                if len(ALB_THUMBS) > 24:
                    ALB_THUMBS.clear()
                ALB_THUMBS[a["file"]] = th
            panel.blit(th, (x, y))
            txt21(panel, f"Day {a.get('day', '?')}  {a.get('season', '')}  -  {a.get('when', '')}", x, y + 174, "h", (255, 232, 140))
            txt21(panel, f"{a.get('fish', '?')} fish, water {a.get('water', '?')}%   scape score {a.get('score', '?')}", x, y + 196)
        end_panel(surface, panel, "Left / Right: pages   B: best of / newest   Esc to close   (F12 records a timelapse clip into the same folder)")
    elif p == "show":
        rows = SHOWR["rows"]
        panel = begin_panel(700, 140 + 34 * max(1, len(rows)), f"Genetic show   day {SHOWR['day']}")
        for i, (sc, nm, mine) in enumerate(rows):
            y = 70 + 34 * i
            txt21(panel, f"#{i + 1}", 26, y, "t", (255, 232, 140) if i < 3 else (130, 150, 180))
            txt21(panel, nm, 90, y + 4, "h", (150, 235, 170) if mine else (200, 215, 232))
            txt21(panel, f"{sc:.1f}", 360, y + 4, "h")
            if mine and i < 3:
                txt21(panel, f"+{(25, 15, 8)[i]} points", 460, y + 6, "d", (255, 232, 140))
        txt21(panel, "Score: colour shift, tail, sheen, lace and fin shape, plus health and condition.", 26, 90 + 34 * max(1, len(rows)), "d", HUD_DIM)
        end_panel(surface, panel, "Esc to close   (one show every three tank days)")

GOALS.extend([
    ("seller", "Fish trader", "Sell a bred fish (7)", lambda: X["sold"] >= 1),
    ("chorer", "Tank keeper", "Finish a week of chores (8)", lambda: X["streak"] >= 1),
    ("challenger", "Challenge accepted", "Win a challenge (8)", lambda: len(X["chal_won"]) >= 1),
    ("raid", "Raid survivor", "Come through a predator raid without losses", lambda: X["raids"] >= 1 and X["points"] >= 0 and RAID["t"] < 0),
    ("friends", "Best friends", "Two fish become friends (F2 shows the web)", lambda: any(getattr(f, "friend", None) is not None for f in fishes)),
    ("memorial", "Gone but remembered", "A grown fish is added to the memorial (F8)", lambda: len(X["memorial"]) >= 1),
    ("lace", "Lace guppy", "Breed a lace-pattern guppy", lambda: any(isinstance(f, GuppyBase) and f.gen >= 2 and f.lace_on() for f in fishes)),
    ("request", "Special order", "Fill a breeding request", lambda: X["reqs"] >= 1),
    ("ribbon", "Blue ribbon", "Win the genetic show (F4)", lambda: X["wins"] >= 1),
    ("shopper", "Well equipped", "Buy something from the shop (,)", lambda: len(X["owned"]) >= 1),
    ("cycled", "Cycled tank", "Finish cycling a new tank (new_tank in the config)", lambda: CHEM["won"]),
    ("scaper", "Aquascaper", "Apply an aquascape preset (.)", lambda: X["scapes"] >= 1),
    ("director", "Director", "Record a timelapse clip (F12)", lambda: X["clips"] >= 1),
    ("guest", "Special guest", "A frog or kingfisher visits (show_visitors)", lambda: X["guests"] >= 1),
    ("lush", "Lush", "Dose fertiliser (')", lambda: X["ferts"] >= 1),
    ("designer", "Designer", "Score 90 or more from the judge in planting mode (Home)", lambda: X["best_scape"] >= 90),
    ("tourist", "Tour guide", "Record a tank tour GIF (PageDown)", lambda: X["tours"] >= 1),
    ("bloom", "In bloom", "A plant flowers in your tank", lambda: X["blooms"] >= 1),
])


def quit_game():
    if AWAY["on"] and current_state == STATE_AQUARIUM:
        try:
            save_game(AUTOSAVE_PATH, quiet=True)
        except Exception:
            pass
    pygame.quit()
    sys.exit()


def apply_away(sec):
    """The tank kept going while the app was closed: time passes, the water tires, hungry fish wait, guppies breed."""
    sec = min(float(sec), 8 * 3600.0)
    if sec < 180:
        return
    e = eco
    frames = sec * 60.0
    adv = e.clock + frames * 0.1 / DAY_LENGTH   # time away passes at a tenth of tank speed
    e.day += int(adv)
    e.clock = adv % 1.0
    hrs = sec / 3600.0
    water0 = e.water
    e.water = max(25.0, e.water - hrs * 7.0)
    for i in range(GLASS_COLS):
        e.glass[i] = min(1.0, e.glass[i] + hrs * 0.2 * GLASS_RATE[i])
    e.filter = max(0.05, e.filter - hrs * 0.12)
    for f in fishes:
        f.hunger = min(80.0, f.hunger + min(30.0, sec / 120.0))
        if f.age < f.lifespan * 0.96:
            f.age = min(f.age + frames * 0.25, f.lifespan * 0.96)
    ms = [f for f in fishes if isinstance(f, GuppyBase) and f.sex == "M" and f.growth >= 1.0]
    fs = [f for f in fishes if isinstance(f, GuppyBase) and f.sex == "F" and f.growth >= 1.0]
    broods = 0
    if ms and fs:
        for _ in range(min(3, int(hrs * 1.5))):
            give_birth(random.choice(ms), random.choice(fs))
            broods += 1
    stats["away"] += 1
    msg = f"Welcome back! Away {int(sec // 3600)}h {int(sec % 3600 // 60):02d}m"
    if broods:
        msg += f": {broods} guppy broods were born"
    notify(msg + f", water {water0:.0f}% -> {e.water:.0f}%")


def try_autoload():
    if not os.path.exists(AUTOSAVE_PATH):
        return
    try:
        load_game(AUTOSAVE_PATH, away=True)
    except Exception as err:
        print("autosave could not be loaded:", err)
        init_ecosystem()
        fishes[:] = spawn_community()


def spawn_visitor():
    side = random.choice([-1, 1])
    b = Channa(-90 if side == 1 else SCREEN_WIDTH + 90, random.randint(160, 340), visitor=True)
    b.vel = pygame.Vector2(side * 2.0, 0)
    predators.append(b)


def update_mouse_track():
    mx, my = world_mouse(pygame.mouse.get_pos())
    p = pygame.Vector2(mx, my)
    speed = p.distance_to(mouse_track["pos"])
    mouse_track["speed"] += (speed - mouse_track["speed"]) * 0.3
    mouse_track["still"] = mouse_track["still"] + 1 if speed < 2.5 else 0
    mouse_track["pos"] = p
    mouse_track["inside"] = bool(pygame.mouse.get_focused()) and 0 <= mx < SCREEN_WIDTH \
        and WATER_TOP < my < SCREEN_HEIGHT - SAND_HEIGHT


def process_respawns():
    for item in respawn_queue[:]:
        due, kind = item
        if eco.t < due:
            continue
        respawn_queue.remove(item)
        if kind == "fish":
            nf = spawn_random_fish()
            if not has_room(type(nf)):
                respawn_queue.append((eco.t + 600, "fish"))  # tank is full: the newcomer waits
                continue
            side = random.choice([-1, 1])
            nf.pos = pygame.Vector2(30 if side == 1 else SCREEN_WIDTH - 30,
                                    random.randint(WATER_TOP + 80, SCREEN_HEIGHT - 150))
            nf.vel = pygame.Vector2(side * 1.5, 0)
            fishes.append(nf)
            eco.births += 1
        else:
            shimps.append(TinyShrimp())


def update_daphnia(k):
    """Daphnia drift on a lazy wander, ride the current, and jump away from fish that get close."""
    k.phase += 0.02
    k.apply_force(pygame.Vector2(math.cos(k.phase * 1.3), math.sin(k.phase)) * 0.012)
    k.apply_force(pygame.Vector2(eco.current * 0.6, 0))
    for f in fishes:
        off = k.pos - f.pos
        if off.length_squared() < 50 * 50:
            k.apply_force(unit(off) * 0.9)
            break
    k.update()
    if k.pos.x < 10:
        k.vel.x = abs(k.vel.x)
    elif k.pos.x > SCREEN_WIDTH - 10:
        k.vel.x = -abs(k.vel.x)
    if k.pos.y < WATER_TOP + 30:
        k.vel.y = abs(k.vel.y)
    elif k.pos.y > SCREEN_HEIGHT - 70:
        k.vel.y = -abs(k.vel.y)


def shrimp_flee(s):
    for p in predators:
        if isinstance(p, Crayfish) and p.state in ("hunt", "flee"):
            off = s.pos - p.pos
            if off.length_squared() < 110 * 110:
                s.pos += unit(off) * 1.6


night_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)


def draw_daylight(surface):
    lt = SCAPE.get("light")
    if isinstance(lt, dict) and eco.lights != "OFF" and not eco.power:   # LED colour temperature: 6500K neutral, 10000K blue-violet
        t = clamp((float(lt.get("kelvin", 6500)) - 6500.0) / 3500.0, -1.0, 1.0)
        a = int(34 * abs(t) * eco.daylight * (1.0 - eco.night))
        if a > 0:
            night_surf.fill((70, 105, 255, a) if t > 0 else (255, 170, 90, a))
            surface.blit(night_surf, (0, 0))
            if t > 0:
                night_surf.fill((255, 60, 110, a // 3))     # the red channel of a blue/red LED set
                surface.blit(night_surf, (0, 0))
    alpha = int(eco.night * 105)
    if alpha > 0:
        night_surf.fill((6, 12, 48, alpha))
        surface.blit(night_surf, (0, 0))
    dusk = clamp(1.0 - abs(eco.daylight - 0.42) / 0.2)
    if dusk > 0.03:
        night_surf.fill((255, 120, 60, int(40 * dusk)))
        surface.blit(night_surf, (0, 0))
    murk = clamp((60 - eco.water) / 60)  # dirty water turns murky green
    if murk > 0.02:
        night_surf.fill((70, 100, 40, int(95 * murk)))
        surface.blit(night_surf, (0, 0))
    if eco.dark > 0.02:   # blackouts and storm clouds
        night_surf.fill((2, 4, 14, int(eco.dark * 80)))
        surface.blit(night_surf, (0, 0))
    if eco.flash > 0.03:   # lightning
        night_surf.fill((235, 240, 255, int(170 * eco.flash)))
        surface.blit(night_surf, (0, 0))
    if eco.blue > 0:   # methylene blue tints the water
        night_surf.fill((40, 100, 230, int(70 * min(1.0, eco.blue / 400.0))))
        surface.blit(night_surf, (0, 0))
    if eco.cloud > 0.03:   # overfed: cloudy water
        night_surf.fill((200, 210, 200, int(75 * eco.cloud)))
        surface.blit(night_surf, (0, 0))


def draw_fx(surface):
    for f in fx[:]:
        f.update()
        if f.life <= 0:
            fx.remove(f)
        else:
            f.draw(surface)
    for ink in inks[:]:
        ink.update()
        if ink.age >= ink.life:
            inks.remove(ink)
        else:
            ink.draw(surface)
    for r in ripples[:]:
        r[1] += 4.0
        r[2] -= 1
        if r[2] <= 0:
            ripples.remove(r)
            continue
        col = mix((20, 50, 100), (220, 240, 255), r[2] / 50.0)
        pygame.draw.circle(surface, col, (int(r[0].x), int(r[0].y)), int(r[1]), 2)


_hud_font = None
_day_strip = None


def hud_font():
    global _hud_font
    if _hud_font is None:
        _hud_font = pygame.font.SysFont("Arial", 13, bold=True)
    return _hud_font


HUD_DIM = (150, 175, 205)


def draw_bar(panel, label, x, y, value, color, width=150):
    panel.blit(hud_font().render(label, True, HUD_DIM), (x, y - 5))
    pygame.draw.rect(panel, (40, 55, 80), (x + 46, y, width, 6), border_radius=3)
    pygame.draw.rect(panel, color, (x + 46, y, int(width * clamp(value)), 6), border_radius=3)


def make_panel(w, h):
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (6, 18, 38, 195), (0, 0, w, h), border_radius=10)
    pygame.draw.rect(panel, (130, 180, 230, 110), (0, 0, w, h), 1, border_radius=10)
    return panel


def draw_hud(surface):
    global _day_strip
    if not eco.show_hud:
        return
    font = hud_font()
    if _day_strip is None:
        _day_strip = pygame.Surface((220, 6))
        for x in range(220):
            dl = 0.5 + 0.5 * math.sin(math.tau * (x / 220 - 0.25))
            pygame.draw.line(_day_strip, mix((24, 32, 80), (255, 215, 120), dl), (x, 0), (x, 5))
    panel = make_panel(250, 168)
    panel.blit(font.render("TANK MOOD", True, HUD_DIM), (12, 8))
    panel.blit(font.render(eco.tank_mood, True, MOOD_COLORS.get(eco.tank_mood, (230, 230, 230))), (92, 8))
    panel.blit(_day_strip, (12, 32))
    mx = 12 + int(eco.clock * 220)
    pygame.draw.circle(panel, (255, 255, 255) if eco.daylight > 0.3 else (190, 200, 255), (mx, 35), 5)
    pygame.draw.circle(panel, (30, 50, 90), (mx, 35), 5, 1)
    if eco.night > 0.5:
        phase = "NIGHT"
    elif eco.daylight < 0.55 and eco.clock < 0.5:
        phase = "DAWN"
    elif eco.daylight < 0.55:
        phase = "DUSK"
    else:
        phase = "DAY"
    if not eco.cycle_on:
        phase += " (paused)"
    if eco.full_moon and eco.night > 0.3:
        phase += "  - FULL MOON"
    panel.blit(font.render(phase, True, HUD_DIM), (12, 44))
    panel.blit(font.render(f"Day {eco.day}", True, (225, 235, 245)), (200, 44))
    draw_bar(panel, "FEAR", 12, 70, max(eco.fear, eco.avg_fear), mix((255, 210, 90), (255, 70, 70), max(eco.fear, eco.avg_fear)))
    draw_bar(panel, "WATER", 12, 88, eco.water / 100, mix((255, 90, 70), (90, 220, 170), eco.water / 100))
    panel.blit(font.render(f"Prey {len(fishes)}/{tank_capacity()}   Hunters {len(predators)}   Caught {eco.kills}   Born {eco.births}", True,
                           (225, 235, 245)), (12, 102))
    tool = DECOR_TOOLS[eco.decor_idx]
    panel.blit(font.render(f"Feed: {FEEDS[eco.feed_idx]}" + (f"   Build: {tool}" if tool != "OFF" else ""), True,
                           (200, 225, 255)), (12, 120))
    line = eco.event if eco.event else "F1 help  H hud  J journal  P photo  W water"
    panel.blit(font.render(line, True, (255, 230, 150) if eco.event else HUD_DIM), (12, 138))
    surface.blit(panel, (12, 12))


SPECIES_INFO = {
    "DemasoniCichlid": ("Pseudotropheus demasoni", "A tiny Malawi mbuna that lives in dense, feisty rock-dwelling groups."),
    "YellowPrinceCichlid": ("", "A golden rock-dweller that claims a cave and defends it."),
    "CobaltZebra": ("Maylandia callainos", "Males are vivid cobalt blue; they graze algae off the rocks."),
    "RedZebra": ("Maylandia estherae", "The orange females are the ones called red zebras."),
    "KenyiCichlid": ("Maylandia lombardoi", "Males turn bright yellow with age and guard their territory."),
    "PeacockCichlid": ("Aulonocara sp.", "Males flash electric colours to impress females over the sand."),
    "AuratusCichlid": ("Melanochromis auratus", "A gold-striped mbuna; males darken and turn bold."),
    "IceBlueCichlid": ("", "A pale blue Malawi cichlid that grazes the rocks."),
    "SocolofiCichlid": ("Pseudotropheus socolofi", "A pastel-blue mbuna, one of the milder ones."),
    "AulonocaraOB": ("Aulonocara sp. OB", "A calico-marbled peacock: orange, blue and black blotches that are different on every fish."),
    "GermanRedPeacock": ("Aulonocara sp. 'rubin red'", "A blood-orange peacock with an iridescent blue face; a classic showpiece."),
    "SunshinePeacock": ("Aulonocara baenschi", "A bright yellow peacock with a neon-blue head and back."),
    "CopadichromisBorleyi": ("Copadichromis borleyi", "An open-water hap: deep metallic blue with orange-red fins."),
    "ElectricBlueHap": ("Sciaenochromis fryeri", "A sleek electric-blue predator that cruises open water and picks off fry."),
    "SynodontisCatfish": ("Synodontis sp.", "A mottled catfish with three pairs of barbels; scavenges at night among the Malawi cichlids."),
    "AngelFish": ("Pterophyllum scalare", "A tall Amazon cichlid; pairs guard eggs on broad leaves."),
    "NeonTetra": ("Paracheirodon innesi", "Its blue stripe stays visible in dim water so the shoal keeps together."),
    "RummyNose": ("Hemigrammus rhodostomus", "A red nose shows good health; the shoal turns in tight lockstep."),
    "CardinalTetra": ("Paracheirodon axelrodi", "Its red stripe runs the whole body, longer than a neon's."),
    "EmberTetra": ("Hyphessobrycon amandae", "A tiny, glowing orange tetra under two centimetres long."),
    "BlackSkirtTetra": ("Gymnocorymbus ternetzi", "The dark skirt fin gives it away; a bold, playful shoaler."),
    "LemonTetra": ("Hyphessobrycon pulchripinnis", "A glassy yellow body with a black-edged anal fin."),
    "MosaicGuppy": ("Poecilia reticulata", "A livebearer: females give birth to free-swimming fry."),
    "TuxedoGuppy": ("Poecilia reticulata", "Dark rear half, pale front: the tuxedo pattern is bred in."),
    "SunsetGuppy": ("Poecilia reticulata", "Males carry broad sweeps of red and orange in the tail."),
    "MoscowGuppy": ("Poecilia reticulata", "Prized for solid deep blue or black males."),
    "Pleco": ("Pterygoplichthys sp.", "An armoured algae grazer with a sail-like fin and a sucker mouth."),
    "BalaShark": ("Balantiocheilos melanopterus", "Not a shark: a silver minnow that needs long runs of open water."),
    "BoesemaniRainbow": ("Melanotaenia boesemani", "Half blue-grey, half orange; the colours deepen with age."),
    "PearlGourami": ("Trichopodus leerii", "Males build bubble nests; the thread-like fins are feelers."),
    "ClownLoach": ("Chromobotia macracanthus", "Bold bands, and groups that sometimes rest on their sides."),
    "TigerBarb": ("Puntigrus tetrazona", "Four black bars on a busy shoaler known for nipping fins."),
    "Corydoras": ("Corydoras aeneus", "Sifts the sand with its barbels and sometimes darts up to gulp air."),
    "Otocinclus": ("Otocinclus affinis", "A tiny grazer that clings to glass, leaves and wood."),
    "BristlenosePleco": ("Ancistrus sp.", "Males grow fleshy bristles on the snout; shy by day."),
    "Betta": ("Betta splendens", "Males flare their huge fins at rivals and blow a bubble nest."),
    "Discus": ("Symphysodon aequifasciatus", "A calm, disc-shaped cichlid; pairs stay close."),
    "Killifish": ("Aplocheilus lineatus", "A surface-dwelling hunter of fallen insects."),
    "Channa": ("Channa sp.", "A snakehead: it breathes air, ambushes from cover and guards a bubble nest."),
    "FireEel": ("Mastacembelus erythrotaenia", "A spiny eel that hides in rocks and sand and strikes from cover."),
    "Crayfish": ("", "A scavenger that lurks in rock lairs and pounces on shrimp."),
}
PORTRAITS = {}
_card_fonts = {}


def card_font(italic=False):
    f = _card_fonts.get(italic)
    if f is None:
        f = _card_fonts[italic] = pygame.font.SysFont("Arial", 12, italic=italic)
    return f


def portrait(f):
    """A small cached picture of the fish for its card, drawn side-on by the fish's own renderer."""
    key = (type(f).__name__, getattr(f, "id", 0), round(f.z * 20), getattr(f, "gene_key", 0), getattr(f, "sex", ""))
    if key in PORTRAITS:
        return PORTRAITS[key]
    canvas = pygame.Surface((320, 220), pygame.SRCALPHA)
    old_pos, old_vel, old_angle = f.pos.copy(), f.vel.copy(), getattr(f, "angle", 0.0)
    try:
        f.pos.update(160, 110)
        f.vel.update(1, 0)
        f.angle = 0.0
        f.draw(canvas)
    except Exception:
        canvas = None
    finally:
        f.pos.update(old_pos)
        f.vel.update(old_vel)
        f.angle = old_angle
    img = None
    if canvas is not None:
        r = canvas.get_bounding_rect()
        if r.w > 4 and r.h > 4:
            crop = canvas.subsurface(r)
            k = min(84 / r.w, 56 / r.h, 1.6)
            img = pygame.transform.smoothscale(crop, (max(1, int(r.w * k)), max(1, int(r.h * k))))
    if len(PORTRAITS) > 120:
        PORTRAITS.clear()
    PORTRAITS[key] = img
    return img


def species_footer(panel, f, y0):
    pygame.draw.line(panel, (130, 180, 230, 80), (12, y0 - 5), (238, y0 - 5))
    pic = portrait(f)
    if pic is not None:
        panel.blit(pic, pic.get_rect(center=(52, y0 + 32)))
    latin, fact = SPECIES_INFO.get(type(f).__name__, ("", ""))
    y = y0
    if latin:
        panel.blit(card_font(True).render(latin, True, (200, 225, 255)), (100, y))
        y += 15
    words, line = fact.split(), ""
    for w in words:
        trial = (line + " " + w).strip()
        if card_font().size(trial)[0] > 138 and line:
            panel.blit(card_font().render(line, True, HUD_DIM), (100, y))
            y += 13
            line = w
        else:
            line = trial
    if line:
        panel.blit(card_font().render(line, True, HUD_DIM), (100, y))


def draw_card(surface):
    f = eco.selected
    if f is None or not eco.show_hud:
        return
    font = hud_font()
    panel = make_panel(250, 246)
    panel.blit(font.render(f"{f.name} the {nice_name(f)}", True, (255, 240, 150)), (12, 8))
    if isinstance(f, Predator):
        panel.blit(font.render(f"{f.mood.upper()}  -  hunter  -  {f.kills} caught", True, HUD_DIM), (12, 26))
        draw_bar(panel, "HUNGER", 12, 52, f.hunger / 100, mix((120, 220, 150), (255, 90, 70), f.hunger / 100))
        draw_bar(panel, "ALERT", 12, 70, clamp(f.flash), mix((255, 210, 90), (255, 70, 70), clamp(f.flash)))
        draw_bar(panel, "ANNOY", 12, 88, clamp(f.annoyance / 900), (230, 150, 90))
        draw_bar(panel, "SPEED", 12, 106, clamp(f.vel.length() / max(f.strike_speed, 1)), (120, 180, 255))
        panel.blit(font.render("Z: follow cam   click empty water: drop", True, HUD_DIM), (12, 138))
    else:
        sex = {"M": "male", "F": "female"}.get(getattr(f, "sex", ""), "")
        panel.blit(font.render(f"{f.mood.upper()}  -  {f.life_stage()} {sex}" + ("  -  SICK" if f.sick else ""), True, HUD_DIM), (12, 26))
        draw_bar(panel, "HUNGER", 12, 52, f.hunger / 100, mix((120, 220, 150), (255, 90, 70), f.hunger / 100))
        draw_bar(panel, "FEAR", 12, 70, f.fear, mix((255, 210, 90), (255, 70, 70), f.fear))
        draw_bar(panel, "STRESS", 12, 88, f.stress / 100, (230, 150, 90))
        draw_bar(panel, "BRAVE", 12, 106, f.bravery, (120, 180, 255))
        draw_bar(panel, "AGE", 12, 124, clamp(f.life_frac()), mix((150, 220, 255), (200, 200, 205), clamp(f.life_frac())))
        note = ""
        if f.partner is not None and f.partner.alive:
            note = f"mate: {f.partner.name}"
        if f.guard_t > 0:
            note = (note + "  " if note else "") + "guarding"
        if getattr(f, "gen", 0) > 1 and len(f.parents) == 2:
            note = f"gen {f.gen}: {f.parents[0].name} x {f.parents[1].name}"[:36]
        panel.blit(font.render(note or "Z: follow cam   click empty water: drop", True, HUD_DIM), (12, 138))
    species_footer(panel, f, 164)
    surface.blit(panel, (12, 188))


def draw_journal(surface):
    if not eco.show_journal:
        return
    font = hud_font()
    entries = journal[-10:]
    panel = make_panel(380, 30 + 17 * max(1, len(entries)))
    panel.blit(font.render("JOURNAL", True, (255, 240, 150)), (12, 7))
    for i, (stamp, text) in enumerate(entries):
        line = f"{stamp}  {text}"
        panel.blit(font.render(line[:56], True, (210, 225, 240) if i == len(entries) - 1 else HUD_DIM), (12, 28 + 17 * i))
    surface.blit(panel, (SCREEN_WIDTH - 392, 56))


def draw_ui(surface):
    draw_hud(surface)
    draw_card(surface)
    draw_journal(surface)
