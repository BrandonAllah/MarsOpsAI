import math
import os
import tempfile
import unittest
from unittest.mock import patch
import pygame
from discoveries import DiscoveryJournal
from expedition import ExpeditionMap
from mission import Mission
from terrain import BASE
from systems import RoverSystems, snapshot, restore, save_progress, load_progress


class ExpeditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_seeded_progressive_maps_and_clear_routes(self):
        for number in range(1, 6):
            exp = ExpeditionMap(number)
            same = ExpeditionMap(number)
            self.assertEqual(exp.targets, same.targets)
            self.assertEqual(exp.types, same.types)
            self.assertEqual(len(exp.targets), 3 + 2*(number-1))
            self.assertEqual(len(set(exp.targets)), len(exp.targets))
            self.assertGreaterEqual(exp.size[0], 2400)
            for point in exp.targets:
                for i in range(41):
                    t = i/40
                    rect = pygame.Rect(0, 0, 50, 50)
                    rect.center = (round(BASE[0]+t*(point[0]-BASE[0])), round(BASE[1]+t*(point[1]-BASE[1])))
                    self.assertFalse(any(rect.colliderect(rock) for rock in exp.obstacles_near(rect)))
            self.assertLessEqual(len(exp.cache), 48)
        self.assertNotEqual(ExpeditionMap(2, 12).targets, ExpeditionMap(2, 13).targets)

    def test_scanner_cost_cooldown_and_remaining_targets(self):
        m, s, exp = Mission(), RoverSystems(), ExpeditionMap()
        point = exp.targets[0]
        result = s.scan(m, exp, point)
        self.assertIn(point, result[0])
        self.assertEqual(m.battery, 97)
        self.assertIsNone(s.scan(m, exp, point))
        s.scan_cooldown = 0
        m.samples = [r for r in m.samples if r.center != point]
        self.assertNotIn(point, s.scan(m, exp, point)[0])

    def test_damage_repairs_and_weather_speed(self):
        system = RoverSystems()
        system.damage_collision()
        self.assertLess(system.wheels, 100)
        system.repair(20, 0)
        self.assertEqual(system.wheels, 100)
        system.time = 110
        self.assertEqual(system.weather, 'Dust storm')
        system.update(1, 1, 0, 240)
        self.assertLess(system.vx, 240)

    def test_save_restore_and_corrupt_files(self):
        mission, exp, journal, system = Mission(), ExpeditionMap(), DiscoveryJournal(), RoverSystems()
        rover = pygame.Rect(BASE[0]-25, BASE[1]-25, 50, 50)
        exp.reveal(BASE)
        journal.investigate(exp.discoveries[0])
        mission.levels['scanner'] = 1
        mission.credits = 42
        data = snapshot(mission, exp, journal, rover, system,
                        dict(missions=0, distance=23, samples=0, credits=0, upgrades=1, regions=4), set())
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            path = os.path.join(directory, 'save.json')
            self.assertTrue(save_progress(data, path))
            recovered = load_progress(path)
            journal2, rover2, system2 = DiscoveryJournal(), rover.copy(), RoverSystems()
            loaded = restore(recovered, journal2, rover2, system2)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded[0].credits, 42)
            self.assertEqual(loaded[0].levels['scanner'], 1)
            self.assertEqual(journal2.found, {'jezero'})
            self.assertEqual(loaded[1].explored, exp.explored)
            with open(path, 'w') as file: file.write('{broken')
            self.assertIsNone(load_progress(path))
        data['position'] = [-1, -1]
        self.assertIsNone(restore(data, journal, rover, system))

    def test_later_mission_and_early_base_visit(self):
        mission = Mission()
        mission.start()
        self.assertEqual(mission.required, 5)
        self.assertEqual(len(mission.samples), 5)
        self.assertFalse(mission.update(BASE, 1, False))
        self.assertFalse(mission.completed)
        mission.samples.clear()
        self.assertTrue(mission.update(BASE, 1, False))
        self.assertFalse(mission.update(BASE, 1, False))

    def test_briefing_uses_dynamic_count_and_safe_route_instruction(self):
        import ai_copilot
        with patch.object(ai_copilot, 'client') as fake_client:
            mock = fake_client.models.generate_content
            mock.return_value.text = 'Continue exploring.'
            ai_copilot.get_mission_advice(60, 2, 50, 50, [], required_samples=7)
        text = mock.call_args.kwargs['contents']
        self.assertIn('Samples collected: 2/7', text)
        self.assertIn('Never claim a route is safe', text)


if __name__ == '__main__':
    unittest.main()
