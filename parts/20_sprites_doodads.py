# ---- turning and facing: a fish swings round through an end-on view instead of flipping, and sometimes faces the glass ----
# f.ph is the fish's facing angle: 0 = side view facing right, 90 = end-on (towards or away from the viewer), 180 = side view
# facing left. A turn sweeps ph from one side to the other; while it passes 90 the side sprite narrows and fades into a
# front-view sprite (head, eyes, spread pectorals) or a back-view sprite (tail fan seen edge-on).
TURN_RATE, GAZE_RATE = 13.0, 6.0       # degrees per frame: a flip takes about a quarter of a second
FRONT_W = {"AngelFish": 0.2, "Discus": 0.28, "Pleco": 0.9, "BristlenosePleco": 0.9, "SynodontisCatfish": 0.8, "Otocinclus": 0.8,
           "Corydoras": 0.8, "ClownLoach": 0.6, "BalaShark": 0.45, "Betta": 0.4, "PearlGourami": 0.4}
VIEW_CACHE = {}
YAW_MOUSE = [-1, (-999.0, -999.0)]


def _mouse_world():
    if YAW_MOUSE[0] != eco.t:
        YAW_MOUSE[0] = eco.t
        try:
            YAW_MOUSE[1] = world_mouse(pygame.mouse.get_pos()) if pygame.mouse.get_focused() else (-999.0, -999.0)
        except pygame.error:
            YAW_MOUSE[1] = (-999.0, -999.0)
    return YAW_MOUSE[1]


def yaw_update(f):
    """Advance the fish's facing angle one frame."""
    if getattr(f, "ph", None) is None:
        f.ph = f.side = 0.0 if f.vel.x >= 0 else 180.0
        f.gaze, f.gaze_t, f.endon, f.last_goal = 0, 0, "front", f.side
        return
    sp = f.vel.length()
    if f.vel.x > 0.12:
        f.side = 0.0
    elif f.vel.x < -0.12:
        f.side = 180.0
    goal, rate = f.side, TURN_RATE
    if f.gaze:
        f.gaze_t -= 1
        if f.gaze_t <= 0 or sp > 0.7 or (f.gaze == 1 and getattr(f, "fear", 0.0) > 0.55):
            f.gaze = 0
        else:
            goal, rate = 90.0, GAZE_RATE
    elif sp < 0.45 and getattr(f, "growth", 1.0) >= 0.5 and not getattr(f, "hidden", False):
        r = random.random()
        if r < 0.02:
            mx, my = _mouse_world()
            near = (mx - f.pos.x) ** 2 + (my - f.pos.y) ** 2 < 150 * 150
        else:
            near = False
        if near or r < 0.003:     # curious about the cursor, or just idling: turn to face the glass (or turn its back on it)
            back = getattr(f, "sleepy", 0.0) > 0.5 or getattr(f, "fear", 0.0) > 0.35 or random.random() < 0.15
            f.gaze, f.gaze_t = (2 if back else 1), random.randint(100, 320)
            f.endon = "back" if back else "front"
            goal, rate = 90.0, GAZE_RATE
    if goal != f.last_goal and not f.gaze:
        f.endon = "front" if random.random() < 0.55 else "back"
    f.last_goal = goal
    d = goal - f.ph
    f.ph += max(-rate, min(rate, d))


def view_sprite(f, back):
    """The fish seen end-on, painted from the species' own palette: front = face, eyes and spread pectorals; back = a tail fan."""
    name = type(f).__name__
    key = (name, f.id if getattr(f, "unique", False) else 0, round(f.z * 20), back, getattr(f, "sex", ""), round(f.vigor() * 3),
           getattr(f, "look", 0), getattr(f, "gene_key", 0))
    spr = VIEW_CACHE.get(key)
    if spr is not None:
        return spr
    if len(VIEW_CACHE) > 600:
        VIEW_CACHE.clear()
    top, mid, belly, fin = f.palette()
    Q = 3
    H = max(8.0, (f.HT + f.HB) * f.z) * Q
    W = max(4.0, H * FRONT_W.get(name, 0.62))
    pad = int(0.5 * H)
    cw, ch = int(W + 2 * pad), int(H * 1.5 + 2 * pad // 2)
    sf = pygame.Surface((cw, ch), pygame.SRCALPHA)
    cx, cy = cw / 2, ch * 0.55
    fa = (*fin, 200)
    # dorsal fin (a thin blade) and the pectorals / pelvics
    pygame.draw.polygon(sf, fa, [(cx - 0.09 * W, cy - H * 0.42), (cx, cy - H * 0.42 - H * 0.32), (cx + 0.09 * W, cy - H * 0.42)])
    if not back:
        for sx in (-1, 1):
            pygame.draw.polygon(sf, fa, [(cx + sx * W * 0.42, cy + H * 0.02), (cx + sx * (W * 0.5 + W * 0.42), cy + H * 0.34),
                                         (cx + sx * W * 0.28, cy + H * 0.26)])
    # the body: dark back, body colour, pale belly
    pygame.draw.ellipse(sf, (*top, 255), (cx - W / 2, cy - H / 2, W, H))
    pygame.draw.ellipse(sf, (*mid, 255), (cx - W * 0.42, cy - H * 0.36, W * 0.84, H * 0.8))
    pygame.draw.ellipse(sf, (*belly, 235), (cx - W * 0.3, cy + H * 0.1, W * 0.6, H * 0.34))
    st = ENDON_STYLE.get(name) or (ENDON_STYLE.get(f.hyb.get("cls")) if getattr(f, "hyb", None) else None)
    if st:      # the species' markings as they show head-on or tail-on
        kind, mk = st
        rngv = random.Random(f.id)
        if kind == "bars":
            for sx in (-1, 1):
                for u in (0.16, 0.34):
                    pygame.draw.line(sf, (*mk, 190), (cx + sx * W * u, cy - H * 0.36), (cx + sx * W * (u + 0.02), cy + H * 0.14), max(1, int(Q * 0.8)))
        elif kind == "stripe":
            pygame.draw.arc(sf, (*mk, 200), (cx - W * 0.4, cy - H * 0.36, W * 0.8, H * 0.5), 0.2, math.pi - 0.2, max(1, Q))
        elif kind == "blotch":
            for _ in range(6):
                pygame.draw.ellipse(sf, (*mk, 170), (cx + rngv.uniform(-0.4, 0.2) * W, cy + rngv.uniform(-0.4, 0.3) * H, W * 0.2, H * 0.14))
        elif kind == "head" and not back:
            pygame.draw.ellipse(sf, (*mk, 130), (cx - W * 0.34, cy - H * 0.42, W * 0.68, H * 0.4))
    if back:
        # the tail fan, seen edge-on in front of the body
        tw = max(3.0, W * 0.22)
        pygame.draw.ellipse(sf, (*fin, 215), (cx - tw / 2, cy - H * 0.46, tw, H * 0.92))
        pygame.draw.line(sf, (*tone(fin, 0.6), 160), (cx, cy - H * 0.44), (cx, cy + H * 0.44), max(1, int(Q * 0.8)))
        for sx in (-1, 1):   # the pectoral edges just show behind the gill covers
            pygame.draw.line(sf, fa, (cx + sx * W * 0.46, cy - H * 0.02), (cx + sx * W * 0.6, cy + H * 0.12), max(1, Q))
    else:
        er = max(2.0 * Q * 0.5, W * 0.15)
        for sx in (-1, 1):
            ex, ey = cx + sx * W * 0.27, cy - H * 0.1
            pygame.draw.circle(sf, (*f.eye_col, 255), (ex, ey), er)
            pygame.draw.circle(sf, (12, 12, 18, 255), (ex, ey), er * 0.55)
            pygame.draw.circle(sf, (255, 255, 255, 200), (ex - er * 0.25, ey - er * 0.25), max(1, er * 0.2))
        pygame.draw.ellipse(sf, (60, 14, 14, 200), (cx - W * 0.1, cy + H * 0.12, W * 0.2, H * 0.07))
        pygame.draw.line(sf, (*tone(mid, 0.5), 140), (cx, cy - H * 0.3), (cx, cy + H * 0.1), max(1, Q // 2))
    spr = pygame.transform.smoothscale(sf, (max(2, cw // Q), max(2, ch // Q)))
    VIEW_CACHE[key] = spr
    return spr


ENDON_STYLE = {"CobaltZebra": ("bars", (10, 24, 100)), "RedZebra": ("bars", (120, 60, 40)), "DemasoniCichlid": ("bars", (6, 14, 66)),
               "IceBlueCichlid": ("bars", (60, 90, 150)), "KenyiCichlid": ("bars", (80, 64, 20)), "PeacockCichlid": ("bars", (20, 40, 120)),
               "AuratusCichlid": ("stripe", (30, 30, 30)), "YellowPrinceCichlid": ("stripe", (150, 90, 10)),
               "AulonocaraOB": ("blotch", (30, 24, 34)), "GermanRedPeacock": ("head", (255, 150, 90)),
               "SunshinePeacock": ("head", (120, 180, 255)), "ElectricBlueHap": ("head", (120, 190, 255)),
               "CopadichromisBorleyi": ("head", (255, 120, 60)), "SocolofiCichlid": ("head", (255, 190, 200))}


def draw_turn(surface, f, sprite, ph):
    """A fish part-way through a turn: the side sprite narrows (and fades) while the end-on sprite takes over."""
    cx, cy = int(f.pos.x), int(f.pos.y)
    c = math.cos(math.radians(ph))
    s = abs(c)
    right = c > 0
    a_side = clamp((s - 0.22) / 0.26)
    if a_side > 0:
        base = sprite if right else pygame.transform.flip(sprite, True, False)
        w, h = base.get_size()
        img = pygame.transform.smoothscale(base, (max(2, int(w * max(s, 0.1))), h))
        img = pygame.transform.rotate(img, (f.angle if right else -f.angle) * s)
        if a_side < 1.0:
            img.set_alpha(int(255 * a_side))
        surface.blit(img, img.get_rect(center=(cx, cy)))
    if a_side < 1.0:
        v = view_sprite(f, f.endon == "back")
        v.set_alpha(int(255 * (1.0 - a_side)))
        surface.blit(v, v.get_rect(center=(cx, cy)))
        v.set_alpha(255)


# ---- sprite cache: fish are drawn once per animation frame instead of every frame ----
SPRITE_CACHE = {}
ROT_CACHE = {}
ORIGINAL_DRAW = {}


def cache_fish_sprites(cls, period, shadow_w, buckets=8):
    """Wrap cls.draw so each fish renders a handful of tail-beat frames once, then just rotates and blits them."""
    original = cls.draw
    ORIGINAL_DRAW[cls] = original
    step = period / buckets

    def make_key(self, b):
        return (type(self).__name__, self.id if getattr(self, "unique", False) else 0, b, round(self.z * 20), min(30, int(self.hunger)) // 15,
                getattr(self, "mouth_open_timer", 0) > 1, round(getattr(self, "puff", 0.0) * 10),
                getattr(self, "sex", ""), int((self.vigor() + 1) * 3), int(getattr(self, "flare", 0)), getattr(self, "gene_key", 0),
                getattr(self, "look", 0))

    def render(self, key, b, surface):
        global _capture
        real_ticks = pygame.time.get_ticks
        pygame.time.get_ticks = lambda: int(b * step)  # render at the bucket's canonical moment
        _capture = []
        try:
            original(self, surface)
            big = _capture[0] if _capture else None
        finally:
            _capture = None
            pygame.time.get_ticks = real_ticks
        if big is None:
            return None
        big = apply_sex(self, big)
        sprite = pygame.transform.smoothscale(big, (big.get_width() // SS, big.get_height() // SS))
        if len(SPRITE_CACHE) > 2500:
            SPRITE_CACHE.clear()
        SPRITE_CACHE[key] = sprite
        return sprite

    def draw(self, surface):
        if getattr(self, "in_mouth", False):
            return
        if not self.alive:
            return original(self, surface)
        b = int((pygame.time.get_ticks() % period) / step) % buckets
        key = make_key(self, b)
        sprite = SPRITE_CACHE.get(key)
        if sprite is None:
            if SPRITE_BUDGET[0] > 0:
                # A new sprite was already built this frame: borrow a near-identical one (adjacent size or beat) so the frame
                # stays fast; this fish builds its own on a later frame.
                for dz in (1, -1, 2, -2):
                    for db in (0, 1, -1):
                        sprite = SPRITE_CACHE.get(key[:2] + ((b + db) % buckets, key[3] + dz) + key[4:])
                        if sprite is not None:
                            break
                    if sprite is not None:
                        break
            if sprite is None:
                SPRITE_BUDGET[0] += 1
                sprite = render(self, key, b, surface)
                if sprite is None:
                    return
            else:
                self.draw_shadow(surface, shadow_w)
        else:
            self.draw_shadow(surface, shadow_w)
            if getattr(self, "mouth_open_timer", 0) > 0:
                self.mouth_open_timer -= 1
        yaw_update(self)
        if 0.0 < self.ph < 180.0:
            draw_turn(surface, self, sprite, self.ph)
            return
        facing = self.ph < 90
        ab = int(round(self.angle / 3.0))  # rotations are cached per 3 degrees; flip + rotate were a big share of the frame
        rkey = (key, facing, ab)
        img = ROT_CACHE.get(rkey)
        if img is None:
            img = sprite if facing else pygame.transform.flip(sprite, True, False)
            img = pygame.transform.rotate(img, ab * 3.0 if facing else -ab * 3.0)
            if len(ROT_CACHE) > 2500:
                ROT_CACHE.clear()
            ROT_CACHE[rkey] = img
        surface.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))

    def warm(self, scratch):
        """Pre-build all tail-beat frames of this fish's current look (called while the welcome screen is up)."""
        for b in range(buckets):
            key = make_key(self, b)
            if key not in SPRITE_CACHE:
                render(self, key, b, scratch)

    cls.draw = draw
    cls.warm_sprites = warm


SPRITE_BUDGET = [0]   # new sprites built this frame; reset every frame so a burst of cache misses is spread over several frames
WARM_QUEUE = []
WARM_DONE = [False]


def warm_step(budget_ms=10.0):
    """Build cached sprites for the current fish for up to budget_ms; returns True while there is more to do."""
    global WARM_QUEUE
    if WARM_DONE[0]:
        return False
    if not WARM_QUEUE:
        seen = set()
        for f in fishes + predators:
            k = (type(f).__name__, round(f.z * 20), getattr(f, "sex", ""))
            if hasattr(f, "warm_sprites") and (k not in seen or getattr(f, "unique", False)):
                seen.add(k)
                WARM_QUEUE.append(f)
        WARM_QUEUE.append(None)   # sentinel: finished
    t0 = pygame.time.get_ticks()
    scratch = pygame.Surface((8, 8), pygame.SRCALPHA)
    while WARM_QUEUE and pygame.time.get_ticks() - t0 < budget_ms:
        f = WARM_QUEUE.pop(0)
        if f is None:
            WARM_DONE[0] = True
            return False
        f.warm_sprites(scratch)
    return True


SEX_ACCENT = {"PeacockCichlid": (255, 200, 40), "YellowPrinceCichlid": (255, 120, 20), "IceBlueCichlid": (255, 255, 255),
              "DemasoniCichlid": (190, 230, 255), "CobaltZebra": (150, 215, 255), "RedZebra": (255, 215, 150),
              "KenyiCichlid": (255, 235, 120), "AuratusCichlid": (240, 215, 90), "SocolofiCichlid": (255, 170, 170),
              "AngelFish": (255, 255, 255), "AulonocaraOB": (255, 150, 60), "GermanRedPeacock": (255, 90, 50),
              "SunshinePeacock": (90, 170, 255), "CopadichromisBorleyi": (255, 120, 50), "ElectricBlueHap": (120, 190, 255),
              "SynodontisCatfish": (230, 200, 120),
              "Pleco": (230, 200, 120), "BalaShark": (255, 255, 255), "NeonTetra": (120, 255, 255), "RummyNose": (255, 80, 80),
              "BoesemaniRainbow": (255, 200, 60), "PearlGourami": (255, 150, 70), "ClownLoach": (255, 220, 120),
              "TigerBarb": (255, 90, 40), "CardinalTetra": (120, 255, 255), "EmberTetra": (255, 200, 100),
              "BlackSkirtTetra": (255, 255, 255), "LemonTetra": (255, 255, 150)}


def apply_sex(f, big):
    """Sexual dimorphism, painted on a finished sprite: females are bigger and have a pale gravid belly,
    males are smaller with a bright nuptial streak and fin-tip dots."""
    sex = getattr(f, "sex", None)
    if sex is None:
        return big
    cls = type(f).__name__
    r = big.get_bounding_rect()
    if r.w < 8 or r.h < 8:
        return big
    accent = SEX_ACCENT.get(cls)
    mark = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    w, h = r.w, r.h
    if sex == "M" and accent:
        y = r.centery - h * 0.05
        pygame.draw.line(mark, (*accent, 185), (r.left + w * 0.30, y), (r.right - w * 0.22, y - h * 0.02), max(2, int(h * 0.05)))
        for k in range(5):
            pygame.draw.circle(mark, (*accent, 210), (int(r.left + w * (0.34 + 0.09 * k)), int(r.top + h * (0.12 + 0.02 * abs(k - 2)))),
                               max(2, int(h * 0.03)))
    elif sex == "F":
        pygame.draw.ellipse(mark, (255, 246, 228, 80), (r.left + w * 0.26, r.centery + h * 0.02, w * 0.44, h * 0.27))
    mask = big.copy()
    mask.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_MAX)
    mark.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    out = big.copy()
    out.blit(mark, (0, 0))
    size = {"M": 0.94, "F": 1.08}[sex]
    return pygame.transform.smoothscale(out, (max(2, int(out.get_width() * size)), max(2, int(out.get_height() * size))))


for _cls in FW_CLASSES:
    cache_fish_sprites(_cls, 628.32 / _cls.beat, _cls.shadow)


def build_world_extras():
    """Pick the eel's lair and the shrimp stations from the freshly built hardscape."""
    build_cover()
    if not any(not isinstance(r, Driftwood) for r in rocks):   # a tank designed without a single rock has no lair and no stations
        return None, []
    cands = [r for r in rocks if not isinstance(r, Driftwood) and r.y_offset == 0 and r.z >= 0.96
             and 120 < r.pos_x < SCREEN_WIDTH - 120]
    if not cands:
        cands = [r for r in rocks if not isinstance(r, Driftwood)]
    eel = FireEel(random.choice(cands))
    spots = [r for r in rocks if not isinstance(r, Driftwood) and r is not eel.rock and r.y_offset == 0 and r.z >= 0.75]
    random.shuffle(spots)
    chosen = []
    for r in spots:
        if all(abs(r.pos_x - st.pos.x) > 250 for st in chosen):
            chosen.append(CleaningStation(r))
        if len(chosen) == 2:
            break
    return eel, chosen


def init_ecosystem():
    """(Re)build everything the ecosystem layer owns; call after the hardscape and plants exist."""
    global eco
    eco = Ecosystem()
    for lst in (fx, emotes, ripples, inks, respawn_queue, eggs, placed, journal, foam_nests):
        lst.clear()
    eel, chosen = build_world_extras()
    predators[:] = ([Channa(random.randint(150, SCREEN_WIDTH - 150), random.randint(180, 330))] + ([eel] if eel is not None else [])
                    + ([Crayfish()] if CRAY["on"] else [])) if PRED["on"] else []
    stations[:] = chosen
    visitors[:] = []
    crawlers[:] = [MysterySnail(), MysterySnail(), Ramshorn(), Ramshorn()]


pygame.display.set_caption("Pixel Aquarium")
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), 0, display)  # the world; scaled up to the display each frame
clock = pygame.time.Clock()

try:
    splash_img = pygame.transform.scale(pygame.image.load(get_path('splash.png')).convert(),
                                        (SCREEN_WIDTH, SCREEN_HEIGHT))
except:
    splash_img = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    splash_img.fill((20, 40, 80))

welcome_font = pygame.font.SysFont("Arial", 32, bold=True)
notif_font = pygame.font.SysFont("Arial", 16, italic=True)

WELCOME_BR = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 100, 240, 60)
WELCOME_SHADE = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
for _y in range(SCREEN_HEIGHT):   # the live tank shows through; a soft shade keeps the title readable
    _d = abs(_y - SCREEN_HEIGHT * 0.45) / (SCREEN_HEIGHT * 0.55)
    pygame.draw.line(WELCOME_SHADE, (4, 12, 28, int(150 - 90 * min(1.0, _d))), (0, _y), (SCREEN_WIDTH, _y))
welcome_title_font = pygame.font.SysFont("Arial", 84, bold=True)


WELCOME_UI = {}


def draw_welcome_screen():
    """The welcome screen is drawn over the running tank: the fish and plants are the live preview."""
    screen.blit(WELCOME_SHADE, (0, 0))
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    title = welcome_title_font.render("PIXEL AQUARIUM", True, (236, 246, 255))
    screen.blit(title, title.get_rect(center=(cx, cy - 120)))
    m_pos = world_mouse(pygame.mouse.get_pos())
    small = hud_font()
    # the set chooser: < name >
    nm = (ACTIVE_SET or "").replace("_", " ").upper()
    st = welcome_font.render(nm, True, (255, 236, 170))
    screen.blit(st, st.get_rect(center=(cx, cy - 40)))
    sub = small.render(f"{len(COMMUNITY_TARGET)} species   (left / right: choose a set)", True, (190, 210, 230))
    screen.blit(sub, sub.get_rect(center=(cx, cy - 8)))
    WELCOME_UI.clear()
    for key, sx, glyph in (("prev", -1, "<"), ("next", 1, ">")):
        r = pygame.Rect(0, 0, 54, 54)
        r.center = (cx + sx * (st.get_width() // 2 + 56), cy - 40)
        pygame.draw.rect(screen, (60, 160, 240) if r.collidepoint(m_pos) else (40, 100, 200), r, border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255), r, 2, border_radius=12)
        g = welcome_font.render(glyph, True, (255, 255, 255))
        screen.blit(g, g.get_rect(center=r.center))
        WELCOME_UI[key] = r
    info = saved_tank_info()
    bw, bh = 400, 60
    for key, label, y, ok in (("cont", "CONTINUE LAST TANK", cy + 50, info is not None), ("new", "NEW GAME", cy + 126, True)):
        r = pygame.Rect(cx - bw // 2, y, bw, bh)
        hot = ok and r.collidepoint(m_pos)
        col = (70, 170, 250) if hot else (40, 100, 200) if ok else (60, 66, 80)
        pygame.draw.rect(screen, col, r, border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255) if ok else (120, 126, 140), r, 2, border_radius=15)
        t = welcome_font.render(label, True, (255, 255, 255) if ok else (140, 146, 160))
        screen.blit(t, t.get_rect(center=(r.centerx, r.centery - (8 if key == "cont" and ok else 0))))
        if key == "cont" and ok:
            mins = int(info[1] // 60)
            ago = f"{mins} min ago" if mins < 120 else f"{mins // 60} h ago" if mins < 2880 else f"{mins // 1440} days ago"
            s2 = small.render(f"{info[0].replace('_', ' ')}, {info[2]} fish, saved {ago}", True, (214, 232, 255))
            screen.blit(s2, s2.get_rect(center=(r.centerx, r.centery + 17)))
        WELCOME_UI[key] = r if ok else None
    hint = small.render(("Enter: continue     N: new game" if info else "Enter or N: new game") + "     F10 in the tank: wallpaper mode (a calm, safe tank)",
                        True, (170, 190, 215))
    screen.blit(hint, hint.get_rect(center=(cx, cy + 214)))

music_files = ["bgmusic.mp3", "bgmusic2.mp3", "bgmusic3.mp3", "bgmusic4.mp3"]
current_music_idx = 0
try:
    pygame.mixer.music.load(get_path(music_files[current_music_idx]))
    pygame.mixer.music.play(-1)
    apply_music_volume()
except pygame.error:
    print(f"Could not load initial music: {music_files[0]}")

bg_files, bg_index = ["wallart.png", "wallart2.png", "wallart3.png", "wallart4.png","wallart5.png","wallart6.png","wallart7.png","wallart8.png","wallart9.png"], 0
BG_MARGIN = 24  # the wall art is larger than the screen so it can slide behind the glass


def load_bg(name):
    size = (SCREEN_WIDTH + 2 * BG_MARGIN, SCREEN_HEIGHT + 2 * BG_MARGIN)
    img = pygame.transform.smoothscale(pygame.image.load(get_path(name)).convert(), size)
    bgc = SCAPE.get("background")
    if isinstance(bgc, dict):   # a scape can darken and tint the wall art (a matte dark blue back wall)
        d = clamp(float(bgc.get("darken", 0.0)), 0.0, 0.9)
        if d > 0:
            img.fill((int(255 * (1 - d)),) * 3, special_flags=pygame.BLEND_RGB_MULT)
        if bgc.get("tint"):
            img.fill(tuple(int(v) for v in bgc["tint"]), special_flags=pygame.BLEND_RGB_ADD)
    return img


try:
    bg_image = load_bg(bg_files[bg_index])
except Exception:
    bg_image = pygame.Surface((SCREEN_WIDTH + 2 * BG_MARGIN, SCREEN_HEIGHT + 2 * BG_MARGIN))
    bg_image.fill((10, 20, 40))

fishes = []  # filled by spawn_community() once the hardscape and plants exist
daphnia = [Daphnia() for _ in range(40)]
shimps = [TinyShrimp() for _ in range(20)]
auto_feed_timer = random.randint(100, 300)
plants = create_plants()
def sand_colours():
    """The sand's colours: the default sand, or whatever colour the active scape asks for (fine pale aragonite...)."""
    top, bot, gr = (200, 184, 144), (118, 106, 86), [(190, 170, 110), (225, 200, 140)]
    if scape("substrate", "color"):
        sc = tuple(scape("substrate", "color"))
        top, bot, gr = tone(sc, 0.95), tone(sc, 0.58), [tone(sc, 0.88), tone(sc, 1.06)]
    return top, bot, gr


SAND_TOP, SAND_BOT, SAND_GRAINS = sand_colours()
grains = [(random.randint(0, SCREEN_WIDTH), random.randint(SCREEN_HEIGHT - 60, SCREEN_HEIGHT), random.choice(SAND_GRAINS))
          for _ in range(600)]
algae, pellets, bubbles, frame = [], [], [], 0
rebuild_world()
build_sfx()
init_ecosystem()
fishes[:] = spawn_community()

# Caustics: sunlight rippling through the surface, pre-rendered as a short loop of additive overlays
CAUSTIC_FRAMES = 8
CAUSTIC_SCALE = 4  # One caustic pixel covers this many screen pixels
CAUSTIC_STRENGTH = 34   # brightness of the rippling light (was 70; lower = calmer water)
CAUSTIC_SLOWNESS = 7    # frames per caustic step (was 4; higher = slower shimmer)


def build_caustic_overlays():
    cw, ch = SCREEN_WIDTH // CAUSTIC_SCALE, SCREEN_HEIGHT // CAUSTIC_SCALE
    overlays = []
    for f in range(CAUSTIC_FRAMES):
        t = f / CAUSTIC_FRAMES * math.tau
        small = pygame.Surface((cw, ch))
        for py in range(ch):
            fall = max(0.0, 1.0 - py / (ch * 0.75))  # Light is strongest near the surface
            y = py * CAUSTIC_SCALE * 0.03
            for px in range(cw):
                x = px * CAUSTIC_SCALE * 0.03
                u = x + math.sin(y * 0.7 + t) * 2.0
                v = y + math.cos(x * 0.8 - t) * 2.0
                c = (math.sin(u * 2.1 + t) + math.sin(v * 2.3 - t * 1.1) + math.sin((u + v) * 1.7 + t * 0.7)) / 3
                val = int(max(0.0, c) ** 2.5 * fall * CAUSTIC_STRENGTH)
                small.set_at((px, py), (val, val, int(val * 0.85)))
        overlays.append(pygame.transform.smoothscale(small, (SCREEN_WIDTH, SCREEN_HEIGHT)))
    return overlays


CAUSTIC_OVERLAYS = build_caustic_overlays()

# Sand is static, so its shading, ripples and grains are rendered once into a layer
sand_top_points = [(x, SCREEN_HEIGHT - 60 + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2) for x in range(0, SCREEN_WIDTH + 11, 10)]
sand_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)


def build_sand():
    sand_layer.fill((0, 0, 0, 0))
    shaded_polygon(sand_layer, sand_top_points + [(SCREEN_WIDTH, SCREEN_HEIGHT), (0, SCREEN_HEIGHT)],
                   SAND_TOP, SAND_BOT)
    for row in range(4):  # Wind/current ripples across the sand
        y0 = SCREEN_HEIGHT - 44 + row * 11
        ripple = [(x, y0 + math.sin(x * 0.07 + row * 2) * 1.5) for x in range(0, SCREEN_WIDTH + 9, 8)]
        pygame.draw.aalines(sand_layer, (120, 104, 80, 150), False, ripple)
    for gx, gy, col in grains:
        if gy > SCREEN_HEIGHT - 60 + math.sin(gx * 0.02) * 5 + math.cos(gx * 0.05) * 2:
            pygame.draw.rect(sand_layer, col, (gx, gy, 2, 2))


build_sand()


class Detritus:
    """Slow drifting detritus that makes the water feel alive and gives depth."""

    def __init__(self):
        self.reset(random.uniform(WATER_TOP, SCREEN_HEIGHT - SAND_HEIGHT))

    def reset(self, y):
        self.pos = pygame.Vector2(random.uniform(0, SCREEN_WIDTH), y)
        self.speed = random.uniform(0.15, 0.45)
        self.phase = random.uniform(0, math.tau)
        self.size = random.choice([1, 1, 1, 2])
        self.col = random.choice([(230, 235, 240), (210, 225, 235)])

    def update(self):
        self.phase += 0.02
        self.pos.y += self.speed
        self.pos.x = (self.pos.x + math.sin(self.phase) * 0.25 + eco.current * 14) % SCREEN_WIDTH
        if self.pos.y > SCREEN_HEIGHT - SAND_HEIGHT:
            self.reset(WATER_TOP)

    def draw(self, surface):
        ox, oy = poff("snow_near" if self.size > 1 else "snow_far")  # big flakes are close to the glass
        pygame.draw.circle(surface, self.col, (int(self.pos.x + ox), int(self.pos.y + oy)), self.size)


snow = [Detritus() for _ in range(90)]
LOG_INTERVAL = 180

# Static layers and reusable surfaces, built once instead of every frame
water_gradient = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
for y in range(SCREEN_HEIGHT):
    t = y / SCREEN_HEIGHT
    col = [int(top * (1 - t) + bottom * t) for top, bottom in zip(CLR_WATER_TOP, CLR_WATER_BOTTOM)]
    pygame.draw.line(water_gradient, (*col, 150), (0, y), (SCREEN_WIDTH, y))

surface_haze = pygame.Surface((SCREEN_WIDTH, 120), pygame.SRCALPHA)
for y in range(120):
    pygame.draw.line(surface_haze, (255, 255, 220, max(0, 100 - y)), (0, y), (SCREEN_WIDTH, y))

light_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

# ---- 2.5D: the tank is drawn as depth layers that slide against each other (parallax) ----
# The mid layer is the focal plane where the fish live and food is eaten, so it never moves; layers behind it drift with
# the viewpoint and layers in front drift against it. Fish are assigned to a layer by their z.
PARALLAX_ON = True
PARALLAX = {"bg": 15.0, "hang_bg": 12.0, "hang_fg": -32.0, "far": 8.0, "mid": 0.0, "plants": -8.0, "near": -20.0, "snow_far": 4.0, "snow_near": -40.0, "fore": -95.0}
par = pygame.Vector2()   # smoothed viewpoint in -1..1 (mouse position, plus a slow idle sway so it never looks frozen)
plant_tick = 0
LAYER_FAR, LAYER_MID = 0.5, 0.9   # z cut-offs between the far, mid and near layers
layer_surfs = {name: pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA) for name in ("far", "mid", "plants", "near", "hang_bg", "hang_fg")}
layer_surfs["far"].set_alpha(205)   # distance haze: the far layer is a little washed out into the water


def blit_edges(dest, layer, off, width=520):
    """The hanging vines only live in the left and right edge bands, so only those bands are composited."""
    h = layer.get_height()
    for x in (0, layer.get_width() - width):
        dest.blit(layer, (x + off[0], off[1]), pygame.Rect(x, 0, width, h))


HELP_COLUMNS = [
    ("TANK", [("1 - 5", "Choose feed type"), ("Left click", "Drop food / place tool"), ("Shift-click", "Select a fish"),
              ("Right click", "Tap the glass"), ("Z", "Follow selected fish"), ("W", "Water change"), ("E", "Random event"),
              ("D", "Cycle build tool"), ("F5 / F9", "Save / load tank"), ("R", "Reset tank, reload config")]),
    ("VIEW", [("H", "Show / hide HUD"), ("J", "Show / hide journal"), ("P", "Take a photo"), ("N", "Cycle lighting mode"),
              ("T", "Pause day / night"), ("B", "Cycle background art"), ("X", "Parallax on / off"), ("M", "Next music track"),
              ("V", "Mute / unmute")]),
    ("SYSTEM", [("F1", "This help"), ("Esc", "Close help / ask to quit"), ("F3", "FPS counter"), ("Q", "Quality: Low / Med / High"),
                ("F11", "Fullscreen / window"), ("F10", "Screensaver mode"), ("- / =", "Master volume"), ("[ / ]", "Effects volume")]),
    ("CARE & CAMERA", [("C", "Wipe the glass"), ("F", "Rinse the filter"), ("L", "Lights: Sun / On / Off"), ("A", "Air stone on / off"),
                       ("G", "Goals"), ("K", "Cinema camera"), ("O", "Real-time clock"), ("Del", "Hub: gear, line, upkeep"), ("Ctrl+drag", "Lift a fish"), ("Hold click", "Drip food")]),
    ("HEALTH & HOME", [("U", "Medicine (cure)"), ("I", "Quarantine selected fish"), ("S", "Nursery net on / off"),
                       ("Y", "Heater Off / Low / High"), ("Tab", "Strain book"), ("\\ (hold)", "Timelapse"), ("D > TRIM", "Prune plants"), ("Shift+D", "Trim all plants"), ("9", "Methylene blue"), ("0", "Vitamins"), ("7", "Sell bred fish"), ("8", "Chores & challenges"), ("Ctrl+S", "Settings and save slots")]),
    ("MORE", [("F2", "Social web"), ("F4", "Genetic show"), ("F6", "Rename fish"), ("F7", "Star a favourite"), ("F8", "Story / memorial"), 
              (",", "Equipment shop"), (".", "Aquascapes"), ("/", "Dashboard"), (";", "Water test kit"), ("'", "Fertiliser"),
              ("`", "Soundscape on / off"), ("PgUp", "Photo album"), ("F12", "Record timelapse"), ("Home", "Planting mode"),
              ("PgDn", "Record a tank tour"), ("Ins", "Before / after")]),
]
show_help = False
show_goals = False
show_strains = False
show_fps = False
frame_times = deque(maxlen=120)
photo_flash = 0
FLASH_SURF = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
FLASH_SURF.fill((255, 255, 255))
screensaver = False
saved_hud = True
is_full = True


def set_display(full):
    """F11: switch between the full-screen tank and a window of the same proportions."""
    global display, DISPLAY_W, DISPLAY_H, is_full
    try:
        if full:
            display = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            w = int(info.current_w * 0.72)
            display = pygame.display.set_mode((w, int(w * SCREEN_HEIGHT / SCREEN_WIDTH)))
        is_full = full
    except pygame.error:
        return
    DISPLAY_W, DISPLAY_H = display.get_size()


_help_surf = [None]
confirm_quit = False
QUIT_BTNS = {}


def draw_quit_modal(surface):
    """Esc asks first: Y / Enter quits, N / Esc (or the buttons) keeps watching."""
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 130))
    surface.blit(dim, (0, 0))
    w, h = 460, 190
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 20, 40, 238), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
    title_f = pygame.font.SysFont("Arial", 26, bold=True)
    txt_f = pygame.font.SysFont("Arial", 17)
    btn_f = pygame.font.SysFont("Arial", 18, bold=True)
    t = title_f.render("Leave the aquarium?", True, (235, 245, 255))
    panel.blit(t, ((w - t.get_width()) // 2, 26))
    sub = txt_f.render("Your tank is not saved unless you pressed F5.", True, (190, 210, 228))
    panel.blit(sub, ((w - sub.get_width()) // 2, 70))
    rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    mx, my = world_mouse(pygame.mouse.get_pos())
    for name, label, x, base in (("quit", "Quit  (Y)", 40, (150, 52, 52)), ("keep", "Keep watching  (N)", 250, (36, 96, 140))):
        br = pygame.Rect(x, 112, 170, 46)
        hover = br.move(rect.topleft).collidepoint(mx, my)
        pygame.draw.rect(panel, tuple(min(255, c + (40 if hover else 0)) for c in base), br, border_radius=10)
        pygame.draw.rect(panel, (230, 240, 250), br, 1, border_radius=10)
        lt = btn_f.render(label, True, (255, 255, 255))
        panel.blit(lt, lt.get_rect(center=br.center))
        QUIT_BTNS[name] = br.move(rect.topleft)
    surface.blit(panel, rect)


def draw_help(surface):
    """A modal listing every control (F1). Built once and cached."""
    if _help_surf[0] is None:
        title_f = pygame.font.SysFont("Arial", 26, bold=True)
        head_f = pygame.font.SysFont("Arial", 17, bold=True)
        key_f = pygame.font.SysFont("Consolas", 16, bold=True)
        txt_f = pygame.font.SysFont("Arial", 16)
        row_h, col_w, pad = 24, 316, 26
        per_row = max(1, min(len(HELP_COLUMNS), (SCREEN_WIDTH - 2 * pad - 40) // col_w))   # wrap the columns to fit the screen
        bands = [HELP_COLUMNS[i:i + per_row] for i in range(0, len(HELP_COLUMNS), per_row)]
        band_h = [34 + max(len(c[1]) for c in band) * row_h + 10 for band in bands]
        w, h = pad * 2 + col_w * per_row, pad * 2 + 40 + sum(band_h) + 22
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (8, 20, 40, 238), (0, 0, w, h), border_radius=14)
        pygame.draw.rect(panel, (120, 190, 230, 255), (0, 0, w, h), 2, border_radius=14)
        panel.blit(title_f.render("Keyboard & mouse", True, (235, 245, 255)), (pad, pad - 4))
        y0 = pad + 40
        for band, bh in zip(bands, band_h):
            for ci, (head, items) in enumerate(band):
                x = pad + ci * col_w
                panel.blit(head_f.render(head, True, (120, 200, 240)), (x, y0))
                for ri, (key, desc) in enumerate(items):
                    y = y0 + 30 + ri * row_h
                    panel.blit(key_f.render(key, True, (255, 214, 120)), (x, y))
                    panel.blit(txt_f.render(desc, True, (214, 226, 238)), (x + 128, y + 1))
            y0 += bh
        panel.blit(txt_f.render("Press F1 or Esc to close", True, (150, 175, 200)), (pad, h - pad - 2))
        _help_surf[0] = panel
    panel = _help_surf[0]
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 110))
    surface.blit(dim, (0, 0))
    surface.blit(panel, panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))


def update_parallax():
    t = pygame.time.get_ticks() * 0.001
    idle = pygame.Vector2(math.sin(t * 0.23), math.sin(t * 0.31 + 1.3) * 0.6) * 0.55
    if mouse_track["inside"]:
        mx, my = mouse_track["pos"]
        goal = pygame.Vector2((mx / SCREEN_WIDTH - 0.5) * 2, (my / SCREEN_HEIGHT - 0.5) * 2) * 0.95 + idle * 0.25
    else:
        goal = idle
    par.update(par + (goal - par) * 0.05 if PARALLAX_ON else par * 0.9)


def poff(name):
    f = PARALLAX[name]
    return (int(par.x * f), int(par.y * f * 0.3))


def build_far_ridge():
    """A dim silhouette of distant gravel hills and driftwood along the back wall, sitting behind everything else."""
    w, h = SCREEN_WIDTH + 80, SCREEN_HEIGHT
    ridge = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = random.Random(77)
    base = h - SAND_HEIGHT - 50
    pts = [(x, base - (40 + 26 * math.sin(x * 0.011 + 1.0) + 18 * math.sin(x * 0.027 + 2.0)
                       + 12 * math.sin(x * 0.061)) * VS) for x in range(0, w + 16, 16)]
    pygame.draw.polygon(ridge, (14, 44, 96, 120), pts + [(w, h), (0, h)])
    for _ in range(max(5, w // 170)):  # distant snags of driftwood standing on the hills
        x = rng.randint(0, w)
        y = base - (40 + 26 * math.sin(x * 0.011 + 1.0) + 18 * math.sin(x * 0.027 + 2.0)) * VS
        ln = rng.randint(40, 90) * VS
        lean = rng.randint(-26, 26)
        pygame.draw.line(ridge, (16, 52, 108, 120), (x, y + 6), (x + lean, y - ln), rng.randint(4, 7))
        for k in range(rng.randint(1, 3)):
            t = rng.uniform(0.35, 0.8)
            bx, by = x + lean * t, y - ln * t
            pygame.draw.line(ridge, (16, 52, 108, 120), (bx, by), (bx + rng.choice((-1, 1)) * rng.randint(14, 30), by - rng.randint(10, 26)), 3)
    return ridge


far_ridge = build_far_ridge()
BG_RIDGE = scape("background", "ridge", True)        # the distant rock silhouettes
BG_DOODADS = scape("background", "doodads", True)    # the deep stalks, jellyfish and school behind the tank
FORE_W = 320
fore_strip = pygame.Surface((FORE_W, SCREEN_HEIGHT), pygame.SRCALPHA)
fore_strip.set_alpha(165)
FORE_BLADES = [(random.randint(60, FORE_W - 40), random.randint(int(0.22 * SCREEN_HEIGHT), int(0.5 * SCREEN_HEIGHT)),
                random.randint(26, 46), random.uniform(0, math.tau), random.randint(-8, 8)) for _ in range(6)]


def draw_foreground(surface, frame):
    """Big dark vallisneria blades hugging the glass at both edges. They sit furthest forward, so they slide the most."""
    fore_strip.fill((0, 0, 0, 0))
    for bx, height, width, phase, tint in FORE_BLADES:
        pts_l, pts_r = [], []
        steps = 14
        for i in range(steps + 1):
            u = i / steps
            sway = math.sin(frame * 0.012 + phase + u * 2.2) * 30 * u * u
            x = bx + sway + 60 * math.sin(phase) * u * u
            y = SCREEN_HEIGHT - u * height
            wd = width * 0.5 * (1 - u) ** 0.8 + 1
            pts_l.append((x - wd, y))
            pts_r.append((x + wd, y))
        col = (10 + tint, 38 + tint, 44 + tint)
        pygame.draw.polygon(fore_strip, col, pts_l + pts_r[::-1])
        pygame.draw.lines(fore_strip, (col[0] + 18, col[1] + 30, col[2] + 28), False, pts_l, 2)
    ox, oy = poff("fore")
    surface.blit(fore_strip, (-110 + ox, oy))
    surface.blit(pygame.transform.flip(fore_strip, True, False), (SCREEN_WIDTH - FORE_W + 110 + ox, oy))


# ---- doodads: extra scenery in the back and front layers, so the parallax has plenty to slide against ----
PARALLAX.update({"deep": 11.0, "deep2": 6.0, "fg1": -85.0, "fg2": -68.0, "fg3": -115.0})
_doodad_rng = random.Random(4242)


def soft_blur(surf, factor=4):
    """Cheap depth-of-field: shrink then enlarge with smoothing."""
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


# --- distant plant tufts: dim silhouettes that sway slowly, deep behind everything ---
def build_deep_stalk(h, seed):
    """A tuft of long thin grass blades that lean and curl, dim and out of focus."""
    rng = random.Random(seed)
    w = 96
    surf = pygame.Surface((w, int(h) + 12), pygame.SRCALPHA)
    col = (14, 50, 102, 255)
    for b in range(rng.randint(4, 6)):
        lean = rng.uniform(-0.5, 0.5)
        ln = h * rng.uniform(0.55, 1.0)
        wd = rng.uniform(3.5, 6.0)
        left, right = [], []
        for i in range(13):
            u = i / 12
            cx = w / 2 + (b - 2) * 5 + lean * ln * u * u * 0.5 + math.sin(u * 3.2 + seed + b) * 4 * u
            cy = h + 6 - ln * u
            half = wd * 0.5 * (1 - u ** 1.6) + 0.4
            left.append((cx - half, cy))
            right.append((cx + half, cy))
        pygame.draw.polygon(surf, col, left + right[::-1])
    return surf


DEEP_SHAPES = [(build_deep_stalk(random.Random(i).uniform(230, 520) * VS ** 0.8, i)) for i in range(4)]
DEEP_ROT = {}
DEEP_STALKS = [(_doodad_rng.uniform(-40, SCREEN_WIDTH + 40), _doodad_rng.randrange(4), _doodad_rng.uniform(0, math.tau))
               for _ in range(max(14, SCREEN_WIDTH // 80))]


def deep_sprite(shape, step):
    key = (shape, step)
    spr = DEEP_ROT.get(key)
    if spr is None:
        spr = pygame.transform.rotate(DEEP_SHAPES[shape], step * 1.6)
        spr.set_alpha(62)
        DEEP_ROT[key] = spr
    return spr


# --- (jellyfish removed for freshwater; the list stays empty) ---
def build_jelly(size, frame_i):
    w, h = int(size * 1.4), int(size * 3.2)
    spr = pygame.Surface((w, h), pygame.SRCALPHA)
    pulse = math.sin(frame_i / 6 * math.tau)
    bw, bh = size * (1.0 + 0.1 * pulse), size * (0.72 - 0.12 * pulse)
    cx = w / 2
    for k in range(6):
        tx = cx + (k - 2.5) * size * 0.16
        pts = [(tx + math.sin(k + j * 0.7 + frame_i * 0.5) * size * 0.08, bh * 0.6 + j * size * 0.3) for j in range(8)]
        pygame.draw.lines(spr, (170, 205, 245, 130), False, pts, 1)
    shaded_ellipse(spr, (cx - bw / 2, 2, bw, bh), (196, 220, 255), (110, 150, 225), 8)
    pygame.draw.ellipse(spr, (225, 240, 255, 150), (cx - bw * 0.28, 5, bw * 0.56, bh * 0.35))
    pygame.draw.arc(spr, (230, 240, 255, 200), (cx - bw / 2, 2, bw, bh * 1.5), 0.15, math.pi - 0.15, 1)
    spr.set_alpha(120)
    return spr


JELLY_FRAMES = {s: [build_jelly(s, i) for i in range(6)] for s in (30, 44, 58)}
JELLIES = [[_doodad_rng.uniform(0, SCREEN_WIDTH), _doodad_rng.uniform(WATER_TOP + 60, SCREEN_HEIGHT - 200),
            _doodad_rng.choice([30, 44, 58]), _doodad_rng.uniform(0, 6), _doodad_rng.uniform(-0.18, 0.18)] for _ in range(0)]


# --- a distant school of tiny fish crossing the back of the tank ---
def build_micro_fish():
    spr = pygame.Surface((26, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(spr, (28, 74, 132, 255), (6, 2, 18, 8))
    pygame.draw.polygon(spr, (28, 74, 132, 255), [(8, 6), (0, 1), (0, 11)])
    spr.set_alpha(120)
    return spr


MICRO_FISH = build_micro_fish()
MICRO_FLIP = pygame.transform.flip(MICRO_FISH, True, False)
SCHOOL = {"x": SCREEN_WIDTH * 0.3, "y": WATER_TOP + 220 * VS, "dir": 1,
          "members": [(_doodad_rng.uniform(-90, 90), _doodad_rng.uniform(-40, 40), _doodad_rng.uniform(0, math.tau)) for _ in range(14)]}


def draw_deep_doodads(surface, clock):
    ox, oy = poff("deep")
    base_y = SCREEN_HEIGHT - SAND_HEIGHT - 50 + oy
    for x, shape, ph in DEEP_STALKS:
        step = max(-3, min(3, round((math.sin(clock * 0.011 + ph + x * 0.004) * 2.4 + eco.current * 20) / 1.6)))
        spr = deep_sprite(shape, step)
        r = DEEP_SHAPES[shape].get_height() / 2 - 6
        a = math.radians(step * 1.6)
        cxs, cys = x + ox - r * math.sin(a), base_y - r * math.cos(a)
        surface.blit(spr, spr.get_rect(center=(int(cxs), int(cys))))
    ox2, oy2 = poff("deep2")
    for j in JELLIES:
        j[1] -= 0.18
        j[0] += j[4] + math.sin(clock * 0.01 + j[3]) * 0.12
        if j[1] < WATER_TOP + 20:
            j[1] = SCREEN_HEIGHT - 150
            j[0] = _doodad_rng.uniform(0, SCREEN_WIDTH)
        frames = JELLY_FRAMES[j[2]]
        spr = frames[int(clock / 7 + j[3]) % 6]
        surface.blit(spr, (int(j[0] % SCREEN_WIDTH) + ox2, int(j[1]) + oy2))
    SCHOOL["x"] += 0.35 * SCHOOL["dir"]
    SCHOOL["y"] += math.sin(clock * 0.004) * 0.15
    if SCHOOL["x"] > SCREEN_WIDTH + 140 or SCHOOL["x"] < -140:
        SCHOOL["dir"] *= -1
        SCHOOL["y"] = WATER_TOP + _doodad_rng.uniform(120, 360) * VS
    spr = MICRO_FISH if SCHOOL["dir"] > 0 else MICRO_FLIP
    for mx, my, ph in SCHOOL["members"]:
        surface.blit(spr, (int(SCHOOL["x"] + mx + math.sin(clock * 0.02 + ph) * 12) + ox2, int(SCHOOL["y"] + my + math.cos(clock * 0.017 + ph) * 8) + oy2))


# --- foreground: big out-of-focus rocks, driftwood and leaves at the bottom corners, bokeh, bubbles and a passing silhouette ---
def build_fg_corner(seed, flip):
    rng = random.Random(seed)
    w, h = 230, 190   # drawn at half size, then blown up and blurred
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for k in range(4):  # rounded rock mounds that fall away from the corner
        rw, rh = rng.randint(60, 110), rng.randint(40, 80)
        rx, ry = rng.randint(0, w - rw - 30), h - rh - rng.randint(0, 30)
        pts = smooth_closed([(rx, h + 4), (rx + 4, ry + rh * 0.5), (rx + rw * 0.3, ry + 6), (rx + rw * 0.7, ry), (rx + rw, ry + rh * 0.6), (rx + rw + 8, h + 4)], 5)
        shaded_polygon(surf, pts, (70, 104, 110), (20, 40, 54))
    cx = rng.randint(70, w - 100)
    bark = (84, 58, 38)
    for k in range(3):  # a driftwood branch with forks, lying across the corner
        bx = rng.randint(10, w - 90)
        by = h - rng.randint(8, 26)
        pts = [(bx, by), (bx + 26, by - 14), (bx + 56, by - 10), (bx + 84, by - 30)]
        pygame.draw.lines(surf, bark, False, pts, 8 - k)
        pygame.draw.lines(surf, (118, 86, 58), False, [(x, y - 2) for x, y in pts], 2)
        fx, fy = pts[2]
        pygame.draw.lines(surf, bark, False, [(fx, fy), (fx + 10, fy - 26), (fx + 4, fy - 46)], 5)
    for k in range(5):  # broad sword-plant leaves arching out of the corner
        sx = rng.randint(14, w - 24)
        lean = rng.uniform(-1, 1)
        ln = rng.randint(70, 140)
        left, right = [], []
        for i in range(10):
            u = i / 9
            cx = sx + lean * ln * u * 0.55 + math.sin(u * 2.6 + k) * 6
            cy = h - ln * u
            half = 11 * math.sin(math.pi * min(1.0, u * 1.05)) ** 0.7 + 0.5
            left.append((cx - half, cy))
            right.append((cx + half, cy))
        pygame.draw.polygon(surf, mix((58, 124, 62), (28, 80, 46), k / 5), left + right[::-1])
        pygame.draw.lines(surf, (110, 168, 96), False, [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(left, right)], 1)
    big = pygame.transform.smoothscale(surf, (w * 2, h * 2))
    big = soft_blur(big, 5)
    big.fill((150, 172, 196, 255), special_flags=pygame.BLEND_RGBA_MULT)
    big.set_alpha(215)
    return pygame.transform.flip(big, True, False) if flip else big


FG_CORNER_L = build_fg_corner(11, False)
FG_CORNER_R = build_fg_corner(23, True)


def build_bokeh(r):
    spr = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    for k in range(r, 0, -1):
        pygame.draw.circle(spr, (210, 235, 255, int(46 * (1 - k / r) ** 0.5 + 8)), (r + 1, r + 1), k)
    return spr


BOKEH = {r: build_bokeh(r) for r in (7, 11, 16)}
BOKEH_LIST = [[_doodad_rng.uniform(0, SCREEN_WIDTH), _doodad_rng.uniform(WATER_TOP, SCREEN_HEIGHT), _doodad_rng.choice([7, 11, 16]),
               _doodad_rng.uniform(0.12, 0.38), _doodad_rng.uniform(0, math.tau)] for _ in range(16)]


def build_big_bubble(r):
    spr = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(spr, (210, 235, 255, 40), (r + 2, r + 2), r)
    pygame.draw.circle(spr, (235, 248, 255, 190), (r + 2, r + 2), r, 2)
    pygame.draw.ellipse(spr, (255, 255, 255, 220), (r * 0.5, r * 0.45, r * 0.5, r * 0.3))
    return spr


BIG_BUBBLES = {r: build_big_bubble(r) for r in (6, 9, 13)}
FG_BUBBLES = []


def build_passing_fish():
    w, h = 300, 130
    spr = pygame.Surface((w, h), pygame.SRCALPHA)
    col = (8, 30, 70, 255)
    pygame.draw.ellipse(spr, col, (60, 24, 210, 82))
    pygame.draw.polygon(spr, col, [(76, 64), (10, 14), (30, 64), (10, 114)])
    pygame.draw.polygon(spr, col, [(150, 26), (190, 0), (225, 30)])
    spr = soft_blur(spr, 4)
    spr.set_alpha(110)
    return spr


PASSING_FISH = build_passing_fish()
PASSING = {"x": -400.0, "y": 300.0, "dir": 1, "wait": 900}


def draw_fore_doodads(surface, clock):
    # passing, very out-of-focus fish
    p = PASSING
    if p["wait"] > 0:
        p["wait"] -= 1
        if p["wait"] == 0:
            p["dir"] = random.choice([-1, 1])
            p["x"] = -340 if p["dir"] > 0 else SCREEN_WIDTH + 340
            p["y"] = random.uniform(WATER_TOP + 120, SCREEN_HEIGHT - 260)
    else:
        p["x"] += 1.1 * p["dir"]
        spr = PASSING_FISH if p["dir"] > 0 else pygame.transform.flip(PASSING_FISH, True, False)
        ox, oy = poff("fg3")
        surface.blit(spr, (int(p["x"]) + ox, int(p["y"] + math.sin(clock * 0.01) * 14) + oy))
        if p["x"] < -420 or p["x"] > SCREEN_WIDTH + 420:
            p["wait"] = random.randint(1500, 3600)
    ox, oy = poff("fg2")
    for b in BOKEH_LIST:
        b[1] -= b[3]
        b[0] += math.sin(clock * 0.01 + b[4]) * 0.2
        if b[1] < WATER_TOP - 20:
            b[1] = SCREEN_HEIGHT + 20
            b[0] = random.uniform(0, SCREEN_WIDTH)
        spr = BOKEH[b[2]]
        surface.blit(spr, (int(b[0]) + ox - b[2], int(b[1]) + oy - b[2]))
    if clock % 140 == 0 and len(FG_BUBBLES) < 7:
        FG_BUBBLES.append([random.uniform(40, SCREEN_WIDTH - 40), SCREEN_HEIGHT + 10, random.choice([6, 9, 13]), random.uniform(1.0, 2.2), random.uniform(0, 6)])
    for b in FG_BUBBLES[:]:
        b[1] -= b[3]
        b[0] += math.sin(clock * 0.05 + b[4]) * 0.6
        if b[1] < WATER_TOP - 20:
            FG_BUBBLES.remove(b)
            continue
        spr = BIG_BUBBLES[b[2]]
        surface.blit(spr, (int(b[0]) + ox - b[2], int(b[1]) + oy - b[2]))
    fx, fy = poff("fg1")
    surface.blit(FG_CORNER_L, (-200 + fx, SCREEN_HEIGHT - FG_CORNER_L.get_height() + 90 + fy))
    surface.blit(FG_CORNER_R, (SCREEN_WIDTH - FG_CORNER_R.get_width() + 200 + fx, SCREEN_HEIGHT - FG_CORNER_R.get_height() + 90 + fy))


def use_set(name, save=True):
    """Switch to another fish set and its aquascape: the scape-driven look (sand, back wall, water values, bands) follows.
    The world itself is built afterwards by fresh_tank() or load_game()."""
    global SAND_TOP, SAND_BOT, SAND_GRAINS, KH_OK, GH_OK, BG_RIDGE, BG_DOODADS, bg_image
    if save:
        try:
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("active_set") != name:
                data["active_set"] = name
                with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2)
        except (OSError, ValueError):
            pass
    load_fish_config(force=name)
    SAND_TOP, SAND_BOT, SAND_GRAINS = sand_colours()
    grains[:] = [(gx, gy, random.choice(SAND_GRAINS)) for gx, gy, _ in grains]
    build_sand()
    KH_OK = tuple(scape("water", "kh_range", (3, 10)))
    GH_OK = tuple(scape("water", "gh_range", (4, 12)))
    BG_RIDGE = scape("background", "ridge", True)
    BG_DOODADS = scape("background", "doodads", True)
    try:
        bg_image = load_bg(bg_files[bg_index])
    except Exception:
        pass
    CHEM.update(nh3=0.0, no2=0.0, no3=6.0, ph=float(scape("water", "ph", 7.1)), kh=float(scape("water", "kh", 6.0)),
                gh=float(scape("water", "gh", 8.0)))


def fresh_tank():
    """A brand-new tank of the active set (the R key, and New game on the start menu)."""
    global fishes, shimps, daphnia, frame
    frame = 0
    fishes = []
    shimps = [TinyShrimp() for _ in range(20)]
    daphnia = [Daphnia() for _ in range(40)]
    rebuild_world()
    algae.clear()
    pellets.clear()
    bubbles.clear()
    init_ecosystem()
    load_fish_config(force=ACTIVE_SET)
    fishes[:] = spawn_community()


def saved_tank_info():
    """What the Continue button offers: the autosave's set and age, or None when there is nothing to continue."""
    try:
        with open(AUTOSAVE_PATH, encoding="utf-8") as fh:
            d = json.load(fh)
        return d.get("set") or "?", max(0.0, time.time() - float(d.get("saved_at", time.time()))), len(d.get("fish", []))
    except (OSError, ValueError, TypeError):
        return None


start_hum()
