"""Tiny synthesized UI tones; the game still works when audio is unavailable."""
from array import array
import math
import pygame


def make_tone():
    try:
        settings = pygame.mixer.get_init()
        if not settings or settings[1] != -16:
            return None
        rate, _, channels = settings
        data = array('h')
        for index in range(int(rate * .07)):
            envelope = 1 - index / (rate * .07)
            value = int(3200 * envelope * math.sin(2 * math.pi * 660 * index / rate))
            data.extend([value] * channels)
        return pygame.mixer.Sound(buffer=data.tobytes())
    except (pygame.error, ValueError):
        return None


def play(sound):
    if sound:
        try:
            sound.play()
        except pygame.error:
            pass
