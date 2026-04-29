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
        avg = pygame.Vector2(0, 0)
        count = 0
        for other in fishes:
            if isinstance(other, NeonTetra) and other != self and self.pos.distance_to(other.pos) < 60:
                avg += other.pos
                count += 1
        if count > 0: self.apply_force(((avg / count) - self.pos) * 0.02)

        mid_tank_y = (WATER_TOP + (SCREEN_HEIGHT - SAND_HEIGHT)) / 2
        dist_from_mid = self.pos.y - mid_tank_y
        if abs(dist_from_mid) > 100:
            push_dir = -0.05 if dist_from_mid > 0 else 0.05
            self.apply_force(pygame.Vector2(0, push_dir))

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
        bottom_y = random.randint(SCREEN_HEIGHT - 200, SCREEN_HEIGHT - SAND_HEIGHT - 20)
        super().__init__(x, bottom_y)
        self.territory = pygame.Vector2(x, bottom_y)
        self.max_speed = 2.4
        self.sifting = False
        self.sift_timer = 0
        self.burst_timer = random.randint(0, 100)

    def behavior(self, fishes):
        for o in fishes:
            if isinstance(o, Cichlid) and o != self:
                if self.pos.distance_to(o.pos) < 60:
                    if self.territory.distance_to(self.pos) < 120:
                        self.apply_force((o.pos - self.pos) * 0.03)
        self.apply_force((self.territory - self.pos) * 0.008)
        bottom_threshold = SCREEN_HEIGHT - 220
        if self.pos.y < bottom_threshold: self.apply_force(pygame.Vector2(0, 0.12))
        self.burst_timer += 1
        if self.burst_timer > 150 and random.random() < 0.02:
            self.apply_force(self.vel * 3.5);
            self.burst_timer = 0
        if not self.sifting and self.hunger > 30 and random.random() < 0.001:
            self.sifting = True;
            self.sift_timer = 100
        if self.sifting:
            wy = 540 + math.sin(self.pos.x * 0.02) * 5
            self.apply_force(pygame.Vector2(0, (wy - 5 - self.pos.y) * 0.1))
            self.sift_timer -= 1
            if self.sift_timer <= 0: self.sifting = False

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
        top_y = random.randint(WATER_TOP + 20, WATER_TOP + 100)
        super().__init__(x, top_y)
        self.max_speed = 1.2
        self.float_offset = random.uniform(0, math.pi * 2)

    def behavior(self, fishes):
        if self.pos.y > WATER_TOP + 150: self.apply_force(pygame.Vector2(0, -0.1))
        if random.random() < 0.01:
            self.apply_force(pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.2, 0.2)))

    def draw(self, surface):
        self.draw_shadow(surface, 28)
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        # Colors
        base_pearl = self.get_depth_color((210, 210, 220))
        throat_orange = self.get_depth_color((255, 120, 40))
        spot_white = (255, 255, 255, 160)
        lateral_line_col = (40, 40, 45)

        # 1. Define Body Polygon (Relative to 0,0 for the mask)
        # We create a local coordinate version of your body pts
        body_rel_pts = [
            (30 * z, 8 * z),  # Nose
            (18 * z, 0 * z),  # Top
            (0 * z, 8 * z),  # Tail Base Top
            (0 * z, 16 * z),  # Tail Base Bot
            (18 * z, 24 * z)  # Belly
        ]

        # 2. Create a Masking Surface
        # Size is based on the fish's bounding box (approx 30z wide, 24z high)
        fish_surf = pygame.Surface((int(32 * z), int(26 * z)), pygame.SRCALPHA)

        # 3. Draw Body & Anatomy onto the Masking Surface
        pygame.draw.polygon(fish_surf, base_pearl, body_rel_pts)

        # Draw the Lateral Stripe (now masked)
        pygame.draw.lines(fish_surf, lateral_line_col, False, [(30 * z, 9 * z), (15 * z, 11 * z), (0 * z, 12 * z)],
                          int(1 * z))

        # 4. Generate Specks (Relative to Size)
        # We use the fish's hash so spots don't move frame-to-frame
        random.seed(hash(self) % 1000)
        num_specks = int(25 * z)  # More specks for larger fish
        for _ in range(num_specks):
            # Coordinates are local to the fish_surf
            sx = random.uniform(2 * z, 28 * z)
            sy = random.uniform(2 * z, 22 * z)
            s_size = random.uniform(0.5, 1.5) * z  # Speck size scales with fish size

            # Use BLEND_RGBA_MIN to ensure spots only appear where the body (alpha > 0) is
            # For simplicity, we just draw them and then 'sandwich' the mask
            pygame.draw.circle(fish_surf, spot_white, (int(sx), int(sy)), int(s_size))
        random.seed()

        # 5. Flip and Blit the masked body to the main screen
        if facing == -1:
            fish_surf = pygame.transform.flip(fish_surf, True, False)

        # Adjust blit position: if facing right, x is the nose (far right of surf)
        # We offset the blit so the nose stays at self.pos.x
        render_x = x - (30 * z if facing == 1 else 0)
        surface.blit(fish_surf, (render_x, y - 6 * z))

        # 6. Draw External Elements (Fins/Tail/Eye)
        # These are drawn outside the mask to allow for swaying/translucency
        t_sway = math.sin(pygame.time.get_ticks() * 0.008) * 3 * z
        tail_tip_x = x - 42 * z * facing
        t_pts = [
            (x - 30 * z * facing, y + 2 * z),
            (tail_tip_x, y - 3 * z + t_sway),
            (x - 36 * z * facing, y + 6 * z + t_sway),
            (tail_tip_x, y + 15 * z + t_sway),
            (x - 30 * z * facing, y + 10 * z)
        ]
        pygame.draw.polygon(surface, base_pearl, t_pts)

        # Eye stays fixed to the head
        eye_x = x - 3 * z * facing
        pygame.draw.circle(surface, (15, 15, 15), (int(eye_x), int(y + 3 * z)), int(2 * z))

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

        # Determine facing: 1 for Right, -1 for Left
        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        blue_front = self.get_depth_color((60, 120, 230))
        orange_back = self.get_depth_color((255, 150, 40))
        mid_glow = self.get_depth_color((180, 200, 255))

        # Points are defined relative to the nose (x, y + 5*z)
        # All X offsets are multiplied by 'facing' so the body always trails the nose
        nose = (x, y + 5 * z)
        top_back = (x - 10 * z * facing, y - 5 * z)
        tail_top = (x - 28 * z * facing, y + 2 * z)
        tail_bot = (x - 28 * z * facing, y + 10 * z)
        belly = (x - 12 * z * facing, y + 16 * z)

        pts = [nose, top_back, tail_top, tail_bot, belly]

        # 1. Draw Body (Orange Back)
        pygame.draw.polygon(surface, orange_back, pts)

        # 2. Blue Front Mask (Covers the front half)
        # We create a triangle/quad that covers the nose and midsection
        front_pts = [nose, top_back, (x - 15 * z * facing, y + 5 * z), belly]
        pygame.draw.polygon(surface, blue_front, front_pts)

        # 3. Shimmer Line
        shimmer_pts = [(x - 5 * z * facing, y + 6 * z), (x - 20 * z * facing, y + 6 * z)]
        pygame.draw.lines(surface, mid_glow, False, shimmer_pts, 1)

        # 4. Animated Tail Fin
        # The tail tip must also be behind the nose (x - 38*z*facing)
        tail_sway = math.sin(pygame.time.get_ticks() * 0.01) * 3 * z
        tail_tip_x = x - 38 * z * facing
        t_pts = [
            tail_top,
            (tail_tip_x, (tail_top[1] - 5 * z) + tail_sway),
            (tail_tip_x, (tail_bot[1] + 5 * z) + tail_sway),
            tail_bot
        ]
        pygame.draw.polygon(surface, orange_back, t_pts)

        # 5. Eye (Placed on the head, near the nose)
        eye_x = x - 4 * z * facing
        pygame.draw.circle(surface, (10, 10, 25), (int(eye_x), int(y + 4 * z)), int(2 * z))
        pygame.draw.circle(surface, (255, 255, 255), (int(eye_x + 1 * facing), int(y + 3 * z)), 1)

        # 6. Pectoral Fin
        pec_col = (200, 200, 255, 120)
        pec_surf = pygame.Surface((int(10 * z), int(6 * z)), pygame.SRCALPHA)
        pygame.draw.ellipse(pec_surf, pec_col, (0, 0, 8 * z, 4 * z))
        # Offset the fin slightly behind the eye
        surface.blit(pec_surf, (x - 10 * z * facing if facing == 1 else x + 2 * z, y + 8 * z))

def spawn_random_fish():
    choice = random.random()
    spawn_x = random.randint(50, SCREEN_WIDTH - 50)
    if choice < 0.4:        # 40% Neons
        return NeonTetra(spawn_x, 300)
    elif choice < 0.65:     # 25% Rainbowfish (Social & Curious)
        return BoesemaniRainbow(spawn_x, 200)
    elif choice < 0.85:     # 20% Cichlids
        return Cichlid(spawn_x, 500)
    else:                   # 15% Gouramis
        return PearlGourami(spawn_x, 100)


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
    bg_image = pygame.image.load(get_path('wallart.png')).convert()
    bg_image = pygame.transform.scale(bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error:
    print("Warning: wallart.png not found in 'doodads'. Using solid color.")
    bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    bg_image.fill((10, 20, 40))


fishes = [spawn_random_fish() for _ in range(30)]
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

        # 2. Layers (Fish/Plants)
        sorted_fishes = sorted(fishes, key=lambda f: f.z)
        for f in sorted_fishes:
            if f.z <= 0.9:
                if isinstance(f, (NeonTetra, Cichlid, PearlGourami)): f.behavior(fishes)
                f.update(pellets, algae)
                f.draw(screen)
        for p in plants: p.draw(screen, frame)
        for f in sorted_fishes:
            if f.z > 0.9:
                if isinstance(f, (NeonTetra, Cichlid, PearlGourami)): f.behavior(fishes)
                f.update(pellets, algae)
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