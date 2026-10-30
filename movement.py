"""Rover motion and rock collision handling in world coordinates."""
import math
import pygame


def move_rover(rover, x, y, dx, dy, speed, dt, rocks, world_size):
    length = math.hypot(dx, dy)
    if length:
        dx, dy = dx / length, dy / length
    old_x, old_y = rover.x, rover.y
    x += dx * speed * dt
    rover.x = round(x)
    if any(rover.colliderect(rock) for rock in rocks):
        rover.x, x = old_x, float(old_x)
    y += dy * speed * dt
    rover.y = round(y)
    if any(rover.colliderect(rock) for rock in rocks):
        rover.y, y = old_y, float(old_y)
    before_clamp = rover.topleft
    rover.clamp_ip(pygame.Rect(0, 0, *world_size))
    if rover.x != before_clamp[0]:
        x = float(rover.x)
    if rover.y != before_clamp[1]:
        y = float(rover.y)
    return x, y, rover.topleft != (old_x, old_y)
