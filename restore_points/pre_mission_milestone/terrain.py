"""Deterministic, original procedural Martian landscape for Rover Explorer."""
import math
import random
import pygame

WORLD_SIZE = (2400, 1800)
BASE = (450, 900)
TARGETS = ((950, 420), (1900, 510), (1900, 1350))
SEED = 4026


def segment_distance(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    t = max(0.0, min(1.0, ((px-ax)*(bx-ax)+(py-ay)*(by-ay)) /
                         ((bx-ax)**2+(by-ay)**2)))
    return math.hypot(px-(ax+t*(bx-ax)), py-(ay+t*(by-ay)))


def clear_route(point, margin):
    # A branching network, wider than the rover, connects every mission site.
    edges = ((BASE, TARGETS[0]), (TARGETS[0], TARGETS[1]),
             (TARGETS[1], TARGETS[2]), (BASE, TARGETS[2]))
    return any(segment_distance(point, a, b) < margin for a, b in edges)


def make_world():
    rng = random.Random(SEED)
    world = pygame.Surface(WORLD_SIZE).convert()
    world.fill((153, 80, 55))
    # Broad translucent deposits form dusty, iron-rich and basaltic regions.
    wash = pygame.Surface(WORLD_SIZE, pygame.SRCALPHA)
    for i in range(155):
        x, y = rng.randrange(2400), rng.randrange(1800)
        w, h = rng.randrange(120, 500), rng.randrange(80, 320)
        color = rng.choice(((209, 129, 86, 24), (104, 52, 45, 24),
                            (74, 61, 58, 29), (186, 103, 67, 22)))
        pygame.draw.ellipse(wash, color, (x-w//2, y-h//2, w, h))
    world.blit(wash, (0, 0))
    # Wind streaks, gravel and tiny pitted marks, baked once for fast scrolling.
    for _ in range(12500):
        x, y = rng.randrange(2400), rng.randrange(1800)
        shade = rng.choice(((128, 65, 48), (174, 92, 61), (190, 109, 72),
                            (112, 62, 50), (206, 123, 82)))
        if rng.random() < .17:
            pygame.draw.line(world, shade, (x, y), (x+rng.randrange(4, 19), y-rng.randrange(0, 4)))
        else:
            pygame.draw.circle(world, shade, (x, y), rng.choice((1, 1, 2, 3)))
    for _ in range(85):
        x, y = rng.randrange(2400), rng.randrange(1800)
        points = [(x, y)]
        for j in range(rng.randrange(2, 5)):
            x += rng.randrange(5, 15); y += rng.randrange(-8, 9)
            points.append ( (x, y) )
        pygame.draw.lines(world, (99, 55, 45), False, points, 2)
        pygame.draw.lines(world, (186, 105, 71), False, [(x, y+2) for x, y in points], 1)
    # Craters are traversable depressions, with offset rims and shaded floors.
    for x, y, radius in ((390, 270, 130), (1250, 760, 175), (2120, 1040, 140),
                         (850, 1500, 115), (1650, 1650, 95)):
        pygame.draw.ellipse(world, (112, 59, 46), (x-radius, y-radius//2+10, radius*2, radius))
        pygame.draw.ellipse(world, (198, 119, 78), (x-radius, y-radius//2-8, radius*2, radius))
        pygame.draw.ellipse(world, (126, 66, 51), (x-radius+13, y-radius//2+2, radius*2-26, radius-14))
        pygame.draw.ellipse(world, (145, 76, 56), (x-radius+23, y-radius//2+12, radius*2-46, radius-28))
        pygame.draw.arc(world, (92, 53, 45), (x-radius+13, y-radius//2+2, radius*2-26, radius-14), 0, math.pi, 5)
        pygame.draw.arc(world, (211, 132, 88), (x-radius, y-radius//2-8, radius*2, radius), math.pi, 2*math.pi, 4)
    # Solid formations stay well clear of the routes and mission sites.
    obstacles = []
    for _ in range(240):
        x, y = rng.randrange(60, 2340), rng.randrange(60, 1740)
        radius = rng.randrange(18, 43)
        if clear_route((x, y), radius + 85) or any(math.hypot(x-p[0], y-p[1]) < radius+110 for p in (BASE, *TARGETS)):
            continue
        rect = pygame.Rect(x-radius, y-radius//2, radius*2, radius)
        obstacles.append(rect)
        pygame.draw.ellipse(world, (83, 48, 40), rect.move(8, 8))
        pygame.draw.ellipse(world, (105, 61, 49), rect)
        pygame.draw.polygon(world, (138, 82, 62), [(rect.left+3, y), (x-radius//2, rect.top+3), (x+radius//3, rect.top+2), (rect.right-6, y-2), (x, y+2)])
        pygame.draw.line(world, (171, 108, 75), (x-radius//2, rect.top+4), (x+radius//3, rect.top+3), 2)
    return world, obstacles


def draw_base(surface, offset):
    x, y = BASE[0]-offset[0], BASE[1]-offset[1]
    pygame.draw.ellipse(surface, (84, 48, 40), (x-80, y-43, 170, 100))
    pygame.draw.circle(surface, (187, 171, 147), (x, y), 52)
    pygame.draw.circle(surface, (225, 215, 191), (x, y), 43)
    pygame.draw.circle(surface, (111, 137, 141), (x, y), 30)
    pygame.draw.circle(surface, (164, 192, 187), (x-8, y-9), 17)
    pygame.draw.rect(surface, (203, 193, 172), (x+38, y-14, 38, 28), border_radius=5)
    pygame.draw.rect(surface, (48, 70, 83), (x-80, y-24, 28, 48))
    for yy in (y-19, y-7, y+5, y+17):
        pygame.draw.line(surface, (110, 154, 166), (x-77, yy), (x-55, yy), 2)
    pygame.draw.line(surface, (218, 209, 186), (x+24, y-37), (x+37, y-67), 3)
    pygame.draw.circle(surface, (239, 176, 97), (x+37, y-67), 4)
