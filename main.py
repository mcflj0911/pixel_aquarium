"""Pixel Aquarium (freshwater).

The game is one program split over ordered files in parts/. They are run, in order, inside this file's own namespace, so
every part sees the names defined by the parts before it, exactly as if they were one long script. Run this file
(python main.py); the Pixel_Tanks launcher and the test harness also run it as a single script.

Order matters: a part may use anything defined in an earlier part at start-up, and anything from any part once the
main loop (the last part) is running.
#   parts/01_core.py               pygame setup, constants, drawing helpers
#   parts/02_scenery.py            pebbles, rocks, driftwood, caves, shrimp, daphnia
#   parts/03_plants.py             plant physics and the Plant class, food pellets, bubbles
#   parts/04_fish_base.py          the Fish base class and the shared freshwater renderer
#   parts/05_fish_cichlids.py      cichlids, Malawi peacocks and haps, plecos and catfish
#   parts/06_fish_community.py     schools, loaches, barbs, tetras, guppies, betta, discus, killifish
#   parts/07_fish_sets.py          carrying capacity and the fish sets in aquarium_config.json
#   parts/08_ecosystem.py          sound effects, particles, emotes, the Ecosystem clock
#   parts/09_care.py               care loop: weather, filter, goals, sickness, strain book, slow care
#   parts/10_social_genes.py       panels, personalities, friendships, genes, breeding requests, genetic show
#   parts/11_water_shop.py         water chemistry, algae, shop, aquascapes, album, soundscapes, chores
#   parts/12_settings_hub.py       settings and save slots, the Del hub (gear, line, upkeep, history, life, guide)
#   parts/13_driver.py             dashboard, per-frame driver, input events
#   parts/14_draw_frame.py         drawing the frame
#   parts/15_community_ai.py       hiding places, cleaning stations, the social life of the fish
#   parts/16_predators.py          scraps, bubble nests, channa, fire eel, crayfish
#   parts/17_husbandry.py          water quality, feeding, breeding, visitors, crawlers, building, photos
#   parts/18_saves_planting.py     save and load, planting mode
#   parts/19_scape_tools.py        plant health, the aquascape judge, before/after, camera tour
#   parts/20_sprites_doodads.py    sprite cache, detritus, 2.5D layer, doodads
#   parts/21_main_loop.py          start-up and the main loop
"""
import os as _os

_HERE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "parts")
_PARTS = (
    "01_core.py",
    "02_scenery.py",
    "03_plants.py",
    "04_fish_base.py",
    "05_fish_cichlids.py",
    "06_fish_community.py",
    "07_fish_sets.py",
    "08_ecosystem.py",
    "09_care.py",
    "10_social_genes.py",
    "11_water_shop.py",
    "12_settings_hub.py",
    "13_driver.py",
    "14_draw_frame.py",
    "15_community_ai.py",
    "16_predators.py",
    "17_husbandry.py",
    "18_saves_planting.py",
    "19_scape_tools.py",
    "20_sprites_doodads.py",
    "21_main_loop.py",
)

for _name in _PARTS:
    _path = _os.path.join(_HERE, _name)
    with open(_path, encoding="utf-8") as _fh:
        _code = compile(_fh.read(), _path, "exec")
    exec(_code, globals())
