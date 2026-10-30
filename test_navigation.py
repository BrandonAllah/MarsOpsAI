import math
import unittest
import pygame
from navigation import bearing_degrees, heading_degrees, smooth_heading
from ui_navigation import ScrollState, focused_panel, driving_allowed, wrap_text, draw_scrolling_text
from systems import RoverSystems


class NavigationTests(unittest.TestCase):
    def test_cardinal_bearings(self):
        for target, expected in (((0, -1), 0), ((1, 0), 90), ((0, 1), 180), ((-1, 0), 270)):
            self.assertAlmostEqual(bearing_degrees((0, 0), target), expected)
            self.assertAlmostEqual(heading_degrees(math.atan2(target[0], -target[1])), expected)
        self.assertIsNone(bearing_degrees((3, 4), (3, 4)))
        self.assertAlmostEqual(bearing_degrees((100, 100), (110, 90)), 45)

    def test_wrapping_and_smooth_short_turn(self):
        self.assertAlmostEqual(heading_degrees(-math.pi/2), 270)
        self.assertAlmostEqual(heading_degrees(2*math.pi), 0)
        result = smooth_heading(math.radians(359), math.radians(1), .1)
        self.assertLess(min(heading_degrees(result), 360-heading_degrees(result)), 2)
        rover = RoverSystems()
        rover.angle = 0
        for _ in range(100): rover.orient(1, 0, .05)
        self.assertAlmostEqual(heading_degrees(rover.angle), 90, places=4)
        before = rover.angle
        rover.orient(0, 0, .05)
        self.assertEqual(rover.angle, before)

    def test_scroll_clamps_and_continuous_motion(self):
        scroll = ScrollState()
        scroll.extent(1000, 200)
        for _ in range(60): scroll.move(240 / 60)
        self.assertAlmostEqual(scroll.offset, 240)
        scroll.move(10000)
        self.assertEqual(scroll.offset, 800)
        scroll.move(-10000)
        self.assertEqual(scroll.offset, 0)
        scroll.move(700)
        scroll.extent(150, 200)
        self.assertEqual((scroll.maximum, scroll.offset), (0, 0))

    def test_focus_and_driving_priority(self):
        self.assertEqual(focused_panel(True, False, False, False, False, False), 'ai')
        self.assertEqual(focused_panel(True, False, False, True, False, True), 'journal')
        self.assertEqual(focused_panel(True, False, False, False, True, True), 'discovery')
        self.assertEqual(focused_panel(True, True, True, True, True, True), 'pause')
        self.assertEqual(focused_panel(False, True, True, True, True, True), 'start')
        self.assertTrue(driving_allowed(True, False, False, False, False, False, False, 10))
        for modal in range(1, 5):
            flags = [False] * 4
            flags[modal-1] = True
            self.assertFalse(driving_allowed(True, *flags, False, False, 10))
        self.assertFalse(driving_allowed(True, False, False, False, False, False, True, 10))
        self.assertFalse(driving_allowed(True, False, False, False, False, False, False, 0))

    def test_wrapping_and_clipping_long_text(self):
        pygame.font.init()
        font = pygame.font.Font(None, 18)
        surface = pygame.Surface((200, 140))
        rect = pygame.Rect(20, 30, 150, 70)
        scroll = ScrollState()
        text = 'https://science.nasa.gov/' + 'mars/'*30 + '\n' + 'long text '*60
        self.assertTrue(all(font.size(line)[0] <= rect.width-16 for line in wrap_text(text, font, rect.width-16)))
        draw_scrolling_text(surface, rect, [(text, (255,255,255))], font, scroll, 20)
        self.assertGreater(scroll.maximum, 0)
        scroll.move(10000)
        draw_scrolling_text(surface, rect, [(text, (255,255,255))], font, scroll, 20)
        self.assertEqual(scroll.offset, scroll.maximum)
        self.assertEqual(surface.get_at((20, 20))[:3], (0, 0, 0))
        self.assertEqual(surface.get_at((20, 110))[:3], (0, 0, 0))


if __name__ == '__main__': unittest.main()
