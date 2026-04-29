import pygame
import random
import math
import sys
import os

is_muted = False
pygame.init()
info = pygame.display.Info()
ASSET_PATH = "doodads"
SCREEN_WIDTH = info.current_w - 300
SCREEN_HEIGHT = 600
SAND_HEIGHT = 40
WATER_TOP = 80
ALGAE_SPAWN_RATE = 30
MAX_HUNGER = 100

CLR_WATER_TOP = (40, 100, 180)
CLR_WATER_BOTTOM = (10, 30, 80)
CLR_SAND = (210, 185, 130)
CLR_ALGAE = (60, 180, 60)
CLR_FOOD = (150, 100, 50)

STATE_WELCOME = 0
STATE_AQUARIUM = 1
current_state = STATE_WELCOME

LIGHT_MODES = [
    {"name": "LED RGB WHITE", "color": (255, 255, 255, 0)},
    {"name": "WARM WHITE",    "color": (255, 240, 200, 30)},
    {"name": "WARM",          "color": (255, 200, 100, 60)},
    {"name": "COOL",          "color": (150, 200, 255, 40)},
    {"name": "DEEP AMAZON",   "color": (100, 65, 20, 70)},
    {"name": "MOONLIGHT",     "color": (10, 20, 80, 110)},
    {"name": "PLANTED GROW",  "color": (255, 100, 255, 25)},
    {"name": "ACTINIC",       "color": (0, 0, 255, 50)},
    {"name": "SUNSET GOLD",   "color": (255, 140, 0, 45)},
    {"name": "MILD GREEN",    "color": (150, 255, 180, 35)},
    {"name": "RGB STROBE",    "color": (0, 0, 0, 0)}
]
current_light_idx = 0
light_notif_text = ""
light_notif_alpha = 0

def get_path(filename):
    return os.path.join(ASSET_PATH, filename)


pygame.mixer.init()


class Pebble:
    def __init__(self):
        self.z = random.uniform(0.7, 1.2)
        self.pos_x = random.randint(0, SCREEN_WIDTH)

        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + \
                      math.sin(self.pos_x * 0.02) * 5 + \
                      math.cos(self.pos_x * 0.05) * 2

        try:
            original_img = pygame.image.load(get_path('pebble.png')).convert_alpha()
            size_var = random.uniform(0.05, 0.12)
            width = int(original_img.get_width() * self.z * size_var)
            height = int(original_img.get_height() * self.z * size_var)
            self.image = pygame.transform.scale(original_img, (width, height))

            if random.random() > 0.5:
                self.image = pygame.transform.flip(self.image, True, random.random() > 0.5)
        except:
            self.image = pygame.Surface((int(6 * self.z), int(4 * self.z)), pygame.SRCALPHA)
            pygame.draw.ellipse(self.image, (100, 102, 105), self.image.get_rect())

    def draw(self, surface):
        sink = int(8 * self.z)
        rect = self.image.get_rect(midbottom=(self.pos_x, int(self.base_y + sink)))

        temp_img = self.image.copy()

        shade = 0.4 + (self.z - 0.7) * (0.6 / 0.5)
        shade = max(0.3, min(1.0, shade))

        temp_img.fill((int(255 * shade), int(255 * shade), int(255 * shade)),
                      special_flags=pygame.BLEND_RGB_MULT)

        surface.blit(temp_img, rect)

def create_pebbles(count=40):
    new_pebbles = [Pebble() for _ in range(count)]
    return sorted(new_pebbles, key=lambda p: p.z)


class Rock:
    def __init__(self, x=None, z=None, y_offset=0):
        self.z = z if z is not None else random.uniform(0.7, 1.2)
        self.pos_x = x if x is not None else random.randint(0, SCREEN_WIDTH)

        self.base_y = (SCREEN_HEIGHT - SAND_HEIGHT) + math.sin(self.pos_x * 0.02) * 5 + math.cos(self.pos_x * 0.05) * 2
        self.y_offset = y_offset

        try:
            original_img = pygame.image.load(get_path('rock.png')).convert_alpha()
            size_mod = 0.25 if y_offset == 0 else 0.2
            width = int(original_img.get_width() * self.z * size_mod)
            height = int(original_img.get_height() * self.z * size_mod)

            if y_offset < -20:
                height = int(height * 0.7)

            self.image = pygame.transform.scale(original_img, (width, height))
            if random.random() > 0.5:
                self.image = pygame.transform.flip(self.image, True, False)
        except:
            self.image = pygame.Surface((int(30 * self.z), int(20 * self.z)), pygame.SRCALPHA)
            pygame.draw.ellipse(self.image, (70, 72, 75), self.image.get_rect())

    def draw(self, surface):
        sink = int(35 * self.z) if self.y_offset >= 0 else 0
        rect = self.image.get_rect(midbottom=(self.pos_x, int(self.base_y + self.y_offset + sink)))

        temp_img = self.image.copy()

        shade = 0.3 + (self.z - 0.7) * (0.7 / 0.5)
        shade = max(0.2, min(1.0, shade))

        temp_img.fill((int(255 * shade), int(255 * shade), int(255 * shade)),
                      special_flags=pygame.BLEND_RGB_MULT)

        surface.blit(temp_img, rect)

def create_hardscape():
    new_rocks = []
    for _ in range(2):
        cx = random.randint(200, SCREEN_WIDTH - 200)
        cz = random.uniform(0.7, 1.2)

        cave_w = random.randint(100, 150)
        cave_h = random.randint(60, 100)

        for i in range(3):
            new_rocks.append(Rock(cx - cave_w // 2 + random.randint(-10, 10), cz, y_offset=-(i * 25)))

        for i in range(3):
            new_rocks.append(Rock(cx + cave_w // 2 + random.randint(-10, 10), cz, y_offset=-(i * 25)))

        num_roof_rocks = 4
        for i in range(num_roof_rocks):
            t = (i + 1) / (num_roof_rocks + 1)
            rx = cx - cave_w // 2 + (cave_w * t)

            ry = -cave_h * (1 - 4 * (t - 0.5) ** 2)
            new_rocks.append(Rock(rx + random.randint(-15, 15), cz, y_offset=int(ry - 40)))

    for _ in range(10):
        new_rocks.append(Rock())

    return sorted(new_rocks, key=lambda r: (r.z, -r.y_offset))

class Snail:
    def __init__(self):
        self.pos = pygame.Vector2(random.randint(50, SCREEN_WIDTH - 50), random.randint(WATER_TOP + 50, SCREEN_HEIGHT - 100))
        self.vel = pygame.Vector2(random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))
        self.size = 12
        self.trail = []
        self.target_algae = None

    def update(self, algae_list):
        self.trail.append(list(self.pos))
        if len(self.trail) > 40:
            self.trail.pop(0)

        if not self.target_algae and algae_list:
            nearby = [a for a in algae_list if self.pos.distance_to(pygame.Vector2(a)) < 120]
            if nearby:
                self.target_algae = nearby[0]

        if self.target_algae:
            direction = (pygame.Vector2(self.target_algae) - self.pos)
            if direction.length() > 2:
                self.pos += direction.normalize() * 0.3
            else:
                if self.target_algae in algae_list:
                    algae_list.remove(self.target_algae)
                self.target_algae = None
        else:
            self.pos += self.vel
            if random.random() < 0.01:
                self.vel = pygame.Vector2(random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))

        if self.pos.x < 10 or self.pos.x > SCREEN_WIDTH - 10: self.vel.x *= -1
        if self.pos.y < WATER_TOP + 10 or self.pos.y > SCREEN_HEIGHT - 30: self.vel.y *= -1

    def draw(self, surface):
        if len(self.trail) > 1:
            trail_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.lines(trail_surf, (200, 200, 255, 30), False, self.trail, 2)
            surface.blit(trail_surf, (0, 0))

        shell_col = (140, 110, 80)
        pygame.draw.ellipse(surface, shell_col, (self.pos.x - 8, self.pos.y - 6, 16, 12))
        pygame.draw.ellipse(surface, (210, 200, 160), (self.pos.x - 10, self.pos.y + 2, 14, 6))
        pygame.draw.line(surface, (210, 200, 160), (self.pos.x + 2, self.pos.y + 2), (self.pos.x + 6, self.pos.y - 4), 1)
        pygame.draw.line(surface, (210, 200, 160), (self.pos.x + 4, self.pos.y + 2), (self.pos.x + 8, self.pos.y - 2), 1)



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

        if random.random() < 0.002:
            bubbles.append(Bubble(self.pos_x, base_y))

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

            elif self.species == "TigerLotus":
                pulse = math.sin(frame * 0.05) * 15
                r = max(0, min(255, 160 + self.tint + pulse))
                g = max(0, min(255, 40 + self.tint // 2))
                b = max(0, min(255, 60 + self.tint))

                leaf_col = (r, g, b)
                mottle_col = (max(0, r - 60), max(0, g - 20), max(0, b - 20))
                stem_col = (max(0, r - 80), 30, 40)

                prev_py = base_y - ((i - 1) * 12) if i > 0 else base_y
                prev_px = self.pos_x + math.sin(frame * self.sway_speed + self.sway_offset + ((i - 1) * 0.2)) * (
                            (i - 1) ** 1.5) * 0.8 if i > 0 else self.pos_x
                pygame.draw.line(surface, stem_col, (px, py), (prev_px, prev_py), 2)

                lw, lh = (20 * (1 - taper) + 15), (12 * (1 - taper) + 8)

                leaf_surf = pygame.Surface((lw * 2, lh * 2), pygame.SRCALPHA)

                pygame.draw.ellipse(leaf_surf, (*leaf_col, 210), (0, 0, lw * 2, lh * 2))

                for s in range(3):
                    dot_x = random.Random(i + s).randint(int(lw * 0.5), int(lw * 1.5))
                    dot_y = random.Random(i + s).randint(int(lh * 0.5), int(lh * 1.5))
                    pygame.draw.circle(leaf_surf, (*mottle_col, 150), (dot_x, dot_y), int(3 * (1 - taper) + 2))

                rot_angle = (i * 45) + (sway * 2)
                final_leaf = pygame.transform.rotate(leaf_surf, rot_angle)

                surface.blit(final_leaf, (px - final_leaf.get_width() // 2, py - final_leaf.get_height() // 2))

                if i == self.segments - 1:
                    shine_rect = (px - 5, py - 5, 10, 5)
                    pygame.draw.ellipse(surface, (255, 255, 255, 100), shine_rect)

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
        self.hunger = 0.0
        self.id = random.randint(1000, 9999)
        self.health = 100.0
        self.max_speed = 2
        self.alive = True

    def update_hunger(self):
        self.hunger = min(100, self.hunger + 0.02)

    def eat(self):
        self.hunger = max(0, self.hunger - 25)
    def get_depth_color(self, base_color):
        dim = 0.4 + (self.z * 0.6)

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


class Pleco(Fish):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 3.5
        self.max_force = 0.3
        self.z = random.uniform(0.65, 0.75)
        self.target_algae = None
        self.eating_timer = 0

    def behavior(self, fishes, algae_list):
        movement_cost = self.vel.length() * 0.02
        self.hunger = min(MAX_HUNGER, self.hunger + 0.05 + movement_cost)

        if self.hunger > 20 and algae_list:
            closest = None
            min_dist = float('inf')
            for a in algae_list:
                dist = self.pos.distance_to(pygame.Vector2(a))
                if dist < min_dist:
                    min_dist = dist
                    closest = a
            self.target_algae = closest
        else:
            self.target_algae = None

        if self.eating_timer > 0:
            self.eating_timer -= 1
            self.vel *= 0.1
        elif self.target_algae:
            target_vec = pygame.Vector2(self.target_algae)
            dist = self.pos.distance_to(target_vec)

            if dist < 8:
                if self.target_algae in algae_list:
                    algae_list.remove(self.target_algae)
                    self.hunger = max(0, self.hunger - 25)
                    self.eating_timer = 20
                self.target_algae = None
            else:
                desired = (target_vec - self.pos).normalize() * self.max_speed
                steer = (desired - self.vel) * self.max_force
                self.apply_force(steer)
        else:
            self.apply_force(pygame.Vector2(random.uniform(-0.05, 0.05), 0.02))

        target_y = SCREEN_HEIGHT - 60
        if self.pos.y < target_y:
            self.apply_force(pygame.Vector2(0, 0.2))

    def draw(self, surface):
        self.draw_shadow(surface, 25)
        z, x, y = self.z, self.pos.x, self.pos.y
        facing = 1 if self.vel.x >= 0 else -1

        body_col = self.get_depth_color((70, 65, 60))
        spot_col = self.get_depth_color((110, 100, 90))

        body_rect = (x - 25 * z, y, 50 * z, 24 * z)
        pygame.draw.ellipse(surface, body_col, body_rect)

        tail_pts = [
            (x, y + 5 * z),
            (x - 45 * z * facing, y + 12 * z),
            (x, y + 19 * z)
        ]
        pygame.draw.polygon(surface, body_col, tail_pts)

        for i in range(5):
            spot_x = x - (10 * i * z * facing) + (math.sin(i) * 5 * z)
            spot_y = y + 8 * z + (math.cos(i) * 4 * z)
            pygame.draw.circle(surface, spot_col, (int(spot_x), int(spot_y)), int(3 * z))

        pygame.draw.ellipse(surface, (100, 95, 90), (x + 8 * z * facing, y + 14 * z, 12 * z, 8 * z))

        sail_pts = [
            (x - 5 * z * facing, y + 2 * z),
            (x - 35 * z * facing, y - 20 * z),
            (x - 20 * z * facing, y + 6 * z)
        ]
        pygame.draw.polygon(surface, body_col, sail_pts)
        pygame.draw.aalines(surface, spot_col, False, sail_pts)

        pec_pts = [
            (x + 5 * z * facing, y + 18 * z),
            (x - 15 * z * facing, y + 30 * z),
            (x - 5 * z * facing, y + 20 * z)
        ]
        pygame.draw.polygon(surface, body_col, pec_pts)

        eye_pos = (int(x + 12 * z * facing), int(y + 6 * z))
        pygame.draw.circle(surface, (10, 10, 10), eye_pos, int(3 * z))
        pygame.draw.circle(surface, (200, 200, 200), (eye_pos[0] + 1, eye_pos[1] - 1), 1)

class BalaShark(Fish):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.2, 0.6)
        self.max_speed = 5.5
        self.lerp_speed = 0.35
        self.angle = 0.0

        self.base_color = (200, 205, 210)
        self.trim_color = (10, 10, 10)
        self.fin_inner = (230, 235, 240)

    def behavior(self, fishes):
        if random.random() < 0.02:
            burst = pygame.Vector2(random.uniform(-2, 2), random.uniform(-0.5, 0.5))
            self.apply_force(burst)

        for o in fishes:
            if isinstance(o, BalaShark) and o != self:
                dist = self.pos.distance_to(o.pos)
                if dist < 150:
                    self.vel += o.vel * 0.02

        if self.vel.length() > 0.1:
            target_angle = math.degrees(math.atan2(-self.vel.y, abs(self.vel.x)))
            self.angle += (target_angle - self.angle) * self.lerp_speed

    def draw(self, surface):
        self.draw_shadow(surface, 25)
        z, x, y = self.z, self.pos.x, self.pos.y
        facing = self.vel.x >= 0

        surf_w, surf_h = int(220 * z), int(140 * z)
        fish_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2

        silver_main = self.get_depth_color(self.base_color)
        silver_bright = self.get_depth_color((240, 245, 255))
        black_trim = (15, 15, 15)
        t = pygame.time.get_ticks() * 0.01

        def draw_bala_fin(pts, is_dorsal=True):
            pygame.draw.polygon(fish_surf, self.fin_inner, pts)
            if is_dorsal:
                margin = [pts[1], pts[2], (pts[2][0] + 8 * z, pts[2][1] + 12 * z)]
            else:
                margin = [pts[1], pts[2], (pts[2][0] + 8 * z, pts[2][1] - 12 * z)]
            pygame.draw.polygon(fish_surf, black_trim, margin)
            pygame.draw.circle(fish_surf, (255, 255, 255, 200), (int(pts[1][0]), int(pts[1][1])), int(1.5 * z))

        draw_bala_fin([(cx - 10 * z, cy - 15 * z), (cx - 40 * z, cy - 50 * z), (cx - 55 * z, cy - 15 * z)])
        draw_bala_fin([(cx - 25 * z, cy + 15 * z), (cx - 50 * z, cy + 40 * z), (cx - 65 * z, cy + 15 * z)], False)

        body_pts = [
            (cx + 70 * z, cy - 2 * z),
            (cx + 30 * z, cy - 22 * z),
            (cx - 55 * z, cy - 14 * z),
            (cx - 55 * z, cy + 14 * z),
            (cx + 30 * z, cy + 22 * z),
        ]
        pygame.draw.polygon(fish_surf, silver_main, body_pts)

        pygame.draw.ellipse(fish_surf, (*silver_bright, 100), (cx - 20 * z, cy - 18 * z, 70 * z, 12 * z))
        pygame.draw.line(fish_surf, (100, 100, 100, 150), (cx + 50 * z, cy), (cx - 50 * z, cy), int(1.5 * z))

        sway = math.sin(t) * 10 * z
        tail_pts = [
            (cx - 55 * z, cy),
            (cx - 95 * z, cy - 40 * z + sway),
            (cx - 75 * z, cy + sway),
            (cx - 95 * z, cy + 40 * z + sway)
        ]
        pygame.draw.polygon(fish_surf, self.fin_inner, tail_pts)
        pygame.draw.polygon(fish_surf, black_trim,
                            [tail_pts[1], (cx - 90 * z, cy - 20 * z + sway), (cx - 80 * z, cy - 35 * z + sway)])
        pygame.draw.polygon(fish_surf, black_trim,
                            [tail_pts[3], (cx - 90 * z, cy + 20 * z + sway), (cx - 80 * z, cy + 35 * z + sway)])

        p_sway = math.cos(t * 0.5) * 5 * z
        pygame.draw.polygon(fish_surf, (*silver_bright, 180), [
            (cx + 25 * z, cy + 5 * z),
            (cx + 5 * z, cy + 20 * z + p_sway),
            (cx + 15 * z, cy + 10 * z)
        ])

        ex, ey = int(cx + 50 * z), int(cy - 5 * z)
        pygame.draw.circle(fish_surf, (30, 30, 30), (ex, ey), int(6 * z))
        pygame.draw.circle(fish_surf, (255, 255, 255, 220), (ex + 2, ey - 2), int(1.8 * z))
        pygame.draw.arc(fish_surf, (50, 50, 50, 100), (cx + 25 * z, cy - 15 * z, 20 * z, 30 * z), -math.pi / 2,
                        math.pi / 2, 2)

        final = fish_surf if facing else pygame.transform.flip(fish_surf, True, False)
        rotated = pygame.transform.rotate(final, self.angle if facing else -self.angle)
        surface.blit(rotated, rotated.get_rect(center=(int(x), int(y))))

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

class YellowPrinceCichlid(Cichlid):
    def draw(self, surface):
        self.draw_shadow(surface, 24)

        facing = 1 if self.vel.x >= 0 else -1
        x, y, z = self.pos.x, self.pos.y, self.z

        base_yellow = (255, 225, 30)
        highlight_yellow = (255, 245, 100)
        prince_yellow = self.get_depth_color(base_yellow)
        black_trim = (15, 15, 15)

        body_pts = [
            (x, y + 4 * z),
            (x - 10 * z * facing, y - 6 * z),
            (x - 25 * z * facing, y - 4 * z),
            (x - 35 * z * facing, y + 4 * z),
            (x - 35 * z * facing, y + 10 * z),
            (x - 25 * z * facing, y + 16 * z),
            (x - 10 * z * facing, y + 15 * z),
        ]
        pygame.draw.polygon(surface, prince_yellow, body_pts)

        pygame.draw.line(surface, self.get_depth_color(highlight_yellow),
                         (x - 5 * z * facing, y + 4 * z),
                         (x - 20 * z * facing, y + 2 * z), int(2 * z))

        dorsal_pts = [
            (x - 8 * z * facing, y - 6 * z),
            (x - 15 * z * facing, y - 11 * z),
            (x - 32 * z * facing, y - 8 * z),
            (x - 34 * z * facing, y + 4 * z)
        ]
        pygame.draw.polygon(surface, prince_yellow, dorsal_pts)
        pygame.draw.lines(surface, black_trim, False, [
            (x - 10 * z * facing, y - 7 * z),
            (x - 16 * z * facing, y - 10 * z),
            (x - 31 * z * facing, y - 7 * z)
        ], int(3 * z))

        pelvic_pts = [
            (x - 12 * z * facing, y + 15 * z),
            (x - 18 * z * facing, y + 22 * z),
            (x - 22 * z * facing, y + 15 * z)
        ]
        pygame.draw.polygon(surface, prince_yellow, pelvic_pts)
        pygame.draw.line(surface, black_trim, (x - 13 * z * facing, y + 15 * z), (x - 19 * z * facing, y + 21 * z),
                         int(2 * z))

        anal_pts = [
            (x - 25 * z * facing, y + 16 * z),
            (x - 32 * z * facing, y + 18 * z),
            (x - 34 * z * facing, y + 10 * z)
        ]
        pygame.draw.polygon(surface, prince_yellow, anal_pts)

        t_sway = math.sin(pygame.time.get_ticks() * 0.012) * 4 * z
        tail_pts = [
            (x - 35 * z * facing, y + 4 * z),
            (x - 44 * z * facing, y - 2 * z + t_sway),
            (x - 44 * z * facing, y + 16 * z + t_sway),
            (x - 35 * z * facing, y + 10 * z)
        ]
        pygame.draw.polygon(surface, prince_yellow, tail_pts)

        eye_pos = (int(x - 4 * z * facing), int(y + 4 * z))
        pygame.draw.circle(surface, (10, 10, 10), eye_pos, int(2.5 * z))
        pygame.draw.circle(surface, (255, 255, 255), eye_pos, int(0.5 * z))

        pygame.draw.arc(surface, black_trim, (x - 12 * z * facing if facing == 1 else x, y, 10 * z, 10 * z), 0,
                        math.pi / 2, 1)


class IceBlueCichlid(Cichlid):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.max_speed = 2.5
        self.base_color = (180, 230, 255)
        self.stripe_color = (70, 130, 180)
        self.fin_highlight = (255, 255, 255)
        self.z = random.uniform(0.5, 0.9)

    def behavior(self, fishes):
        if random.random() < 0.01:
            self.apply_force(pygame.Vector2(random.uniform(-1.5, 1.5), random.uniform(-0.8, 0.8)))

        self.vel *= 0.98

    def draw(self, surface):
        self.draw_shadow(surface, 30)
        z, x, y = self.z, self.pos.x, self.pos.y
        facing = 1 if self.vel.x >= 0 else -1

        body_col = self.get_depth_color(self.base_color)
        bar_col = self.get_depth_color(self.stripe_color)

        body_width, body_height = 60 * z, 35 * z
        body_rect = (x - body_width // 2, y - body_height // 2, body_width, body_height)
        pygame.draw.ellipse(surface, body_col, body_rect)

        for i in range(5):
            bar_x = x - (20 * z) + (i * 10 * z)
            bar_w = 4 * z
            pygame.draw.rect(surface, bar_col, (bar_x, y - body_height // 2.5, bar_w, body_height * 0.8),
                             border_radius=int(2 * z))

        dorsal_pts = [
            (x - 20 * z, y - body_height // 2),
            (x + 15 * z, y - body_height // 2 - 10 * z),
            (x + 25 * z, y - body_height // 4)
        ]
        pygame.draw.polygon(surface, body_col, dorsal_pts)
        pygame.draw.line(surface, self.fin_highlight, dorsal_pts[0], dorsal_pts[1], max(1, int(2 * z)))

        tail_rect = (x - 35 * z * facing, y - 12 * z, 15 * z, 24 * z)
        pygame.draw.ellipse(surface, body_col, tail_rect)

        eye_x = x + (18 * z * facing)
        eye_y = y - (4 * z)
        pygame.draw.circle(surface, (10, 10, 10), (int(eye_x), int(eye_y)), int(4 * z))
        pygame.draw.circle(surface, (255, 255, 0), (int(eye_x), int(eye_y)), int(4 * z), 1)

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


class ClownLoach(Fish):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.3, 0.6)
        self.max_speed = 2.5
        self.lerp_speed = 0.12
        self.angle = 0.0

        self.base_color = (255, 160, 20)
        self.stripe_color = (15, 15, 15)
        self.fin_color = (200, 50, 30)

    def behavior(self, fishes):
        ground_level = SCREEN_HEIGHT - 60
        if self.pos.y < ground_level:
            self.apply_force(pygame.Vector2(0, 0.15))
        else:
            self.apply_force(pygame.Vector2(0, -0.1))

        t = pygame.time.get_ticks() * 0.005
        search_wiggle = math.sin(t + self.id) * 0.5
        self.apply_force(pygame.Vector2(search_wiggle, 0))

        if random.random() < 0.005:
            zoom_dir = pygame.Vector2(random.uniform(-5, 5), random.uniform(-3, 1))
            self.apply_force(zoom_dir)

        for o in fishes:
            if isinstance(o, ClownLoach) and o != self:
                dist = self.pos.distance_to(o.pos)
                if dist < 80:
                    self.apply_force((o.pos - self.pos) * 0.02)
                elif dist > 200:
                    self.apply_force((o.pos - self.pos) * 0.005)

        if self.vel.length() > 0.1:
            move_angle = math.degrees(math.atan2(-self.vel.y, abs(self.vel.x)))

            if self.pos.y > ground_level - 20:
                target_angle = -20
            else:
                target_angle = move_angle

            self.angle += (target_angle - self.angle) * self.lerp_speed

        self.vel *= 0.96

    def draw(self, surface):
        self.draw_shadow(surface, 30)
        z, x, y = self.z, self.pos.x, self.pos.y
        facing = self.vel.x >= 0

        surf_w, surf_h = int(180 * z), int(100 * z)
        fish_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2

        body_col = self.get_depth_color(self.base_color)
        t = pygame.time.get_ticks() * 0.01
        sway = math.sin(t) * 4 * z

        fin_c = (*self.fin_color, 200)
        pygame.draw.polygon(fish_surf, fin_c,
                            [(cx, cy - 15 * z), (cx - 30 * z, cy - 40 * z), (cx - 45 * z, cy - 12 * z)])
        pygame.draw.polygon(fish_surf, fin_c,
                            [(cx + 20 * z, cy + 15 * z), (cx + 10 * z, cy + 30 * z), (cx, cy + 15 * z)])

        body_pts = [
            (cx + 65 * z, cy + 5 * z),
            (cx + 20 * z, cy - 20 * z),
            (cx - 50 * z, cy - 10 * z),
            (cx - 50 * z, cy + 15 * z),
            (cx + 20 * z, cy + 22 * z)
        ]
        pygame.draw.polygon(fish_surf, body_col, body_pts)

        band_col = (*self.stripe_color, 240)
        pygame.draw.polygon(fish_surf, band_col,
                            [(cx + 35 * z, cy - 18 * z), (cx + 55 * z, cy - 5 * z), (cx + 45 * z, cy + 18 * z),
                             (cx + 25 * z, cy + 5 * z)])
        pygame.draw.polygon(fish_surf, band_col,
                            [(cx - 5 * z, cy - 20 * z), (cx + 15 * z, cy - 15 * z), (cx, cy + 21 * z),
                             (cx - 20 * z, cy + 15 * z)])
        pygame.draw.polygon(fish_surf, band_col,
                            [(cx - 35 * z, cy - 14 * z), (cx - 50 * z, cy - 10 * z), (cx - 50 * z, cy + 15 * z),
                             (cx - 45 * z, cy + 15 * z)])

        for b in [-1, 1]:
            bx = cx + 65 * z
            by = cy + 5 * z
            pygame.draw.line(fish_surf, body_col, (bx, by), (bx + 8 * z, by + b * 5 * z + sway), int(2 * z))

        t_sway = math.sin(t * 1.5) * 8 * z
        tail_pts = [
            (cx - 50 * z, cy + 2 * z),
            (cx - 85 * z, cy - 30 * z + t_sway),
            (cx - 70 * z, cy + t_sway),
            (cx - 85 * z, cy + 30 * z + t_sway)
        ]
        pygame.draw.polygon(fish_surf, fin_c, tail_pts)

        ex, ey = int(cx + 45 * z), int(cy - 5 * z)
        pygame.draw.circle(fish_surf, (0, 0, 0), (ex, ey), int(4 * z))
        pygame.draw.circle(fish_surf, (255, 255, 255, 150), (ex + 1, ey - 1), int(1 * z))

        final = fish_surf if facing else pygame.transform.flip(fish_surf, True, False)
        rotated = pygame.transform.rotate(final, self.angle if facing else -self.angle)
        surface.blit(rotated, rotated.get_rect(center=(int(x), int(y))))


class TigerBarb(Fish):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.z = random.uniform(0.5, 0.8)
        self.max_speed = 1.2
        self.target_y = WATER_TOP + random.randint(15, 45)

        self.base_color = (200, 200, 210)
        self.stripe_color = (60, 65, 75)
        self.eye_color = (255, 255, 255)

    def behavior(self, fishes):
        dy = self.target_y - self.pos.y
        self.apply_force(pygame.Vector2(0, dy * 0.02))

        if random.random() < 0.01:
            self.apply_force(pygame.Vector2(random.uniform(-1.5, 1.5), 0))

        for o in fishes:
            if isinstance(o, TigerBarb) and o != self:
                dist = self.pos.distance_to(o.pos)
                if dist < 60:
                    self.apply_force((self.pos - o.pos) * 0.01)

        self.vel.x *= 0.98
        self.vel.y *= 0.95

    def draw(self, surface):
        self.draw_shadow(surface, 15)
        z, x, y = self.z, self.pos.x, self.pos.y
        facing = 1 if self.vel.x >= 0 else -1

        surf_w, surf_h = int(120 * z), int(120 * z)
        fish_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2

        body_col = self.get_depth_color((230, 180, 50))
        stripe_col = self.get_depth_color((15, 15, 15))
        accent_col = self.get_depth_color((210, 40, 30))
        t = pygame.time.get_ticks() * 0.01

        body_pts = [
            (cx + 45 * z, cy),
            (cx + 10 * z, cy - 30 * z),
            (cx - 30 * z, cy - 10 * z),
            (cx - 30 * z, cy + 10 * z),
            (cx + 10 * z, cy + 30 * z),
        ]
        pygame.draw.polygon(fish_surf, body_col, body_pts)

        stripe_offsets = [25, 8, -8, -22]

        for sx in stripe_offsets:
            dist_from_center = abs(sx) / 45.0
            h_scale = 1.0 - (dist_from_center ** 2)

            s_w = int(7 * z)
            s_h = int(50 * z * h_scale)

            s_rect = (int(cx + sx * z), int(cy - s_h // 2), s_w, s_h)
            pygame.draw.rect(fish_surf, stripe_col, s_rect, border_radius=int(3 * z))

        pygame.draw.polygon(fish_surf, accent_col,
                            [(cx + 5 * z, cy - 25 * z), (cx - 5 * z, cy - 45 * z), (cx - 15 * z, cy - 25 * z)])

        sway = math.sin(t) * 6 * z
        tail_pts = [(cx - 30 * z, cy), (cx - 55 * z, cy - 28 * z + sway), (cx - 45 * z, cy + sway),
                    (cx - 55 * z, cy + 28 * z + sway)]
        pygame.draw.polygon(fish_surf, body_col, tail_pts)
        pygame.draw.lines(fish_surf, accent_col, False, [tail_pts[1], tail_pts[0], tail_pts[3]], int(2 * z))

        ex, ey = int(cx + 32 * z), int(cy - 3 * z)
        pygame.draw.circle(fish_surf, (10, 10, 10), (ex, ey), int(5 * z))
        pygame.draw.circle(fish_surf, (255, 255, 255, 150), (ex + 1, ey - 1), int(1.5 * z))

        final = fish_surf if facing == 1 else pygame.transform.flip(fish_surf, True, False)
        surface.blit(final, final.get_rect(center=(int(x), int(y))))


def spawn_random_fish(fishes=None):
    sx = random.randint(50, SCREEN_WIDTH - 50)

    surface_zone = random.randint(WATER_TOP + 10, WATER_TOP + 60)
    mid_zone = random.randint(200, 500)
    bottom_y = SCREEN_HEIGHT - 120
    floor_y = SCREEN_HEIGHT - 60

    spawn_table = [
        (0.15, TigerBarb, surface_zone),
        (0.25, PearlGourami, surface_zone + 40),
        (0.25, Pleco, floor_y),
        (0.55, NeonTetra, mid_zone),
        (0.25, BoesemaniRainbow, mid_zone - 50),
        (0.30, BalaShark, mid_zone),
        (0.20, ClownLoach, floor_y - 20),
        (0.60, PeacockCichlid, mid_zone),
        (1.70, YellowPrinceCichlid, mid_zone),
        (1.80, IceBlueCichlid, mid_zone),
        (1.00, Cichlid, mid_zone)
    ]

    choice = random.random()

    for chance, fish_class, y_pos in spawn_table:
        if choice < chance:
            return fish_class(sx, y_pos)

pygame.display.set_caption("Pixel Aquarium")
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

music_files = ["bgmusic.mp3", "bgmusic2.mp3", "bgmusic3.mp3", "bgmusic4.mp3"]
current_music_idx = 0
try:
    pygame.mixer.music.load(get_path(music_files[current_music_idx]))
    pygame.mixer.music.play(-1)
except pygame.error:
    print(f"Could not load initial music: {music_files[0]}")

bg_files, bg_index = ["wallart.png", "wallart2.png", "wallart3.png", "wallart4.png","wallart5.png","wallart6.png","wallart7.png","wallart8.png","wallart9.png"], 0
try:
    bg_image = pygame.transform.scale(pygame.image.load(get_path(bg_files[bg_index])), (SCREEN_WIDTH, SCREEN_HEIGHT))
except:
    bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    bg_image.fill((10, 20, 40))

fishes = [spawn_random_fish() for _ in range(30)]
snails = [Snail() for _ in range(3)]
auto_feed_timer = random.randint(100, 300)
plants = [Plant(x, random.choice(["Rotala", "Ludwigia", "Vallisneria", "Anubias", "TigerLotus"])) for x in
          range(40, SCREEN_WIDTH, 30)]
grains = [(random.randint(0, SCREEN_WIDTH), random.randint(540, 600), random.choice([(190, 170, 110), (225, 200, 140)]))
          for _ in range(600)]
algae, pellets, bubbles, frame = [], [], [], 0
rocks = create_hardscape()
pebbles = create_pebbles(50)

caustic_beams = [
    [random.randint(0, SCREEN_WIDTH), random.randint(20, 60), random.uniform(0.5, 1.5), random.uniform(0, 2 * math.pi)]
    for _ in range(8)]
LOG_INTERVAL = 180

while True:
    if current_state == STATE_WELCOME:
        br = draw_welcome_screen()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and br.collidepoint(e.pos):
                current_state = STATE_AQUARIUM
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    current_state = STATE_AQUARIUM

    else:
        frame += 1

        LOG_INTERVAL = 180
        if frame % LOG_INTERVAL == 0:
            starving_count = 0

            log_output = ""

            fish_counts = {}

            for f in fishes:
                fish_type = f.__class__.__name__
                fish_counts[fish_type] = fish_counts.get(fish_type, 0) + 1
                if f.hunger > 70:
                    status = "STARVING"
                    fish_type = f.__class__.__name__
                    fish_id = getattr(f, 'id', '???')
                    log_output += f"[{fish_type}"
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
                        random.randint(300, SCREEN_HEIGHT - SAND_HEIGHT)
                    )
                    algae.append(new_algae)

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
            auto_feed_timer = 100

        for f in fishes[:]:

            if isinstance(f, Pleco):
                f.behavior(fishes, algae)
            else:
                f.behavior(fishes)

            f.update(pellets, algae)
            if not f.alive:
                    fishes.remove(f)
                    fishes.append(spawn_random_fish(fishes))

        sorted_f = sorted(fishes, key=lambda f: f.z)
        for f in sorted_f:
            if f.z <= 0.9:
                f.draw(screen)
        for p in pebbles:
            p.draw(screen)
        for r in rocks:
            if r.z < 0.95:
                r.draw(screen)
        for p in plants:
            p.draw(screen, frame)
        for f in sorted_f:
            if f.z > 0.9:
                f.draw(screen)
        for r in rocks:
            if r.z >= 0.95:
                r.draw(screen)
        for s in snails:
            s.update(algae)
            s.draw(screen)



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
                if e.key == pygame.K_v:
                    is_muted = not is_muted
                    if is_muted:
                        pygame.mixer.music.set_volume(0)
                        light_notif_text = "Audio: MUTED"
                    else:
                        pygame.mixer.music.set_volume(0.7)
                        light_notif_text = "Audio: ON"

                    light_notif_alpha = 255
                if e.key == pygame.K_m:
                    current_music_idx = (current_music_idx + 1) % len(music_files)

                    try:
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(get_path(music_files[current_music_idx]))
                        pygame.mixer.music.set_volume(0.7)
                        pygame.mixer.music.play(-1)
                        light_notif_text = f"NOW PLAYING: {music_files[current_music_idx]}"
                        light_notif_alpha = 255
                    except pygame.error:
                        print(f"Error loading: {music_files[current_music_idx]}")
                if e.key == pygame.K_n:
                    current_light_idx = (current_light_idx + 1) % len(LIGHT_MODES)
                    light_notif_text = f"Mode: {LIGHT_MODES[current_light_idx]['name']}"
                    light_notif_alpha = 255
                    print(f"Lighting: {light_notif_text}")
                if e.key == pygame.K_b:
                    bg_index = (bg_index + 1) % len(bg_files)
                    light_notif_text = f"ART CHANGED TO: {bg_files[bg_index]}"
                    light_notif_alpha = 255
                    try:
                        bg_image = pygame.transform.scale(pygame.image.load(get_path(bg_files[bg_index])),
                                                          (SCREEN_WIDTH, SCREEN_HEIGHT))
                    except:
                        pass
                if e.key == pygame.K_r:
                    current_state, frame = STATE_WELCOME, 0
                    fishes = [spawn_random_fish() for _ in range(30)]
                    snails = [Snail() for _ in range(3)]
                    rocks = create_hardscape()
                    pebbles = create_pebbles(50)
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

        mode = LIGHT_MODES[current_light_idx]
        light_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        if mode["name"] == "RGB STROBE":
            t = pygame.time.get_ticks() * 0.0005
            r = int(127 + 127 * math.sin(t))
            g = int(127 + 127 * math.sin(t + 2))
            b = int(127 + 127 * math.sin(t + 4))
            light_surf.fill((r, g, b, 40))
        elif mode["name"] == "MOONLIGHT":
            light_surf.fill(mode["color"])
        else:
            light_surf.fill(mode["color"])

        screen.blit(light_surf, (0, 0))
    if light_notif_alpha > 0:
        temp_font = pygame.font.SysFont("Arial", 16, italic=True)
        text_surf = temp_font.render(light_notif_text, True, (220, 220, 220))

        notif_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        notif_surf.blit(text_surf, (0, 0))
        notif_surf.set_alpha(light_notif_alpha)

        padding = 20
        screen.blit(notif_surf, (SCREEN_WIDTH - text_surf.get_width() - padding, padding))

        light_notif_alpha = max(0, light_notif_alpha - 2)

    pygame.display.flip()
    clock.tick(60)


    frame += 1