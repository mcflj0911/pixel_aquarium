while True:
    SPRITE_BUDGET[0] = 0
    WELCOME_LIVE = current_state == STATE_WELCOME
    if WELCOME_LIVE:
        warm_step(10.0)   # the welcome screen is idle time: build the fish sprites now so the tank never hitches later
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                quit_game()
            act = None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                wm = world_mouse(e.pos)
                for k, r in WELCOME_UI.items():
                    if r is not None and r.collidepoint(wm):
                        act = k
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    act = "cont" if saved_tank_info() else "new"
                elif e.key == pygame.K_c:
                    act = "cont" if saved_tank_info() else None
                elif e.key == pygame.K_n:
                    act = "new"
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    act = "prev"
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    act = "next"
            if act in ("prev", "next") and SET_NAMES:
                i = SET_NAMES.index(ACTIVE_SET) if ACTIVE_SET in SET_NAMES else 0
                use_set(SET_NAMES[(i + (1 if act == "next" else -1)) % len(SET_NAMES)])
                fresh_tank()                # the preview behind the menu is a fresh tank of the chosen set
            elif act == "new":
                fresh_tank()
                current_state = STATE_AQUARIUM
            elif act == "cont":
                load_game(AUTOSAVE_PATH, away=True)
                current_state = STATE_AQUARIUM
    else:
        warm_step(3.0)   # finish any sprites the welcome screen didn't get to, a few ms at a time
    if True:   # the tank runs behind the welcome screen too, so the menu is a live preview
        frame += 1
        if frame % LOG_INTERVAL == 0:
            starving_count = 0
            log_output = ""
            fish_counts = {}

            for f in fishes:
                fish_type = f.__class__.__name__
                fish_counts[fish_type] = fish_counts.get(fish_type, 0) + 1
                if f.hunger > 70:
                    log_output += f"[{fish_type} #{getattr(f, 'id', '???')}] "
                    starving_count += 1

            print("--- Current Tank Population ---")
            sorted_fish = sorted(fish_counts.items(), key=lambda item: item[1], reverse=True)
            for species, count in sorted_fish:
                print(f"{species}: {count}")

            if starving_count > 0:
                print(f"\n--- ALERT: STARVING FISH DETECTED ({starving_count}) ---")
                print(log_output.strip())
                print("---------------------------------------------------\n")
            if starving_count > 10:
                print("!!! CRITICAL STARVATION: MASSIVE ALGAE BLOOM TRIGGERED !!!")
                for _ in range(50):
                    new_algae = (
                        random.randint(20, SCREEN_WIDTH - 20),
                        random.randint(int(WATER_TOP + 220 * VS), SCREEN_HEIGHT - SAND_HEIGHT)
                    )
                    algae.append(new_algae)

        update_parallax()
        bgx, bgy = poff("bg")
        screen.blit(bg_image, (bgx - BG_MARGIN, bgy - BG_MARGIN))
        screen.blit(water_gradient, (0, 0))
        if BG_RIDGE:
            screen.blit(far_ridge, (-40 + poff("far")[0], poff("far")[1]))
        if BG_DOODADS:
            draw_deep_doodads(screen, PLANT_CLOCK)

        auto_feed_timer -= 1
        if auto_feed_timer <= 0:
            if len(pellets) < 15:
                pellets.append(FoodPellet(random.randint(50, SCREEN_WIDTH - 50), WATER_TOP))
            auto_feed_timer = 100

        update_mouse_track()
        eco.update()
        process_respawns()
        fw21_update()
        for p in (() if PM["on"] else predators[:]):
            p.update()
            if not p.alive:
                predators.remove(p)
        for v in (() if PM["on"] else visitors[:]):
            v.update()
            if not v.alive:
                visitors.remove(v)

        for f in (() if PM["on"] else fishes[:]):   # planting mode: the fish are put away, nothing swims or ages
            if not f.alive:  # eaten this frame; a newcomer swims in later
                record_death(f, "eaten")
                fishes.remove(f)
                respawn_queue.append((eco.t + random.randint(300, 800), "fish"))
                continue
            f.behavior(fishes)
            prey_social(f)
            feed_learning(f)
            fish_life(f)
            f.update(pellets, algae)
            if not f.alive:  # starved
                record_death(f)
                fishes.remove(f)
                respawn_queue.append((eco.t + random.randint(120, 360), "fish"))
        eco.refresh_moods()
        update_plants()

        plant_tick += 1
        # Plants sway slowly and are the costliest layer, so each frame redraws only one third-width strip of the tank
        # (rotating), which keeps the load identical every frame instead of one heavy frame in three.
        n_strips = QUALITY_SPECS[QUALITY[0]]["strips"]
        strip_w = SCREEN_WIDTH // n_strips + 1
        strip = pygame.Rect((plant_tick % n_strips) * strip_w, 0, strip_w, SCREEN_HEIGHT)
        for name, layer in layer_surfs.items():
            if name in ("plants", "hang_bg", "hang_fg"):
                layer.fill((0, 0, 0, 0), strip)
            else:
                layer.fill((0, 0, 0, 0))
        L_far, L_mid, L_plants, L_near = (layer_surfs[k] for k in ("far", "mid", "plants", "near"))
        entities = [] if PM["on"] else sorted(fishes + predators + visitors, key=lambda e: e.z)
        for e in entities:
            if e.dz <= LAYER_FAR:
                e.draw(L_far)
        for r in rocks:
            if r.z < LAYER_FAR:
                r.draw(L_far)
        for e in entities:
            if LAYER_FAR < e.dz <= LAYER_MID:
                e.draw(L_mid)
        for r in rocks:
            if LAYER_FAR <= r.z < 0.95:
                r.draw(L_mid)
        draw_stations(L_mid, False)
        L_hbg, L_hfg = layer_surfs["hang_bg"], layer_surfs["hang_fg"]
        for lay in (L_plants, L_hbg, L_hfg):
            lay.set_clip(strip)
        hang_target = {"bg": L_hbg, "mid": L_plants, "fg": L_hfg}
        for p in plants:
            if strip.left - 90 < p.pos_x < strip.right + 90:
                p.draw(hang_target[p.layer] if p.hang else L_plants, frame)
        for lay in (L_plants, L_hbg, L_hfg):
            lay.set_clip(None)
        for e in entities:
            if e.dz > LAYER_MID:
                e.draw(L_near)
        for r in rocks:
            if r.z >= 0.95:
                r.draw(L_near)
        draw_stations(L_near, True)
        for egg in eggs:
            egg.draw(L_near)
        for p in pebbles:
            p.draw(L_near)
        draw_pits(L_near)
        for c in (() if PM["on"] else crawlers):
            c.update()
            c.draw(L_near)

        blit_edges(screen, L_hbg, poff("hang_bg"))   # pothos behind the fish
        screen.blit(L_far, poff("far"))
        screen.blit(sand_layer, (0, SCREEN_HEIGHT - 120), area=pygame.Rect(0, SCREEN_HEIGHT - 120, SCREEN_WIDTH, 120))
        screen.blit(L_mid, (0, 0))
        screen.blit(L_plants, poff("plants"))
        screen.blit(L_near, poff("near"))
        blit_edges(screen, L_hfg, poff("hang_fg"))   # pothos in front of everything in the tank

        draw_sick(screen)
        draw_world21(screen)
        draw_world6(screen)
        for nst in foam_nests[:]:
            if nst.update():
                nst.draw(screen)
            else:
                foam_nests.remove(nst)
        for s in (() if PM["on"] else shimps):
            s.update(algae)
            shrimp_flee(s)
            s.draw(screen)
        draw_air_stone(screen)
        draw_nets(screen)
        draw_shells(screen)
        if eco.bag is not None:
            eco.bag.draw(screen)
        for k in (() if PM["on"] else daphnia):
            update_daphnia(k)
            k.draw(screen)

        for s in snow:
            s.update()
            s.draw(screen)

        screen.blit(CAUSTIC_OVERLAYS[(frame // CAUSTIC_SLOWNESS) % CAUSTIC_FRAMES], (poff('bg')[0] // 2, 0), special_flags=pygame.BLEND_RGB_ADD)

        for e in (() if WELCOME_LIVE else pygame.event.get()):
            if e.type == pygame.QUIT:
                quit_game()
            if screensaver:   # any key or click wakes the tank back up
                if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    screensaver = False
                    eco.show_hud = saved_hud
                    pygame.mouse.set_visible(True)
                continue
            if confirm_quit:   # the quit dialog swallows all other input
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                        quit_game()
                    if e.key in (pygame.K_n, pygame.K_ESCAPE):
                        confirm_quit = False
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    pos = world_mouse(e.pos)
                    if QUIT_BTNS.get("quit") and QUIT_BTNS["quit"].collidepoint(pos):
                        quit_game()
                    if QUIT_BTNS.get("keep") and QUIT_BTNS["keep"].collidepoint(pos):
                        confirm_quit = False
                continue
            if pm_event(e):
                continue
            if fw21_event(e):
                continue
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F1:
                    show_help = not show_help
                elif e.key == pygame.K_ESCAPE and show_help:
                    show_help = False
                elif e.key == pygame.K_ESCAPE and show_goals:
                    show_goals = False
                elif e.key == pygame.K_ESCAPE and show_strains:
                    show_strains = False
                elif e.key == pygame.K_ESCAPE:
                    confirm_quit = True
                if e.key == pygame.K_F3:
                    show_fps = not show_fps
                if e.key == pygame.K_q:
                    names = list(QUALITY_SPECS)
                    QUALITY[0] = names[(names.index(QUALITY[0]) + 1) % len(names)]
                    GOV["base"] = QUALITY[0]
                    save_prefs()
                    light_notif_text = "Quality: " + QUALITY[0]
                    light_notif_alpha = 255
                if e.key == pygame.K_F11:
                    set_display(not is_full)
                    light_notif_text = "Fullscreen" if is_full else "Windowed"
                    light_notif_alpha = 255
                if e.key == pygame.K_F10:
                    screensaver, saved_hud = True, eco.show_hud
                    eco.show_hud, eco.show_journal, show_help = False, False, False
                    light_notif_alpha = 0
                    if not is_full:
                        set_display(True)
                    pygame.mouse.set_visible(False)
                if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    step = -0.1 if e.key in (pygame.K_MINUS, pygame.K_KP_MINUS) else 0.1
                    VOL["master"] = clamp(round(VOL["master"] + step, 2))
                    apply_music_volume()
                    save_prefs()
                    play_sfx("bubble")
                    light_notif_text = f"Volume {round(VOL['master'] * 100)}%"
                    light_notif_alpha = 255
                if e.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    VOL["fx"] = clamp(round(VOL["fx"] + (-0.1 if e.key == pygame.K_LEFTBRACKET else 0.1), 2))
                    save_prefs()
                    play_sfx("chime")
                    light_notif_text = f"Effects volume {round(VOL['fx'] * 100)}%"
                    light_notif_alpha = 255
                if e.key == pygame.K_9:
                    pour_methylene_blue()
                if e.key == pygame.K_0:
                    pour_vitamins()
                if e.key == pygame.K_u:
                    dose_medicine()
                if e.key == pygame.K_i:
                    toggle_quarantine()
                if e.key == pygame.K_s:
                    toggle_nursery()
                if e.key == pygame.K_y:
                    eco.heater = {"OFF": "LOW", "LOW": "HIGH", "HIGH": "OFF"}[eco.heater]
                    notify("Heater: " + eco.heater, log=False)
                if e.key == pygame.K_TAB:
                    show_strains = not show_strains
                if e.key == pygame.K_c:
                    start_wipe()
                if e.key == pygame.K_f:
                    rinse_filter()
                    chem_rinse()
                if e.key == pygame.K_l:
                    eco.lights = {"SUN": "ON", "ON": "OFF", "OFF": "SUN"}[eco.lights]
                    notify("Lights: " + eco.lights, log=False)
                if e.key == pygame.K_a:
                    eco.air_on = not eco.air_on
                    notify("Air stone: " + ("ON" if eco.air_on else "OFF"), log=False)
                if e.key == pygame.K_g:
                    show_goals = not show_goals
                if e.key == pygame.K_k:
                    eco.cinema = not eco.cinema
                    eco.cin_t = 0
                    if not eco.cinema:
                        eco.follow = False
                    notify("Cinema camera: " + ("ON" if eco.cinema else "OFF"), log=False)
                if e.key == pygame.K_o:
                    eco.realtime = not eco.realtime
                    notify("Clock: " + ("REAL TIME" if eco.realtime else "TANK TIME"), log=False)
                if e.key == pygame.K_x:
                    PARALLAX_ON = not PARALLAX_ON
                    light_notif_text = "Parallax: " + ("ON" if PARALLAX_ON else "OFF")
                    light_notif_alpha = 255
                if e.key == pygame.K_v:
                    is_muted = not is_muted
                    apply_music_volume()
                    light_notif_text = "Audio: MUTED" if is_muted else "Audio: ON"
                    light_notif_alpha = 255
                if e.key == pygame.K_m:
                    current_music_idx = (current_music_idx + 1) % len(music_files)
                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(get_path(music_files[current_music_idx]))
                        apply_music_volume()
                        pygame.mixer.music.play(-1)
                        light_notif_text = f"NOW PLAYING: {music_files[current_music_idx]}"
                        light_notif_alpha = 255
                    except pygame.error:
                        print(f"Error loading: {music_files[current_music_idx]}")
                if e.key == pygame.K_n:
                    current_light_idx = (current_light_idx + 1) % len(LIGHT_MODES)
                    light_notif_text = f"Mode: {LIGHT_MODES[current_light_idx]['name']}"
                    light_notif_alpha = 255
                if e.key == pygame.K_b:
                    bg_index = (bg_index + 1) % len(bg_files)
                    light_notif_text = f"ART CHANGED TO: {bg_files[bg_index]}"
                    light_notif_alpha = 255
                    try:
                        bg_image = load_bg(bg_files[bg_index])
                    except Exception:
                        pass
                if e.key == pygame.K_r:
                    current_state = STATE_WELCOME
                    fresh_tank()
                if e.key == pygame.K_h:
                    eco.show_hud = not eco.show_hud
                if e.key == pygame.K_t:
                    eco.cycle_on = not eco.cycle_on
                    notify("Day/night cycle: " + ("RUNNING" if eco.cycle_on else "PAUSED"))
                if e.key == pygame.K_e:
                    eco.start_event()
                if e.key == pygame.K_j:
                    eco.show_journal = not eco.show_journal
                if e.key == pygame.K_p and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    PHOTO["style"] = (PHOTO["style"] + 1) % len(PHOTO_STYLES)
                    notify("Photo style: " + PHOTO_STYLES[PHOTO["style"]], log=False)
                elif e.key == pygame.K_p:
                    eco.photo = True
                if e.key == pygame.K_z and eco.selected is not None:
                    eco.follow = not eco.follow
                if e.key == pygame.K_w:
                    eco.water = min(100.0, eco.water + 35)
                    play_sfx("bubble")
                    notify("Water change: the tank is fresher", log=True)
                    chem_water_change()
                if e.key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    trim_plants()
                elif e.key == pygame.K_d:
                    eco.decor_idx = (eco.decor_idx + 1) % len(DECOR_TOOLS)
                    notify("Build tool: " + DECOR_TOOLS[eco.decor_idx] + (" (click to place)" if eco.decor_idx else ""), log=False)
                if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    eco.feed_idx = e.key - pygame.K_1
                    notify("Feed: " + FEEDS[eco.feed_idx], log=False)
                if e.key == pygame.K_F5:
                    save_game()
                if e.key == pygame.K_F9:
                    backup_current()
                    load_game()
            if e.type == pygame.MOUSEBUTTONDOWN:
                tool = DECOR_TOOLS[eco.decor_idx]
                if e.button == 2 or (e.button == 1 and pygame.key.get_mods() & pygame.KMOD_SHIFT):
                    pick_fish(pygame.Vector2(world_mouse(e.pos)))
                elif e.button == 1 and tool == "TRIM":
                    trim_plants(world_mouse(e.pos)[0])
                elif e.button == 1 and tool != "OFF":
                    place_decor(tool, world_mouse(e.pos)[0])
                elif e.button == 1:
                    if eco.selected is not None and eco.follow is False and not any(
                            f.pos.distance_to(pygame.Vector2(world_mouse(e.pos))) < 60 for f in fishes):
                        eco.selected = None
                    drop_feed(world_mouse(e.pos))
                elif e.button == 3:
                    eco.tap(world_mouse(e.pos))

        if frame % ALGAE_SPAWN_RATE == 0 and len(algae) < 35:
            algae.append((random.randint(10, SCREEN_WIDTH - 10), random.randint(WATER_TOP + 20, SCREEN_HEIGHT - SAND_HEIGHT - 60)))

        for a in algae:
            pygame.draw.circle(screen, CLR_ALGAE, a, 3)

        for p in pellets[:]:
            p.update()
            p.draw(screen)

        for b in bubbles[:]:
            b.update()
            b.draw(screen)
            if b.pos.y < 80:
                bubbles.remove(b)

        draw_fx(screen)
        draw_fore_doodads(screen, PLANT_CLOCK)
        draw_foreground(screen, frame)
        draw_algae_world(screen)
        screen.blit(surface_haze, (0, 0))
        draw_daylight(screen)
        draw_glass(screen)
        draw_moon(screen)
        draw_rain(screen)

        mode = LIGHT_MODES[current_light_idx]

        if mode["name"] == "RGB STROBE":
            t = pygame.time.get_ticks() * 0.0005
            r = int(127 + 127 * math.sin(t))
            g = int(127 + 127 * math.sin(t + 2))
            b = int(127 + 127 * math.sin(t + 4))
            light_surf.fill((r, g, b, 40))
        else:
            light_surf.fill(mode["color"])

        screen.blit(light_surf, (0, 0))
        draw_emotes(screen)
        draw_selection(screen)
        apply_follow_cam(screen)
        apply_tour_cam(screen)
        cap_tick(screen)
        if eco.photo:  # captured before the HUD goes on, so the picture is clean
            eco.photo = False
            take_photo(screen)
        rec_capture(screen)
        draw_ui(screen)
        draw_care_status(screen)
        draw_hud21(screen)
        draw_card21(screen)
        draw_hud6(screen)
        draw_plant_mode(screen)
        if show_goals:
            draw_goals(screen)
        if show_strains:
            draw_strains(screen)
        if show_help:
            draw_help(screen)
        draw_panel21(screen)
        if confirm_quit:
            draw_quit_modal(screen)
        if photo_flash > 0:   # the camera flash after a photo
            FLASH_SURF.set_alpha(photo_flash * 17)
            screen.blit(FLASH_SURF, (0, 0))
            photo_flash -= 1
        if show_fps:
            frame_times.append(clock.get_time())
            fps = clock.get_fps()
            txt = hud_font().render(f"FPS {fps:4.1f}   worst {max(frame_times)} ms", True,
                                    (120, 255, 150) if fps >= 58 else (255, 200, 90) if fps >= 45 else (255, 90, 90))
            screen.blit(txt, (SCREEN_WIDTH - txt.get_width() - 14, SCREEN_HEIGHT - 26))
        if screensaver:
            light_notif_alpha = 0
    if WELCOME_LIVE:
        draw_welcome_screen()
    if light_notif_alpha > 0:
        text_surf = notif_font.render(light_notif_text, True, (220, 220, 220))
        notif_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        notif_surf.blit(text_surf, (0, 0))
        notif_surf.set_alpha(light_notif_alpha)
        padding = 20
        screen.blit(notif_surf, (SCREEN_WIDTH - text_surf.get_width() - padding, padding))
        light_notif_alpha = max(0, light_notif_alpha - 2)

    try:
        if QUALITY_SPECS[QUALITY[0]]["smooth"]:
            pygame.transform.smoothscale(screen, (DISPLAY_W, DISPLAY_H), display)
        else:
            pygame.transform.scale(screen, (DISPLAY_W, DISPLAY_H), display)
    except (ValueError, pygame.error):
        display.blit(pygame.transform.scale(screen, (DISPLAY_W, DISPLAY_H)), (0, 0))
    pygame.display.flip()
    quality_governor()
    clock.tick(60)
    frame += 1
