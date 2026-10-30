"""Headless end-to-end exercise of real game-loop transitions, without live API or saves."""
import os
import subprocess
import sys
import unittest


class GameLoopTest(unittest.TestCase):
    def test_complete_upgrade_and_next_expedition(self):
        script = r'''
import inspect, runpy, pygame, systems, ai_copilot
systems.load_progress = lambda: None
systems.save_progress = lambda *args: True
ai_copilot.discovery_briefing = lambda *args: 'Local briefing'
frames = [0]
flip = pygame.display.flip
def post(key): pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
def place(state, position):
    rover = state['rover']; rover.center = position
    state['rover_x'], state['rover_y'] = float(rover.x), float(rover.y)
    state['rover_systems'].vx = state['rover_systems'].vy = 0
def step():
    frames[0] += 1
    frame = frames[0]
    s = inspect.currentframe().f_back.f_globals
    if frame == 1: post(pygame.K_RETURN)
    if frame == 3:
        place(s, s['expedition'].targets[0]); post(pygame.K_f)
    if frame == 5: post(pygame.K_e)
    if frame == 7:
        assert s['mission'].collected == 1 and s['active_discovery'] is None
        post(pygame.K_e)
    if frame == 9:
        assert s['active_discovery'] is not None
        post(pygame.K_f)
    if frame == 11: post(pygame.K_e)
    if frame == 13:
        place(s, s['expedition'].targets[1]); post(pygame.K_e)
    if frame == 15:
        place(s, s['expedition'].targets[2]); post(pygame.K_e)
    if frame == 17:
        assert s['mission'].objective == 'Return to Base'
        place(s, (450,900))
    if frame == 19:
        assert s['mission'].completed and s['mission'].credits >= 200
        assert s['mission'].optional_site_paid and s['mission'].optional_paid
        post(pygame.K_u)
    if frame == 21: post(pygame.K_1)
    if frame == 23:
        assert s['mission'].levels['battery'] == 1
        post(pygame.K_n)
    if frame == 25:
        assert s['mission'].number == 2 and len(s['mission'].samples) == 5
        assert not s['mission'].completed
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    flip()
pygame.display.flip = step
runpy.run_path('main.py', run_name='__main__')
'''
        environment = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYTHONPYCACHEPREFIX='./.cache')
        result = subprocess.run([sys.executable, '-c', script], cwd=os.path.dirname(__file__), env=environment,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_scroll_focus_and_wasd_through_game_loop(self):
        script = r'''
import inspect, runpy, pygame, systems
systems.load_progress = lambda: None
systems.save_progress = lambda *args: True
frames = [0]; held = set(); state_at_start = [0]; saved_ai = [0]
flip = pygame.display.flip
class Pressed:
    def __getitem__(self, key): return key in held
pygame.key.get_pressed = lambda: Pressed()
def post(key): pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
def step():
    frames[0] += 1
    n = frames[0]
    s = inspect.currentframe().f_back.f_globals
    if n == 1: post(pygame.K_RETURN)
    if n == 2: s['ai_message'] = 'Detailed briefing. ' * 200
    if n == 4: post(pygame.K_DOWN); held.add(pygame.K_DOWN)
    if n == 7:
        assert s['scroll_states']['ai'].offset > 30
        held.clear(); saved_ai[0] = s['scroll_states']['ai'].offset; post(pygame.K_j)
    if n == 9:
        assert s['journal'].is_open
        post(pygame.K_DOWN); held.add(pygame.K_DOWN)
    if n == 12:
        assert s['journal'].selected == 0
        assert s['scroll_states']['journal'].offset > 0
        assert s['scroll_states']['ai'].offset == saved_ai[0]
        held.clear(); post(pygame.K_RIGHT)
    if n == 14:
        assert s['journal'].selected == 1
        assert s['scroll_states']['journal'].offset == 0
        post(pygame.K_j)
    if n == 16:
        state_at_start[0] = s['rover'].centerx
        held.add(pygame.K_d)
    if n == 36:
        held.clear()
        assert s['rover'].centerx > state_at_start[0]
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    flip()
pygame.display.flip = step
runpy.run_path('main.py', run_name='__main__')
'''
        environment = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYTHONPYCACHEPREFIX='./.cache')
        result = subprocess.run([sys.executable, '-c', script], cwd=os.path.dirname(__file__), env=environment,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
