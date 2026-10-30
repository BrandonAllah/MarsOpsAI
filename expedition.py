"""Seeded, lazily rendered expedition maps and lightweight exploration systems."""
from collections import OrderedDict
from dataclasses import replace
import math
import random
import pygame
from terrain import BASE, TARGETS, segment_distance
from discoveries import DISCOVERIES

CHUNK = 400
CELL = 200
BASE_SEED = 4026
ROCK_TYPES = {
    'basalt': ('Basaltic', (86, 84, 88), 10, 'Simulated volcanic rock; basalt forms from cooled lava.', 'common'),
    'sediment': ('Sedimentary', (198, 157, 111), 15, 'Simulated layered sedimentary rock.', 'common'),
    'hematite': ('Hematite-bearing', (145, 72, 70), 25, 'Simulated iron-bearing material.', 'uncommon'),
    'sulfate': ('Sulfate-bearing', (220, 205, 170), 30, 'Simulated sulfate-bearing material.', 'rare'),
    'clay': ('Clay-bearing', (151, 150, 119), 20, 'Simulated clay-bearing material.', 'uncommon'),
}


class ExpeditionMap:
    def __init__(self, number=1, seed=None):
        self.number = max(1, int(number))
        self.seed = BASE_SEED + self.number - 1 if seed is None else int(seed)
        self.size = (2400 + 200*(self.number-1), 1800 + 150*(self.number-1))
        rng = random.Random(self.seed)
        count = 3 + 2*(self.number-1)
        if self.number == 1 and self.seed == BASE_SEED:
            self.targets = list(TARGETS)
        else:
            self.targets = []
            for i in range(count):
                # Spread locations in angular sectors; clear radial routes to base.
                angle = 2*math.pi*i/count + rng.uniform(-.15, .15)
                radius = rng.uniform(500, min(self.size)*.42)
                x = max(150, min(self.size[0]-150, int(BASE[0]+radius*math.cos(angle))))
                y = max(150, min(self.size[1]-150, int(BASE[1]+radius*math.sin(angle))))
                # Avoid closely spaced targets, while keeping generated positions deterministic.
                for attempt in range(150):
                    if math.dist((x, y), BASE) >= 240 and all(math.dist((x, y), p) >= 100 for p in self.targets):
                        break
                    x, y = rng.randint(150, self.size[0]-150), rng.randint(150, self.size[1]-150)
                self.targets.append((x, y))
        # Locations are fictional within the condensed simulation.
        self.discoveries = tuple(replace(d, position=self.targets[i % len(self.targets)])
                                 for i, d in enumerate(DISCOVERIES[:min(len(DISCOVERIES), 3 + (self.number-1)//2)]))
        self.routes = [(BASE, p) for p in self.targets]
        self.types = {point: rng.choices(list(ROCK_TYPES), weights=[35, 27, 15, 10, 13])[0] for point in self.targets}
        self.cache = OrderedDict()
        self.explored = set()
        self.detected = set()

    def region(self, position):
        cx, cy = position[0]//CHUNK, position[1]//CHUNK
        return ("Dusty plains", "Basaltic plain", "Dunes")[(cx//2 + cy//2 + self.seed) % 3]

    def chunk(self, cx, cy):
        key = (cx, cy)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        rng = random.Random(f'{self.seed}:{cx}:{cy}')
        surface = pygame.Surface((CHUNK, CHUNK)).convert()
        region = (cx//2 + cy//2 + self.seed) % 3
        surface.fill(((158, 81, 53), (121, 72, 61), (174, 98, 65))[region])
        for _ in range(38):
            x, y = rng.randrange(CHUNK), rng.randrange(CHUNK)
            color = rng.choice(((144, 75, 54), (186, 108, 73), (126, 70, 57), (164, 88, 63)))
            pygame.draw.ellipse(surface, color, (x, y, rng.randrange(20, 120), rng.randrange(8, 45)))
        for _ in range(900):
            x, y = rng.randrange(CHUNK), rng.randrange(CHUNK)
            pygame.draw.circle(surface, rng.choice(((113, 61, 48), (197, 116, 76), (146, 76, 58))), (x, y), rng.choice((1, 1, 2)))
        # Craters, dune/ridge curves, and fractures are traversable decoration.
        for _ in range(2):
            x, y, r = rng.randrange(CHUNK), rng.randrange(CHUNK), rng.randrange(25, 75)
            pygame.draw.ellipse(surface, (94, 55, 48), (x-r, y-r//2, r*2, r))
            pygame.draw.ellipse(surface, (189, 112, 76), (x-r, y-r//2-5, r*2, r), 5)
            pygame.draw.ellipse(surface, (139, 76, 56), (x-r+8, y-r//2+5, r*2-16, r-12))
        for _ in range(6):
            x, y = rng.randrange(CHUNK), rng.randrange(CHUNK)
            pygame.draw.arc(surface, (204, 128, 85), (x, y, 80, 32), .2, 2.5, 2)
        obstacles = []
        for _ in range(20):
            x, y, r = rng.randrange(30, CHUNK-30), rng.randrange(30, CHUNK-30), rng.randrange(15, 32)
            wx, wy = cx*CHUNK+x, cy*CHUNK+y
            if any(segment_distance((wx, wy), a, b) < r+75 for a, b in self.routes):
                continue
            if math.dist((wx, wy), BASE) < 140:
                continue
            rect = pygame.Rect(wx-r, wy-r//2, 2*r, r)
            obstacles.append(rect)
            pygame.draw.ellipse(surface, (80, 48, 41), (x-r+5, y-r//2+5, 2*r, r))
            pygame.draw.ellipse(surface, (115, 69, 54), (x-r, y-r//2, 2*r, r))
            pygame.draw.arc(surface, (170, 106, 74), (x-r, y-r//2, 2*r, r), .3, 2.8, 3)
        self.cache[key] = (surface, obstacles)
        if len(self.cache) > 48:
            self.cache.popitem(last=False)
        return surface, obstacles

    def visible_chunks(self, view):
        for cy in range(max(0, view.top//CHUNK), min((self.size[1]-1)//CHUNK, view.bottom//CHUNK)+1):
            for cx in range(max(0, view.left//CHUNK), min((self.size[0]-1)//CHUNK, view.right//CHUNK)+1):
                yield cx, cy

    def draw(self, screen, offset, size):
        view = pygame.Rect(*offset, *size)
        for cx, cy in self.visible_chunks(view):
            surface, _ = self.chunk(cx, cy)
            screen.blit(surface, (cx*CHUNK-offset[0], cy*CHUNK-offset[1]))

    def obstacles_near(self, rover):
        view = rover.inflate(200, 200).clip(pygame.Rect(0, 0, *self.size))
        return [r for cx, cy in self.visible_chunks(view) for r in self.chunk(cx, cy)[1]]

    def reveal(self, point, radius=320):
        x, y = point
        for cy in range(max(0, (y-radius)//CELL), min((self.size[1]-1)//CELL, (y+radius)//CELL)+1):
            for cx in range(max(0, (x-radius)//CELL), min((self.size[0]-1)//CELL, (x+radius)//CELL)+1):
                if math.hypot((cx+.5)*CELL-x, (cy+.5)*CELL-y) <= radius+CELL*.7:
                    self.explored.add((cx, cy))

    def scan(self, point, radius, samples=None):
        targets = self.targets if samples is None else [sample.center for sample in samples]
        found = [p for p in targets if math.dist(point, p) <= radius]
        features = [d.id for d in self.discoveries if math.dist(point, d.position) <= radius]
        self.detected.update(found)
        self.detected.update(features)
        return found, features
