# MarsOps AI

Run the game from this folder with `.venv/bin/python main.py` (or use a Python environment with Pygame, python-dotenv, and google-genai installed).

- Drive with **WASD** and press **E** near a sample to collect it.
- Collect all three samples, then return to the research base to complete the mission and earn 200 research credits. The base recharges the rover automatically.
- At the base, press **U** to open or close upgrades. Press **1**, **2**, or **3** to upgrade battery capacity, speed, or sample collection range. Each has three levels; costs rise from 100 to 150 and 200 credits.
- After completing a mission, press **N** to begin another. If the battery runs out away from the base, press **R** to restart without a reward.
- Press **H** for a Gemma 4 briefing. The rover's position and the minimap use world coordinates.

Credits and upgrades last for the current game session; they are not saved after the game closes. Terrain and sample locations are deterministic and repeat between missions.

Run the offline gameplay tests with `.venv/bin/python -m unittest -v test_mission`. The existing `test_ai.py` and `test_copilot.py` are live API scripts and require a working Gemma connection.
