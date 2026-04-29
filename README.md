# 🐠 Advanced Aquarium Simulator

A high-fidelity, interactive aquarium ecosystem built with Python and **Pygame-CE**. This project features complex fish AI, dynamic lighting systems, and a procedurally generated underwater environment.

## 🌟 Key Features

### 🐟 Sophisticated Fish Ecosystem
* **Diverse Species**: Includes Bala Sharks, Clown Loaches, Discus, Neon Tetras, Boesemani Rainbowfish, Pearl Gouramis, and various Cichlids.
* **Specialized AI**:
    * **Clown Loach**: Bottom-dwelling scavenger logic with "zoomies" and social huddling.
    * **Bala Shark**: High-speed torpedo movement with schooling alignment.
    * **Hatchetfish**: Strict surface-tethering behavior for top-water realism.
* **Hunger & Health System**: Fish gradually get hungry and will actively seek out food pellets or algae.
* **Emergency Bloom**: Automatic algae spawning during critical starvation events (>10 starving fish) to prevent ecosystem collapse.

### 💡 Dynamic Lighting System (Toggle: 'N')
Switch between 11 discreet lighting profiles with a smooth fading notification in the top right:
* **Deep Amazon**: Tannin-heavy tea water for a natural look.
* **Moonlight**: Low-light blue tint for a midnight vibe.
* **Planted Grow**: Pink-spectrum lighting to make plant reds pop.
* **RGB Strobe**: Dynamic, cycling colors for a high-energy atmosphere.

### 🎵 Audio Management (Toggle: 'M')
* **Circular Playlist**: Automatically cycles through your `bgmusic.mp3` collection.
* **Normalized Audio**: Volume is hard-coded to a discreet 40% (0.4) to provide a relaxing background ambiance without overpowering sound effects.

### 🌿 High-End Aquascaping
* **Tiger Lotus (Eye Candy)**: Procedurally generated red/purple plants with heart-shaped leaves, unique "tiger" mottling, and a rhythmic color-pulse animation.
* **Hardscape**: Randomized cave structures and depth-sorted pebbles.
* **Caustics**: Dynamic light beams that shift across the tank for a "shimmer" effect.

## ⚙️ Installation Procedure

This project is optimized for **Pygame-CE** (Community Edition). Follow these steps to set up your environment:

1.  **Ensure Python is Installed**: This simulator requires Python 3.8 or higher.
2.  **Remove Standard Pygame**: To avoid namespace conflicts, it is recommended to uninstall the standard version:
    ```bash
    pip uninstall pygame
    ```
3.  **Install Pygame-CE**:
    ```bash
    pip install pygame-ce
    ```
4.  **Prepare Assets**: Ensure the `/doodads` folder exists in the root directory and contains your assets (pebbles, rocks, and music files).

## 🚀 Running the Simulator

1.  Open your terminal or command prompt.
2.  Navigate to the project directory.
3.  Execute the script:
    ```bash
    python main.py
    ```

## 🎮 Controls

| Key | Action |
| :--- | :--- |
| **Mouse Click** | Drop a food pellet at the cursor position |
| **N** | Toggle Lighting Mode (Fades in top-right) |
| **M** | Toggle Background Music (Cycles playlist) |
| **B** | Toggle Background Wall Art |
| **R** | Reset the Aquarium / Re-spawn everything |

## 🛠️ Technical Details

* **Resolution**: Maximizes monitor width with a fixed 800px height.
* **Depth Sorting**: All entities (fish, rocks, pebbles) are sorted by their `Z` value to create a true 3D parallax effect.
* **Optimized Rendering**: Uses per-pixel alpha surfaces for soft lighting effects and transparent fin rendering.
* **Sand Logic**: Mathematically tethered sand dunes that scale perfectly with screen width.

## 📂 Asset Structure
```text
/
├── main.py
└── doodads/
    ├── pebble.png
    ├── rock.png
    ├── splash.png
    ├── wallart1.png ... wallart6.png
    └── bgmusic.mp3  ... bgmusic4.mp3