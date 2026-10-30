import unittest
from unittest.mock import patch
import pygame
from mission import Mission, REWARD
from terrain import BASE, TARGETS


class MissionTests(unittest.TestCase):
    def setUp(self):
        self.mission = Mission()
        self.rover = pygame.Rect(0, 0, 50, 50)

    def test_return_required_and_reward_only_once(self):
        for target in TARGETS:
            self.rover.center = target
            self.assertEqual(self.mission.collect(self.rover), 1)
        self.assertEqual(self.mission.objective, "Return to Base")
        self.assertFalse(self.mission.update(TARGETS[-1], 1, False))
        self.assertEqual(self.mission.credits, 0)
        self.assertTrue(self.mission.update(BASE, 1, False))
        self.assertEqual(self.mission.objective, "Mission Complete")
        self.assertEqual(self.mission.credits, REWARD)
        self.assertFalse(self.mission.update(BASE, 1, False))
        self.assertEqual(self.mission.credits, REWARD)

    def test_recharging_is_limited_to_base_and_capacity(self):
        self.mission.battery = 50
        self.mission.update(TARGETS[0], 1, False)
        self.assertEqual(self.mission.battery, 50)
        self.mission.update(BASE, 1, False)
        self.assertEqual(self.mission.battery, 65)
        self.mission.update(BASE, 100, False)
        self.assertEqual(self.mission.battery, self.mission.capacity)

    def test_upgrades_have_cost_and_gameplay_effects(self):
        self.assertFalse(self.mission.upgrade("battery"))
        self.mission.credits = 1000
        self.assertTrue(self.mission.upgrade("battery"))
        self.assertTrue(self.mission.upgrade("speed"))
        self.assertTrue(self.mission.upgrade("scanner"))
        self.assertEqual((self.mission.capacity, self.mission.speed, self.mission.scanner_range), (125, 270, 30))
        self.assertEqual(self.mission.credits, 700)
        self.assertEqual(self.mission.upgrade_cost("battery"), 150)
        self.rover.center = (TARGETS[0][0] - 55, TARGETS[0][1])
        self.assertEqual(self.mission.collect(self.rover), 1)
        self.assertTrue(self.mission.upgrade("battery"))
        self.assertTrue(self.mission.upgrade("battery"))
        self.assertFalse(self.mission.upgrade("battery"))

    def test_next_mission_resets_progress_but_keeps_upgrades_and_credits(self):
        self.mission.credits = 250
        self.mission.upgrade("battery")
        self.mission.samples.clear()
        self.mission.completed = True
        self.mission.battery = 0
        self.mission.start()
        self.assertEqual((self.mission.number, self.mission.collected, self.mission.battery), (2, 0, 125))
        self.assertEqual(self.mission.credits, 150)
        self.assertFalse(self.mission.completed)

    def test_copilot_receives_current_objective(self):
        import ai_copilot
        with patch.object(ai_copilot.client.models, 'generate_content') as generate:
            generate.return_value.text = 'Return to base.'
            answer = ai_copilot.get_mission_advice(75, 3, 1900, 1350, [],
                                                   'Return to Base', 125, 200, False)
        self.assertEqual(answer, 'Return to base.')
        prompt = generate.call_args.kwargs['contents']
        for detail in ('Objective: Return to Base', 'Battery: 75.0 / 125', 'Research credits: 200'):
            self.assertIn(detail, prompt)


if __name__ == '__main__':
    unittest.main()
