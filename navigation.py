"""Map-coordinate bearings: north is up, east is right, clockwise is positive."""
import math


def heading_degrees(angle_radians):
    return math.degrees(angle_radians) % 360.0


def bearing_degrees(origin, destination):
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    if dx == 0 and dy == 0:
        return None
    return math.degrees(math.atan2(dx, -dy)) % 360.0


def smooth_heading(current, target, dt, rate=8):
    """Interpolate along the shortest arc, including across north."""
    delta = (target - current + math.pi) % (2 * math.pi) - math.pi
    return (current + delta * (1 - math.exp(-rate * max(0, dt)))) % (2 * math.pi)
