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

## 📂 Asset Requirements
The simulator looks for assets in the `/doodads` folder:
* `pebble.png` and `rock.png`
* `splash.png`
* Music files (`bgmusic.mp3` to `bgmusic4.mp3`)
* Wall art files (`wallart.png` to `wallart9.png`)