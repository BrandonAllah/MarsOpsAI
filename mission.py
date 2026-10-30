"""Mission progression and upgrades, independent of rendering and AI requests."""
import math
import pygame
from terrain import BASE, TARGETS

REWARD = 200
BASE_RADIUS = 85
MAX_LEVEL = 3


class Mission:
    def __init__(self):
        self.credits = 0
        self.levels = {"battery": 0, "speed": 0, "scanner": 0}
        self.number = 0
        self.start()

    @property
    def capacity(self):
        return 100 + 25 * self.levels["battery"]

    @property
    def speed(self):
        return 240 + 30 * self.levels["speed"]

    @property
    def scanner_range(self):
        # Extra reach beyond the rover's edge for the E interaction.
        return 15 + 15 * self.levels["scanner"]

    @property
    def objective(self):
        if self.completed:
            return "Mission Complete"
        if not self.samples:
            return "Return to Base"
        return "Collect Samples"

    @property
    def collected(self):
        return len(TARGETS) - len(self.samples)

    def start(self):
        self.number += 1
        self.samples = [pygame.Rect(x-10, y-10, 20, 20) for x, y in TARGETS]
        self.battery = float(self.capacity)
        self.completed = False

    def at_base(self, position):
        return math.dist(position, BASE) <= BASE_RADIUS

    def collect(self, rover):
        if self.completed:
            return 0
        reach = rover.inflate(self.scanner_range * 2, self.scanner_range * 2)
        found = [sample for sample in self.samples if reach.colliderect(sample)]
        for sample in found:
            self.samples.remove(sample)
        return len(found)

    def update(self, position, dt, moved):
        if moved and not self.completed:
            self.battery = max(0.0, self.battery - 2 * dt)
        if self.at_base(position):
            self.battery = min(float(self.capacity), self.battery + 15 * dt)
            if not self.samples and not self.completed:
                self.completed = True
                self.credits += REWARD
                return True
        return False

    def upgrade_cost(self, kind):
        return 100 + 50 * self.levels[kind]

    def upgrade(self, kind):
        if self.levels[kind] >= MAX_LEVEL or self.credits < self.upgrade_cost(kind):
            return False
        self.credits -= self.upgrade_cost(kind)
        self.levels[kind] += 1
        return True
