"""Expedition weather, rover health, scanner, statistics, and safe local saves."""
import json
import math
import os
import tempfile
from navigation import smooth_heading

DAY_SECONDS = 240.0
SAVE_PATH = os.path.join(os.path.dirname(__file__), 'marsops_save.json')


class RoverSystems:
    def __init__(self):
        self.wheels = 100.0
        self.chassis = 100.0
        self.science = 100.0
        self.vx = self.vy = 0.0
        self.angle = 0.0
        self.scan_cooldown = 0.0
        self.scan_pulse = 0.0
        self.collision_cooldown = 0.0
        self.time = DAY_SECONDS*.28
        self.day_seconds = DAY_SECONDS
        self.effects = True

    @property
    def light(self):
        return max(.26, .26 + .74 * max(0, math.sin(2*math.pi*self.time/self.day_seconds)))

    @property
    def weather(self):
        phase = int(self.time // 55) % 4
        return ('Clear', 'Blowing dust', 'Dust storm', 'Clear')[phase]

    @property
    def visibility(self):
        return (0.65 if self.weather == 'Dust storm' else .85 if self.weather == 'Blowing dust' else 1) * (.55 + .45*self.light)

    def update(self, dt, dx, dy, speed):
        self.time += dt
        self.scan_cooldown = max(0, self.scan_cooldown-dt)
        self.scan_pulse = max(0, self.scan_pulse-dt)
        self.collision_cooldown = max(0, self.collision_cooldown-dt)
        magnitude = math.hypot(dx, dy)
        if magnitude: dx, dy = dx/magnitude, dy/magnitude
        health_factor = .6 + .4*min(self.wheels, self.chassis)/100
        weather_factor = .8 if self.weather == 'Dust storm' else 1
        blend = 1-math.exp(-8*dt)
        self.vx += (dx*speed*health_factor*weather_factor-self.vx)*blend
        self.vy += (dy*speed*health_factor*weather_factor-self.vy)*blend
    def orient(self, dx, dy, dt):
        # Align the visible rover and compass to actual travel, including wall slides.
        if dx or dy:
            target = math.atan2(dx, -dy)
            self.angle = smooth_heading(self.angle, target, dt)

    def damage_collision(self):
        if self.collision_cooldown <= 0:
            self.wheels = max(25, self.wheels-.7)
            self.chassis = max(25, self.chassis-.35)
            self.science = max(25, self.science-.15)
            self.collision_cooldown = .8

    def repair(self, dt, level):
        rate = (2+level)*dt
        self.wheels = min(100, self.wheels+rate)
        self.chassis = min(100, self.chassis+rate)
        self.science = min(100, self.science+rate)

    def scan(self, mission, expedition, position):
        cost = max(1, 3 - .6*mission.levels['efficiency'])
        if self.scan_cooldown > 0 or mission.battery < cost:
            return None
        mission.battery -= cost
        self.scan_cooldown = max(2, 6 - mission.levels['efficiency'])
        self.scan_pulse = 1.0
        radius = mission.scan_radius * (.6 + .4*self.science/100)
        return expedition.scan(position, radius, mission.samples)


def save_progress(data, path=SAVE_PATH):
    directory = os.path.dirname(path) or '.'
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=directory, delete=False) as file:
            tmp = file.name
            json.dump(data, file, separators=(',', ':'))
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
        return True
    except (OSError, TypeError, ValueError):
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass
        return False


def load_progress(path=SAVE_PATH):
    try:
        with open(path, encoding='utf-8') as file:
            data = json.load(file)
        return data if isinstance(data, dict) and data.get('version') == 1 else None
    except (OSError, ValueError, TypeError):
        return None


def snapshot(mission, expedition, journal, rover, systems, stats, achievements):
    """Serialize only game data; never include environment variables or API keys."""
    return {
        'version': 1, 'number': mission.number, 'seed': expedition.seed,
        'credits': mission.credits, 'levels': mission.levels.copy(),
        'samples': [list(r.center) for r in mission.samples],
        'cargo': [list(p) for p in mission.cargo], 'unloaded': mission.unloaded,
        'battery': mission.battery, 'completed': mission.completed,
        'optional_done': mission.optional_done, 'optional_paid': mission.optional_paid,
        'optional_site_done': mission.optional_site_done, 'optional_site_paid': mission.optional_site_paid,
        'position': list(rover.center), 'discoveries': sorted(journal.found),
        'explored': [list(p) for p in sorted(expedition.explored)],
        'detected_points': [list(p) for p in expedition.detected if isinstance(p, tuple)],
        'detected_features': [p for p in expedition.detected if isinstance(p, str)],
        'health': [systems.wheels, systems.chassis, systems.science],
        'time': systems.time, 'day_seconds': systems.day_seconds, 'effects': systems.effects,
        'stats': stats.copy(), 'achievements': sorted(achievements),
    }


def restore(data, journal, rover, systems):
    """Validate and reconstruct a save before applying any journal or rover state."""
    from mission import Mission, MAX_LEVEL
    from expedition import ExpeditionMap
    from discoveries import DISCOVERIES
    import pygame
    try:
        if not isinstance(data, dict) or data.get('version') != 1:
            return None
        number = int(data['number'])
        if not 1 <= number <= 100: return None
        exp = ExpeditionMap(number, int(data['seed']))
        mission = Mission()
        mission.number = number
        levels = data['levels']
        for key in mission.levels:
            value = int(levels[key])
            if not 0 <= value <= MAX_LEVEL: return None
            mission.levels[key] = value
        mission.credits = max(0, int(data['credits']))
        targets = set(exp.targets)
        samples = [tuple(p) for p in data['samples']]
        cargo = [tuple(p) for p in data['cargo']]
        if (len(set(samples)) != len(samples) or len(set(cargo)) != len(cargo)
                or set(samples) & set(cargo) or not set(samples+list(cargo)) <= targets):
            return None
        mission.samples = [pygame.Rect(x-10, y-10, 20, 20) for x, y in samples]
        mission.cargo = cargo
        mission.unloaded = int(data.get('unloaded', 0))
        if mission.unloaded != mission.required-len(samples)-len(cargo): return None
        mission.battery = max(0, min(mission.capacity, float(data['battery'])))
        mission.completed = bool(data['completed'])
        if mission.completed and samples: return None
        mission.optional_done = bool(data.get('optional_done', False))
        mission.optional_paid = bool(data.get('optional_paid', False))
        mission.optional_site_done = bool(data.get('optional_site_done', False))
        mission.optional_site_paid = bool(data.get('optional_site_paid', False))
        pos = tuple(data['position'])
        if len(pos) != 2 or not (25 <= pos[0] <= exp.size[0]-25 and 25 <= pos[1] <= exp.size[1]-25): return None
        health = [float(x) for x in data['health']]
        if len(health) != 3 or not all(math.isfinite(x) and 0 <= x <= 100 for x in health): return None
        elapsed = float(data['time'])
        if not math.isfinite(elapsed) or elapsed < 0: return None
        exp.explored = {tuple(p) for p in data.get('explored', []) if len(p) == 2 and all(isinstance(v, int) for v in p) and 0 <= p[0] <= exp.size[0]//200 and 0 <= p[1] <= exp.size[1]//200}
        exp.detected = {tuple(p) for p in data.get('detected_points', []) if tuple(p) in targets}
        exp.detected.update(p for p in data.get('detected_features', []) if p in {d.id for d in DISCOVERIES})
        rawstats = data.get('stats', {})
        stats = {k: max(0, float(rawstats.get(k, 0))) for k in ('missions', 'distance', 'samples', 'credits', 'upgrades', 'regions')}
        if not all(math.isfinite(v) for v in stats.values()): return None
        found = set(data.get('discoveries', [])) & {d.id for d in DISCOVERIES}
        awards = set(data.get('achievements', [])) & {'First expedition', 'Field geologist', 'Mars historian', 'Explorer'}
        rover.center = pos
        journal.found = found
        systems.wheels, systems.chassis, systems.science = health
        systems.time, systems.effects = elapsed, bool(data.get('effects', True))
        systems.day_seconds = max(60, min(900, float(data.get('day_seconds', DAY_SECONDS))))
        return mission, exp, stats, awards
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
