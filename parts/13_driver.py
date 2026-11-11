# ---------------------------------------------------------------- 20: dashboard
def dash_sample():
    DASH["pop"].append(len(fishes))
    DASH["water"].append(eco.water)
    DASH["births"].append(eco.births)
    DASH["deaths"].append(stats.get("deaths", 0))
    DASH["no3"].append(CHEM["no3"])
    DASH["temp"].append(eco.temp)
    DASH["ph"].append(CHEM["ph"])
    DASH["gh"].append(CHEM["gh"])
    DASH["kh"].append(CHEM["kh"])
    DASH["points"].append(X["points"])
    DASH["cash"].append(X["cash"])
    WEEK["water"].append(eco.water)


def week_tick():
    if "init" not in WEEK:
        WEEK.update(init=True, day=eco.day, births=eco.births, deaths=stats.get("deaths", 0), reqs=X["reqs"])
    if eco.day - WEEK["day"] < 7:
        return
    w = WEEK["water"]
    summary = {"week": len(X["weeks"]) + 1, "fish": len(fishes), "births": eco.births - WEEK["births"],
               "deaths": stats.get("deaths", 0) - WEEK["deaths"], "reqs": X["reqs"] - WEEK["reqs"],
               "water": int(sum(w) / len(w)) if w else int(eco.water), "day": eco.day}
    X["weeks"].append(summary)
    del X["weeks"][:-8]
    WEEK.update(day=eco.day, births=eco.births, deaths=stats.get("deaths", 0), reqs=X["reqs"], water=[])
    notify(f"Week {summary['week']} summary is ready (press /)", log=True)
    save_prefs()


# ---------------------------------------------------------------- per-frame driver
def unattended_tick():
    """Wallpaper mode: heal everything every frame, so the tank can run for days with nobody there."""
    if eco.event in ("THUNDERSTORM", "POWER CUT", "CHANNA VISITOR"):
        eco.end_event()
    eco.power = False
    eco.fear = 0.0
    eco.cloud = min(eco.cloud, 0.05)
    eco.filter = max(eco.filter, 0.9)
    eco.water = max(eco.water, 88.0)
    eco.overgrown = min(eco.overgrown, 0.3)
    if EV["name"] in ("cold snap", "heat wave", "leaf fall"):
        EV.update(name=None, dt=0.0)
    EV["dt"] = 0.0
    CAT["t"] = 0
    RAID["t"] = -1
    c = CHEM
    c["nh3"], c["no2"] = 0.0, 0.0
    c["no3"] = min(c["no3"], 15.0)
    c["kh"] = max(c["kh"], 4.0)
    for i in range(len(HAIR)):
        HAIR[i] = min(HAIR[i], 0.05)
    del DEB[:]
    for p in predators[:]:
        if getattr(p, "visitor", False):
            predators.remove(p)
        else:
            p.hunger = min(p.hunger, 15.0)
    for f in fishes:
        f.hunger = min(f.hunger, 55.0)
        f.health = max(getattr(f, "health", 1.0), 1.0)
        if hasattr(f, "stress"):
            f.stress = min(f.stress, 12.0)
        if getattr(f, "sick", False):
            f.sick, f.sick_t = False, 0
            f.immune = 5400


def fw21_update():
    t = eco.t
    if unattended():
        unattended_tick()
    if FERT["t"] > 0:
        FERT["t"] -= 1
    if t % 60 == 0:
        chem_tick()
        algae_tick()
        shop_tick()
    if t % 30 == 0:
        sound_tick()
    if t % 300 == 0 and (FERT["t"] > 0 or "co2" in X["owned"]):
        k = 1.0 + (0.03 if FERT["t"] > 0 else 0.0) + (0.02 if "co2" in X["owned"] else 0.0)
        for p in plants:
            if p.species in TALL_PLANTS:
                if not hasattr(p, "base_h"):
                    p.base_h = p.height
                if p.height < p.base_h * 1.8:
                    scale_plant(p, k)
    if t % 600 == 0:
        dash_sample()
        week_tick()
        for f in fishes:
            if getattr(f, "fav", False):
                if f.fav_cd <= 0 and (f.sick or f.hunger > 85):
                    notify(f"* {f.name} " + ("is sick" if f.sick else "is very hungry"), log=False)
                    f.fav_cd = 3000
                else:
                    f.fav_cd -= 600
    request_tick()
    if t % 120 == 0:
        rank_tick()
    raid_tick()
    fw6_update()
    if t % 600 == 0:
        plant_care()
        chore_tick()
        chal_tick()
        check_goals()


def save21():
    return {"chem": dict(CHEM), "hair": [round(h, 3) for h in HAIR], "dia": DIA[0], "fert": FERT["t"],
            "req": REQ["cur"], "req_next": REQ["next"],
            "eq": dict(EQ), "ev": dict(EV), "debs": DEBS[0]}


def load21(d):
    if not isinstance(d, dict):
        return
    try:
        c = d.get("chem")
        if isinstance(c, dict):
            for k in CHEM:
                v = c.get(k)
                if isinstance(CHEM[k], bool):
                    if isinstance(v, bool):
                        CHEM[k] = v
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    CHEM[k] = type(CHEM[k])(v)
        h = d.get("hair")
        if isinstance(h, list) and len(h) == GLASS_COLS:
            HAIR[:] = [clamp(float(v)) for v in h]
        DIA[0] = clamp(float(d.get("dia", 0.0)))
        FERT["t"] = int(d.get("fert", 0))
        r = d.get("req")
        REQ["cur"] = r if isinstance(r, dict) and "cls" in r and "text" in r else None
        if REQ["cur"]:
            REQ["cur"]["swatch"] = tuple(REQ["cur"].get("swatch", (150, 190, 220)))
        REQ["next"] = int(d.get("req_next", 2))
        for src, dst in ((d.get("eq"), EQ), (d.get("ev"), EV)):
            if isinstance(src, dict):
                for k in dst:
                    v = src.get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and isinstance(dst[k], (int, float)):
                        dst[k] = int(v) if k in ("sd", "until", "start", "b0") else float(v)
                    elif isinstance(v, str) or v is None and k == "name":
                        dst[k] = v
        DEBS[0] = int(clamp(float(d.get("debs", 0)), 0, 60))
    except (TypeError, ValueError):
        pass


# ---------------------------------------------------------------- events
def fw21_event(e):
    """Returns True when the event was used here (rename typing, panel keys, the new hotkeys)."""
    u = UI21
    if e.type == pygame.KEYDOWN:
        TUTF.add(e.key)
    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        TUTF.add("click")
    if hand_event(e):
        return True
    if e.type == pygame.MOUSEBUTTONDOWN:
        return u["panel"] is not None or u["rename"] is not None
    if e.type != pygame.KEYDOWN:
        return False
    k = e.key
    if u["rename"] is not None:
        f = eco.selected
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            nm = u["rename"].strip()
            if nm and f is not None:
                story(f, f"Renamed from {f.name} to {nm}")
                f.name = nm
                notify(f"Renamed to {nm}", log=False)
            u["rename"] = None
        elif k == pygame.K_ESCAPE:
            u["rename"] = None
        elif k == pygame.K_BACKSPACE:
            u["rename"] = u["rename"][:-1]
        elif getattr(e, "unicode", "") and e.unicode.isprintable() and len(u["rename"]) < 14:
            u["rename"] += e.unicode
        return True
    p = u["panel"]
    if p is not None:
        if k == pygame.K_ESCAPE:
            u["panel"] = None
            return True
        if k in (pygame.K_g, pygame.K_TAB, pygame.K_F1):
            u["panel"] = None
            return False
        if p == "settings" and settings_key(k):
            return True
        if p == "hub":
            return hub_key(k)
        if p == "sell" and pygame.K_1 <= k <= pygame.K_9:
            sell_fish(k - pygame.K_1)
            return True
        if p == "care" and pygame.K_1 <= k <= pygame.K_4:
            if X["chal"] and X["chal"].get("id") == CHALLENGES[k - pygame.K_1][0]:
                X["chal"] = {}
                notify("Challenge abandoned", log=False)
            else:
                chal_start(k - pygame.K_1)
            return True
        if p == "shop" and pygame.K_1 <= k <= pygame.K_7:
            buy_item(k - pygame.K_1)
            return True
        if p == "scape":
            if pygame.K_1 <= k <= pygame.K_9:
                sc = all_scapes()
                if k - pygame.K_1 < len(sc):
                    apply_scape(sc[k - pygame.K_1])
                return True
            if k == pygame.K_n:
                save_scape()
                return True
        if p == "album" and k == pygame.K_b:
            UI21["best"] = not UI21.get("best", False)
            UI21["page"] = 0
            return True
        if p == "album" and k in (pygame.K_LEFT, pygame.K_RIGHT):
            u["page"] = max(0, u["page"] + (1 if k == pygame.K_RIGHT else -1))
            return True
        if p == "story" and k == pygame.K_m:
            u["mem"] = not u["mem"]
            return True
        if p == "show" and k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            run_show()
            return True
        if p == "ba" and k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            ba_save()
            return True
    if k == pygame.K_F2:
        u["web"] = not u["web"]
        notify("Social web: " + ("ON (green friends, red rivals)" if u["web"] else "OFF"), log=False)
    elif k == pygame.K_F4:
        if p == "show":
            u["panel"] = None
        elif run_show() or SHOWR["rows"]:
            set_panel("show")
    elif k == pygame.K_F6:
        f = eco.selected
        if f is not None and hasattr(f, "persona"):
            u["rename"] = ""
        else:
            notify("Select a fish first (Shift-click), then press F6 to rename it", log=False)
    elif k == pygame.K_F7:
        f = eco.selected
        if f is not None and hasattr(f, "persona"):
            f.fav = not f.fav
            notify(f"{f.name} {'is now a favourite' if f.fav else 'is no longer a favourite'}", log=False)
        else:
            notify("Select a fish first (Shift-click), then press F7 to star it", log=False)
    elif k == pygame.K_F8:
        set_panel("story")
    elif k == pygame.K_COMMA:
        set_panel("shop")
    elif k == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
        SET["mode"], SET["slots"] = None, None
        set_panel("settings")
    elif k == pygame.K_DELETE:
        set_panel("hub")
    elif k == pygame.K_7:
        set_panel("sell")
    elif k == pygame.K_8:
        set_panel("care")
    elif k == pygame.K_PERIOD:
        set_panel("scape")
    elif k == pygame.K_SLASH:
        set_panel("dash")
    elif k == pygame.K_SEMICOLON:
        set_panel("test")
    elif k == pygame.K_QUOTE:
        dose_fert()
    elif k == pygame.K_BACKQUOTE:
        cycle_sound()
    elif k == pygame.K_PAGEUP:
        set_panel("album")
    elif k == pygame.K_F12:
        rec_toggle()
    else:
        return False
    return True
