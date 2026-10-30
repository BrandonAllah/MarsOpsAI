import unittest
from unittest.mock import patch
import pygame
from discoveries import DISCOVERIES, DiscoveryJournal, interaction_choice, nearest_discovery
from movement import move_rover
from terrain import BASE, TARGETS, make_world


class DiscoveryTests(unittest.TestCase):
    def test_proximity_and_priority(self):
        item = DISCOVERIES[0]
        self.assertEqual(nearest_discovery(item.position), item)
        self.assertIsNone(nearest_discovery((0, 0)))
        rover = pygame.Rect(0, 0, 50, 50)
        rover.center = item.position
        sample = pygame.Rect(item.position[0]-10, item.position[1]-10, 20, 20)
        self.assertEqual(interaction_choice(rover, [sample], 15)[0], 'sample')
        self.assertEqual(interaction_choice(rover, [], 15), ('discovery', item))

    def test_journal_tracks_once_and_navigation_wraps(self):
        journal = DiscoveryJournal()
        self.assertFalse(journal.is_open)
        journal.toggle()
        self.assertTrue(journal.is_open)
        journal.investigate(DISCOVERIES[1])
        journal.investigate(DISCOVERIES[1])
        self.assertEqual(len(journal.found), 1)
        self.assertTrue(journal.is_found(DISCOVERIES[1]))
        self.assertFalse(journal.is_found(DISCOVERIES[0]))
        journal.move(len(DISCOVERIES) - 1)
        self.assertEqual(journal.current, DISCOVERIES[0])
        journal.toggle()
        self.assertFalse(journal.is_open)

    def test_movement_collision_bounds_and_diagonal_speed(self):
        rover = pygame.Rect(10, 10, 50, 50)
        x, y, moved = move_rover(rover, 10, 10, 1, 0, 240, .1, [pygame.Rect(65, 0, 30, 100)], (200, 200))
        self.assertFalse(moved)
        self.assertEqual((x, y), (10, 10))
        x, y, moved = move_rover(rover, x, y, -1, 0, 240, 1, [], (200, 200))
        self.assertEqual(rover.left, 0)
        rover.topleft = (10, 10)
        x, y, moved = move_rover(rover, 10, 10, 1, 1, 100, 1, [], (200, 200))
        self.assertAlmostEqual(x, 10 + 100 / 2**.5)
        self.assertAlmostEqual(y, x)

    def test_landmarks_are_on_clear_routes(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        _, rocks = make_world()
        for item, start in zip(DISCOVERIES, (BASE, TARGETS[0], BASE)):
            for step in range(101):
                fraction = step / 100
                rover = pygame.Rect(0, 0, 50, 50)
                rover.center = tuple(round(a + (b-a)*fraction) for a, b in zip(start, item.position))
                self.assertFalse(any(rover.colliderect(rock) for rock in rocks), item.name)

    def test_ai_prompt_uses_verified_facts_and_uncertainty(self):
        import ai_copilot
        with patch.object(ai_copilot, 'client') as fake_client:
            generate = fake_client.models.generate_content
            generate.return_value.text = 'Potential evidence needs further study.'
            result = ai_copilot.get_discovery_explanation(DISCOVERIES[1], more=True)
        prompt = generate.call_args.kwargs['contents']
        self.assertIn(DISCOVERIES[1].description, prompt)
        self.assertIn(DISCOVERIES[1].significance, prompt)
        self.assertIn('Do not claim life was found', prompt)
        self.assertIn('different angle', prompt)
        self.assertEqual(result, 'Potential evidence needs further study.')

    def test_ai_failure_uses_nasa_facts(self):
        import ai_copilot
        with patch.object(ai_copilot, 'get_discovery_explanation', side_effect=RuntimeError('offline')):
            text = ai_copilot.discovery_briefing(DISCOVERIES[1])
        self.assertIn('AI unavailable', text)
        self.assertIn(DISCOVERIES[1].description, text)
        self.assertIn(DISCOVERIES[1].significance, text)


if __name__ == '__main__':
    unittest.main()
