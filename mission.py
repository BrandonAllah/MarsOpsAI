"""Mission progression, upgrades, cargo and base services."""
import math
import pygame
from terrain import BASE, TARGETS

REWARD = 200
BASE_RADIUS = 85
MAX_LEVEL = 3


class Mission:
    def __init__(self):
        self.credits = 0
        self.levels = {"battery": 0, "speed": 0, "scanner": 0, "efficiency": 0, "repair": 0}
        self.number = 0
        self.start()

    @property
    def capacity(self): return 100 + 25 * self.levels['battery']
    @property
    def speed(self): return 240 + 30 * self.levels['speed']
    @property
    def scanner_range(self): return 15 + 15 * self.levels['scanner']
    @property
    def scan_radius(self): return 350 + 100 * self.levels['scanner']
    @property
    def required(self): return 3 + 2 * (self.number - 1)
    @property
    def objective(self):
        return 'Mission Complete' if self.completed else ('Return to Base' if not self.samples else 'Collect Samples')
    @property
    def collected(self): return self.required - len(self.samples)

    def start(self, positions=None, advance=True):
        if advance: self.number += 1
        if positions is None:
            from expedition import ExpeditionMap
            positions = ExpeditionMap(self.number).targets
        self.samples = [pygame.Rect(x-10, y-10, 20, 20) for x, y in positions]
        self.battery = float(self.capacity)
        self.completed = False
        self.cargo = []
        self.unloaded = 0
        self.optional_done = False
        self.optional_paid = False
        self.optional_site_done = False
        self.optional_site_paid = False

    def at_base(self, position): return math.dist(position, BASE) <= BASE_RADIUS

    def collect(self, rover):
        if self.completed: return 0
        reach = rover.inflate(self.scanner_range * 2, self.scanner_range * 2)
        found = [sample for sample in self.samples if reach.colliderect(sample)]
        for sample in found:
            self.samples.remove(sample)
            self.cargo.append(sample.center)
        return len(found)

    def update(self, position, dt, moved, charging_factor=1):
        if moved and not self.completed: self.battery = max(0.0, self.battery - 2*dt)
        if self.at_base(position):
            self.battery = min(float(self.capacity), self.battery + 15*dt*charging_factor)
            if not self.samples and not self.completed:
                self.completed = True
                self.credits += REWARD
                return True
        return False

    def upgrade_cost(self, kind): return 100 + 50*self.levels[kind]
    def upgrade(self, kind):
        if self.levels[kind] >= MAX_LEVEL or self.credits < self.upgrade_cost(kind): return False
        self.credits -= self.upgrade_cost(kind)
        self.levels[kind] += 1
        return True
