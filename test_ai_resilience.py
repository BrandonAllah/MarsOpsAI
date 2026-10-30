import unittest
from unittest.mock import patch
import ai_copilot
from discoveries import DISCOVERIES


class DeadlineError(Exception):
    code = 504


class AuthenticationError(Exception):
    code = 403


class ResilienceTests(unittest.TestCase):
    def test_timeout_fallback_has_safe_status(self):
        with patch.object(ai_copilot, 'get_discovery_explanation', side_effect=DeadlineError('sensitive details')):
            response = ai_copilot.discovery_briefing(DISCOVERIES[0])
        self.assertTrue(response.offline)
        self.assertIn('timed out', response)
        self.assertIn(DISCOVERIES[0].description, response)
        self.assertNotIn('sensitive details', response)

    def test_mission_fallback_and_authentication_message(self):
        with patch.object(ai_copilot, 'generate_ai_response', side_effect=AuthenticationError('secret')):
            response = ai_copilot.get_mission_advice(50, 1, 10, 20, [])
        self.assertTrue(response.offline)
        self.assertIn('rejected', response)
        self.assertNotIn('secret', response)

    def test_online_response_remains_string_compatible(self):
        with patch.object(ai_copilot, 'get_discovery_explanation', return_value='Science explanation'):
            response = ai_copilot.discovery_briefing(DISCOVERIES[0])
        self.assertIsInstance(response, str)
        self.assertFalse(response.offline)
        self.assertIn('Science explanation', response)

    def test_request_timeout_increased(self):
        self.assertGreaterEqual(ai_copilot.API_TIMEOUT_MS, 60000)


if __name__ == '__main__': unittest.main()
