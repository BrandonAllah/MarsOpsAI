"""Original top-down rover art, cached and rotated to follow travel direction."""
import math
import pygame


def build_rover(phase=0):
    art = pygame.Surface((88, 100), pygame.SRCALPHA)
    # Six wheels, three axles, and suspension arms.
    for y in (22, 45, 68):
        pygame.draw.line(art, (116, 119, 112), (16, y+6), (72, y+6), 4)
        for x in (8, 68):
            pygame.draw.rect(art, (31, 37, 40), (x, y, 12, 20), border_radius=3)
            for stripe in ((3, 8, 13) if phase else (5, 10, 15)):
                pygame.draw.line(art, (93, 99, 96), (x+2, y+stripe), (x+10, y+stripe), 1)
    pygame.draw.rect(art, (134, 137, 128), (22, 12, 44, 68), border_radius=8)
    pygame.draw.rect(art, (222, 219, 198), (26, 15, 36, 60), border_radius=6)
    pygame.draw.rect(art, (76, 102, 109), (31, 31, 26, 22), border_radius=3)
    for x in (34, 41, 48, 55):
        pygame.draw.line(art, (145, 179, 177), (x, 33), (x, 50), 1)
    pygame.draw.circle(art, (186, 175, 148), (48, 65), 7)
    pygame.draw.circle(art, (62, 77, 79), (48, 65), 4)
    pygame.draw.line(art, (214, 205, 182), (37, 27), (36, 8), 4)
    pygame.draw.rect(art, (236, 226, 202), (27, 4, 19, 10), border_radius=2)
    pygame.draw.circle(art, (45, 75, 85), (32, 9), 3)
    pygame.draw.circle(art, (45, 75, 85), (42, 9), 3)
    pygame.draw.circle(art, (241, 190, 106), (31, 20), 2)
    pygame.draw.circle(art, (241, 190, 106), (57, 20), 2)
    return art


def draw_rover(screen, art, center, angle, wheel_phase, light):
    x, y = center
    pygame.draw.ellipse(screen, (71, 43, 39), (x-29, y-13, 64, 40))
    if light < .55:
        forward = (math.sin(angle), -math.cos(angle))
        side = (math.cos(angle), math.sin(angle))
        points = [(x + forward[0]*20, y + forward[1]*20),
                  (x + forward[0]*150 + side[0]*50, y + forward[1]*150 + side[1]*50),
                  (x + forward[0]*150 - side[0]*50, y + forward[1]*150 - side[1]*50)]
        beam = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(beam, (255, 225, 155, 38), points)
        screen.blit(beam, (0, 0))
    rotated = pygame.transform.rotate(art[int(bool(wheel_phase))], -math.degrees(angle))
    screen.blit(rotated, rotated.get_rect(center=(x, y)))
