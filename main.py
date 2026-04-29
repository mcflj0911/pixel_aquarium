import pygame
import random
import math
import sys
import os


# --- Asset Path Setup ---
# This ensures we look inside the 'doodads' folder
ASSET_PATH = "doodads"


# --- Configuration ---
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 600
SAND_HEIGHT = 60
WATER_TOP = 80
ALGAE_SPAWN_RATE = 65
MAX_HUNGER = 100

# Colors
CLR_WATER_TOP = (40, 100, 180)
CLR_WATER_BOTTOM = (10, 30, 80)
CLR_SAND = (210, 185, 130)
CLR_ALGAE = (60, 180, 60)
CLR_FOOD = (150, 100, 50)

STATE_WELCOME = 0
STATE_AQUARIUM = 1
current_state = STATE_WELCOME


# --- Classes ---


def get_path(filename):
    return os.path.join(ASSET_PATH, filename)

# --- NEW: Load all assets from 'doodads' ---
pygame.mixer.init()


class Plant:
    def __init__(self, x, species_type):
        self.pos_x = x
        self.species = species_type
        # Specialized stats per species
        if species_type == "Vallisneria":
            self.segments = random.randint(15, 25)  # Tall grass
            self.sway_speed = random.uniform(0.01, 0.02)  # Slower, heavy sway
        elif species_type == "Anubias":
            self.segments = random.randint(4, 7)  # Short and bushy
            self.sway_speed = random.uniform(0.005, 0.01)  # Stiff
        else:
            self.segments = random.randint(8, 14)
            self.sway_speed = random.uniform(0.02, 0.04)

        self.sway_offset = random.uniform(0, math.pi * 2)
        self.tint = random.randint(-20, 20)

    def draw(self, surface, frame):
        base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2

        for i in range(self.segments):
            taper = 1.0 - (i / self.segments)
            sway_intensity = (i ** 1.5) * 0.8
            sway = math.sin(frame * self.sway_speed + self.sway_offset + (i * 0.2)) * sway_intensity
            px, py = self.pos_x + sway, base_y - (i * 10 * (0.8 + taper * 0.2))

            if self.species == "Rotala":
                # 1. Color Logic: Green at bottom, Pink/Red at the top
                # Calculate pinkness based on the segment index (i)
                pink_factor = i / self.segments
                r = int(60 * (1 - pink_factor) + (180 + self.tint) * pink_factor)
                g = int((140 + self.tint) * (1 - pink_factor) + 80 * pink_factor)
                b = int(60 * (1 - pink_factor) + 120 * pink_factor)

                leaf_col = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                stem_col = (max(0, min(255, r - 20)), max(0, min(255, g - 20)), max(0, min(255, b - 20)))

                # 2. Draw Stem Segment
                prev_py = base_y - ((i - 1) * 10 * (0.8 + (1.0 - ((i - 1) / self.segments)) * 0.2)) if i > 0 else base_y
                pygame.draw.line(surface, stem_col, (px, py), (px, prev_py), 1)

                # 3. Whorled Leaf Pattern
                # Rotala often has 3-4 leaves radiating from the same point
                # We'll use 6 angles for a denser, more high-end "aquascaped" look
                num_leaves = 6
                for j in range(num_leaves):
                    angle = (j * (math.pi * 2 / num_leaves)) + (i * 0.5)  # Spiral offset per segment
                    # Leaves are thin and needle-like
                    length = 14 * taper + 4
                    lx = px + math.cos(angle) * length
                    ly = py + math.sin(angle) * (length * 0.3)  # Flattened perspective

                    # Draw leaf with a slight fade
                    pygame.draw.line(surface, leaf_col, (px, py), (lx, ly), 1)

                    # Add a tiny "leaf tip" highlight
                    if i > self.segments * 0.6:
                        pygame.draw.circle(surface, (min(255, r + 30), g, b), (int(lx), int(ly)), 1)

                # 4. Central Node
                pygame.draw.circle(surface, stem_col, (int(px), int(py)), 2)

            elif self.species == "Ludwigia":
                # 1. Color Logic: Top is Olive Green, Bottom is Deep Red
                # The red intensifies as the plant reaches the "light" (higher i)
                red_val = max(0, min(255, 120 + (i * 10) + self.tint))
                green_val = max(0, min(255, 80 + self.tint))
                leaf_under = (red_val, 30, 40)  # Deep Magenta/Red
                leaf_top = (60, green_val, 30)  # Olive Green
                stem_col = (max(0, red_val - 40), 60, 30)

                # 2. Draw Central Stem
                # Connects this segment to the one below it
                prev_py = base_y - ((i - 1) * 10 * (0.8 + (1.0 - ((i - 1) / self.segments)) * 0.2)) if i > 0 else base_y
                pygame.draw.line(surface, stem_col, (px, py), (px, prev_py), 2)

                # 3. Draw Opposite Leaves (Paired)
                # Ludwigia leaves grow in pairs on opposite sides of the stem
                lw, lh = 16 * taper + 6, 8 * taper + 4
                for side in [-1, 1]:
                    # Leaf Base (The reddish underside peeking out)
                    lx = px + (2 * side)  # Slight offset from stem center
                    # Pointed Leaf Shape (Two overlapping ellipses)
                    # Main Body
                    pygame.draw.ellipse(surface, leaf_under, (lx if side == 1 else lx - lw, py - lh // 2, lw, lh))
                    # Top Surface (Smaller, shifted ellipse to show the red edge/underside)
                    pygame.draw.ellipse(surface, leaf_top,
                                        (lx + 1 if side == 1 else lx - lw + 1,
                                         py - lh // 2 + 1,
                                         lw - 3, lh - 4))

                    # 4. Central Vein
                    vein_col = (red_val, 80, 80)
                    pygame.draw.line(surface, vein_col,
                                     (lx, py),
                                     (lx + (lw - 2) * side, py), 1)

                # 5. Terminal Bud (The very top tiny leaves)
                if i == self.segments - 1:
                    pygame.draw.circle(surface, leaf_top, (int(px), int(py - 5)), int(4 * taper + 2))


            elif self.species == "Vallisneria":
                # 1. Ribbon Colors: Slightly translucent forest green
                v_green = max(0, min(255, 90 + self.tint + (i * 2)))
                leaf_col = (30, v_green, 40)
                edge_col = (40, v_green + 30, 50)

                # 2. Surface Physics
                # If the segment height reaches the water surface, it starts to trail
                current_y = base_y - (i * 12)
                width = 10 * taper + 3
                final_px, final_py = px, py

                if current_y < WATER_TOP:
                    # Trailing logic: The leaf "bends" at the surface
                    over_surface = WATER_TOP - current_y
                    # Push the leaf horizontally based on the frame and sway
                    trail_offset = over_surface * (1.2 + math.sin(frame * 0.02) * 0.2)
                    final_px = px + trail_offset
                    final_py = WATER_TOP  # Keep it pinned to the surface

                # 3. Draw the Ribbon Segment
                # We draw a thick line for the main blade
                pygame.draw.line(surface, leaf_col, (px, py), (final_px, final_py), int(width))

                # 4. Vein/Cellular Detail
                # Vallisneria has visible longitudinal veins
                if width > 4:
                    pygame.draw.line(surface, edge_col,
                                     (px - width // 3, py),
                                     (final_px - width // 3, final_py), 1)

                # 5. Translucency highlight
                # Makes it look like light is passing through the thin leaf
                highlight_surf = pygame.Surface((int(width), 12), pygame.SRCALPHA)
                pygame.draw.rect(highlight_surf, (200, 255, 200, 40), (0, 0, int(width // 2), 12))
                surface.blit(highlight_surf, (final_px - width // 2, final_py))

            elif self.species == "Anubias":

                # 1. Broad, dark, waxy leaf colors
                base_green = max(0, min(255, 40 + self.tint))
                mid_green = max(0, min(255, 60 + self.tint))
                highlight = max(0, min(255, 100 + self.tint))

                # 2. Draw the Petiole (Leaf Stem)
                # Anubias has long stems connecting the leaf to the base
                stem_col = (max(0, base_green - 10), base_green, 10)
                pygame.draw.line(surface, stem_col, (self.pos_x, base_y), (px, py), 2)

                # 3. Draw Heart-Shaped Leaf
                # We use two overlapping ellipses at an angle to create the 'lobes' of the heart
                lw, lh = 22 * taper + 12, 14 * taper + 8
                # Draw only on upper segments to give it that "bushy head" look

                if i >= 1:
                    # Create a temporary surface for the leaf to handle rotation easily
                    leaf_surf = pygame.Surface((lw * 2, lh * 2), pygame.SRCALPHA)
                    # Leaf Shadow/Base
                    pygame.draw.ellipse(leaf_surf, (20, base_green, 20), (lw // 2, lh // 2, lw, lh))
                    # Main Leaf Body (Higher Green)
                    pygame.draw.ellipse(leaf_surf, (30, mid_green, 30), (lw // 2 + 2, lh // 2 + 1, lw - 4, lh - 2))
                    # Heart Lobe Detail (The 'indent' at the stem)
                    pygame.draw.circle(leaf_surf, (35, highlight, 35), (int(lw // 2 + 4), int(lh)), 3)

                    # Central Vein
                    pygame.draw.line(leaf_surf, (10, 30, 10), (lw // 2 + 2, lh + lh // 2), (lw + lw // 2, lh + lh // 2),
                                     1)
                    # Rotate leaf slightly based on sway and index for a natural look
                    rot_leaf = pygame.transform.rotate(leaf_surf, sway * 2 + (i * 10))
                    surface.blit(rot_leaf, (px - lw, py - lh))

                # 4. Draw the Rhizome (The thick base)
                if i == 0:
                    rhizome_rect = (self.pos_x - 15, base_y - 5, 30, 12)
                    pygame.draw.ellipse(surface, (40, 30, 20), rhizome_rect)  # Dark woody brown
                    pygame.draw.ellipse(surface, (60, 50, 30), (self.pos_x - 12, base_y - 3, 24, 6))

class FoodPellet:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 1.2)

    def update(self):
        dune_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5 + math.cos(self.pos.x * 0.05) * 2
        if self.pos.y < dune_y: self.pos += self.vel

    def draw(self, surface):
        pygame.draw.rect(surface, CLR_FOOD, (int(self.pos.x), int(self.pos.y), 4, 4))

class Bubble:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = random.uniform(0.5, 1.2)

    def update(self):
        self.pos.y -= self.speed
        self.pos.x += math.sin(pygame.time.get_ticks() * 0.01) * 0.5

    def draw(self, surface):
        pygame.draw.circle(surface, (220, 240, 255), (int(self.pos.x), int(self.pos.y)), 1)

class Fish:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.z = random.uniform(0.6, 1.1)
        self.z_speed = random.uniform(-0.002, 0.002)
        self.vel = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.acc = pygame.Vector2(0, 0)
        self.hunger = random.uniform(0, 30)
        self.health = 100.0
        self.max_speed = 2
        self.alive = True

    def get_depth_color(self, base_color):
        dim = 1.0 - (self.z - 0.6) * 0.5
        return (int(base_color[0] * dim), int(base_color[1] * dim), int(base_color[2] * dim))

    def apply_force(self, force):
        self.acc += force

    def update(self, pellets, algae):
        self.z += self.z_speed
        if self.z < 0.6 or self.z > 1.1: self.z_speed *= -1
        self.hunger += 0.05
        if self.hunger >= MAX_HUNGER:
            self.hunger = MAX_HUNGER
            self.health -= 0.1
            if self.health <= 0: self.alive = False

        target_pos, is_alg = None, False
        if self.hunger > 40:
            if pellets:
                target_pos = min(pellets, key=lambda p: self.pos.distance_to(p.pos)).pos
            elif algae:
                target_pos = pygame.Vector2(min(algae, key=lambda a: self.pos.distance_to(pygame.Vector2(a))))
                is_alg = True

        if target_pos and self.pos.distance_to(target_pos) < 250:
            self.apply_force((target_pos - self.pos).normalize() * 0.2)
            if self.pos.distance_to(target_pos) < 10:
                self.hunger = max(0, self.hunger - (20 if is_alg else 60))
                if not is_alg:
                    for p in pellets:
                        if p.pos == target_pos: pellets.remove(p); break
                else:
                    for a in algae:
                        if pygame.Vector2(a) == target_pos: algae.remove(a); break

        self.vel += self.acc
        if self.vel.length() > self.max_speed: self.vel.scale_to_length(self.max_speed)
        self.pos += self.vel
        self.acc *= 0
        if self.pos.x < 0 or self.pos.x > SCREEN_WIDTH: self.vel.x *= -1
        if self.pos.y < WATER_TOP or self.pos.y > SCREEN_HEIGHT - SAND_HEIGHT: self.vel.y *= -1
        if random.random() < 0.005: bubbles.append(Bubble(self.pos.x, self.pos.y))

    def draw_shadow(self, surface, width):
        dune_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5 + math.cos(self.pos.x * 0.05) * 2
        s_col = (20, 20, 20, 70) if self.health > 30 else (80, 20, 20, 90)
        pygame.draw.ellipse(surface, s_col, (self.pos.x, dune_y, width * self.z, 5))

class NeonTetra(Fish):
    def __init__(self, x, y):
        mid_y = random.randint(200, 400)
        super().__init__(x, mid_y)
        self.glow_intensity = random.randint(0, 70)
        self.streak_offset = random.uniform(-1, 1)

    def behavior(self, fishes):
        # 1. Schooling Forces (Boids)
        cohesion = pygame.Vector2(0, 0)
        alignment = pygame.Vector2(0, 0)
        separation = pygame.Vector2(0, 0)
        count = 0

        for other in fishes:
            if isinstance(other, NeonTetra) and other != self:
                dist = self.pos.distance_to(other.pos)
                if dist < 80: # Neighborhood radius
                    cohesion += other.pos
                    alignment += other.vel
                    count += 1
                    # Separation: Push away if too close to avoid overlapping
                    if dist < 25:
                        diff = self.pos - other.pos
                        if diff.length() > 0:
                            separation += diff.normalize() / dist

        if count > 0:
            cohesion = ((cohesion / count) - self.pos) * 0.03
            alignment = (alignment / count) * 0.05
            self.apply_force(cohesion + alignment + (separation * 0.8))

        # 2. Depth Preference (Middle of the Water Column)
        # Neons are mid-water fish; they avoid the very top and very bottom
        mid_tank_y = (WATER_TOP + (SCREEN_HEIGHT - SAND_HEIGHT)) / 2
        dy = self.pos.y - mid_tank_y
        if abs(dy) > 80:
            self.apply_force(pygame.Vector2(0, -dy * 0.002))

        # 3. Occasional "Twitch" / Darting
        # Small fish dart quickly then glide.
        if random.random() < 0.005:
            dart_dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-0.5, 0.5))
            self.apply_force(dart_dir * 2.5)

        # 4. Reaction to Larger Fish (Predator Evasion)
        # If a larger Cichlid or Rainbowfish gets too close, the school scatters
        for other in fishes:
            if not isinstance(other, NeonTetra) and self.pos.distance_to(other.pos) < 50:
                escape_force = (self.pos - other.pos).normalize() * 0.15
                self.apply_force(escape_force)

    def draw(self, surface):
        self.draw_shadow(surface, 15)
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        # Colors
        body_silver = self.get_depth_color((180, 185, 200))
        neon_blue = (80, 240, 255)
        neon_red = (255, 30, 60)

        # 1. Torpedo Body
        # Nose, Top, TailBase, Bottom
        pts = [(x, y), (x - 8 * z * facing, y - 3 * z), (x - 20 * z * facing, y), (x - 8 * z * facing, y + 4 * z)]
        pygame.draw.polygon(surface, body_silver, pts)

        # 2. Glowing Neon Stripe
        # We draw a thick line for the blue glow
        stripe_start = (x - 4 * z * facing, y - 1 * z)
        stripe_end = (x - 18 * z * facing, y - 1 * z)

        # Inner "Hot" White/Blue center
        pygame.draw.line(surface, (200, 255, 255), stripe_start, stripe_end, int(2 * z))

        # 3. Red Tail Section (Lower half of the back)
        red_pts = [(x - 12 * z * facing, y + 1 * z), (x - 20 * z * facing, y), (x - 20 * z * facing, y + 3 * z),
                   (x - 12 * z * facing, y + 3 * z)]
        pygame.draw.polygon(surface, neon_red, red_pts)

        # 4. Tiny translucent fins
        tail_sway = math.sin(pygame.time.get_ticks() * 0.015) * 2 * z
        t_pts = [(x - 20 * z * facing, y), (x - 26 * z * facing, y - 4 * z + tail_sway),
                 (x - 26 * z * facing, y + 4 * z + tail_sway)]
        pygame.draw.polygon(surface, body_silver, t_pts)


class Cichlid(Fish):
    def __init__(self, x, y):
        # Choose a permanent home spot on the sand
        bottom_y = random.randint(SCREEN_HEIGHT - 120, SCREEN_HEIGHT - SAND_HEIGHT - 10)
        super().__init__(x, bottom_y)
        self.territory = pygame.Vector2(x, bottom_y)
        self.max_speed = 2.8

        # Behavior States
        self.state = "PATROL"  # PATROL, DEFEND, SIFT
        self.target_rival = None
        self.sift_timer = 0
        self.patrol_timer = 0

    def behavior(self, fishes):
        # 1. State Machine Logic
        if self.state == "PATROL":
            self.handle_patrol(fishes)
        elif self.state == "DEFEND":
            self.handle_defense()
        elif self.state == "SIFT":
            self.handle_sifting()

        # 2. General Gravity (Keep them at the bottom)
        # Cichlids are rock-dwellers; they hate being in open top water
        if self.pos.y < SCREEN_HEIGHT - 250:
            self.apply_force(pygame.Vector2(0, 0.15))

    def handle_patrol(self, fishes):
        # Move back and forth near the home territory
        dist_to_home = self.pos.distance_to(self.territory)
        if dist_to_home > 150:
            self.apply_force((self.territory - self.pos) * 0.01)

        # Look for intruders
        for o in fishes:
            if o != self and self.pos.distance_to(o.pos) < 100:
                # If it's another Cichlid, initiate defense
                if isinstance(o, Cichlid):
                    self.target_rival = o
                    self.state = "DEFEND"
                    return

        # Occasionally decide to sift the sand
        if random.random() < 0.005:
            self.state = "SIFT"
            self.sift_timer = 120

    def handle_defense(self):
        if not self.target_rival or not self.target_rival.alive:
            self.state = "PATROL"
            return

        dist = self.pos.distance_to(self.target_rival.pos)

        if dist > 200 or self.pos.distance_to(self.territory) > 300:
            # Rival is gone or we are too far from home
            self.target_rival = None
            self.state = "PATROL"
        elif dist > 40:
            # Charge at the rival!
            charge = (self.target_rival.pos - self.pos).normalize() * 0.12
            self.apply_force(charge)
        else:
            # Face-off: Jitter back and forth (Aggressive display)
            jitter = pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))
            self.apply_force(jitter)
            # Apply a small push away to prevent overlapping too long
            self.apply_force((self.pos - self.target_rival.pos) * 0.05)

    def handle_sifting(self):
        # Sink to the very bottom
        target_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5
        self.apply_force(pygame.Vector2(0, (target_y - 2 - self.pos.y) * 0.1))

        # Stop horizontal movement
        self.vel *= 0.9

        self.sift_timer -= 1
        if self.sift_timer <= 0:
            # "Spit" out sand by creating a few bubbles
            if hasattr(self, 'bubbles'):  # If your main loop has a bubble list
                # bubbles.append(Bubble(self.pos.x, self.pos.y))
                pass
            self.state = "PATROL"
    def draw(self, surface):
        self.draw_shadow(surface, 26)
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        body_blue = self.get_depth_color((40, 120, 255))
        dark_blue = self.get_depth_color((20, 40, 100))

        # 1. Main Body Silhouette
        pts = [
            (x, y + 4 * z),  # Nose
            (x - 5 * z * facing, y - 4 * z),  # Forehead (Nuchal hump)
            (x - 18 * z * facing, y - 2 * z),  # Back
            (x - 28 * z * facing, y + 2 * z),  # Tail Base Top
            (x - 28 * z * facing, y + 10 * z),  # Tail Base Bot
            (x - 15 * z * facing, y + 14 * z)  # Belly
        ]
        pygame.draw.polygon(surface, body_blue, pts)

        # 2. Malawi Stripes (Vertical Bars)
        # We place these between the head and the tail base
        for i in range(5):
            # Calculate bar X position trailing behind the head
            bar_x = x - (8 + i * 4) * z * facing

            # The top and bottom of the bars should stay within the body height
            bar_top = y + (0 + abs(i - 2)) * z
            bar_bot = y + (12 - abs(i - 2)) * z

            pygame.draw.line(surface, dark_blue, (bar_x, bar_top), (bar_x, bar_bot), int(3 * z))

        # 3. Dorsal Fin (Top fin)
        dorsal_pts = [(x - 6 * z * facing, y - 3 * z), (x - 24 * z * facing, y - 8 * z),
                      (x - 28 * z * facing, y + 1 * z)]
        pygame.draw.polygon(surface, dark_blue, dorsal_pts)
        pygame.draw.lines(surface, (150, 220, 255), False, dorsal_pts, 1)

        # 4. Tail Fin
        t_sway = math.sin(pygame.time.get_ticks() * 0.012) * 4 * z
        tail_tip_x = x - 36 * z * facing
        t_pts = [
            (x - 28 * z * facing, y + 2 * z),
            (tail_tip_x, y - 2 * z + t_sway),
            (tail_tip_x, y + 14 * z + t_sway),
            (x - 28 * z * facing, y + 10 * z)
        ]
        pygame.draw.polygon(surface, dark_blue, t_pts)

        # 5. Eye
        eye_x = x - 4 * z * facing
        pygame.draw.circle(surface, (0, 0, 0), (int(eye_x), int(y + 4 * z)), int(2 * z))
        pygame.draw.circle(surface, (255, 255, 255), (int(eye_x + 1 * facing), int(y + 3 * z)), 1)

class PearlGourami(Fish):
    def __init__(self, x, y):
        # Naturally prefers the top third of the tank
        top_y = random.randint(WATER_TOP + 40, WATER_TOP + 150)
        super().__init__(x, top_y)
        self.max_speed = 1.2
        self.target_y = top_y
        self.is_gulping = False
        self.inquiry_timer = 0
        self.look_target = None

    def behavior(self, fishes):
        # 1. Labyrinth Breathing (Surface Gulping)
        # Occasionally heads to the surface to "breathe" air
        if not self.is_gulping and random.random() < 0.002:
            self.is_gulping = True

        if self.is_gulping:
            # Move toward the surface
            surface_force = (WATER_TOP + 5 - self.pos.y) * 0.05
            self.apply_force(pygame.Vector2(0, surface_force))
            if self.pos.y <= WATER_TOP + 10:
                self.is_gulping = False # Gulp finished
        else:
            # 2. Buoyancy: Maintain preferred depth with a gentle hover
            depth_force = (self.target_y - self.pos.y) * 0.01
            self.apply_force(pygame.Vector2(0, depth_force))

        # 3. Inquisitive "Feeler" Behavior
        # Gouramis "touch" objects/fish with their long feelers
        self.inquiry_timer -= 1
        if self.inquiry_timer <= 0:
            # Look for something to investigate (a plant or another fish)
            nearby = [f for f in fishes if f != self and self.pos.distance_to(f.pos) < 150]
            if nearby:
                self.look_target = random.choice(nearby)
                self.inquiry_timer = random.randint(200, 500)
            else:
                self.look_target = None

        if self.look_target:
            # Gently glide toward the target but stop at a distance to "feel" it
            dist = self.pos.distance_to(self.look_target.pos)
            if dist > 60:
                self.apply_force((self.look_target.pos - self.pos).normalize() * 0.02)
            else:
                # Hover and "inspect" (Slow down)
                self.vel *= 0.95

        # 4. Graceful Glide (Slow friction)
        # Gouramis don't dart; they drift elegantly.
        if self.vel.length() > self.max_speed:
            self.vel *= 0.9

        # 5. Avoidance (Gentle turn away from glass)
        if self.pos.x < 50 or self.pos.x > SCREEN_WIDTH - 50:
            self.apply_force(pygame.Vector2(-0.05 if self.pos.x > 50 else 0.05, 0))

    def draw(self, surface):
        self.draw_shadow(surface, 28)
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        # Colors
        base_pearl = self.get_depth_color((210, 210, 220))
        throat_orange = self.get_depth_color((255, 130, 60))
        spot_white = (255, 255, 255, 180)
        lateral_line_col = (45, 45, 50)
        shimmer_col = (200, 230, 255, 40)  # Soft blue iridescence

        # 1. Create a Masking Surface for the Body
        # We increase height to accommodate the large anal fin
        fish_surf = pygame.Surface((int(35 * z), int(40 * z)), pygame.SRCALPHA)

        # Local Coordinates (relative to surface)
        # Body logic: x_off centers the fish horizontally in the surf
        x_off = 2 * z
        body_rel_pts = [
            (30 * z + x_off, 10 * z),  # Nose
            (18 * z + x_off, 2 * z),  # Top
            (0 * z + x_off, 10 * z),  # Tail Base Top
            (0 * z + x_off, 18 * z),  # Tail Base Bot
            (18 * z + x_off, 26 * z)  # Belly
        ]

        # 2. Draw Main Body & Orange Throat
        pygame.draw.polygon(fish_surf, base_pearl, body_rel_pts)

        # Orange throat (Drawn inside the mask)
        throat_pts = [(30 * z + x_off, 10 * z), (22 * z + x_off, 18 * z), (10 * z + x_off, 24 * z),
                      (25 * z + x_off, 12 * z)]
        pygame.draw.polygon(fish_surf, throat_orange, throat_pts)

        # 3. Add Lateral Stripe and Pearls (Masked)
        pygame.draw.lines(fish_surf, lateral_line_col, False,
                          [(30 * z + x_off, 11 * z), (15 * z + x_off, 13 * z), (0 * z + x_off, 14 * z)], int(1 * z))

        random.seed(hash(self) % 1000)
        for _ in range(int(30 * z)):
            sx = random.uniform(4 * z, 28 * z) + x_off
            sy = random.uniform(4 * z, 24 * z)
            # Only draw if the pixel is already colored (ensures it's inside the fish body)
            if fish_surf.get_at((int(sx), int(sy))).a > 0:
                pygame.draw.circle(fish_surf, spot_white, (int(sx), int(sy)), int(random.uniform(0.5, 1.2) * z))

        # 4. Iridescent Shimmer Overlay
        # A soft glow that follows the top curve
        pygame.draw.ellipse(fish_surf, shimmer_col, (5 * z + x_off, 2 * z, 20 * z, 10 * z))
        random.seed()

        # 5. Flip and Blit Body Surface
        if facing == -1:
            fish_surf = pygame.transform.flip(fish_surf, True, False)

        # Blit so the nose (30*z + x_off) aligns with self.pos.x
        render_x = x - ((30 * z + x_off) if facing == 1 else (2 * z))
        surface.blit(fish_surf, (render_x, y - 10 * z))

        # 6. External Fins (Flowy & Physics-based)
        t_sway = math.sin(pygame.time.get_ticks() * 0.008) * 3 * z
        f_sway = math.sin(pygame.time.get_ticks() * 0.005) * 5 * z  # Slower sway for large fins

        # Tail Fin (Notched fan)
        tail_tip_x = x - 44 * z * facing
        t_pts = [
            (x - 30 * z * facing, y),
            (tail_tip_x, y - 5 * z + t_sway),
            (x - 36 * z * facing, y + 4 * z + t_sway),
            (tail_tip_x, y + 13 * z + t_sway),
            (x - 30 * z * facing, y + 8 * z)
        ]
        pygame.draw.polygon(surface, base_pearl, t_pts)

        # Large Anal Fin (The long trailing bottom fin)
        anal_pts = [
            (x - 12 * z * facing, y + 15 * z),
            (x - 28 * z * facing, y + 25 * z + f_sway),
            (x - 32 * z * facing, y + 12 * z)
        ]
        pygame.draw.polygon(surface, throat_orange, anal_pts)

        # Eye & Feelers
        eye_x = x - 3 * z * facing
        pygame.draw.circle(surface, (10, 10, 10), (int(eye_x), int(y + 1 * z)), int(2 * z))

        # Physics feeler (moves opposite to velocity)
        feeler_end = (x - 22 * z * facing - (self.vel.x * 5), y + 32 * z + f_sway)
        pygame.draw.line(surface, throat_orange, (x - 10 * z * facing, y + 12 * z), feeler_end, 1)

class BoesemaniRainbow(Fish):
    def __init__(self, x, y):
        mid_top_y = random.randint(WATER_TOP + 50, 350)
        super().__init__(x, mid_top_y)
        self.max_speed = 2.2
        self.curiosity_target = None
        self.curiosity_timer = 0
        self.z = random.uniform(0.7, 1.0)

    def behavior(self, fishes):
        # 1. Social Schooling
        avg_pos = pygame.Vector2(0, 0)
        count = 0
        for o in fishes:
            if isinstance(o, BoesemaniRainbow) and o != self and self.pos.distance_to(o.pos) < 120:
                avg_pos += o.pos
                count += 1
        if count > 0:
            self.apply_force(((avg_pos / count) - self.pos) * 0.02)

        # 2. Curiosity Logic
        self.curiosity_timer -= 1
        if self.curiosity_timer <= 0:
            if random.random() < 0.02:
                nearby = [f for f in fishes if f != self and self.pos.distance_to(f.pos) < 250]
                if nearby:
                    self.curiosity_target = random.choice(nearby)
                    self.curiosity_timer = random.randint(150, 400)
            else:
                self.curiosity_target = None

        if self.curiosity_target and self.curiosity_target.alive:
            target_pos = self.curiosity_target.pos
            dist = self.pos.distance_to(target_pos)
            if dist > 50:
                self.apply_force((target_pos - self.pos).normalize() * 0.07)
            elif dist < 30:
                self.apply_force((self.pos - target_pos).normalize() * 0.09)

    def draw(self, surface):
        self.draw_shadow(surface, 22)
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        # Colors
        blue_front = self.get_depth_color((60, 110, 220))
        orange_back = self.get_depth_color((255, 160, 40))
        mid_blend = self.get_depth_color((120, 150, 180))  # The transition color
        fin_highlight = (255, 230, 150)

        # 1. Deep Triangular Body Points
        # Boesemani are famous for being very "tall" or deep-bodied
        nose = (x, y + 5 * z)
        top_peak = (x - 12 * z * facing, y - 6 * z)
        tail_base_top = (x - 28 * z * facing, y + 2 * z)
        tail_base_bot = (x - 28 * z * facing, y + 10 * z)
        belly_low = (x - 14 * z * facing, y + 18 * z)

        body_pts = [nose, top_peak, tail_base_top, tail_base_bot, belly_low]

        # 2. Draw Main Body Layers for Gradient Effect
        # Back half (Orange)
        pygame.draw.polygon(surface, orange_back, body_pts)

        # Mid Blend (A smaller polygon in the middle to soften the transition)
        mid_pts = [nose, top_peak, (x - 20 * z * facing, y + 5 * z), belly_low]
        pygame.draw.polygon(surface, mid_blend, mid_pts)

        # Front half (Blue)
        front_pts = [nose, (x - 8 * z * facing, y - 3 * z), (x - 12 * z * facing, y + 5 * z),
                     (x - 8 * z * facing, y + 14 * z)]
        pygame.draw.polygon(surface, blue_front, front_pts)

        # 3. Double Dorsal & Anal Fins (Iconic Rainbowfish trait)
        # Top Fins
        pygame.draw.polygon(surface, orange_back, [(x - 15 * z * facing, y - 5 * z), (x - 25 * z * facing, y - 10 * z),
                                                   (x - 27 * z * facing, y)])
        # Bottom Fin (Anal fin)
        pygame.draw.polygon(surface, orange_back, [(x - 12 * z * facing, y + 17 * z), (x - 26 * z * facing, y + 20 * z),
                                                   (x - 28 * z * facing, y + 10 * z)])

        # 4. Animated Tail Fin
        t_sway = math.sin(pygame.time.get_ticks() * 0.015) * 4 * z
        tail_tip_x = x - 38 * z * facing
        t_pts = [
            tail_base_top,
            (tail_tip_x, y - 4 * z + t_sway),
            (tail_tip_x, y + 16 * z + t_sway),
            tail_base_bot
        ]
        pygame.draw.polygon(surface, orange_back, t_pts)
        # Tail trim highlight
        pygame.draw.lines(surface, fin_highlight, False, t_pts[1:3], 1)

        # 5. Shimmer Scale Detail
        # Vertical thin lines in the mid-section
        for i in range(3):
            line_x = x - (10 + i * 3) * z * facing
            pygame.draw.line(surface, (100, 180, 255, 100), (line_x, y), (line_x, y + 10 * z), 1)

        # 6. Eye (Placed specifically in the blue section)
        eye_x = x - 4 * z * facing
        pygame.draw.circle(surface, (10, 10, 30), (int(eye_x), int(y + 4 * z)), int(2 * z))
        pygame.draw.circle(surface, (255, 255, 255), (int(eye_x + 1 * facing), int(y + 3 * z)), 1)


class PeacockCichlid(Cichlid):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.0
        self.state = "HOVER"  # Special hunting state
        self.hunt_timer = 0
        self.color_shift = random.uniform(0, 30)  # Individual color variation

    def behavior(self, fishes):
        # 1. State Machine
        if self.state == "HOVER":
            # Motionless hunting: Cichlids "listen" for invertebrates in the sand
            self.vel *= 0.8
            self.hunt_timer += 1
            if self.hunt_timer > 100:
                self.state = "PATROL"
                self.hunt_timer = 0

        elif self.state == "PATROL":
            # Standard movement, staying near the bottom
            if random.random() < 0.01:
                self.state = "HOVER"
            super().behavior(fishes)  # Inherit territorial behavior from Cichlid

    def draw(self, surface):
        self.draw_shadow(surface, 28)
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        # Colors
        electric_blue = self.get_depth_color((40, 110, 255))
        fin_red = self.get_depth_color((200, 50, 40))
        egg_spot_gold = (255, 200, 50)
        bar_color = (20, 40, 100, 80)  # Subtle dark vertical bars
        shimmer_top = (180, 230, 255, 70)

        # 1. Create Body Surface
        fish_surf = pygame.Surface((int(42 * z), int(32 * z)), pygame.SRCALPHA)
        x_off = 5 * z

        # Refined Body Points
        body_rel_pts = [
            (35 * z + x_off, 12 * z),  # Nose
            (25 * z + x_off, 4 * z),  # High forehead
            (10 * z + x_off, 6 * z),  # Back
            (0 * z + x_off, 12 * z),  # Tail Base Top
            (0 * z + x_off, 20 * z),  # Tail Base Bot
            (15 * z + x_off, 28 * z)  # Deep Belly
        ]

        # 2. Draw Layered Body Colors
        pygame.draw.polygon(fish_surf, electric_blue, body_rel_pts)

        # Red "Shoulder" Glow (Blended into the blue)
        pygame.draw.ellipse(fish_surf, fin_red, (20 * z + x_off, 8 * z, 12 * z, 14 * z))

        # 3. Vertical Barring & Body Specks (Deterministic)
        random.seed(hash(self) % 1000)
        # Vertical bars common in Malawi Cichlids
        for i in range(6):
            bx = (6 + i * 4) * z + x_off
            pygame.draw.line(fish_surf, bar_color, (bx, 8 * z), (bx, 22 * z), int(2 * z))

        # Metallic "Scales" Specks
        for _ in range(int(20 * z)):
            sx = random.uniform(5 * z, 30 * z) + x_off
            sy = random.uniform(8 * z, 24 * z)
            if fish_surf.get_at((int(sx), int(sy))).a > 0:
                pygame.draw.circle(fish_surf, shimmer_top, (int(sx), int(sy)), 1)
        random.seed()

        # 4. Flip and Blit Body
        if facing == -1:
            fish_surf = pygame.transform.flip(fish_surf, True, False)

        render_x = x - ((35 * z + x_off) if facing == 1 else (2 * z))
        surface.blit(fish_surf, (render_x, y - 12 * z))

        # 5. Fins with Egg Spots
        f_sway = math.sin(pygame.time.get_ticks() * 0.01) * 3 * z

        # Dorsal Fin (Electric blue/white edge)
        d_pts = [(x - 28 * z * facing, y - 5 * z), (x - 12 * z * facing, y - 14 * z + f_sway),
                 (x - 4 * z * facing, y - 2 * z)]
        pygame.draw.polygon(surface, electric_blue, d_pts)
        pygame.draw.lines(surface, (200, 240, 255), False, d_pts[:2], 2)  # Glowing edge

        # Anal Fin (Red/Orange with Yellow Egg Spots)
        a_pts = [(x - 26 * z * facing, y + 16 * z + f_sway), (x - 10 * z * facing, y + 14 * z),
                 (x - 24 * z * facing, y + 8 * z)]
        pygame.draw.polygon(surface, fin_red, a_pts)

        # Add the Egg Spots (Signature Peacock Cichlid feature)
        for i in range(3):
            spot_x = x - (16 + i * 4) * z * facing
            spot_y = y + 12 * z + f_sway
            pygame.draw.circle(surface, egg_spot_gold, (int(spot_x), int(spot_y)), int(1.2 * z))

        # 6. Tail Fin
        t_sway = math.sin(pygame.time.get_ticks() * 0.012) * 5 * z
        tail_tip_x = x - 46 * z * facing
        t_pts = [(x - 28 * z * facing, y), (tail_tip_x, y - 6 * z + t_sway), (tail_tip_x, y + 16 * z + t_sway),
                 (x - 28 * z * facing, y + 8 * z)]
        pygame.draw.polygon(surface, electric_blue, t_pts)

        # 7. Eye
        eye_x, eye_y = x - 6 * z * facing, y + 3 * z
        pygame.draw.circle(surface, (10, 10, 10), (int(eye_x), int(eye_y)), int(2.5 * z))
        pygame.draw.circle(surface, (255, 200, 0), (int(eye_x), int(eye_y)), int(2.5 * z), 1)  # Gold iris


class SocialFlowerhorn(Fish):
    population = 0

    def __init__(self, x, y):
        SocialFlowerhorn.population += 1
        self.target_friend = None
        super().__init__(x, y)
        self.z = random.uniform(0.1, 0.5)

        self.max_speed = 2.2
        self.state = "IDLE"
        self.angle = 0.0
        self.lerp_speed = 0.1
        self.wiggle_energy = 0.0

        # --- NEW STATS ---
        self.aggression = random.uniform(0.3, 1.0)
        self.energy = random.uniform(0.5, 1.0)
        self.burst_timer = 0

        # --- GENETICS (reduced hump) ---
        self.kok_scale = random.uniform(0.6, 1.0)

        r = random.randint(200, 255)
        g = random.randint(20, 80)
        b = random.randint(40, 100)
        self.base_color = (r, g, b)

        self.pearl_count = random.randint(25, 60)
        self.seed = random.random()

    # ---------------- BEHAVIOR ----------------
    def behavior(self, fishes):
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        dist_to_mouse = self.pos.distance_to(mouse_pos)

        self.burst_timer -= 1

        if dist_to_mouse < 300:
            self.state = "INTERACT"
            desired = (mouse_pos - self.pos).normalize()
            self.apply_force(desired * 0.12)

            self.wiggle_energy = min(1.0, self.wiggle_energy + 0.06)

            if self.burst_timer <= 0 and random.random() < 0.02:
                self.vel += desired * 2.5
                self.burst_timer = random.randint(40, 100)

        else:
            self.state = "SOCIALIZE"
            self.wiggle_energy *= 0.94

            if not self.target_friend or random.random() < 0.01:
                others = [f for f in fishes if f != self]
                if others:
                    self.target_friend = random.choice(others)

            if self.target_friend:
                offset = self.target_friend.pos - self.pos
                dist = offset.length()

                if dist > 120:
                    self.apply_force(offset.normalize() * 0.035)
                elif dist < 60:
                    self.apply_force(-offset.normalize() * 0.04)

        # Separation
        for f in fishes:
            if f != self:
                d = self.pos.distance_to(f.pos)
                if 0 < d < 40:
                    self.apply_force((self.pos - f.pos).normalize() * 0.05)

        # Angle
        if self.vel.length() > 0.1:
            target_angle = math.degrees(math.atan2(-self.vel.y, abs(self.vel.x)))
            self.angle += (target_angle - self.angle) * self.lerp_speed

    # ---------------- DRAW ----------------
    def draw(self, surface):
        self.draw_shadow(surface, 60)
        z = self.z

        # Dynamic canvas sizing
        surf_w, surf_h = int(280 * z), int(280 * z)
        fish_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2

        # Physics-based animation timing
        t = pygame.time.get_ticks() * (0.004 + self.wiggle_energy * 0.01)
        tail_move = math.sin(t) * (12 * z + self.wiggle_energy * 10)
        fin_wave = math.cos(t * 0.8) * 6 * z

        # ---------------------------------------------------------
        # 🎨 DYNAMIC PALETTE
        # ---------------------------------------------------------
        shimmer = int(15 * math.sin(t * 1.5))
        base_rgb = list(self.base_color)

        # Pearl/Scale highlight color
        pearl_color = (
            min(255, base_rgb[0] + 100),
            min(255, base_rgb[1] + 100),
            min(255, base_rgb[2] + 100),
            150
        )

        # ---------------------------------------------------------
        # 🐟 FINS (Drawn First for Layering)
        # ---------------------------------------------------------
        def draw_organic_fin(points, color, alpha=100, wavy=True):
            f_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            # Main membrane
            pygame.draw.polygon(f_surf, (*color[:3], alpha), points)
            # Fin Rays (the "bones")
            root = points[0]
            for p in points[1:]:
                pygame.draw.line(f_surf, (*pearl_color[:3], 40), root, p, max(1, int(2 * z)))

            # Soften edges
            pygame.draw.aalines(f_surf, (*color[:3], 180), False, points)
            fish_surf.blit(f_surf, (0, 0))

        # Pectoral/Dorsal Fins
        draw_organic_fin([
            (cx - 20 * z, cy - 30 * z),
            (cx - 60 * z, cy - 90 * z + fin_wave),
            (cx - 120 * z, cy - 70 * z + tail_move),
            (cx - 70 * z, cy - 10 * z)
        ], self.base_color, 120)

        # Anal Fin
        draw_organic_fin([
            (cx - 20 * z, cy + 30 * z),
            (cx - 60 * z, cy + 90 * z - fin_wave),
            (cx - 120 * z, cy + 70 * z + tail_move),
            (cx - 70 * z, cy + 10 * z)
        ], self.base_color, 120)

        # ---------------------------------------------------------
        # 🐟 BODY CONSTRUCTION
        # ---------------------------------------------------------
        body_mask = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # Define body parts as a unified shape
        parts = [
            ((cx - 10 * z, cy), (140 * z, 105 * z)),  # Main Midsection
            ((cx + 40 * z, cy), (90 * z, 95 * z)),  # Head/Chest
            ((cx - 60 * z, cy + 5 * z), (110 * z, 75 * z))  # Rear Taper
        ]

        for pos, size in parts:
            rect = pygame.Rect(0, 0, size[0], size[1])
            rect.center = pos
            pygame.draw.ellipse(body_mask, (255, 255, 255), rect)

        # Apply a "Spherical" lighting effect rather than a flat line gradient
        render_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        render_surf.fill(self.get_depth_color(self.base_color))

        # Highlight (Top/Shoulder)
        highlight_rect = pygame.Rect(cx - 50 * z, cy - 60 * z, 130 * z, 60 * z)
        pygame.draw.ellipse(render_surf, pearl_color, highlight_rect)

        # Belly (Bottom Glow)
        belly_rect = pygame.Rect(cx - 40 * z, cy + 10 * z, 100 * z, 50 * z)
        pygame.draw.ellipse(render_surf, (255, 255, 255, 80), belly_rect)

        # Mask everything to the body shape
        render_surf.blit(body_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        fish_surf.blit(render_surf, (0, 0))

        # ---------------------------------------------------------
        # 🌸 THE "FLOWER" MARKINGS (Flowerhorn Signature)
        # ---------------------------------------------------------
        for i in range(5):
            spot_x = cx - 60 * z + (i * 25 * z)
            spot_y = cy + math.sin(t + i) * 2 * z
            spot_size = (12 * z - i * z)
            # Black irregular spots
            pygame.draw.circle(fish_surf, (20, 20, 20, 200), (int(spot_x), int(spot_y)), int(spot_size))
            # Silver halo around spots
            pygame.draw.circle(fish_surf, (255, 255, 255, 100), (int(spot_x), int(spot_y)), int(spot_size + 2 * z), 1)

        # ---------------------------------------------------------
        # 🧠 KOK (The Nuchal Hump)
        # ---------------------------------------------------------
        k_size = (70 * z * self.kok_scale, 60 * z * self.kok_scale)
        kok_rect = pygame.Rect(0, 0, k_size[0], k_size[1])
        kok_rect.center = (cx + 55 * z, cy - 45 * z)

        # Gradient for the Hump
        pygame.draw.ellipse(fish_surf, (230, 50, 50), kok_rect)
        # Vein-like highlights on the hump
        pygame.draw.ellipse(fish_surf, (255, 100, 100, 150), kok_rect.inflate(-10 * z, -15 * z))

        # ---------------------------------------------------------
        # 👁️ REALISTIC EYE
        # ---------------------------------------------------------
        ex, ey = int(cx + 80 * z), int(cy - 5 * z)
        pygame.draw.circle(fish_surf, (50, 0, 0), (ex, ey), int(10 * z))  # Socket
        pygame.draw.circle(fish_surf, (255, 50, 0), (ex, ey), int(8 * z))  # Iris
        pygame.draw.circle(fish_surf, (0, 0, 0), (ex, ey), int(5 * z))  # Pupil
        pygame.draw.circle(fish_surf, (255, 255, 255, 200), (ex + 3, ey - 3), int(2 * z))  # Glint

        # ---------------------------------------------------------
        # 🎬 TAIL (Trailing Layer)
        # ---------------------------------------------------------
        draw_organic_fin([
            (cx - 90 * z, cy),
            (cx - 180 * z, cy - 80 * z + tail_move),
            (cx - 210 * z, cy + tail_move * 0.5),
            (cx - 180 * z, cy + 80 * z + tail_move),
            (cx - 90 * z, cy + 20 * z)
        ], self.base_color, 150)

        # Final transform and blit
        facing_right = self.vel.x >= 0
        final = pygame.transform.flip(fish_surf, True, False) if not facing_right else fish_surf
        rotated = pygame.transform.rotate(final, self.angle if facing_right else -self.angle)
        surface.blit(rotated, rotated.get_rect(center=(self.pos.x, self.pos.y)))

def spawn_random_fish(fishes=[]):
    choice = random.random()
    spawn_x = random.randint(50, SCREEN_WIDTH - 50)

    if choice < 0.05:
            return SocialFlowerhorn(spawn_x, random.randint(200, 400))
    # 3. Standard spawning for the rest
    elif choice < 0.35:  # 30% Neons
        return NeonTetra(spawn_x, random.randint(250, 450))
    elif choice < 0.55:  # 20% Rainbowfish
        return BoesemaniRainbow(spawn_x, random.randint(150, 300))
    elif choice < 0.70:  # 15% Standard Cichlids
        return Cichlid(spawn_x, SCREEN_HEIGHT - 150)
    elif choice < 0.85:  # 15% Peacock Cichlids
        return PeacockCichlid(spawn_x, SCREEN_HEIGHT - 160)
    else:  # 15% Pearl Gouramis
        return PearlGourami(spawn_x, 120)


# --- Main ---
pygame.init()
pygame.mixer.init() # Initialize the mixer for audio
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# --- NEW: Load Splash Screen Asset ---
try:
    splash_img = pygame.image.load(get_path('splash.png')).convert()
    splash_img = pygame.transform.scale(splash_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error:
    print("Warning: splash.png not found in 'doodads'.")
    splash_img = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    splash_img.fill((20, 40, 80))


def draw_welcome_screen():
    screen.blit(splash_img, (0, 0))

    # Button Configuration
    btn_w, btn_h = 240, 60
    btn_x, btn_y = (SCREEN_WIDTH // 2) - (btn_w // 2), (SCREEN_HEIGHT // 2) + 100

    mouse_pos = pygame.mouse.get_pos()
    button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    # Hover Effect
    color = (60, 160, 240) if button_rect.collidepoint(mouse_pos) else (40, 100, 200)

    # Draw Button
    pygame.draw.rect(screen, color, button_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), button_rect, 2, border_radius=15)

    # Button Text
    font = pygame.font.SysFont("Arial", 32, bold=True)
    text_surf = font.render("WELCOME", True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=button_rect.center)
    screen.blit(text_surf, text_rect)

    return button_rect


try:
    pygame.mixer.music.load(get_path('bgmusic.mp3'))
    pygame.mixer.music.play(-1)
    pygame.mixer.music.set_volume(0.5)
except pygame.error:
    print("Warning: bgmusic.mp3 not found in 'doodads' folder.")

# 2. Background Wallpaper
try:
    # Use get_path to look inside the folder
    bg_files = ["wallart.png", "wallart2.png", "wallart3.png", "wallart4.png"]
    bg_index = 0
    # Load the initial background
    bg_image = pygame.image.load(get_path(bg_files[bg_index]))
    # Ensure it fits your screen size
    bg_image = pygame.transform.scale(bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error:
    print("Warning: wallart.png not found in 'doodads'. Using solid color.")
    bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    bg_image.fill((10, 20, 40))


fishes = [spawn_random_fish() for _ in range(30)]
auto_feed_timer = random.randint(100, 300)  # Frames until next drop
species_list = ["Rotala", "Ludwigia", "Vallisneria", "Anubias"]
plants = [Plant(x, random.choice(species_list)) for x in range(40, SCREEN_WIDTH, 60)]
grains = [(random.randint(0, SCREEN_WIDTH), random.randint(540, 600),
           random.choice([(190, 170, 110), (225, 200, 140)])) for _ in range(600)]

algae, pellets, bubbles, frame = [], [], [], 0

bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
for y in range(SCREEN_HEIGHT):
    ratio = y / SCREEN_HEIGHT
    r = int(CLR_WATER_TOP[0] * (1 - ratio) + CLR_WATER_BOTTOM[0] * ratio)
    g = int(CLR_WATER_TOP[1] * (1 - ratio) + CLR_WATER_BOTTOM[1] * ratio)
    b = int(CLR_WATER_TOP[2] * (1 - ratio) + CLR_WATER_BOTTOM[2] * ratio)
    pygame.draw.line(bg_surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

caustic_beams = []
for _ in range(8):
    caustic_beams.append([
        random.randint(0, SCREEN_WIDTH),
        random.randint(20, 60),
        random.uniform(0.5, 1.5),
        random.uniform(0, 2 * math.pi)
    ])

while True:
    if current_state == STATE_WELCOME:
        btn_rect = draw_welcome_screen()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect.collidepoint(event.pos):
                    current_state = STATE_AQUARIUM

    elif current_state == STATE_AQUARIUM:
        # This renders behind everything else
        screen.blit(bg_image, (0, 0))

        bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            # Using a lower alpha (150) so the wallart.png is visible through it
            r = int(CLR_WATER_TOP[0] * (1 - ratio) + CLR_WATER_BOTTOM[0] * ratio)
            g = int(CLR_WATER_TOP[1] * (1 - ratio) + CLR_WATER_BOTTOM[1] * ratio)
            b = int(CLR_WATER_TOP[2] * (1 - ratio) + CLR_WATER_BOTTOM[2] * ratio)
            pygame.draw.line(bg_surface, (r, g, b, 150), (0, y), (SCREEN_WIDTH, y))
        screen.blit(bg_surface, (0, 0))

        # 1. Sand with Shadow/Light refraction
        s_pts = []
        for x in range(0, SCREEN_WIDTH + 11, 10):
            s_pts.append((x, 540 + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2))
        s_pts.extend([(SCREEN_WIDTH, SCREEN_HEIGHT), (0, SCREEN_HEIGHT)])
        # Use a slightly transparent sand if you want to see the bottom of the wallart
        pygame.draw.polygon(screen, CLR_SAND, s_pts)

        for gx, gy, col in grains:
            if gy > 540 + math.sin(gx * 0.02) * 5 + math.cos(gx * 0.05) * 2:
                pygame.draw.rect(screen, col, (gx, gy, 2, 2))

                # --- NEW: Automatic Feeding Logic ---
                auto_feed_timer -= 1
                if auto_feed_timer <= 0:
                    if len(pellets) < 15 and len(algae) < 5 :  # Only auto-drop if there are fewer than 15 pellets
                        random_x = random.randint(50, SCREEN_WIDTH - 50)
                        pellets.append(FoodPellet(random_x, WATER_TOP))
                    auto_feed_timer = random.randint(120, 420)


        # 2. Layers (Fish/Plants)
        for f in fishes[:]:
            # Update behavior for ALL fish types including the Gar
            f.behavior(fishes)
            f.update(pellets, algae)

            # Handling death/eating and immediate respawn
            if not f.alive:
                fishes.remove(f)
                fishes.append(spawn_random_fish(fishes))

            # --- 2. MODIFIED DRAWING LOOP ---
            # Sort by depth so small fish stay in back and large in front
        sorted_fishes = sorted(fishes, key=lambda f: f.z)

        for f in sorted_fishes:
            if f.z <= 0.9:
                # Remove the behavior/update calls from here since
                # we moved them to the loop above!
                f.draw(screen)

        for p in plants:
            p.draw(screen, frame)

        for f in sorted_fishes:
            if f.z > 0.9:
                # Just draw here
                f.draw(screen)

        # 3. Caustics
        caustic_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for beam in caustic_beams:
            beam[0] += beam[2]
            if beam[0] > SCREEN_WIDTH + 100: beam[0] = -100
            pulse = math.sin(frame * 0.02 + beam[3]) * 10 + 15
            c_pts = []
            for cy in range(0, SCREEN_HEIGHT + 21, 40):
                wave = math.sin(cy * 0.005 + frame * 0.03) * 15
                c_pts.append((beam[0] + wave, cy))
            if len(c_pts) > 1:
                pygame.draw.lines(caustic_surf, (255, 255, 230, int(pulse)), False, c_pts, beam[1])
        screen.blit(caustic_surf, (0, 0))

        # 4. Events & Objects
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b:  # Toggle with 'B' key
                    # Increment and wrap around using modulo
                    bg_index = (bg_index + 1) % len(bg_files)

                    # Load the new image
                    try:
                        new_bg = pygame.image.load(get_path(bg_files[bg_index]))
                        bg_image = pygame.transform.scale(new_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
                        print(f"Switched to {bg_files[bg_index]}")
                    except pygame.error as e:
                        print(f"Could not load {bg_files[bg_index]}: {e}")
                if event.key == pygame.K_r:
                    # Return to welcome screen
                    current_state = STATE_WELCOME
                    # Optional: Reset aquarium frame or clear pellets
                    frame = 0
                    fishes = [spawn_random_fish() for _ in range(30)]
                    algae.clear()
                    pellets.clear()
                    bubbles.clear()
                    pellets.clear()
            if event.type == pygame.MOUSEBUTTONDOWN: pellets.append(FoodPellet(*event.pos))

        if frame % ALGAE_SPAWN_RATE == 0 and len(algae) < 35:
            algae.append((random.randint(10, SCREEN_WIDTH - 10), random.randint(100, 500)))

        for a in algae: pygame.draw.circle(screen, CLR_ALGAE, a, 3)
        for p in pellets[:]: p.update(); p.draw(screen)
        for b in bubbles[:]:
            b.update()
            b.draw(screen)
            if b.pos.y < 80: bubbles.remove(b)
        for f in fishes[:]:
            if not f.alive: fishes.remove(f); fishes.append(spawn_random_fish())

        # 5. Top Surface Glow
        # Fixed: Surface matches SCREEN_WIDTH
        l_surf = pygame.Surface((SCREEN_WIDTH, 120), pygame.SRCALPHA)
        for y in range(120):
            pygame.draw.line(l_surf, (255, 255, 220, max(0, 100 - y)), (0, y), (SCREEN_WIDTH, y))
        screen.blit(l_surf, (0, 0))

    pygame.display.flip()
    clock.tick(60)
    frame += 1