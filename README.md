# MarsOps AI

Run the game from this folder with `.venv/bin/python main.py` (or use a Python environment with Pygame, python-dotenv, and google-genai installed).

- Drive with **WASD** and press **E** near a sample to collect it.
- Collect all three samples, then return to the research base to complete the mission and earn 200 research credits. The base recharges the rover automatically.
- At the base, press **U** to open or close upgrades. Press **1**, **2**, or **3** to upgrade battery capacity, speed, or sample collection range. Each has three levels; costs rise from 100 to 150 and 200 credits.
- After completing a mission, press **N** to begin another. If the battery runs out away from the base, press **R** to restart without a reward.
- Press **H** for a Gemma 4 briefing. The rover's position and the minimap use world coordinates.

Credits and upgrades last for the current game session; they are not saved after the game closes. Terrain and sample locations are deterministic and repeat between missions.

Run the offline gameplay tests with `.venv/bin/python -m unittest -v test_mission`. The existing `test_ai.py` and `test_copilot.py` are live API scripts and require a working Gemma connection.

## NASA Discovery Update

The map includes three landmarks inspired by NASA discoveries: Jezero Crater, Cheyava Falls, and Martian Blueberries. They are placed together for educational gameplay; the map is not a geographically accurate reconstruction of Mars. Uninvestigated landmarks have blue scan rings and outlined yellow minimap markers. Investigated landmarks turn green.

- Drive near a landmark and press **E** to investigate. If a collectible sample is also in reach, **E** collects the sample first; press **E** again to investigate.
- The discovery panel shows NASA-sourced facts and the source URL. Press **F** while it is open for another Gemma explanation, or **E/Esc** to close it. Gemma runs in the background; if unavailable, the copilot displays the local verified facts. Use Page Up/Page Down or the mouse wheel over the copilot to scroll longer responses.
- Press **J** to open the discovery journal, use the **arrow keys** to select an entry, and press **J** or **Esc** to close it. Journal progress is retained during repeat missions but resets when the game closes.
- AI-generated explanations can be mistaken; the journal's NASA sources are the reference. In particular, potential biosignatures at Cheyava Falls are not confirmed evidence of life.

Run the offline tests with `.venv/bin/python -m unittest -v test_mission test_discoveries`.
