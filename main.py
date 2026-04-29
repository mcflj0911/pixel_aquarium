import pygame
import random
import math
import sys
import os

ASSET_PATH = "doodads"
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 600
SAND_HEIGHT = 60
WATER_TOP = 80
ALGAE_SPAWN_RATE = 65
MAX_HUNGER = 100

CLR_WATER_TOP = (40, 100, 180)
CLR_WATER_BOTTOM = (10, 30, 80)
CLR_SAND = (210, 185, 130)
CLR_ALGAE = (60, 180, 60)
CLR_FOOD = (150, 100, 50)

STATE_WELCOME = 0
STATE_AQUARIUM = 1
current_state = STATE_WELCOME


def get_path(filename):
    return os.path.join(ASSET_PATH, filename)


pygame.mixer.init()


class Plant:
    def __init__(self, x, species_type):
        self.pos_x = x
        self.species = species_type
        if species_type == "Vallisneria":
            self.segments = random.randint(15, 25)
            self.sway_speed = random.uniform(0.01, 0.02)
        elif species_type == "Anubias":
            self.segments = random.randint(4, 7)
            self.sway_speed = random.uniform(0.005, 0.01)
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
                pink_factor = i / self.segments
                r = int(60 * (1 - pink_factor) + (180 + self.tint) * pink_factor)
                g = int((140 + self.tint) * (1 - pink_factor) + 80 * pink_factor)
                b = int(60 * (1 - pink_factor) + 120 * pink_factor)
                leaf_col = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                stem_col = (max(0, min(255, r - 20)), max(0, min(255, g - 20)), max(0, min(255, b - 20)))

                prev_py = base_y - ((i - 1) * 10 * (0.8 + (1.0 - ((i - 1) / self.segments)) * 0.2)) if i > 0 else base_y
                pygame.draw.line(surface, stem_col, (px, py), (px, prev_py), 1)

                num_leaves = 6
                for j in range(num_leaves):
                    angle = (j * (math.pi * 2 / num_leaves)) + (i * 0.5)
                    length = 14 * taper + 4
                    lx, ly = px + math.cos(angle) * length, py + math.sin(angle) * (length * 0.3)
                    pygame.draw.line(surface, leaf_col, (px, py), (lx, ly), 1)
                    if i > self.segments * 0.6:
                        pygame.draw.circle(surface, (min(255, r + 30), g, b), (int(lx), int(ly)), 1)
                pygame.draw.circle(surface, stem_col, (int(px), int(py)), 2)

            elif self.species == "Ludwigia":
                red_val = max(0, min(255, 120 + (i * 10) + self.tint))
                green_val = max(0, min(255, 80 + self.tint))
                leaf_under, leaf_top = (red_val, 30, 40), (60, green_val, 30)
                stem_col = (max(0, red_val - 40), 60, 30)

                prev_py = base_y - ((i - 1) * 10 * (0.8 + (1.0 - ((i - 1) / self.segments)) * 0.2)) if i > 0 else base_y
                pygame.draw.line(surface, stem_col, (px, py), (px, prev_py), 2)

                lw, lh = 16 * taper + 6, 8 * taper + 4
                for side in [-1, 1]:
                    lx = px + (2 * side)
                    pygame.draw.ellipse(surface, leaf_under, (lx if side == 1 else lx - lw, py - lh // 2, lw, lh))
                    pygame.draw.ellipse(surface, leaf_top,
                                        (lx + 1 if side == 1 else lx - lw + 1, py - lh // 2 + 1, lw - 3, lh - 4))
                    pygame.draw.line(surface, (red_val, 80, 80), (lx, py), (lx + (lw - 2) * side, py), 1)

                if i == self.segments - 1:
                    pygame.draw.circle(surface, leaf_top, (int(px), int(py - 5)), int(4 * taper + 2))

            elif self.species == "Vallisneria":
                v_green = max(0, min(255, 90 + self.tint + (i * 2)))
                leaf_col, edge_col = (30, v_green, 40), (40, v_green + 30, 50)

                current_y, width = base_y - (i * 12), 10 * taper + 3
                final_px, final_py = px, py

                if current_y < WATER_TOP:
                    over_surface = WATER_TOP - current_y
                    trail_offset = over_surface * (1.2 + math.sin(frame * 0.02) * 0.2)
                    final_px, final_py = px + trail_offset, WATER_TOP

                pygame.draw.line(surface, leaf_col, (px, py), (final_px, final_py), int(width))
                if width > 4:
                    pygame.draw.line(surface, edge_col, (px - width // 3, py), (final_px - width // 3, final_py), 1)

                highlight_surf = pygame.Surface((int(width), 12), pygame.SRCALPHA)
                pygame.draw.rect(highlight_surf, (200, 255, 200, 40), (0, 0, int(width // 2), 12))
                surface.blit(highlight_surf, (final_px - width // 2, final_py))

            elif self.species == "Anubias":
                base_green = max(0, min(255, 40 + self.tint))
                mid_green, highlight = max(0, min(255, 60 + self.tint)), max(0, min(255, 100 + self.tint))
                stem_col = (max(0, base_green - 10), base_green, 10)

                pygame.draw.line(surface, stem_col, (self.pos_x, base_y), (px, py), 2)

                lw, lh = 22 * taper + 12, 14 * taper + 8
                if i >= 1:
                    leaf_surf = pygame.Surface((lw * 2, lh * 2), pygame.SRCALPHA)
                    pygame.draw.ellipse(leaf_surf, (20, base_green, 20), (lw // 2, lh // 2, lw, lh))
                    pygame.draw.ellipse(leaf_surf, (30, mid_green, 30), (lw // 2 + 2, lh // 2 + 1, lw - 4, lh - 2))
                    pygame.draw.circle(leaf_surf, (35, highlight, 35), (int(lw // 2 + 4), int(lh)), 3)
                    pygame.draw.line(leaf_surf, (10, 30, 10), (lw // 2 + 2, lh + lh // 2), (lw + lw // 2, lh + lh // 2),
                                     1)

                    rot_leaf = pygame.transform.rotate(leaf_surf, sway * 2 + (i * 10))
                    surface.blit(rot_leaf, (px - lw, py - lh))

                if i == 0:
                    pygame.draw.ellipse(surface, (40, 30, 20), (self.pos_x - 15, base_y - 5, 30, 12))
                    pygame.draw.ellipse(surface, (60, 50, 30), (self.pos_x - 12, base_y - 3, 24, 6))


class FoodPellet:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 1.2)

    def update(self):
        dune_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5 + math.cos(self.pos.x * 0.05) * 2
        if self.pos.y < dune_y:
            self.pos += self.vel

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
        # This formula dims the fish as it gets "deeper" (lower z)
        # Adjust 0.2 and 1.0 to match your new z range
        dim = 0.4 + (self.z * 0.6)

        # Clamp and cast to int to prevent ValueError
        r = max(0, min(255, int(base_color[0] * dim)))
        g = max(0, min(255, int(base_color[1] * dim)))
        b = max(0, min(255, int(base_color[2] * dim)))

        return (r, g, b)

    def apply_force(self, force):
        self.acc += force

    def update(self, pellets, algae):
        self.z += self.z_speed
        if self.z < 0.6 or self.z > 1.1:
            self.z_speed *= -1

        self.hunger += 0.05
        if self.hunger >= MAX_HUNGER:
            self.hunger = MAX_HUNGER
            self.health -= 0.1
            if self.health <= 0:
                self.alive = False

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
                        if p.pos == target_pos:
                            pellets.remove(p)
                            break
                else:
                    for a in algae:
                        if pygame.Vector2(a) == target_pos:
                            algae.remove(a)
                            break

        self.vel += self.acc
        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)
        self.pos += self.vel
        self.acc *= 0

        if self.pos.x < 0 or self.pos.x > SCREEN_WIDTH:
            self.vel.x *= -1
        if self.pos.y < WATER_TOP or self.pos.y > SCREEN_HEIGHT - SAND_HEIGHT:
            self.vel.y *= -1

        if random.random() < 0.005:
            bubbles.append(Bubble(self.pos.x, self.pos.y))

    def draw_shadow(self, surface, width):
        dune_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5 + math.cos(self.pos.x * 0.05) * 2
        s_col = (20, 20, 20, 70) if self.health > 30 else (80, 20, 20, 90)
        pygame.draw.ellipse(surface, s_col, (self.pos.x, dune_y, width * self.z, 5))


class NeonTetra(Fish):
    def __init__(self, x, y):
        super().__init__(x, random.randint(200, 400))

    def behavior(self, fishes):
        cohesion, alignment, separation, count = pygame.Vector2(0, 0), pygame.Vector2(0, 0), pygame.Vector2(0, 0), 0
        for other in fishes:
            if isinstance(other, NeonTetra) and other != self:
                dist = self.pos.distance_to(other.pos)
                if dist < 80:
                    cohesion += other.pos
                    alignment += other.vel
                    count += 1
                    if dist < 25:
                        diff = self.pos - other.pos
                        if diff.length() > 0:
                            separation += diff.normalize() / dist

        if count > 0:
            self.apply_force(((cohesion / count) - self.pos) * 0.03 + (alignment / count) * 0.05 + (separation * 0.8))

        mid_tank_y = (WATER_TOP + (SCREEN_HEIGHT - SAND_HEIGHT)) / 2
        dy = self.pos.y - mid_tank_y
        if abs(dy) > 80:
            self.apply_force(pygame.Vector2(0, -dy * 0.002))

        if random.random() < 0.005:
            self.apply_force(pygame.Vector2(random.uniform(-1, 1), random.uniform(-0.5, 0.5)) * 2.5)

        for other in fishes:
            if not isinstance(other, NeonTetra) and self.pos.distance_to(other.pos) < 50:
                self.apply_force((self.pos - other.pos).normalize() * 0.15)

    def draw(self, surface):
        self.draw_shadow(surface, 15)
        facing, x, y, z = (1 if self.vel.x >= 0 else -1), self.pos.x, self.pos.y, self.z

        pygame.draw.polygon(surface, self.get_depth_color((180, 185, 200)),
                            [(x, y), (x - 8 * z * facing, y - 3 * z), (x - 20 * z * facing, y),
                             (x - 8 * z * facing, y + 4 * z)])
        pygame.draw.line(surface, (200, 255, 255), (x - 4 * z * facing, y - 1 * z), (x - 18 * z * facing, y - 1 * z),
                         int(2 * z))
        pygame.draw.polygon(surface, (255, 30, 60), [(x - 12 * z * facing, y + 1 * z), (x - 20 * z * facing, y),
                                                     (x - 20 * z * facing, y + 3 * z),
                                                     (x - 12 * z * facing, y + 3 * z)])

        t_sway = math.sin(pygame.time.get_ticks() * 0.015) * 2 * z
        pygame.draw.polygon(surface, self.get_depth_color((180, 185, 200)),
                            [(x - 20 * z * facing, y), (x - 26 * z * facing, y - 4 * z + t_sway),
                             (x - 26 * z * facing, y + 4 * z + t_sway)])


class Cichlid(Fish):
    def __init__(self, x, y):
        bottom_y = random.randint(SCREEN_HEIGHT - 120, SCREEN_HEIGHT - SAND_HEIGHT - 10)
        super().__init__(x, bottom_y)
        self.territory, self.max_speed = pygame.Vector2(x, bottom_y), 2.8
        self.state, self.target_rival, self.sift_timer = "PATROL", None, 0

    def behavior(self, fishes):
        if self.state == "PATROL":
            if self.pos.distance_to(self.territory) > 150:
                self.apply_force((self.territory - self.pos) * 0.01)
            for o in fishes:
                if o != self and isinstance(o, Cichlid) and self.pos.distance_to(o.pos) < 100:
                    self.target_rival, self.state = o, "DEFEND"
                    return
            if random.random() < 0.005:
                self.state, self.sift_timer = "SIFT", 120
        elif self.state == "DEFEND":
            if not self.target_rival or not self.target_rival.alive or self.pos.distance_to(
                    self.target_rival.pos) > 200:
                self.target_rival, self.state = None, "PATROL"
            elif self.pos.distance_to(self.target_rival.pos) > 40:
                self.apply_force((self.target_rival.pos - self.pos).normalize() * 0.12)
            else:
                self.apply_force(pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)) + (
                            self.pos - self.target_rival.pos) * 0.05)
        elif self.state == "SIFT":
            target_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos.x * 0.02) * 5
            self.apply_force(pygame.Vector2(0, (target_y - 2 - self.pos.y) * 0.1))
            self.vel *= 0.9
            self.sift_timer -= 1
            if self.sift_timer <= 0:
                self.state = "PATROL"

        if self.pos.y < SCREEN_HEIGHT - 250:
            self.apply_force(pygame.Vector2(0, 0.15))

    def draw(self, surface):
        self.draw_shadow(surface, 26)
        facing, x, y, z = (1 if self.vel.x >= 0 else -1), self.pos.x, self.pos.y, self.z
        body_blue, dark_blue = self.get_depth_color((40, 120, 255)), self.get_depth_color((20, 40, 100))

        pygame.draw.polygon(surface, body_blue,
                            [(x, y + 4 * z), (x - 5 * z * facing, y - 4 * z), (x - 18 * z * facing, y - 2 * z),
                             (x - 28 * z * facing, y + 2 * z), (x - 28 * z * facing, y + 10 * z),
                             (x - 15 * z * facing, y + 14 * z)])
        for i in range(5):
            bar_x = x - (8 + i * 4) * z * facing
            pygame.draw.line(surface, dark_blue, (bar_x, y + (0 + abs(i - 2)) * z), (bar_x, y + (12 - abs(i - 2)) * z),
                             int(3 * z))

        d_pts = [(x - 6 * z * facing, y - 3 * z), (x - 24 * z * facing, y - 8 * z), (x - 28 * z * facing, y + 1 * z)]
        pygame.draw.polygon(surface, dark_blue, d_pts)
        pygame.draw.lines(surface, (150, 220, 255), False, d_pts, 1)

        t_sway = math.sin(pygame.time.get_ticks() * 0.012) * 4 * z
        pygame.draw.polygon(surface, dark_blue,
                            [(x - 28 * z * facing, y + 2 * z), (x - 36 * z * facing, y - 2 * z + t_sway),
                             (x - 36 * z * facing, y + 14 * z + t_sway), (x - 28 * z * facing, y + 10 * z)])
        pygame.draw.circle(surface, (0, 0, 0), (int(x - 4 * z * facing), int(y + 4 * z)), int(2 * z))


class PearlGourami(Fish):
    def __init__(self, x, y):
        top_y = random.randint(WATER_TOP + 40, WATER_TOP + 150)
        super().__init__(x, top_y)
        self.max_speed, self.target_y, self.is_gulping, self.inquiry_timer, self.look_target = 1.2, top_y, False, 0, None

    def behavior(self, fishes):
        if not self.is_gulping and random.random() < 0.002:
            self.is_gulping = True

        if self.is_gulping:
            self.apply_force(pygame.Vector2(0, (WATER_TOP + 5 - self.pos.y) * 0.05))
            if self.pos.y <= WATER_TOP + 10:
                self.is_gulping = False
        else:
            self.apply_force(pygame.Vector2(0, (self.target_y - self.pos.y) * 0.01))

        self.inquiry_timer -= 1
        if self.inquiry_timer <= 0:
            nearby = [f for f in fishes if f != self and self.pos.distance_to(f.pos) < 150]
            self.look_target = random.choice(nearby) if nearby else None
            self.inquiry_timer = random.randint(200, 500)

        if self.look_target:
            if self.pos.distance_to(self.look_target.pos) > 60:
                self.apply_force((self.look_target.pos - self.pos).normalize() * 0.02)
            else:
                self.vel *= 0.95

        if self.vel.length() > self.max_speed:
            self.vel *= 0.9

        if self.pos.x < 50 or self.pos.x > SCREEN_WIDTH - 50:
            self.apply_force(pygame.Vector2(-0.05 if self.pos.x > 50 else 0.05, 0))

    def draw(self, surface):
        self.draw_shadow(surface, 28)
        facing, x, y, z = (1 if self.vel.x >= 0 else -1), self.pos.x, self.pos.y, self.z
        base_pearl, throat_orange = self.get_depth_color((210, 210, 220)), self.get_depth_color((255, 130, 60))

        fish_surf = pygame.Surface((int(35 * z), int(40 * z)), pygame.SRCALPHA)
        x_off = 2 * z
        body_rel_pts = [(30 * z + x_off, 10 * z), (18 * z + x_off, 2 * z), (0 * z + x_off, 10 * z),
                        (0 * z + x_off, 18 * z), (18 * z + x_off, 26 * z)]
        pygame.draw.polygon(fish_surf, base_pearl, body_rel_pts)
        pygame.draw.polygon(fish_surf, throat_orange,
                            [(30 * z + x_off, 10 * z), (22 * z + x_off, 18 * z), (10 * z + x_off, 24 * z),
                             (25 * z + x_off, 12 * z)])
        pygame.draw.lines(fish_surf, (45, 45, 50), False,
                          [(30 * z + x_off, 11 * z), (15 * z + x_off, 13 * z), (0 * z + x_off, 14 * z)], int(1 * z))

        random.seed(hash(self) % 1000)
        for _ in range(int(30 * z)):
            sx, sy = random.uniform(4 * z, 28 * z) + x_off, random.uniform(4 * z, 24 * z)
            if fish_surf.get_at((int(sx), int(sy))).a > 0:
                pygame.draw.circle(fish_surf, (255, 255, 255, 180), (int(sx), int(sy)),
                                   int(random.uniform(0.5, 1.2) * z))
        random.seed()

        pygame.draw.ellipse(fish_surf, (200, 230, 255, 40), (5 * z + x_off, 2 * z, 20 * z, 10 * z))
        if facing == -1:
            fish_surf = pygame.transform.flip(fish_surf, True, False)
        surface.blit(fish_surf, (x - ((30 * z + x_off) if facing == 1 else (2 * z)), y - 10 * z))

        t_sway, f_sway = math.sin(pygame.time.get_ticks() * 0.008) * 3 * z, math.sin(
            pygame.time.get_ticks() * 0.005) * 5 * z
        pygame.draw.polygon(surface, base_pearl, [(x - 30 * z * facing, y), (x - 44 * z * facing, y - 5 * z + t_sway),
                                                  (x - 36 * z * facing, y + 4 * z + t_sway),
                                                  (x - 44 * z * facing, y + 13 * z + t_sway),
                                                  (x - 30 * z * facing, y + 8 * z)])
        pygame.draw.polygon(surface, throat_orange,
                            [(x - 12 * z * facing, y + 15 * z), (x - 28 * z * facing, y + 25 * z + f_sway),
                             (x - 32 * z * facing, y + 12 * z)])
        pygame.draw.circle(surface, (10, 10, 10), (int(x - 3 * z * facing), int(y + 1 * z)), int(2 * z))
        pygame.draw.line(surface, throat_orange, (x - 10 * z * facing, y + 12 * z),
                         (x - 22 * z * facing - (self.vel.x * 5), y + 32 * z + f_sway), 1)


class BoesemaniRainbow(Fish):
    def __init__(self, x, y):
        super().__init__(x, random.randint(WATER_TOP + 50, 350))
        self.max_speed, self.curiosity_target, self.curiosity_timer, self.z = 2.2, None, 0, random.uniform(0.7, 1.0)

    def behavior(self, fishes):
        avg_pos, count = pygame.Vector2(0, 0), 0
        for o in fishes:
            if isinstance(o, BoesemaniRainbow) and o != self and self.pos.distance_to(o.pos) < 120:
                avg_pos += o.pos
                count += 1
        if count > 0:
            self.apply_force(((avg_pos / count) - self.pos) * 0.02)

        self.curiosity_timer -= 1
        if self.curiosity_timer <= 0:
            if random.random() < 0.02:
                nearby = [f for f in fishes if f != self and self.pos.distance_to(f.pos) < 250]
                self.curiosity_target, self.curiosity_timer = (
                    random.choice(nearby) if nearby else None), random.randint(150, 400)
            else:
                self.curiosity_target = None

        if self.curiosity_target and self.curiosity_target.alive:
            dist = self.pos.distance_to(self.curiosity_target.pos)
            if dist > 50:
                self.apply_force((self.curiosity_target.pos - self.pos).normalize() * 0.07)
            elif dist < 30:
                self.apply_force((self.pos - self.curiosity_target.pos).normalize() * 0.09)

    def draw(self, surface):
        self.draw_shadow(surface, 22)
        facing, x, y, z = (1 if self.vel.x >= 0 else -1), self.pos.x, self.pos.y, self.z
        b_front, o_back, m_blend = self.get_depth_color((60, 110, 220)), self.get_depth_color(
            (255, 160, 40)), self.get_depth_color((120, 150, 180))

        body_pts = [(x, y + 5 * z), (x - 12 * z * facing, y - 6 * z), (x - 28 * z * facing, y + 2 * z),
                    (x - 28 * z * facing, y + 10 * z), (x - 14 * z * facing, y + 18 * z)]
        pygame.draw.polygon(surface, o_back, body_pts)
        pygame.draw.polygon(surface, m_blend,
                            [(x, y + 5 * z), (x - 12 * z * facing, y - 6 * z), (x - 20 * z * facing, y + 5 * z),
                             (x - 14 * z * facing, y + 18 * z)])
        pygame.draw.polygon(surface, b_front,
                            [(x, y + 5 * z), (x - 8 * z * facing, y - 3 * z), (x - 12 * z * facing, y + 5 * z),
                             (x - 8 * z * facing, y + 14 * z)])

        pygame.draw.polygon(surface, o_back, [(x - 15 * z * facing, y - 5 * z), (x - 25 * z * facing, y - 10 * z),
                                              (x - 27 * z * facing, y)])
        pygame.draw.polygon(surface, o_back, [(x - 12 * z * facing, y + 17 * z), (x - 26 * z * facing, y + 20 * z),
                                              (x - 28 * z * facing, y + 10 * z)])

        t_sway, tx = math.sin(pygame.time.get_ticks() * 0.015) * 4 * z, x - 38 * z * facing
        t_pts = [(x - 28 * z * facing, y + 2 * z), (tx, y - 4 * z + t_sway), (tx, y + 16 * z + t_sway),
                 (x - 28 * z * facing, y + 10 * z)]
        pygame.draw.polygon(surface, o_back, t_pts)
        pygame.draw.lines(surface, (255, 230, 150), False, t_pts[1:3], 1)

        for i in range(3):
            lx = x - (10 + i * 3) * z * facing
            pygame.draw.line(surface, (100, 180, 255, 100), (lx, y), (lx, y + 10 * z), 1)
        pygame.draw.circle(surface, (10, 10, 30), (int(x - 4 * z * facing), int(y + 4 * z)), int(2 * z))


class PeacockCichlid(Cichlid):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed, self.state, self.hunt_timer = 2.0, "HOVER", 0

    def behavior(self, fishes):
        if self.state == "HOVER":
            self.vel *= 0.8
            self.hunt_timer += 1
            if self.hunt_timer > 100:
                self.state, self.hunt_timer = "PATROL", 0
        elif self.state == "PATROL":
            if random.random() < 0.01:
                self.state = "HOVER"
            super().behavior(fishes)

    def draw(self, surface):
        self.draw_shadow(surface, 28)
        facing, x, y, z = (1 if self.vel.x >= 0 else -1), self.pos.x, self.pos.y, self.z
        e_blue, f_red = self.get_depth_color((40, 110, 255)), self.get_depth_color((200, 50, 40))

        fish_surf = pygame.Surface((int(42 * z), int(32 * z)), pygame.SRCALPHA)
        x_off = 5 * z
        body_rel_pts = [(35 * z + x_off, 12 * z), (25 * z + x_off, 4 * z), (10 * z + x_off, 6 * z),
                        (0 * z + x_off, 12 * z), (0 * z + x_off, 20 * z), (15 * z + x_off, 28 * z)]
        pygame.draw.polygon(fish_surf, e_blue, body_rel_pts)
        pygame.draw.ellipse(fish_surf, f_red, (20 * z + x_off, 8 * z, 12 * z, 14 * z))

        random.seed(hash(self) % 1000)
        for i in range(6):
            pygame.draw.line(fish_surf, (20, 40, 100, 80), ((6 + i * 4) * z + x_off, 8 * z),
                             ((6 + i * 4) * z + x_off, 22 * z), int(2 * z))
        for _ in range(int(20 * z)):
            sx, sy = random.uniform(5 * z, 30 * z) + x_off, random.uniform(8 * z, 24 * z)
            if fish_surf.get_at((int(sx), int(sy))).a > 0:
                pygame.draw.circle(fish_surf, (180, 230, 255, 70), (int(sx), int(sy)), 1)
        random.seed()

        if facing == -1:
            fish_surf = pygame.transform.flip(fish_surf, True, False)
        surface.blit(fish_surf, (x - ((35 * z + x_off) if facing == 1 else (2 * z)), y - 12 * z))

        f_sway = math.sin(pygame.time.get_ticks() * 0.01) * 3 * z
        d_pts = [(x - 28 * z * facing, y - 5 * z), (x - 12 * z * facing, y - 14 * z + f_sway),
                 (x - 4 * z * facing, y - 2 * z)]
        pygame.draw.polygon(surface, e_blue, d_pts)
        pygame.draw.lines(surface, (200, 240, 255), False, d_pts[:2], 2)

        a_pts = [(x - 26 * z * facing, y + 16 * z + f_sway), (x - 10 * z * facing, y + 14 * z),
                 (x - 24 * z * facing, y + 8 * z)]
        pygame.draw.polygon(surface, f_red, a_pts)
        for i in range(3):
            pygame.draw.circle(surface, (255, 200, 50), (int(x - (16 + i * 4) * z * facing), int(y + 12 * z + f_sway)),
                               int(1.2 * z))

        t_sway, tx = math.sin(pygame.time.get_ticks() * 0.012) * 5 * z, x - 46 * z * facing
        pygame.draw.polygon(surface, e_blue,
                            [(x - 28 * z * facing, y), (tx, y - 6 * z + t_sway), (tx, y + 16 * z + t_sway),
                             (x - 28 * z * facing, y + 8 * z)])
        pygame.draw.circle(surface, (10, 10, 10), (int(x - 6 * z * facing), int(y + 3 * z)), int(2.5 * z))
        pygame.draw.circle(surface, (255, 200, 0), (int(x - 6 * z * facing), int(y + 3 * z)), int(2.5 * z), 1)


class SocialFlowerhorn(Fish):
    population = 0

    def __init__(self, x, y):
        SocialFlowerhorn.population += 1
        super().__init__(x, y)
        self.target_friend, self.z, self.max_speed, self.state, self.angle, self.lerp_speed, self.wiggle_energy = None, random.uniform(
            0.1, 0.5), 2.2, "IDLE", 0.0, 0.1, 0.0
        self.aggression, self.energy, self.burst_timer, self.kok_scale = random.uniform(0.3, 1.0), random.uniform(0.5,
                                                                                                                  1.0), 0, random.uniform(
            0.6, 1.0)
        self.base_color = (random.randint(200, 255), random.randint(20, 80), random.randint(40, 100))

    def behavior(self, fishes):
        m_pos = pygame.Vector2(pygame.mouse.get_pos())
        self.burst_timer -= 1
        if self.pos.distance_to(m_pos) < 300:
            self.state, desired = "INTERACT", (m_pos - self.pos).normalize()
            self.apply_force(desired * 0.12)
            self.wiggle_energy = min(1.0, self.wiggle_energy + 0.06)
            if self.burst_timer <= 0 and random.random() < 0.02:
                self.vel += desired * 2.5
                self.burst_timer = random.randint(40, 100)
        else:
            self.state, self.wiggle_energy = "SOCIALIZE", self.wiggle_energy * 0.94
            if not self.target_friend or random.random() < 0.01:
                others = [f for f in fishes if f != self]
                if others:
                    self.target_friend = random.choice(others)
            if self.target_friend:
                off = self.target_friend.pos - self.pos
                if off.length() > 120:
                    self.apply_force(off.normalize() * 0.035)
                elif off.length() < 60:
                    self.apply_force(-off.normalize() * 0.04)

        for f in fishes:
            if f != self and 0 < self.pos.distance_to(f.pos) < 40:
                self.apply_force((self.pos - f.pos).normalize() * 0.05)

        if self.vel.length() > 0.1:
            self.angle += (math.degrees(math.atan2(-self.vel.y, abs(self.vel.x))) - self.angle) * self.lerp_speed

    def draw(self, surface):
        self.draw_shadow(surface, 60)
        z = self.z
        # Ensure dimensions are integers
        surf_w, surf_h = int(280 * z), int(280 * z)
        fish_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2

        t = pygame.time.get_ticks() * (0.004 + self.wiggle_energy * 0.01)
        tm, fw = math.sin(t) * (12 * z + self.wiggle_energy * 10), math.cos(t * 0.8) * 6 * z

        # Ensure p_col elements are integers
        p_col = (
            min(255, int(self.base_color[0] + 100)),
            min(255, int(self.base_color[1] + 100)),
            min(255, int(self.base_color[2] + 100)),
            150
        )

        def draw_fin(pts, alpha):
            f_s = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            # Cast color to integers for safety
            color = tuple(int(c) for c in self.base_color[:3])
            pygame.draw.polygon(f_s, (*color, alpha), pts)
            for p in pts[1:]:
                pygame.draw.line(f_s, (int(p_col[0]), int(p_col[1]), int(p_col[2]), 40), pts[0], p, max(1, int(2 * z)))
            pygame.draw.aalines(f_s, (*color, 180), False, pts)
            fish_surf.blit(f_s, (0, 0))

        draw_fin([(cx - 20 * z, cy - 30 * z), (cx - 60 * z, cy - 90 * z + fw), (cx - 120 * z, cy - 70 * z + tm),
                  (cx - 70 * z, cy - 10 * z)], 120)
        draw_fin([(cx - 20 * z, cy + 30 * z), (cx - 60 * z, cy + 90 * z - fw), (cx - 120 * z, cy + 70 * z + tm),
                  (cx - 70 * z, cy + 10 * z)], 120)

        body_mask = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        for p, s in [((cx - 10 * z, cy), (140 * z, 105 * z)), ((cx + 40 * z, cy), (90 * z, 95 * z)),
                     ((cx - 60 * z, cy + 5 * z), (110 * z, 75 * z))]:
            r = pygame.Rect(0, 0, int(s[0]), int(s[1]))  # Ensure Rect sizes are ints
            r.center = (int(p[0]), int(p[1]))
            pygame.draw.ellipse(body_mask, (255, 255, 255), r)

        render_s = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # CRITICAL FIX: Cast get_depth_color output to integers and clamp 0-255
        depth_col = self.get_depth_color(self.base_color)
        safe_col = tuple(max(0, min(255, int(c))) for c in depth_col)
        render_s.fill(safe_col)

        pygame.draw.ellipse(render_s, p_col, (int(cx - 50 * z), int(cy - 60 * z), int(130 * z), int(60 * z)))
        pygame.draw.ellipse(render_s, (255, 255, 255, 80),
                            (int(cx - 40 * z), int(cy + 10 * z), int(100 * z), int(50 * z)))
        render_s.blit(body_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        fish_surf.blit(render_s, (0, 0))

        for i in range(5):
            sx, sy, ss = cx - 60 * z + (i * 25 * z), cy + math.sin(t + i) * 2 * z, (12 * z - i * z)
            pygame.draw.circle(fish_surf, (20, 20, 20, 200), (int(sx), int(sy)), int(ss))
            pygame.draw.circle(fish_surf, (255, 255, 255, 100), (int(sx), int(sy)), int(ss + 2 * z), 1)

        kr = pygame.Rect(0, 0, int(70 * z * self.kok_scale), int(60 * z * self.kok_scale))
        kr.center = (int(cx + 55 * z), int(cy - 45 * z))
        pygame.draw.ellipse(fish_surf, (230, 50, 50), kr)
        pygame.draw.ellipse(fish_surf, (255, 100, 100, 150), kr.inflate(int(-10 * z), int(-15 * z)))

        ex, ey = int(cx + 80 * z), int(cy - 5 * z)
        pygame.draw.circle(fish_surf, (50, 0, 0), (ex, ey), int(10 * z))
        pygame.draw.circle(fish_surf, (255, 50, 0), (ex, ey), int(8 * z))
        pygame.draw.circle(fish_surf, (0, 0, 0), (ex, ey), int(5 * z))
        pygame.draw.circle(fish_surf, (255, 255, 255, 200), (int(ex + 3), int(ey - 3)), int(2 * z))

        draw_fin([(cx - 90 * z, cy), (cx - 180 * z, cy - 80 * z + tm), (cx - 210 * z, cy + tm * 0.5),
                  (cx - 180 * z, cy + 80 * z + tm), (cx - 90 * z, cy + 20 * z)], 150)

        fr = self.vel.x >= 0
        final = pygame.transform.flip(fish_surf, True, False) if not fr else fish_surf
        rotated = pygame.transform.rotate(final, self.angle if fr else -self.angle)
        surface.blit(rotated, rotated.get_rect(center=(int(self.pos.x), int(self.pos.y))))


class MajesticBetta(Fish):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 1.0
        self.flare_timer = 0
        self.is_flaring = False
        self.color_shift = random.uniform(0, 100)
        self.z = random.uniform(0.2, 0.6)

    def behavior(self, fishes):
        m_pos = pygame.Vector2(pygame.mouse.get_pos())
        dist = self.pos.distance_to(m_pos)
        if dist < 250:
            self.apply_force((m_pos - self.pos).normalize() * 0.08)
            if dist < 120:
                self.is_flaring = True
                self.flare_timer = 40
        if self.flare_timer > 0:
            self.flare_timer -= 1
            self.vel *= 0.85
        else:
            self.is_flaring = False
            if random.random() < 0.01:
                self.apply_force(pygame.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)))

    def draw(self, surface):
        self.draw_shadow(surface, 35)
        facing, x, y, z = (1 if self.vel.x >= 0 else -1), self.pos.x, self.pos.y, self.z

        # 1. Metallic Platinum Color Logic
        time_ms = pygame.time.get_ticks()
        t = time_ms * 0.002 + self.color_shift
        # High base brightness for that "Platinum" look
        bright = int(220 + 35 * math.sin(t))
        # Subtle blue/cyan shift for iridescence
        r = max(0, min(255, bright - 10))
        g = max(0, min(255, bright))
        b = max(0, min(255, bright + 15))

        base_col = self.get_depth_color((r, g, b))
        flare_mod = 1.3 if self.is_flaring else 1.0  # Plakats have stiffer, shorter flares
        sway = math.sin(time_ms * 0.006) * 6 * z  # Faster, tighter wiggle for short fins

        # 2. Transparent Fin Rendering
        fin_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        def draw_plakat_fin(origin, width, height, color, alpha, upward=True, is_tail=False):
            steps = 10
            pts = [origin]
            dir_y = -1 if upward else 1

            for i in range(steps + 1):
                pct = i / steps
                # Plakat fins are more rounded and spade-like
                if is_tail:
                    angle = (pct - 0.5) * math.pi * (1.6 * flare_mod)
                    px = origin[0] - (width * math.cos(angle) * facing)
                    py = origin[1] + (height * math.sin(angle))
                else:
                    px = origin[0] - (width * pct * facing)
                    # Rounding the dorsal/anal fins
                    py = origin[1] + (height * math.sin(pct * math.pi) * dir_y * flare_mod)

                pts.append((int(px), int(py + (sway * pct * 0.5))))

            pts.append((int(origin[0] - (width * 0.1 * facing)), int(origin[1])))

            # Platinum fins often have a white/transparent edge
            c = (*[max(0, min(255, int(c))) for c in color], alpha)
            pygame.draw.polygon(fin_surf, c, pts)
            pygame.draw.aalines(fin_surf, (255, 255, 255, 200), False, pts[1:-1])

        # 3. Render Fins (Plakat Style: Short & Stout)
        # Dorsal (Top) - Smaller and rounded
        draw_plakat_fin((int(x - 8 * z * facing), int(y + 2 * z)), 35 * z, 30 * z, (r, g, b), 200, True)
        # Anal (Bottom) - Runs along the back half
        draw_plakat_fin((int(x - 12 * z * facing), int(y + 14 * z)), 50 * z, 35 * z, (r, g, b), 200, False)
        # Caudal (Tail) - Strong spade/D-shape
        draw_plakat_fin((int(x - 24 * z * facing), int(y + 8 * z)), 45 * z, 40 * z, (r, g, b), 220, True, True)

        surface.blit(fin_surf, (0, 0))

        # 4. Metallic Body
        bw, bh = 45 * z, 18 * z  # Plakats have thicker, more muscular bodies
        bx = x - bw if facing == 1 else x
        body_rect = pygame.Rect(int(bx + (12 * z if facing == 1 else 0)), int(y), int(bw), int(bh))
        pygame.draw.ellipse(surface, base_col, body_rect)

        # Specular Highlight (The "Platinum" Shine)
        shine_col = (255, 255, 255, 120)
        shine_rect = pygame.Rect(int(bx + (15 * z if facing == 1 else 5 * z)), int(y + 3 * z), int(25 * z), int(6 * z))
        shine_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(shine_surf, shine_col, shine_rect)
        surface.blit(shine_surf, (0, 0))

        # 5. Face & Eye
        snout_x = x + (6 * z if facing == 1 else -6 * z)
        pygame.draw.circle(surface, base_col, (int(snout_x), int(y + 9 * z)), int(8 * z))

        eye_x = x + (5 * z if facing == 1 else -5 * z)
        pygame.draw.circle(surface, (20, 20, 20), (int(eye_x), int(y + 8 * z)), int(4 * z))
        pygame.draw.circle(surface, (255, 255, 255), (int(eye_x - 1 * facing), int(y + 7 * z)), 1)

        # Large "Platty" Pectoral Fin
        pec_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(pec_surf, (255, 255, 255, 180), [
            (int(x - 2 * z * facing), int(y + 11 * z)),
            (int(x - 18 * z * facing), int(y + 18 * z + sway * 0.3)),
            (int(x - 6 * z * facing), int(y + 22 * z))
        ])
        surface.blit(pec_surf, (0, 0))

def spawn_random_fish(fishes=[]):
    choice, sx = random.random(), random.randint(50, SCREEN_WIDTH - 50)
    if choice < 0.05:
        return SocialFlowerhorn(sx, random.randint(200, 400))
    elif choice < 0.35:
        return NeonTetra(sx, random.randint(250, 450))
    elif choice < 0.45:
        return MajesticBetta(sx, random.randint(250, 450))
    elif choice < 0.55:
        return BoesemaniRainbow(sx, random.randint(150, 300))
    elif choice < 0.70:
        return Cichlid(sx, SCREEN_HEIGHT - 150)
    elif choice < 0.85:
        return PeacockCichlid(sx, SCREEN_HEIGHT - 160)
    else:
        return PearlGourami(sx, 120)


pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

try:
    splash_img = pygame.transform.scale(pygame.image.load(get_path('splash.png')).convert(),
                                        (SCREEN_WIDTH, SCREEN_HEIGHT))
except:
    splash_img = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    splash_img.fill((20, 40, 80))


def draw_welcome_screen():
    screen.blit(splash_img, (0, 0))
    bw, bh = 240, 60
    bx, by = (SCREEN_WIDTH // 2) - (bw // 2), (SCREEN_HEIGHT // 2) + 100
    m_pos = pygame.mouse.get_pos()
    br = pygame.Rect(bx, by, bw, bh)
    col = (60, 160, 240) if br.collidepoint(m_pos) else (40, 100, 200)
    pygame.draw.rect(screen, col, br, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), br, 2, border_radius=15)
    txt = pygame.font.SysFont("Arial", 32, bold=True).render("WELCOME", True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=br.center))
    return br


try:
    pygame.mixer.music.load(get_path('bgmusic.mp3'))
    pygame.mixer.music.play(-1)
    pygame.mixer.music.set_volume(0.5)
except:
    pass

bg_files, bg_index = ["wallart.png", "wallart2.png", "wallart3.png", "wallart4.png","wallart5.png","wallart6.png"], 0
try:
    bg_image = pygame.transform.scale(pygame.image.load(get_path(bg_files[bg_index])), (SCREEN_WIDTH, SCREEN_HEIGHT))
except:
    bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    bg_image.fill((10, 20, 40))

fishes = [spawn_random_fish() for _ in range(30)]
auto_feed_timer = random.randint(100, 300)
plants = [Plant(x, random.choice(["Rotala", "Ludwigia", "Vallisneria", "Anubias"])) for x in
          range(40, SCREEN_WIDTH, 60)]
grains = [(random.randint(0, SCREEN_WIDTH), random.randint(540, 600), random.choice([(190, 170, 110), (225, 200, 140)]))
          for _ in range(600)]
algae, pellets, bubbles, frame = [], [], [], 0

caustic_beams = [
    [random.randint(0, SCREEN_WIDTH), random.randint(20, 60), random.uniform(0.5, 1.5), random.uniform(0, 2 * math.pi)]
    for _ in range(8)]

while True:
    if current_state == STATE_WELCOME:
        br = draw_welcome_screen()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and br.collidepoint(e.pos):
                current_state = STATE_AQUARIUM
    else:
        screen.blit(bg_image, (0, 0))
        bg_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(SCREEN_HEIGHT):
            r = int(CLR_WATER_TOP[0] * (1 - y / SCREEN_HEIGHT) + CLR_WATER_BOTTOM[0] * y / SCREEN_HEIGHT)
            g = int(CLR_WATER_TOP[1] * (1 - y / SCREEN_HEIGHT) + CLR_WATER_BOTTOM[1] * y / SCREEN_HEIGHT)
            b = int(CLR_WATER_TOP[2] * (1 - y / SCREEN_HEIGHT) + CLR_WATER_BOTTOM[2] * y / SCREEN_HEIGHT)
            pygame.draw.line(bg_s, (r, g, b, 150), (0, y), (SCREEN_WIDTH, y))
        screen.blit(bg_s, (0, 0))

        s_pts = [(x, 540 + math.sin(x * 0.02) * 5 + math.cos(x * 0.05) * 2) for x in range(0, SCREEN_WIDTH + 11, 10)]
        pygame.draw.polygon(screen, CLR_SAND, s_pts + [(SCREEN_WIDTH, SCREEN_HEIGHT), (0, SCREEN_HEIGHT)])
        for gx, gy, col in grains:
            if gy > 540 + math.sin(gx * 0.02) * 5 + math.cos(gx * 0.05) * 2:
                pygame.draw.rect(screen, col, (gx, gy, 2, 2))

        auto_feed_timer -= 1
        if auto_feed_timer <= 0:
            if len(pellets) < 15:
                pellets.append(FoodPellet(random.randint(50, SCREEN_WIDTH - 50), WATER_TOP))
            auto_feed_timer = random.randint(120, 420)

        for f in fishes[:]:
            f.behavior(fishes)
            f.update(pellets, algae)
            if not f.alive:
                fishes.remove(f)
                fishes.append(spawn_random_fish(fishes))

        sorted_f = sorted(fishes, key=lambda f: f.z)
        for f in sorted_f:
            if f.z <= 0.9:
                f.draw(screen)
        for p in plants:
            p.draw(screen, frame)
        for f in sorted_f:
            if f.z > 0.9:
                f.draw(screen)

        cs = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for b in caustic_beams:
            b[0] = b[0] + b[2] if b[0] < SCREEN_WIDTH + 100 else -100
            p = math.sin(frame * 0.02 + b[3]) * 10 + 15
            pts = [(b[0] + math.sin(cy * 0.005 + frame * 0.03) * 15, cy) for cy in range(0, SCREEN_HEIGHT + 21, 40)]
            if len(pts) > 1:
                pygame.draw.lines(cs, (255, 255, 230, int(p)), False, pts, b[1])
        screen.blit(cs, (0, 0))

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_b:
                    bg_index = (bg_index + 1) % len(bg_files)
                    try:
                        bg_image = pygame.transform.scale(pygame.image.load(get_path(bg_files[bg_index])),
                                                          (SCREEN_WIDTH, SCREEN_HEIGHT))
                    except:
                        pass
                if e.key == pygame.K_r:
                    current_state, frame = STATE_WELCOME, 0
                    fishes = [spawn_random_fish() for _ in range(30)]
                    algae.clear()
                    pellets.clear()
                    bubbles.clear()
            if e.type == pygame.MOUSEBUTTONDOWN:
                pellets.append(FoodPellet(*e.pos))

        if frame % ALGAE_SPAWN_RATE == 0 and len(algae) < 35:
            algae.append((random.randint(10, SCREEN_WIDTH - 10), random.randint(100, 500)))

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

        l_s = pygame.Surface((SCREEN_WIDTH, 120), pygame.SRCALPHA)
        for y in range(120):
            pygame.draw.line(l_s, (255, 255, 220, max(0, 100 - y)), (0, y), (SCREEN_WIDTH, y))
        screen.blit(l_s, (0, 0))

    pygame.display.flip()
    clock.tick(60)
    frame += 1