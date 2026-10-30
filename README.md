# MarsOps AI v0.6

A Pygame Mars rover game with procedurally generated expeditions and a Gemma 4 copilot. The map combines discoveries from different real places for education; it is not a geographically accurate reconstruction. The generated collectible rocks are fictional game samples, not real discoveries.

## Install and run

From the existing project folder, use the existing environment:

```bash
cd /Users/brandonallah/Projects/MarsOpsAI
.venv/bin/python main.py
```

To create your own environment in this folder, install Python 3, then run `python3 -m venv .venv` and `.venv/bin/pip install pygame python-dotenv google-genai`. Gemma needs the existing `GEMINI_API_KEY` in `.env`; never share the file. The game and its local NASA facts work when the API is unavailable.

## Controls

- **Enter** starts or resumes from the title screen; **WASD** drives, with acceleration and steering in the direction of travel.
- **F** scans nearby samples and sites. The scanner uses battery and has a cooldown; detected targets appear on the minimap. Scan feedback identifies simulated rock types, rarity, and research values.
- **E** collects a nearby sample or investigates a landmark. If both overlap, E collects the sample first; press E again to investigate. In a discovery panel, **F** asks Gemma for more and **E/Esc** closes it.
- **J** opens the discovery journal. Use **Left/Right** to select, **Up/Down** to scroll, and **J/Esc** to close. NASA source links and real locations are shown in the journal. AI explanations may be mistaken; refer to the NASA source.
- **T** sets a waypoint to the nearest scanned sample, or to base when none is scanned. Its minimap line indicates bearing only and is not a validated safe route. **H** requests a mission briefing. Use **Up/Down** to scroll the currently open panel; holding a key scrolls continuously. **Page Up/Page Down** and the mouse wheel also work. The copilot receives scrolling when no modal panel is open.
- The compass is north-up: cyan shows rover heading (0° north, 90° east), while amber points toward the selected destination. It points to base when no sample waypoint is selected.
- **U** opens upgrades at base. **1–5** buy battery, speed, scanner range, scanner efficiency, or repair speed upgrades. **N** launches the next expedition after completion; **R** restarts the current expedition if the battery is depleted.
- **I** shows statistics and achievements. **Esc** pauses. **V** toggles weather and dust particles; **[ / ]** shortens or lengthens the day cycle in 60-second steps (60–900 seconds).

## Missions and systems

Mission N requires `3 + 2 × (N - 1)` samples. Each mission uses a reproducible seed (`4026 + N - 1`), a larger chunk-rendered map, and new target placements. Explore to reveal the map; scanning reveals targets on the minimap. The base automatically recharges, repairs and unloads cargo for research credits. Return with all samples to earn the mission reward; returning earlier is useful for recharging and unloading. Optional scanning and landmark investigations pay extra when their data reaches base.

Dunes gradually wear wheels, collisions damage the rover, and dust storms reduce speed and visibility while gradually affecting scientific equipment. Damage limits performance; the base repairs it. Night lowers visibility and charging speed; headlights activate automatically. Visual particles can be disabled without removing weather's gameplay effects.

Progress, upgrades, cargo, discovered sites, map exploration, statistics and achievements save to `marsops_save.json` in this folder approximately every 20 seconds and on exit. The file contains no credentials and is ignored by Git. A missing or invalid save starts a new game. The save is written through an atomic replacement. Keep a copy of this file if you want a backup of your progress.

## Tests

Run the offline tests:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m unittest -v test_mission test_discoveries test_expedition test_game_loop test_navigation
```

The existing `test_ai.py` and `test_copilot.py` contact the live Gemma API, so they require network access, a configured key, and model availability.
