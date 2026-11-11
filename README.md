# 🐠 Pixel Aquarium (Freshwater Edition)

A high-fidelity, interactive freshwater community tank built with Python and **Pygame-CE**: hand-shaded fish, living plants, a full ecosystem with predators, breeding and a day/night cycle, drawn as a full-screen 2.5D scene with parallax.

## 🌟 The community

### Fish sets (config file)

The game has 22 species and stocks one **set** of them at a time. Choose it in `aquarium_config.json`, which is created next to `main.py` the first time you run the game:

```json
{
  "active_set": "tetra_set",
  "max_fish": 34,
  "sets": { "tetra_set": { "NeonTetra": [10, 6, 10] } }
}
```

| Set | What it stocks |
| :--- | :--- |
| `cichlid_set` | The all-cichlid mbuna tank around the demasoni (below) |
| `tetra_set` (default) | The tetra family: neon, rummy-nose, cardinal, ember, black skirt and lemon tetras, plus four guppy varieties |
| `mixed_set` | Cichlids and tetras together with the bala shark, boesemani rainbow, tiger barb, clown loach, pleco and pearl gourami |

Set `active_set` to any of these and press **R** in the game to re-read the file and re-stock the tank (or just restart). Each set maps a species class name to `[share, smallest_group, largest_group]`, and you can add your own sets under `"sets"`. `max_fish` caps the number of fish in the tank (lower it if the frame rate drops). The full species list is in the file's `_help` entry. Unknown names are skipped with a message in the console, and a missing or broken file falls back to the defaults.

### The cichlid set

An **all-cichlid tank** built around the **demasoni**, a colony of sharp-barred sky-blue mbuna that live in dense shoals and are the feistiest fish in the tank. Ten species start in these proportions:

| Species | Look | Role |
| :--- | :--- | :--- |
| **Demasoni** (9) | Small, sky blue with sharp black bars | The colony: shoals tightly, very aggressive toward other species |
| **Yellow lab** (4) | Lemon yellow, dark eye stripe | Peaceful mbuna |
| **Cobalt zebra** (3) | Deep cobalt blue, soft bars | Mid-aggression neighbour |
| **Red zebra** (3) | Orange with cream blotches | Mid-aggression neighbour |
| **Kenyi** (3) | Male mustard-gold with dark bars; female blue-grey with orange blotches | Pushy |
| **Peacock** (3) | Electric blue with an orange flank | Hovers over the sand looking for food |
| **Auratus** (2) | Male black with pale-blue stripes; female golden | The bully |
| **Ice blue ahli** (2) | Pale ice blue, white fin edges | Piscivore: picks off other species' fry |
| **Socolofi** (2) | Pearl pink with salmon fins | Gentle |
| **Angelfish** (2) | Tall silver disc, bold bars, long trailing fins | Open-water cruiser that also eats fry |

All of them patrol a territory, dig the sand, chase other species (and rival males of their own kind), pair up, spawn at a sword plant and guard their clutch. Fry of any species are fair game for the ice blue and the angelfish, and hide in the plants.

Every species is drawn from one shared kit: tapered body outlines, three-tone gradients with a glossy back highlight and faint scales, translucent finned rays, ringed eyes. Sprites are cached.

### The tetra family

Tetras are small, shy shoalers that hide in the plants and are the favourite prey of the ice blue and the angelfish. They have iridescent, glossy bodies with tapered red bellies and glowing neon stripes.

**Guppies** are the showy members of the family. Males carry an oversized fan tail and dorsal fin in one of four patterns (blue **Mosaic**, red **Tuxedo**, **Sunset** cobra and purple **Moscow**) and show off to nearby females; females are larger and plainer, with a soft tinted tail and a gravid spot.

### Hunters
- **Channa** (snakehead): a long cylindrical body that undulates as it swims, small scales in a black and golden-yellow mosaic over a cream belly, one long dorsal fin and a long anal fin, a banded rounded tail, big rounded pectorals, and a flat plated head with a wide toothy mouth, protruding lower jaw, tube nostrils and a small high eye. It lurks, stalks, then blasts in, and brightens to orange when hunting. Picks off strays, sleepers and stressed fish.
- **Fire eel**: dark brown with orange flame stripes; lives in a rock lair, peeks out, scans and lunges.
- **Crayfish**: a bottom ambusher that creeps up on cherry shrimp and pounces with open claws, flicks backwards away from danger and raises a claw toward a still cursor.
- **Red-eared slider**: a rare visitor.

Click (or Shift/middle-click) any hunter for its stats card and press `Z` to follow it. Every kill clouds the water with blood mist and sprays tumbling bits around the bitten fish. The ice blue ahli and the angelfish are also predators of small fry.

### Micro-life and crawlers
**Cherry shrimp** (scavengers, and cleaner stations on the rocks), **Daphnia** (hopping water fleas that serve as live food), **mystery snails** and **ramshorn snails** that help keep the water clean.

## 🧬 Life cycle, sex and breeding
- **Ageing**: fry hatch at 30% size and grow over about 2 minutes; adults are brightest and most saturated in their prime, then fade to a paler, greyer colour as elders and eventually die of old age (the tank restocks).
- **Male / female**: females are larger with a pale gravid belly, males slimmer with a bright nuptial streak and fin-tip dots. Males are bolder.
- **Mating**: every species pairs up for life (a male and a female of the same kind). The male courts with a zig-zag dance, the female plays coy, then the pair leads each other to a sword plant or the sand and spawns.
- **Territory**: after spawning both parents guard (the male longest), chasing off intruders; hungry fish won't eat a guarded clutch and the fry stay near the nest until they are bigger.

## 🌿 Plants, hardscape and scenery
- **Plants**: Rotala, Ludwigia, Hairgrass, Sword (a rosette of arching leaves), Vallisneria, Tiger Lotus and Anubias, with a low ground cover of **dwarf grass**, **cryptocoryne** rosettes (bronze or green), **clover** and **moss balls** across the whole bottom, planted in natural drifts and swaying on a spring model. Slow swells travel across the tank, events push them, and fish stir the plants they pass.
- **Hardscape**: rocks and branching **driftwood** are stacked procedurally; fish and the eel take cover in them.
- **Parallax**: back wall, distant hills and grass tufts, far fish, mid-water fish (the focal plane), plants, near fish and rocks, then blurred foreground driftwood and sword leaves, all slide against each other with the mouse (**X** toggles it). Detritus, bokeh, bubbles and an occasional out-of-focus fish pass in front.

## 🦈 Ecosystem and mood
- **Fish personalities** (bravery, curiosity, sociability): they flee, spread alarm through the shoal, hide, sleep at night, and brave fish can **mob** a resting hunter.
- **Cleaning stations**: stressed fish queue at cleaner shrimp on the rocks.
- **Day/night cycle** (about 4 minutes): fish sleep, hunters hunt harder. Every fourth night is a full-moon spawn.
- **Random events**: Current Surge, Daphnia Bloom, Channa Visitor.
- **Water quality**: uneaten food rots, fish and algae foul the water; plants and snails clean it. Murky water stresses fish and spreads **disease** that the cleaner shrimp can cure.
- **Food chain**: kills leave scraps that sink and feed the fish; losses are replaced by newcomers after a delay, favouring the species furthest below its share.
- **Carrying capacity**: the fish count scales with the tank, worked out from each species' body size, the water-cleaning budget and a frame-rate ceiling (`Prey n/cap` in the HUD).
- **Feed types**: pellets, flakes or live daphnia.
- **Fish have names**: Shift-click one to see its mood, hunger and bravery.
- **Journal**, **photo mode**, **build mode** and **save/load**.

## 🖥️ Full screen and rendering
The tank fills the monitor (**Esc** quits). The world is drawn at reduced resolution (about 1.1 million pixels) and scaled up, keeping the pixel-art look and speed. Set the `AQUARIUM_SCALE` environment variable to override (`1.0` native, `2.0` chunky and fastest). 23 lighting modes (**N**), 9 wall arts (**B**), 4 music tracks (**M**).

## 🎮 Controls

| Key | Action |
| :--- | :--- |
| **Left Click** | Drop food |
| **Right Click** | Tap the glass (scares nearby fish) |
| **Shift+Click / Middle Click** | Select a fish or hunter |
| **Z** | Follow cam on the selection |
| **1 / 2 / 3** | Feed type: pellet, flakes, live daphnia |
| **H** | Toggle the mood HUD |
| **T** | Pause / resume the day-night cycle |
| **E** | Trigger a random event |
| **J** | Journal |
| **P** | Photo mode (saves to `screenshots/`) |
| **W** | Water change |
| **D** | Cycle build tool (rock, driftwood, sword, rotala, ludwigia, dwarf grass, cryptocoryne, clover, moss ball, undo); click to place |
| **F5 / F9** | Save / load (`aquarium_save.json`) |
| **N** | Cycle lighting modes |
| **B** | Cycle wall art |
| **M** | Cycle music |
| **V** | Mute |
| **X** | Toggle parallax |
| **R** | Reset the tank |
| **Space** | Start from the welcome screen |
| **Esc** | Quit |

## 🛠️ Adding a species

All freshwater fish derive from `FWFish`, a data-driven renderer. Subclass it (or one of the existing species classes), set its size, shape and palette, then:

1. Add the class to `FW_CLASSES`.
2. Add it to a set under `"sets"` in `aquarium_config.json` (or to `DEFAULT_SETS` in `main.py`) as `"ClassName": [share, smallest_group, largest_group]`.
3. If it has a new `family_name`, add it to `SPACE_FACTOR`.

## 🚀 Run

```bash
python -m pip install pygame-ce
python main.py
```

`main_original.py` is the previous version, kept for reference.

## Performance notes

- Plants redraw one third-width strip of the tank per frame (rotating), so every frame costs about the same instead of one heavy frame in three.
- Fish sprites are cached per tail-beat frame. The welcome screen pre-builds them, and during play at most one new sprite is built per frame (other fish borrow a near-identical cached one until their own is ready), so first-time sprites no longer cause hitches.
- If it still stutters, lower `max_fish` in `aquarium_config.json` (R reloads it) or set the `AQUARIUM_SCALE` environment variable higher (for example 1.4) to render the world at a lower resolution.

## Tetra-set additions

- `max_fish` now defaults to 45 and the tetra_set shoals are bigger (neons 8-11, embers 7-10, cardinals 6-9...). Delete `aquarium_config.json` to pick up the new defaults.
- In tetra_set the channa and fire eel get hungry 45% slower, so the shoals aren't picked off too fast.
- Guppies are livebearers: a bonded pair produces a brood of 4-7 free-swimming fry (no eggs, no nest).
- New mid-height decor: java fern tied to the driftwood, and pothos vines hanging from the surface.
- Pothos is layered for parallax: background vines (smaller, dimmer, behind the fish), middle strands, and big foreground leaves in front of everything; they shift against each other as the view moves.
- F1 opens a help window listing every key and mouse command (F1 or Esc closes it).
- Esc now asks for confirmation (Y / Enter quits, N / Esc keeps watching; the buttons work too).

## System, species and behaviour additions
- **F3** FPS counter with the worst recent frame. **Q** cycles quality Low / Med / High (plant slices, scaling, fish cap) and is remembered in `aquarium_config.json`.
- **F11** toggles fullscreen and a window. **F10** is screensaver mode: fullscreen, HUD and cursor hidden, any key or click exits.
- **- / =** master volume, **[ / ]** effects volume (both saved). **V** still mutes, **M** still changes track.
- **P** photo: shutter sound, white flash, and the PNG is saved at the monitor's full resolution.
- Click-selected fish now show a portrait, Latin name and a short fact on the card.
- New bottom-dwellers in tetra_set: **Corydoras**, **Otocinclus**, **BristlenosePleco**. Plecos and corydoras rest by day and graze at night.
- Pothos leaves droop and close up a little at night.
- **Channa** now ambushes (lurks still, then bursts out), patrols its own patch, rises to gulp air, and blows and guards a bubble nest at the surface.

## Fire eel and crayfish redraw
- **Fire eel** now has a slim brown body with a pale belly, a long dorsal and an anal fin edged in orange, wavy orange flame stripes with spots, and a pointed head with a fleshy snout tip, a tiny high eye, a gill cover, a pectoral fin and a toothy underslung jaw that opens when it strikes.
- **Crayfish** is a red swamp crayfish: rounded carapace with rostrum and cervical groove, six overlapping tail segments with pleura and a fanned tail, stalked eyes, antennules and antennae, four pairs of walking legs, and two red claws with slender pale-tipped fingers and tubercles. Its colour runs from a red-brown at rest to a brighter red when hunting.

## Realism pass: behaviour
- **Tetras** swim in quick darts followed by glides instead of a constant speed (pauses when scared, sleepy or feeding).
- **Feeding:** pellets are nibbled in three bites, so fish compete, take a bite and drift off; hungry fish speed up in a frenzy. Mid-water fish take food on the way down and only eat from the sand when starving, while corydoras, plecos and loaches go for what has landed.
- **Corydoras** sift the sand head-down in pauses between slow walks, kicking up sand, and occasionally dash to the surface for a gulp of air. They are active by day.
- **Plecos and otocinclus** graze: they pick a leaf, rock or patch of floor, cling on head-up and rasp, which slowly improves water quality. Plecos are nocturnal; otocinclus are diurnal.
- **Guppies:** males pick the nearest adult female, chase her, then shadow her with an S-shaped shimmy, and a female sometimes slips away.

## Realism pass 2
- **Fin flaring:** fish can now spread their fins (a drawn pose, cached like the other sprites). Guppy males flare while shadowing a female, cichlids flare when facing a rival, boesemani males flare side by side, and tiger barbs flare briefly when they nip.
- **Cichlids** also peck the algae film off rocks. **Boesemani** males square up to each other. **Tiger barbs** chase long-finned guppies and angelfish and nip their tails, which stresses and startles the victim. **Pearl gourami** males build a bubble nest at the surface, hover under it and see off visitors.
- **Food clouds:** when flakes or pellets cluster, fish head for the middle of the cloud rather than single pieces, hungry-ish fish join in, and the frenzy is faster the denser the cloud.

## Round 4: learning, genetics, upkeep, events, clock, species, away mode, goals

New keys (also in the F1 help, "CARE & CAMERA" column): **C** wipe the glass, **F** rinse the filter, **L** lights Sun/On/Off,
**A** air stone, **G** goals, **K** cinema camera, **O** real-time clock. The bottom-left status line shows glass, filter, lights and air.

- **Feeding spot**: where you usually click to feed is remembered; hungry mid-water fish drift there while no food is out. Shy fish
  only come once the habit is firm and no hunter is near. The memory fades if you stop.
- **Guppy genetics**: each guppy has a colour gene and a tail-length gene. Fry average both parents, plus mutation, so strains
  drift. The species card shows generation and parents (`gen 3: A x B`). Gene levels change the sprite (hue steps, shorter/longer tail).
- **Upkeep**: algae film grows on the glass (faster with lights on, dirty water, near the edges); otocinclus, plecos and snails graze
  it, C wipes it. The filter sponge clogs slowly and cuts water cleaning until you press F. The air stone (left) makes a bubble
  curtain and adds a little oxygen. L forces lights on/off (algae loves light).
- **Events** (E or random): thunderstorm (lightning, thunder, rain ripples, flicker, frightened fish), power cut (dark, filter and
  air stone off, water degrades), new arrivals (a bag floats at the surface, curious fish visit, newcomers are released stressed).
- **Real-time clock** (O): day/night follows your computer's clock. **Cinema camera** (K): follows interesting fish (courting,
  nesting, being stalked, newborn, sick) and changes subject every 5-9 seconds.
- **Sound**: a low filter hum (off during power cuts), quiet bubble sounds from the air stone, thunder, and the music softens at night.
- **Species**: Betta (flowing fins, bubble nest, flares at rivals), Discus (round, pairs stay close), Killifish (surface shoal).
  They are in `tetra_set`, and `showcase_set` stocks mostly them.
- **Cherry shrimp** now breed (berried females carry green eggs, shrimplets grow up, cap ~44) and moult (pale shells drift down).
- **Away mode**: quitting writes `aquarium_autosave.json`; the next launch restores that tank and applies the time away (water
  tires, glass greens, hunger rises, aging and guppy broods are capped, a "Welcome back" message summarises it). Autosave also runs
  every ~5 minutes. Turn it off with `"away_mode": false` in `aquarium_config.json`; delete the autosave file to start fresh.
  Pressing R still rebuilds the tank from the config.
- **Goals** (G): 19 goals, saved in `aquarium_config.json` under `goals`.

## Round 5: health, nursery, temperature, seasons, plants, feeds, strains

New keys (F1 help, "HEALTH & HOME" column): **U** medicine, **I** quarantine the selected fish, **S** nursery net, **Y** heater
Off/Low/High, **Tab** strain book, hold **\** for timelapse, **4 / 5** bloodworm and algae wafer, **D** then TRIM to prune plants.

- **Health**: sick fish get a hint when they fall ill. Medicine (U) cures every sick fish but kills some shrimp and costs a little
  water quality (30 s cooldown). A quarantine net (I) stops a fish catching or spreading disease and speeds its recovery.
- **Fry survival**: small fry are eaten by hungry adults that swim next to them; plant cover makes that five times less likely. The
  nursery net (S) makes guppy fry born while it is placed appear inside it, fed and safe until they are half grown.
- **Temperature**: the water follows day, night and season and the heater (Y). Species have preferred ranges (default 22-28 C; discus
  28-31, betta 26-30, killifish 20-26). Fish outside their range accumulate stress and you get a warning.
- **Seasons**: a season lasts 20 tank days (or follows your calendar in real-time mode). Spring speeds up breeding, winter is cooler.
  Hold backslash to fast-forward the day.
- **Plants**: tall plants grow when the water is good; overgrown ones shade the tank and speed glass algae. Pruning (D, TRIM, click) cuts
  them back, and a big plant may sprout a daughter plant.
- **Feeds**: bloodworm (a frenzy) and algae wafers (sink fast, bottom feeders only). Too many leftovers make the water cloudy.
- **Shrimp colours**: cherry shrimp babies inherit red, blue or yellow from their parents, with a small chance of mutation.
- **Strain book** (Tab): every guppy colour/tail strain you breed, with best generation and count; saved in the config as `strains`.
- **Polish**: rain runs down the glass in storms, a moon glow crosses the surface at night. (No surface reflection: skipped.)

**Crayfish** are now hidden by default. Set `"show_crayfish": true` in `aquarium_config.json` (then press R or restart) to bring them back.
**Turtle** visits are hidden by default too: set `"show_turtle": true` in `aquarium_config.json` to allow the rare turtle event.

**Sickness is gentler**: every sick fish now recovers on its own (about 30-50 seconds, faster in clean water). Death is a small chance
(`SICK_DEATH_CHANCE`, roughly 1 in 30 sick fish in decent water; worse in foul water or when starving), and spreading is slower. The
numbers sit next to `infect()` in `main.py` if you want to tune them. Medicine (U) and quarantine (I) still speed things up.

**9** pours methylene blue (the water turns blue for a while; sick fish recover much faster; a few shrimp may not like it) and **0**
pours vitamins (calms and feeds the fish, heals a little and gives them resistance for about 90 seconds; one dose a minute). The F1 help
now wraps its columns to fit the screen.

**Predators** are off by default: `"predators": false` in `aquarium_config.json`. Set it to `true` (then press R or restart) to bring in the
channa and fire eel; the crayfish additionally needs `"show_crayfish": true`. With predators off there are no hunters and no channa visitor events.

## Round 6: the long-term tank (fw21)

New keys: **F2** social web, **F4** genetic show, **F6** rename the selected fish, **F7** star a favourite, **F8** life story / memorial,
**,** equipment shop, **.** aquascapes, **/** dashboard, **;** water test kit, **'** fertiliser, **`** soundscape on/off, **PageUp** photo
album, **F12** record a timelapse clip. They are all listed in the F1 help under MORE.

- **Personalities**: every fish is greedy, shy, bossy, an explorer or calm, and it changes how they swim (greedy fish race for food, shy ones
  stay low, bossy ones shove others and can fall out with another bossy fish, explorers roam, calm ones shrug off fright). It shows on the
  card under the selected fish.
- **Ageing**: fish past 80% of their life are slower (and already paler); "Grew old and slow" goes into their story.
- **Friends and rivals**: fish of one species that spend time together become friends and stay close; when a friend dies the other grieves
  (slow, stressed) for a while. Press F2 to see friends (green lines), rivals (red) and grieving fish.
- **Names, stars, stories**: F6 renames the selected fish (type, Enter), F7 stars it (a star over it, and a note when it is sick or very
  hungry). Each fish keeps a short biography (F8). Grown fish that die are added to the memorial (F8, then M), kept in the config.
- **More guppy genes**: besides colour and tail there is a *lace* pattern (recessive: needs both parents to carry it, so it can skip a
  generation), a *sheen* that blends between parents, and fin shape (round, delta, long). Non-guppy fish carry a colour line gene too, so
  tetras, cichlids, bettas and so on can be line-bred; their strains appear in the strain book (Tab).
- **Breeding requests**: a request appears on the bottom left (a colour swatch, what to breed, a reward and a deadline of ten days). Breed it
  (bred in this tank, generation 2+) and you get points. **Genetic show** (F4): your three best adults compete against three rivals; the
  top three places pay points; one show every three tank days.
- **Points and the shop**: goals (+3), requests, shows and cycling a tank earn points; `,` spends them on a canister filter, glass magnet,
  thermostat, CO2 diffuser, UV steriliser or a pair of otocinclus.
- **Water chemistry**: the test kit (`;`) shows ammonia, nitrite, nitrate and pH, and the two bacteria colonies. A normal tank starts
  established. Set `"new_tank": true` in `aquarium_config.json` to start an uncycled tank: ammonia spikes, nitrite follows, and you keep fish
  alive with water changes (W) until the colonies are established (a lightly stocked tank takes about six tank days; a full one much
  longer and rougher). Rinsing the filter (F) sets the bacteria back a little; high ammonia/nitrite poison the water.
- **Algae kinds**: green film on the glass (C wipes it), hair algae along the bottom (shrimp, snails and otos eat it, dark tanks starve it,
  nitrate and fertiliser feed it) and a brown diatom film in new tanks that fades as the tank matures.
- **Fertiliser** (`'`): plants grow faster for two minutes (and algae thrive too unless you own a CO2 diffuser). New plants to build with
  (D): cabomba and hygrophila.
- **Diseases**: white spot (ich: fixed by warm water, heater High), fin rot (red ragged tails: clean water, a water change) and swim bladder
  trouble (the fish sinks: a short fast helps). Medicine, methylene blue and quarantine still work for all three.
- **Aquascapes** (`.`): four built-in layouts (Jungle, Zen rocks, Meadow, Open water) and your own (N saves the current layout to
  `aquarium_scapes.json`). Applying one replaces the plants and rocks; the fish stay.
- **Guests**: set `"show_visitors": true` in `aquarium_config.json` and a tree frog may cling to the glass or a kingfisher dive in (both are
  rare events, off by default like the turtle).
- **Album** (PageUp) lists your photos with the day, season, fish count and water quality (`screenshots/album.json`). **F12** records a
  timelapse clip as a GIF into `screenshots/` (one frame every third of a second, up to about two minutes of tank time).
- **Soundscape** (`` ` ``): quiet rain in storms, crickets at night and a faint room hum, following the master and effects volume and the mute key.
- **Dashboard** (`/`): population, water quality, births, deaths, nitrate and temperature over the last ~40 minutes of play, plus a summary
  after every seven tank days.

Not verified on a real display: all of this was run headless (screenshots checked), so check the frame rate with F3.

### Plant drawings
Every stem plant now has its own drawing: Rotala (needle whorls, pink tips), Ludwigia (broad oval leaves, red undersides), Cabomba (feathery forked fans), Hygrophila (big alternating lance leaves). Vallisneria sometimes carries a coiled flower stalk, hairgrass has seed heads, swords have side veins and java fern has spore dots.

### Planting mode (Home)
Press **Home** to put the fish, shrimp and snails away and design the tank. A tool bar appears at the top: pick a plant, rock or driftwood and click the tank to place it. **Move** picks any existing piece (including the original ones) and drags it sideways; arrow keys nudge it, right-click or Del removes it, Ctrl+Z undoes, the mouse wheel sets the depth of new rocks. **Clear all** (click twice) removes every plant, rock and piece of driftwood so you can start from scratch. Esc or Home returns to the tank. The layout is stored in the save file (and in aquascapes you save with N).

### Planting mode, round 2
- **Stack and lift:** with a rock tool, click an existing rock to stack on it. Select any piece and press Up/Down to raise or lower it (plants can stand on rocks).
- **Size, depth, flip:** PgUp/PgDn resize, `[` `]` change a rock's depth (it is redrawn), F flips a rock.
- **Fill and mirror:** *Fill* lets you drag a stroke of plants or rocks; *Mirror* flips the whole layout left to right.
- **New pieces:** caves, clay pots, a shipwreck and a stone bridge. Cichlids spawn in caves and pots; shy fish shelter in thick stands of tall plants.
- **Judge:** scores balance, layers, colour and shelter and pays points only when you beat your best. Goal: Designer (90+).
- **Before / after:** leaving planting mode opens a slider comparing the tank before and after (Enter saves it to the album, Insert reopens it).
- **Plant care:** plants yellow in the dark, without nitrate or under hair algae; Pleco, Kenyi, Auratus, Socolofi and Bala sharks nibble them (brown patches). Anubias, crypts and swords flower; carpet and clover send runners; stems grow slowly each day and can be pruned (Prune tool).
- **Tank tour:** PgDn films one whole day as a camera pan and saves a GIF (Esc stops).

## Round 7: depth, care, economy, hub

- **Welcome screen** is drawn over the live tank (no static image).
- **Plant depth** (`[` / `]` in planting mode): front, middle, back; back plants are hazier and drawn first.
- **Health**: recovered fish stay carriers for a while; a Hospital tank in the shop doubles recovery in quarantine (I).
- **Sell** bred fish (7), **chores and challenges** (8), occasional predator raids when predators are enabled.
- **Moss** creeps over rocks and wood; photo styles (Shift+P: plain, polaroid, blur); album best-of (B).
- **Settings and save slots** (Ctrl+S): toggles, 5 slots, restore before last load, double-Z progress reset.
- **Quality governor**: lowers plant detail automatically when frames are slow (`"auto_quality": false` turns it off).
- **Hub (Del)**: Gear (cash purchases), Line (breeding standard), Upkeep (filter media, air stone, heater drift, sand mulm,
  KH/GH), History (graphs), Life (snails, shrimp, weather, fish of the week), Guide (tour toggle, controller notes).
- **Water hardness**: KH and GH in the test kit; soft-water fish (tetras, rummynose, otos, corydoras) and hard-water fish
  (guppies, killifish, cichlids) get stressed outside their range. Water changes pull toward the tap (GH 8, KH 6).
- **Weather events** follow the season: spawning (spring), heat wave (summer), leaf fall (autumn), cold snap (winter).
- **Colonies**: snails boom on spare food, shrimp breed in moss and carpets; both crash in dirty water.
- **Debris** drifts down and settles as mulm; siphon it from the Upkeep tab.
- **Hand**: hold the mouse button to drip food, Ctrl+drag to lift a fish, hover a fish to see its personality.
- **Night life**: moth at the surface, sleeping fish show Zs, window light shafts move with the day, an occasional cat visits.
- **Tour**: a short first-run guide appears on a fresh tank only.
- **Controller**: stick moves the pointer, A clicks, B back, X help, Y hub, LB shop, RB test kit, right trigger taps the glass.

### Live weather (real-time clock)

With the real-time clock on (O), the tank copies the weather outside: rain and snow fall over the water, cloud dims the light, a real thunderstorm triggers the storm event, and the outdoor temperature nudges the tank temperature a little. The place comes from a single IP lookup (ipwho.is) and the weather from Open-Meteo, refreshed every 15 minutes on a background thread; with no network nothing changes. Hub > Life shows the current reading, and W there switches it off. Shift+D (or T in hub > Upkeep) trims every overgrown plant.

### Cichlid set rework (Lake Malawi show tank)

`cichlid_set` is now a peacock-and-hap showpiece tank: OB peacock, German red peacock, Sunshine peacock, red fin borleyi, electric blue hap (all new species, with colourful males and plain silvery females, stocked about 65% male) plus a Synodontis catfish and the bristlenose pleco as bottom cleaners. Switch to it with `"active_set": "cichlid_set"` in aquarium_config.json. The old mbuna species are still in the game and usable in custom sets.

### Code layout and nursery start

main.py is now a small loader: the game lives in ordered files under parts/ that run in one shared namespace (see the list at the top of main.py). Edit the part files, not main.py. `cichlid_set` starts as tiny fry that grow up in the tank (`FRY_START_SETS` in parts/07_fish_sets.py).

### Aquascape per fish set

aquarium_config.json has a `scapes` section: one entry per set name, every key optional. A set without an entry keeps the usual random layout (so existing saves and the tetra tank are unchanged). Keys: `layout` ("dual_anchor" = two tall rock pillars on the far flanks, a low arch in the middle, open front), `rock_style` (rock / smooth / river / lace), `pillar_height`, `arch`, `plants` (species, density, ground_cover, mounted), `substrate` (colour, buffer = aragonite holds KH and pH up), `water` (starting ph/kh/gh, tap kh/gh, the good KH/GH bands), `background` (darken, tint, ridge, doodads) and `light` (kelvin, shafts). `cichlid_set` ships with the Malawi design: lace-rock pillars, a stone arch, pale aragonite sand, pH about 8.2, a dark-blue back wall and 9000K light. The layout is built when a tank is created, so start a fresh tank after changing it; saved tanks keep the layout they were saved with only if the same set is active.

### Turning and facing (semi-3D)

Fish no longer flip instantly. When one reverses, it swings round through an end-on view: the side sprite narrows and fades into a front view (face, eyes, spread pectorals) or a back view (tail fan seen edge-on), then widens on the other side, in about a quarter of a second. Slow or idle fish also sometimes turn to face the glass for a few seconds, more often when the cursor is near, and shy, sleepy or frightened ones turn their back instead. The code is the "turning and facing" block at the top of parts/20_sprites_doodads.py (`TURN_RATE`, `GAZE_RATE`, `FRONT_W`). Predators, the eel and visitors still flip.

### Wallpaper mode is safe (F10)

F10 turns the tank into an unattended wallpaper, so while it is on nothing can hurt the fish: no power cuts, storms, channa visitors, predator raids, cold snaps, heat waves or leaf fall; no new illness (any sickness is cured), no starvation, no old-age or fry-eating deaths; the water stays clean, the glass stays clear and the stress, fear and hunger levels are held down. Only friendly events (current surge, daphnia bloom, new arrivals, moon spawning, rare visitors) still happen. The tank behaves normally again the moment you leave wallpaper mode (any key). The code is `unattended()` and `unattended_tick()` (parts/13_driver.py) plus the guards that call `unattended()`.

### Start menu

The game now opens on a menu instead of silently loading the last tank. Left/Right (or the < > buttons) cycle through the fish sets in aquarium_config.json, and the tank behind the menu becomes a fresh preview of that set (its sand, back wall and water values included). CONTINUE LAST TANK (Enter or C) loads the autosave, switching to the set it was saved with; NEW GAME (N) starts a fresh tank of the chosen set. The chosen set is remembered as `active_set`. The R key still restarts into this menu.

### Cichlid cross-breeding and trait passing

Different cichlid species can now pair and spawn (every cichlid except the angelfish). A fish prefers a mate of its own kind and only crosses when none is free, which is the usual case in `cichlid_set`, where each species starts as a few fry. Each fry of a mixed clutch is one parent's species and wears a blend of both parents' colours (body and fins, 25-75%), with the colour-line gene passed down as before. Hybrids are fertile: the blend is handed on, at full strength if both parents carry it and at 60% if only one does, so it fades back out over a few generations. The fish card shows "hybrid: 46% Kenyi Cichlid", and the blend is saved with the tank. Set `"cichlid_crossbreed": false` in aquarium_config.json to switch it off. The markings (bars, blotches) still come from the fry's own species. Code: `cross_traits`, `cichlid_cols` (parts/05_fish_cichlids.py), `find_mate` (15), `Eggs.hatch` (17).

### Cichlid improvements (breeding, rank, looks)

- **Stocking:** every species that starts with two or more fish gets at least one male and one female. A set can have its own fish budget: `"max_fish"` inside its `scapes` entry (`cichlid_set` uses 70).
- **Rank and territory:** every couple of seconds `rank_tick()` (parts/05) ranks the adult males. The strongest quarter become dominant, each claiming a cave, nest or rock as a territory, and drive lesser males out of it. Shoving matches shift a male's rank (`contest`); the loser slinks away with drained colour and stress. A dominant male shows richer colour, and the fish card says "boss".
- **Stocking and aggression:** a sparse tank focuses the aggression on the few fish present, a medium stocking is calmest, and an overcrowded tank gets nastier and stresses the cichlids (`CROWD`).
- **Courtship:** a courting male raises his fins, blazes his colours and quivers in front of the female before leading her to the site.
- **Mouthbrooding:** every cichlid except the angelfish is a mouthbrooder. The female takes the eggs into her mouth (her cheeks visibly bulge), moves slowly, cannot eat and stays out of fights for about 45 seconds, then releases the fry. If she dies first, the brood is lost.
- **Hybrids:** a hybrid now also wears the other parent's markings, faintly. Two hybrids of the same cross breed true, and after three generations the line becomes a named, stable strain (a notification, a "(stable strain)" tag on the card and an entry in the saved `hybrids` record). A hybrid bred with a pure fish thins out.
- **Looks:** fry are plain silvery-brown and colour up as they grow; stressed or beaten fish lose colour; the head-on and tail-on views of each species carry its markings (bars, stripe, blotches or a head glow).

### Cichlid movement and behaviour: kicks, fin folding, digging, caves

- **Burst-and-glide:** cichlids no longer cruise at a steady speed (`burst_glide` in parts/05). A quick kick of the tail, then a coast that loses speed. Kicks are lazy on patrol and hard when fleeing, chasing or lunging at a rival; hovering, sifting, digging, resting and brooding fish do not kick. The angelfish still glide smoothly.
- **Fin folding:** `fold` (0..1) follows how hard the fish is swimming. While kicking or fleeing the dorsal, anal, pelvic and pectoral fins fold flat against the body and the tail fans wider; in the glide and at rest they open again, and a display flare overrides it. It is drawn in three cached steps (`self_fold`), so it costs no frame rate.
- **Digging:** dominant males, and males with a mate, dig a spawning pit in the sand at their territory: down for a mouthful, a swim to the rim, a puff of sand where it is spat out. The pit gets deeper and the mound higher with each scoop (`PITS`, `draw_pits`), and fills in slowly if it is not kept up. He leads the female to his pit to spawn.
- **Caves:** cichlids shelter in caves rather than behind any rock: at night, when frightened, and brooding females for the whole brood. A dominant male's cave is his own; others share a cave up to three fish and avoid a boss's. The cichlid scape now builds two caves between the pillars and the arch (`"caves": 2` in its `scapes` entry).

### More cichlid behaviours

- **Fry recall:** a brooding mother who hatched fry keeps watch for a while (`fry_t`); if she is scared, she sucks the fry back into her mouth (cheeks bulge again) and spits them out once it is calm.
- **Lateral displays:** rivals can square up side by side with fins flared (`LATERAL`, `resolve_lateral`) and the bigger or higher-ranked one wins without a fight; mock fights show dark fighting bars on the flanks (`fighting`).
- **Egg spots:** males of some species carry egg-spot dummies on the anal fin; more spots attract females and give a bigger clutch, and the trait is inherited (`egg_spots`).
- **Sneaker males:** a small share of males are sneakers: pale and female-like, they drift near a spawning pair and can fertilise some of the eggs; the trait is inherited (`sneaker`, `sneaker_gene`).
- **Feeding styles:** grazers peck rocks, sifters sift sand, pelagic species snap mid-water food, and some carry food away (`feed_w`, states `SNAP`, `CARRY`).
- **Female choice:** females prefer dominant, richly coloured, egg-spotted males and reject others; males also reject poor mates (`find_mate`, `attract`).
- **Sleeping postures:** at night fish rest in species-typical poses (head-down, tilted, wedged in a cave).
- **Pebble moving:** digging males rearrange pebbles around their pit.
- **Personalities:** each cichlid is explorer, shy, greedy, bossy or calm, which changes how far it roams, how fast it hides, how it feeds and how it fights.
