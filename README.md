# 🐠 Advanced Aquarium Simulator

![image](https://github.com/mcflj0911/pixel_aquarium/blob/main/doodads/splash.png)

A high-fidelity, interactive aquarium ecosystem built with Python and **Pygame-CE**. This project features complex fish AI, dynamic lighting systems, and a procedurally generated underwater environment.

## 🌟 Key Features

### 🐟 Sophisticated Fish Ecosystem
* **Diverse Species**: Includes Bala Sharks, Plecos, Snails, Neon Tetras, Cichlids (Yellow Prince, Ice Blue, Peacock), Pearl Gouramis, Boesemani Rainbowfish, Clown Loaches, and Tiger Barbs.
* **Specialized AI**:
    * **Bala Shark**: High-speed torpedo movement with schooling alignment and active horizontal bursts.
    * **Pleco**: Bottom-dwelling scavengers with an aggressive search mode for algae and a "suction lock" feeding logic.
    * **Snail**: Slow-moving cleaners that leave subtle slime trails and track nearby algae.
    * **Clown Loach**: Scavenging "snake" movement with "zoomies" and social huddling.
    * **Cichlids**: Territorial behavior including patrolling, defending territory, and sifting sand.
* **Hunger & Health System**: Fish metabolic rates are influenced by speed; they must seek food pellets or algae to maintain health. High starvation levels can trigger a massive algae bloom.
* **Dynamic Hardscape**: Procedurally generated cave structures and scattered rocks that respect depth (Z-axis) for realistic overlapping.

### 🌿 Living Flora
* **Interactive Plants**: Species include Vallisneria, Anubias, Rotala, Ludwigia, and Tiger Lotus.
* **Biological Activity**: Plants realistically sway and occasionally release oxygen bubbles from their base.
* **Procedural Growth**: Each plant has unique segment counts, sway speeds, and color tints.

### 💡 Dynamic Lighting System (Toggle: 'N')
Switch between 11 discreet lighting profiles with a smooth fading notification:
* **LED RGB White**: Neutral, clear lighting.
* **Warm / Warm White**: Simulates home and amber-tinted lighting.
* **Deep Amazon**: Tannin-heavy tea water for a natural blackwater look.
* **Moonlight**: Low-light blue tint with increased opacity to simulate darkness.
* **Planted Grow**: Pink-spectrum lighting to promote plant aesthetics.
* **RGB Strobe**: Dynamic, cycling colors that shift over time.
* **Additional Modes**: Includes Cool, Actinic, Sunset Gold, and Mild Green.

## 🎮 Controls

| Key | Action |
| :--- | :--- |
| **Mouse Click** | Drop a food pellet at the cursor position |
| **N** | Toggle Lighting Mode (Fades in top-right) |
| **M** | Toggle Background Music (Cycles playlist) |
| **B** | Toggle Background Wall Art |
| **V** | Toggle Audio Mute |
| **R** | Reset the Aquarium / Re-spawn everything |

## 🛠️ Technical Details

* **Resolution**: Dynamic width based on monitor size (`info.current_w - 300`) and a fixed height of 600px.
* **Depth Sorting**: Entities utilize a `z` value (0.2 to 1.2) for scaling, shading, and draw order.
* **Optimized Rendering**: Uses `pygame.SRCALPHA` for transparency in lighting, slime trails, and fin rendering.
* **Sand Logic**: Tethered sand dunes calculated using `math.sin` and `math.cos`.

## 🛠️ Developer Guide: Adding New Fish
Expanding the ecosystem is designed to be modular. You can add a new species by extending existing classes and registering the fish in the spawning logic.

1. Choose a Base Class
Fish: The standard base class. Use this for mid-water swimmers (like Tetras or Gouramis).

Cichlid: A specialized subclass of Fish. Use this if your new fish should exhibit territorial behavior, patrol specific areas, or sift sand.

2. Create the New Fish Class
Inherit from your chosen base and override the behavior and draw methods.

```python
class MyNewFish(Fish):  # Or extends Cichlid
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.5
        # Custom attributes (e.g., specific colors or school ID)

    def behavior(self, fishes):
        # Define AI logic here (e.g., schooling, avoiding predators)
        # Use self.apply_force(pygame.Vector2) to move
        pass

    def draw(self, surface):
        self.draw_shadow(surface, 20) # Draw a shadow on the sand
        # Use pygame.draw or surface.blit to render the fish
        # Use self.get_depth_color(color) to adjust for Z-depth shading
```
3. Update the Spawn Logic
To make your fish appear in the aquarium, add it to the spawn_random_fish function (or the initialization loop) in main.py.

```python
#ADD NEW FISH IN THIS LIST WITH CHANCE TO SPAWN RATE
spawn_table = [
        (0.15, TigerBarb, surface_zone),
        (0.25, PearlGourami, surface_zone + 40),

        (0.35, Pleco, floor_y),
        (0.45, NeonTetra, mid_zone),
        (0.55, BoesemaniRainbow, mid_zone - 50),
        (0.60, BalaShark, mid_zone),

        (0.70, ClownLoach, floor_y - 20),
        (0.80, PeacockCichlid, bottom_y),
        (0.88, YellowPrinceCichlid, bottom_y),
        (0.96, IceBlueCichlid, bottom_y),
        (1.00, Cichlid, bottom_y)
    ]
```
## 📂 Asset Requirements
The simulator looks for assets in the `/doodads` folder:
* `pebble.png` and `rock.png`
* `splash.png`
* Music files (`bgmusic.mp3` to `bgmusic4.mp3`)
* Wall art files (`wallart.png` to `wallart9.png`)

## 🚀 Installation
Follow these steps to get the simulator running on your local machine:

Clone the Repository:

```Bash
git clone https://github.com/mcflj0911/pixel_aquarium.git
cd pixel_aquarium
```

Install Dependencies:
The project requires Python 3.x and the pygame-ce (Community Edition) library:
```Bash
python -m pip install pygame-ce
```

Run the Simulator:

```Bash
python main.py
```