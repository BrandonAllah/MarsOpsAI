
import pygame
import threading
import queue
import math
import webbrowser

from terrain import BASE, draw_base
from expedition import ExpeditionMap, ROCK_TYPES, CELL
from systems import RoverSystems, load_progress, save_progress, snapshot as make_snapshot, restore
from rover_art import build_rover, draw_rover
from feedback import make_tone, play
from mission import Mission, MAX_LEVEL, REWARD
from movement import move_rover
from ui_navigation import ScrollState, focused_panel, driving_allowed, draw_scrolling_text, draw_compass

from ai_copilot import get_mission_advice, discovery_briefing
from discoveries import DISCOVERIES, DiscoveryJournal, interaction_choice
from gallery import DiscoveryImageCache, gallery_blocks, journal_is_unlocked, draw_gallery

# ======================================
# MARSOPS AI - ROVER EXPLORER
# ======================================

pygame.init()

# Window layout
GAME_WIDTH = 900
PANEL_WIDTH = 350
WIDTH = GAME_WIDTH + PANEL_WIDTH
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("MarsOps AI - Rover Explorer")

clock = pygame.time.Clock()

# Colors
MARS_RED = (160, 75, 45)
ROVER_WHITE = (220, 220, 220)
WHEEL_BLACK = (40, 40, 40)
ROCK_BROWN = (95, 55, 40)
SAMPLE_BLUE = (80, 220, 255)
WHITE = (255, 255, 255)
GREEN = (100, 255, 130)
PANEL_BG = (24, 30, 42)
PANEL_GRAY = (180, 190, 205)
YELLOW = (255, 215, 100)

# Fonts
font = pygame.font.SysFont("Arial", 24)
small_font = pygame.font.SysFont("Arial", 18)
title_font = pygame.font.SysFont("Arial", 28, bold=True)

# World coordinates stay independent of the camera and the side panel.
mission = Mission()
expedition = ExpeditionMap(mission.number)
rover_systems = RoverSystems()
rover_art = (build_rover(0), build_rover(1))
ui_tone = make_tone()
particles = []
fog_layer = pygame.Surface((GAME_WIDTH, HEIGHT), pygame.SRCALPHA)
dark_layer = pygame.Surface((GAME_WIDTH, HEIGHT), pygame.SRCALPHA)
stats = {"missions": 0, "distance": 0.0, "samples": 0, "credits": 0, "upgrades": 0, "regions": 0}
achievements = set()
started = False
paused = False
stats_menu = False
save_timer = 0.0
ui_fade = 0.0
previous_view = None
waypoint = None
scan_message = "F: scan for nearby samples"
rover = pygame.Rect(BASE[0] - 25, BASE[1] - 25, 50, 50)
journal = DiscoveryJournal()
image_cache = DiscoveryImageCache()
discovery_explanations = {}
discovery_loading_id = None
active_discovery = None
upgrade_menu = False
menu_notice = ""
rover_x, rover_y = float(rover.x), float(rover.y)
camera_x = max(0, min(expedition.size[0] - GAME_WIDTH, rover.centerx - GAME_WIDTH / 2))
camera_y = max(0, min(expedition.size[1] - HEIGHT, rover.centery - HEIGHT / 2))
expedition.reveal(BASE)

# Resume an interrupted expedition when a valid save is available.
saved = load_progress()
if saved:
    restored = restore(saved, journal, rover, rover_systems)
    if restored:
        mission, expedition, stats, achievements = restored
        rover_x, rover_y = float(rover.x), float(rover.y)
        camera_x = max(0, min(expedition.size[0]-GAME_WIDTH, rover.centerx-GAME_WIDTH/2))
        camera_y = max(0, min(expedition.size[1]-HEIGHT, rover.centery-HEIGHT/2))

# ======================================
# AI COPILOT SETTINGS
# ======================================

ai_message = (
    "Welcome to MarsOps AI!\n\n"
    "Press H to request a mission briefing.\n\n"
    "I will analyze your rover's battery, "
    "position, and remaining samples."
)

ai_loading = False
ai_failed = False
ai_request_id = 0
scroll_states = {name: ScrollState() for name in ("ai", "journal", "discovery", "upgrades", "stats", "start", "pause")}
last_ai_message = ai_message

# Thread-safe communication
ai_results = queue.Queue()


def request_ai_advice(
    current_battery,
    collected,
    x,
    y,
    remaining,
    objective,
    capacity,
    credits,
    at_base,
    required,
    snapshot
):
    """
    Contact Gemma in a background thread.

    The worker never draws to the screen or
    changes Pygame UI state directly.
    """
    try:
        advice = get_mission_advice(
            battery=current_battery,
            samples_collected=collected,
            rover_x=x,
            rover_y=y,
            remaining_samples=remaining,
            objective=objective,
            battery_capacity=capacity,
            credits=credits,
            at_base=at_base,
            required_samples=required
        )

        ai_results.put(("success", advice, snapshot))

    except Exception as error:
        # Avoid displaying credentials or
        # sensitive request details in the UI.
        print("AI request failed:", type(error).__name__)

        ai_results.put((
            "error",
            "Unable to contact Gemma right now. "
            "Check your internet connection, "
            "API key, and model availability.",
            snapshot
        ))


def request_discovery_advice(discovery, more, snapshot):
    """Generate an explanation in a worker; retain verified facts if it fails."""
    message = discovery_briefing(discovery, more)
    ai_results.put(("discovery", message, snapshot))


def ask_about_discovery(discovery, more=False):
    """Start an asynchronous request and associate its result with the site."""
    global ai_request_id, ai_loading, ai_message, discovery_loading_id
    ai_request_id += 1
    ai_loading = True
    discovery_loading_id = discovery.id
    ai_message = f"Contacting Gemma 4 about {discovery.name}...\n\nA response can take over a minute."
    threading.Thread(target=request_discovery_advice,
                     args=(discovery, more, ("discovery", ai_request_id, discovery.id)),
                     daemon=True).start()


def open_discovery_source(discovery):
    # A player's O key explicitly opens the official image source in their browser.
    threading.Thread(target=webbrowser.open, args=(discovery.image_source_url,), daemon=True).start()


def current_panel():
    return focused_panel(started, paused, stats_menu, journal.is_open,
                         active_discovery is not None, upgrade_menu)


# ======================================
# MAIN GAME LOOP
# ======================================

running = True

while running:

    dt = min(clock.tick(60) / 1000, 0.05)

    # Read completed AI requests
    try:
        while True:
            result_type, result_text, snapshot = ai_results.get_nowait()

            if snapshot[1] == ai_request_id:
                ai_loading = False
                ai_failed = result_type == "error" or getattr(result_text, "offline", False)
                if snapshot[0] == "discovery":
                    discovery_explanations[snapshot[2]] = result_text
                    discovery_loading_id = None
                scroll_states["ai"].reset()
                if snapshot[0] == "discovery" or snapshot[2] == (mission.number, mission.collected, mission.completed):
                    ai_message = result_text
                else:
                    ai_message = "Mission status changed. Press H for an updated briefing."

    except queue.Empty:
        pass

    # ==================================
    # EVENTS
    # ==================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEWHEEL:
            scroll_states[current_panel()].move(-event.y * 48)

        if event.type == pygame.KEYDOWN:
            if not started:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    started = True
                continue
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                amount = {pygame.K_UP: -30, pygame.K_DOWN: 30,
                          pygame.K_PAGEUP: -160, pygame.K_PAGEDOWN: 160}[event.key]
                scroll_states[current_panel()].move(amount)
                continue
            if paused:
                if event.key == pygame.K_ESCAPE:
                    paused = False
                elif event.key == pygame.K_v:
                    rover_systems.effects = not rover_systems.effects
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    direction = -1 if event.key == pygame.K_LEFTBRACKET else 1
                    rover_systems.day_seconds = max(60, min(900, rover_systems.day_seconds + direction*60))
                continue
            if event.key == pygame.K_i and not (journal.is_open or active_discovery is not None or upgrade_menu):
                stats_menu = not stats_menu
                scroll_states["stats"].reset()
                continue
            if stats_menu:
                if event.key == pygame.K_ESCAPE:
                    stats_menu = False
                continue
            if event.key == pygame.K_ESCAPE and not journal.is_open and active_discovery is None and not upgrade_menu:
                paused = not paused
                continue
            if event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                direction = -1 if event.key == pygame.K_LEFTBRACKET else 1
                rover_systems.day_seconds = max(60, min(900, rover_systems.day_seconds + direction*60))
                scan_message = f"Day cycle: {rover_systems.day_seconds:.0f} seconds"
            if event.key == pygame.K_v:
                rover_systems.effects = not rover_systems.effects
            if event.key == pygame.K_j:
                journal.toggle()
                scroll_states["journal"].reset()
                active_discovery = None
                upgrade_menu = False
                continue
            if journal.is_open:
                if event.key == pygame.K_LEFT:
                    journal.move(-1)
                    scroll_states["journal"].reset()
                elif event.key == pygame.K_RIGHT:
                    journal.move(1)
                    scroll_states["journal"].reset()
                elif event.key == pygame.K_ESCAPE:
                    journal.is_open = False
                elif event.key == pygame.K_f and journal_is_unlocked(journal, journal.current):
                    ask_about_discovery(journal.current, more=True)
                elif event.key == pygame.K_o and journal_is_unlocked(journal, journal.current):
                    open_discovery_source(journal.current)
                continue
            if active_discovery is not None:
                if event.key in (pygame.K_ESCAPE, pygame.K_e):
                    active_discovery = None
                elif event.key == pygame.K_f:
                    ask_about_discovery(active_discovery, more=True)
                elif event.key == pygame.K_o:
                    open_discovery_source(active_discovery)
                continue

            if event.key == pygame.K_ESCAPE and upgrade_menu:
                upgrade_menu = False
                continue
            if event.key == pygame.K_u:
                if upgrade_menu:
                    upgrade_menu = False
                elif mission.at_base(rover.center):
                    upgrade_menu = True
                    scroll_states["upgrades"].reset()
                    menu_notice = ""
                else:
                    ai_message = "Return to the research base to access upgrades."

            if upgrade_menu and event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                kind = {pygame.K_1: "battery", pygame.K_2: "speed", pygame.K_3: "scanner", pygame.K_4: "efficiency", pygame.K_5: "repair"}[event.key]
                if mission.upgrade(kind):
                    menu_notice = f"{kind.title()} upgraded!"
                    stats["upgrades"] += 1
                    play(ui_tone)
                elif mission.levels[kind] >= MAX_LEVEL:
                    menu_notice = f"{kind.title()} is already at maximum level."
                else:
                    menu_notice = "Not enough research credits."

            if upgrade_menu and not (event.key == pygame.K_n and mission.completed):
                continue

            if event.key == pygame.K_n and mission.completed:
                mission.start()
                expedition = ExpeditionMap(mission.number)
                expedition.reveal(BASE)
                waypoint = None
                rover.center = BASE
                rover_x, rover_y = float(rover.x), float(rover.y)
                upgrade_menu = False
                ai_message = f"Mission {mission.number} started. Collect {mission.required} samples."

            if event.key == pygame.K_r and mission.battery <= 0:
                mission.start(expedition.targets, advance=False)
                rover.center = BASE
                rover_x, rover_y = float(rover.x), float(rover.y)
                upgrade_menu = False
                ai_message = "Mission restarted at base. No credits awarded."

            if event.key == pygame.K_e and not upgrade_menu:
                choice, discovery = interaction_choice(rover, mission.samples, mission.scanner_range, expedition.discoveries)
                if choice == "sample":
                    found = mission.collect(rover)
                    if waypoint is not None and all(sample.center != waypoint for sample in mission.samples):
                        waypoint = None
                    if found:
                        play(ui_tone)
                        point = mission.cargo[-1]
                        kind = ROCK_TYPES[expedition.types[point]]
                        ai_message = f"Simulated {kind[0]} sample ({kind[4]}): {kind[3]} Research value: {kind[2]} credits at base."
                    if not mission.samples:
                        ai_message = "All samples secured. Return to base to complete the mission."
                elif choice == "discovery":
                    active_discovery = discovery
                    scroll_states["discovery"].reset()
                    journal.investigate(discovery)
                    mission.optional_site_done = True
                    ask_about_discovery(discovery)

            if event.key == pygame.K_f and not upgrade_menu:
                scan = rover_systems.scan(mission, expedition, rover.center)
                if scan is None:
                    scan_message = "Scanner cooling down or low battery"
                else:
                    play(ui_tone)
                    points, features = scan
                    kinds = sorted({ROCK_TYPES[expedition.types[p]][0] for p in points})
                    scan_message = f"Scan: {len(points)} samples, {len(features)} sites"
                    if kinds:
                        ai_message = "Simulated samples detected: " + "; ".join(ROCK_TYPES[expedition.types[p]][0] + " (" + ROCK_TYPES[expedition.types[p]][4] + ", " + str(ROCK_TYPES[expedition.types[p]][2]) + " credits)" for p in points) + ". Collect with E and unload at base."
                    if points:
                        mission.optional_done = True
            if event.key == pygame.K_t:
                visible = [sample.center for sample in mission.samples if sample.center in expedition.detected]
                waypoint = min(visible, key=lambda p: math.dist(rover.center, p)) if visible else BASE

            if event.key == pygame.K_h and not ai_loading:
                ai_request_id += 1
                ai_loading = True
                ai_message = "Contacting Gemma 4...\n\nA response can take over a minute."
                worker = threading.Thread(
                    target=request_ai_advice,
                    args=(mission.battery, mission.collected, rover.centerx, rover.centery,
                          [sample.center for sample in mission.samples], mission.objective,
                          mission.capacity, mission.credits, mission.at_base(rover.center), mission.required,
                          ("mission", ai_request_id, (mission.number, mission.collected, mission.completed))),
                    daemon=True
                )
                worker.start()

    # ==================================
    # WASD MOVEMENT
    # ==================================

    keys = pygame.key.get_pressed()

    dx = 0.0
    dy = 0.0

    if driving_allowed(started, paused, stats_menu, journal.is_open,
                       active_discovery is not None, upgrade_menu, mission.completed, mission.battery):

        if keys[pygame.K_w]:
            dy -= 1

        if keys[pygame.K_s]:
            dy += 1

        if keys[pygame.K_a]:
            dx -= 1

        if keys[pygame.K_d]:
            dx += 1

    scroll_direction = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])
    if scroll_direction:
        scroll_states[current_panel()].move(scroll_direction * 240 * dt)

    active = started and not paused and not stats_menu and not upgrade_menu and not journal.is_open and active_discovery is None
    if not active or mission.completed or mission.battery <= 0:
        rover_systems.vx = rover_systems.vy = 0
    step = dt if active else 0
    rover_systems.update(step, dx, dy, mission.speed)
    old_position = rover.center
    obstacles = expedition.obstacles_near(rover)
    intended = math.hypot(rover_systems.vx, rover_systems.vy) * step
    rover_x, rover_y, moved = move_rover(
        rover, rover_x, rover_y, rover_systems.vx, rover_systems.vy,
        math.hypot(rover_systems.vx, rover_systems.vy), step, obstacles, expedition.size
    )
    distance = math.dist(old_position, rover.center)
    rover_systems.orient(rover.centerx - old_position[0], rover.centery - old_position[1], step)
    stats["distance"] += distance
    if intended > 1 and distance < intended*.35:
        probe = rover.move(round(rover_systems.vx * step), round(rover_systems.vy * step))
        if any(probe.colliderect(rock) for rock in obstacles):
            rover_systems.damage_collision()
    if moved and expedition.region(rover.center) == "Dunes":
        rover_systems.wheels = max(25, rover_systems.wheels - step*.02)
    if moved and rover_systems.weather == "Dust storm":
        rover_systems.science = max(25, rover_systems.science - step*.015)
    prior_regions = len(expedition.explored)
    expedition.reveal(rover.center, int(320 * rover_systems.visibility))
    stats["regions"] += len(expedition.explored) - prior_regions
    if mission.at_base(rover.center):
        rover_systems.repair(step, mission.levels['repair'])
        if mission.cargo:
            value = sum(ROCK_TYPES[expedition.types[p]][2] for p in mission.cargo)
            mission.credits += value
            stats["credits"] += value
            mission.unloaded += len(mission.cargo)
            stats["samples"] += len(mission.cargo)
            mission.cargo.clear()
            scan_message = f"Cargo unloaded: +{value} credits"
        if mission.optional_done and not mission.optional_paid:
            mission.optional_paid = True
            mission.credits += 50
            stats["credits"] += 50
            scan_message = "Scan data returned: +50 credits"
        if mission.optional_site_done and not mission.optional_site_paid:
            mission.optional_site_paid = True
            mission.credits += 50
            stats["credits"] += 50
            scan_message = "Discovery data returned: +50 credits"
    if mission.update(rover.center, step, moved, .4 + .6*rover_systems.light):
        play(ui_tone)
        stats["missions"] += 1
        stats["credits"] += REWARD
        ai_message = f"Mission complete! {REWARD} research credits awarded. Press U to upgrade or N for a new mission."
    if stats['missions'] >= 1: achievements.add('First expedition')
    if stats['samples'] >= 10: achievements.add('Field geologist')
    if len(journal.found) >= 3: achievements.add('Mars historian')
    if stats['regions'] >= 30: achievements.add('Explorer')

    # A frame-rate-independent camera eases toward the rover and stays in the map.
    target_x = max(0, min(expedition.size[0] - GAME_WIDTH, rover.centerx - GAME_WIDTH / 2))
    target_y = max(0, min(expedition.size[1] - HEIGHT, rover.centery - HEIGHT / 2))
    smoothing = 1 - math.exp(-5 * dt)
    camera_x += (target_x - camera_x) * smoothing
    camera_y += (target_y - camera_y) * smoothing
    offset = (round(camera_x), round(camera_y))
    screen.set_clip(pygame.Rect(0, 0, GAME_WIDTH, HEIGHT))
    expedition.draw(screen, offset, (GAME_WIDTH, HEIGHT))
    draw_base(screen, offset)

    # Small procedural landmarks and a pulsing scan ring; no per-frame terrain generation.
    pulse = int(3 * (1 + math.sin(pygame.time.get_ticks() / 450)))
    for discovery in expedition.discoveries:
        x, y = discovery.position[0] - offset[0], discovery.position[1] - offset[1]
        if not (-100 < x < GAME_WIDTH + 100 and -100 < y < HEIGHT + 100):
            continue
        if discovery.id == "jezero":
            pygame.draw.ellipse(screen, (90, 58, 48), (x-48, y-25, 96, 50))
            pygame.draw.ellipse(screen, (211, 148, 105), (x-46, y-30, 92, 48), 5)
            for step in range(3):
                pygame.draw.arc(screen, (200, 125, 85), (x-26+step*8, y-18+step*4, 48, 25), 0.2, 2.8, 3)
        elif discovery.id == "cheyava":
            pygame.draw.ellipse(screen, (76, 45, 40), (x-37, y-18, 78, 43))
            pygame.draw.ellipse(screen, (174, 100, 76), (x-37, y-24, 74, 42))
            for dx, dy in ((-22, -8), (-6, -14), (11, -6), (22, 3), (-13, 6), (4, 8)):
                pygame.draw.circle(screen, (77, 63, 58), (x+dx, y+dy), 5)
                pygame.draw.circle(screen, (218, 191, 152), (x+dx, y+dy), 3)
        else:
            pygame.draw.ellipse(screen, (117, 81, 71), (x-43, y-22, 86, 44))
            for dx, dy in ((-28, -5), (-15, 7), (-8, -12), (3, 2), (15, -8), (27, 5), (10, 12)):
                pygame.draw.circle(screen, (64, 81, 94), (x+dx, y+dy), 5)
                pygame.draw.circle(screen, (126, 146, 150), (x+dx-1, y+dy-1), 2)
        color = GREEN if journal.is_found(discovery) else SAMPLE_BLUE
        pygame.draw.circle(screen, color, (x, y), 55 + pulse, 1)
        pygame.draw.circle(screen, color, (x, y-58), 5, 0 if journal.is_found(discovery) else 2)

    for sample in mission.samples:
        x, y = sample.centerx - offset[0], sample.centery - offset[1]
        color = ROCK_TYPES[expedition.types[sample.center]][1]
        pygame.draw.ellipse(screen, (76, 47, 40), (x-10, y-5, 23, 17))
        pygame.draw.polygon(screen, color, [(x-10,y+3),(x-7,y-7),(x+3,y-10),(x+10,y-3),(x+7,y+7),(x-3,y+9)])
        pygame.draw.line(screen, (235, 209, 171), (x-5, y-5), (x+3, y-7), 2)
    # Obscure unexplored cells; the rover's explored area remains visible.
    fog = fog_layer
    fog.fill((0, 0, 0, 0))
    view = pygame.Rect(*offset, GAME_WIDTH, HEIGHT)
    for cy in range(max(0, view.top//CELL), min((expedition.size[1]-1)//CELL, view.bottom//CELL)+1):
        for cx in range(max(0, view.left//CELL), min((expedition.size[0]-1)//CELL, view.right//CELL)+1):
            if (cx, cy) not in expedition.explored:
                pygame.draw.rect(fog, (19, 23, 28, 210), (cx*CELL-offset[0], cy*CELL-offset[1], CELL+1, CELL+1))
    screen.blit(fog, (0, 0))
    if rover_systems.light < .95:
        darkness = dark_layer
        darkness.fill((18, 21, 39, int((1-rover_systems.light)*125)))
        screen.blit(darkness, (0, 0))
    if rover_systems.effects and rover_systems.weather != "Clear":
        tick = pygame.time.get_ticks() // 25
        count = 35 if rover_systems.weather == "Dust storm" else 14
        for i in range(count):
            wx = (i*131 + tick*3) % GAME_WIDTH
            wy = (i*79 + tick) % HEIGHT
            pygame.draw.line(screen, (207, 153, 109), (wx, wy), (wx+9, wy-2), 1)

    r = rover.move(-offset[0], -offset[1])
    if rover_systems.effects and moved and len(particles) < 36:
        particles.append([r.centerx, r.centery, .65])
    for particle in particles[:]:
        particle[2] -= step
        particle[0] -= (rover.centerx-old_position[0])
        particle[1] -= (rover.centery-old_position[1])
        if particle[2] <= 0:
            particles.remove(particle)
        else:
            pygame.draw.circle(screen, (164, 107, 78), (int(particle[0]), int(particle[1])), max(1, int(5*particle[2])))
    draw_rover(screen, rover_art, r.center, rover_systems.angle, moved and int(pygame.time.get_ticks()/120)%2, rover_systems.light)
    if rover_systems.scan_pulse:
        pygame.draw.circle(screen, SAMPLE_BLUE, r.center, int((1-rover_systems.scan_pulse)*mission.scan_radius), 2)
    screen.set_clip(None)

    # ==================================
    # MISSION HUD
    # ==================================

    # Solid backplates keep telemetry readable over every terrain color.
    hud_lines = [
        (f"Battery: {mission.battery:.1f}/{mission.capacity}", WHITE),
        (f"Samples: {mission.collected}/{mission.required}    Credits: {mission.credits}", WHITE),
        (mission.objective.upper(), GREEN if mission.completed else YELLOW),
        (f"Wheels {rover_systems.wheels:.0f}  Hull {rover_systems.chassis:.0f}  Science {rover_systems.science:.0f}", WHITE),
        (f"{expedition.region(rover.center)}  |  {rover_systems.weather}  |  Base {math.dist(rover.center, BASE):.0f}", PANEL_GRAY),
        ("Optional: " + ("return scan data" if mission.optional_done and not mission.optional_paid else "scan a sample" if not mission.optional_done else "data rewarded"), SAMPLE_BLUE),
        ("Site objective: " + ("data rewarded" if mission.optional_site_paid else "return data" if mission.optional_site_done else "investigate a site"), SAMPLE_BLUE),
        (f"Scanner: {rover_systems.scan_cooldown:.1f}s  |  Cargo: {len(mission.cargo)}", SAMPLE_BLUE),
    ]
    if mission.completed:
        hud_lines.append(("U: upgrades  |  N: new mission", SAMPLE_BLUE))
    elif mission.at_base(rover.center):
        charge_status = "RECHARGING" if mission.battery < mission.capacity else "BATTERY FULL"
        hud_lines.append((f"BASE: {charge_status}  |  U: UPGRADES", SAMPLE_BLUE))
    elif mission.battery <= 0:
        hud_lines.append(("BATTERY DEPLETED - R: RESTART", YELLOW))
    if waypoint:
        hud_lines.append((f"Waypoint distance: {math.dist(rover.center, waypoint):.0f}m", YELLOW))
    hud_surfaces = [small_font.render(label, False, color) for label, color in hud_lines]
    hud_width = max(surface.get_width() for surface in hud_surfaces) + 20
    pygame.draw.rect(screen, (28, 34, 37), (10, 10, hud_width, len(hud_lines) * 26 + 21), border_radius=7)
    for index, surface in enumerate(hud_surfaces):
        screen.blit(surface, (20, 18 + index * 26))

    bar_y = 18 + len(hud_lines)*26
    pygame.draw.rect(screen, (62, 69, 72), (20, bar_y, 160, 6), border_radius=3)
    pygame.draw.rect(screen, GREEN if mission.battery > mission.capacity*.25 else YELLOW,
                     (20, bar_y, int(160*mission.battery/mission.capacity), 6), border_radius=3)
    for i, health in enumerate((rover_systems.wheels, rover_systems.chassis, rover_systems.science)):
        pygame.draw.rect(screen, (70, 70, 70), (190+i*32, bar_y, 27, 6))
        pygame.draw.rect(screen, SAMPLE_BLUE, (190+i*32, bar_y, int(27*health/100), 6))

    choice, nearby_discovery = interaction_choice(rover, mission.samples, mission.scanner_range, expedition.discoveries)
    if not upgrade_menu and not journal.is_open and active_discovery is None:
        if choice == "sample":
            hint = "Press E to collect sample (samples first)"
        elif choice == "discovery":
            hint = "Press E to investigate: " + nearby_discovery.name
        else:
            hint = scan_message + "  |  J: journal"
        hint_surface = small_font.render(hint, False, SAMPLE_BLUE)
        pygame.draw.rect(screen, (28, 34, 37), (10, HEIGHT-38, hint_surface.get_width()+20, 30), border_radius=5)
        screen.blit(hint_surface, (20, HEIGHT-32))

    destination = waypoint if waypoint is not None else BASE
    draw_compass(screen, pygame.Rect(GAME_WIDTH - 160, 10, 150, 157),
                 rover_systems.angle, rover.center, destination,
                 destination == BASE, small_font)

    # Fog-aware minimap: scanned targets are revealed, base and rover stay visible.
    map_x, map_y = GAME_WIDTH - 220, HEIGHT - 170
    pygame.draw.rect(screen, (28, 34, 37), (map_x-5, map_y-25, 210, 180), border_radius=5)
    screen.blit(small_font.render("MISSION MAP", False, WHITE), (map_x, map_y-22))
    pygame.draw.rect(screen, (13, 18, 23), (map_x, map_y, 200, 150))
    def map_point(point):
        return (map_x + round(point[0] * 200 / expedition.size[0]),
                map_y + round(point[1] * 150 / expedition.size[1]))
    for cx, cy in expedition.explored:
        x, y = map_point((cx*CELL, cy*CELL))
        pygame.draw.rect(screen, (128, 74, 54), (x, y, max(1, math.ceil(CELL*200/expedition.size[0])), max(1, math.ceil(CELL*150/expedition.size[1]))))
    pygame.draw.rect(screen, WHITE, (*map_point(BASE), 5, 5))
    for sample in mission.samples:
        if sample.center in expedition.detected:
            pygame.draw.circle(screen, SAMPLE_BLUE, map_point(sample.center), 3)
    for discovery in expedition.discoveries:
        if discovery.id in expedition.detected or journal.is_found(discovery):
            pygame.draw.circle(screen, GREEN if journal.is_found(discovery) else YELLOW, map_point(discovery.position), 4, 1)
    pygame.draw.line(screen, (245, 220, 128), map_point(rover.center), map_point(destination), 1)
    pygame.draw.circle(screen, (255, 242, 150), map_point(rover.center), 4)
    pygame.draw.rect(screen, (225, 205, 181), (map_x, map_y, 200, 150), 1)

    # ==================================
    # AI SIDE PANEL
    # ==================================

    panel_rect = pygame.Rect(
        GAME_WIDTH, 0, PANEL_WIDTH, HEIGHT
    )

    pygame.draw.rect(
        screen, PANEL_BG, panel_rect
    )

    panel_x = GAME_WIDTH + 20
    content_width = PANEL_WIDTH - 40

    title = title_font.render(
        "MARSOPS AI", False, SAMPLE_BLUE
    )

    screen.blit(title, (panel_x, 20))

    subtitle = small_font.render(
        "GEMMA 4 MISSION COPILOT",
        False, PANEL_GRAY
    )

    screen.blit(subtitle, (panel_x, 60))

    pygame.draw.line(
        screen,
        PANEL_GRAY,
        (panel_x, 95),
        (WIDTH - 20, 95),
        1
    )

    # Live telemetry
    telemetry_lines = [
        f"Battery: {mission.battery:.1f}/{mission.capacity}",
        f"Samples: {mission.collected}/{mission.required}",
        f"Position: {rover.centerx}, {rover.centery}",
        f"Objective: {mission.objective}"
    ]

    telemetry_y = 115

    for line in telemetry_lines:
        rendered = small_font.render(
            line, False, WHITE
        )
        screen.blit(
            rendered, (panel_x, telemetry_y)
        )
        telemetry_y += 28

    pygame.draw.line(
        screen,
        PANEL_GRAY,
        (panel_x, 240),
        (WIDTH - 20, 240),
        1
    )

    # Copilot status
    status_color = YELLOW if ai_loading or ai_failed else GREEN
    status_text = ("AI: CONNECTING..." if ai_loading else
                   "AI: OFFLINE - RETRY" if ai_failed else "AI: READY")

    status = small_font.render(
        status_text, False, status_color
    )

    screen.blit(status, (panel_x, 255))
    screen.blit(small_font.render("Up / Down: scroll", False, PANEL_GRAY), (panel_x, 278))

    if ai_message != last_ai_message:
        scroll_states["ai"].reset()
        last_ai_message = ai_message
    draw_scrolling_text(screen, pygame.Rect(panel_x, 304, content_width, HEIGHT-369),
                        [(ai_message, WHITE)], small_font, scroll_states["ai"], 24)

    # Bottom help text
    pygame.draw.line(
        screen,
        PANEL_GRAY,
        (panel_x, HEIGHT - 55),
        (WIDTH - 20, HEIGHT - 55),
        1
    )

    screen.blit(small_font.render("WASD: Drive  |  E: Collect", False, SAMPLE_BLUE), (panel_x, HEIGHT - 50))
    screen.blit(small_font.render("F: Scan  T: Waypoint  J: Journal", False, SAMPLE_BLUE), (panel_x, HEIGHT - 28))

    if upgrade_menu:
        box = pygame.Rect(220, 120, 460, 350)
        pygame.draw.rect(screen, (24, 30, 42), box, border_radius=10)
        pygame.draw.rect(screen, SAMPLE_BLUE, box, 2, border_radius=10)
        screen.blit(title_font.render("ROVER UPGRADES", False, SAMPLE_BLUE), (box.x+22, box.y+18))
        screen.blit(small_font.render(f"Credits: {mission.credits}", False, WHITE), (box.x+22, box.y+55))
        labels = (("battery", "+25 capacity"), ("speed", "+30 speed"),
                  ("scanner", "+100 scan range"), ("efficiency", "cheaper / faster scans"),
                  ("repair", "faster base repairs"))
        upgrade_lines = []
        for index, (kind, effect) in enumerate(labels):
            level = mission.levels[kind]
            cost = "MAX" if level >= MAX_LEVEL else f"{mission.upgrade_cost(kind)} credits"
            upgrade_lines.append((f"{index+1}: {kind.title()} {level}/{MAX_LEVEL} - {effect} - {cost}", WHITE))
        draw_scrolling_text(screen, pygame.Rect(box.x+22, box.y+87, box.width-44, 178),
                            upgrade_lines, small_font, scroll_states["upgrades"], 30)
        screen.blit(small_font.render(menu_notice, False, YELLOW), (box.x+22, box.bottom-64))
        hint = "N: next mission  |  U: close" if mission.completed else "U: close  |  Base repairs and recharges automatically"
        screen.blit(small_font.render(hint, False, SAMPLE_BLUE), (box.x+22, box.bottom-35))
    if journal.is_open or active_discovery is not None:
        item = journal.current if journal.is_open else active_discovery
        box = pygame.Rect(100, 105, 700, 410)
        pygame.draw.rect(screen, (24, 30, 42), box, border_radius=10)
        pygame.draw.rect(screen, SAMPLE_BLUE, box, 2, border_radius=10)
        heading = "DISCOVERY JOURNAL" if journal.is_open else "DISCOVERY INVESTIGATED"
        screen.blit(title_font.render(heading, False, SAMPLE_BLUE), (box.x+22, box.y+16))
        screen.blit(small_font.render(f"Found: {len(journal.found)}/{len(DISCOVERIES)}", False, GREEN), (box.x+22, box.y+52))
        unlocked = journal_is_unlocked(journal, item)
        blocks = []
        if journal.is_open:
            for index, entry in enumerate(DISCOVERIES):
                found = journal_is_unlocked(journal, entry)
                name = entry.name if found else "Unknown discovery"
                status = "FOUND" if found else "LOCKED"
                prefix = "> " if index == journal.selected else "  "
                blocks.append(("text", f"{prefix}{name}  [{status}]", YELLOW if index == journal.selected else PANEL_GRAY))
            blocks.append(("text", "", WHITE))
        blocks.extend(gallery_blocks(item, unlocked,
                      discovery_explanations.get(item.id), discovery_loading_id == item.id))
        focus_name = "journal" if journal.is_open else "discovery"
        draw_gallery(screen, pygame.Rect(box.x+22, box.y+80, box.width-44, box.height-125),
                     blocks, small_font, scroll_states[focus_name], image_cache)
        hint = "Left/Right: select  Up/Down: scroll  F: AI  O: source  J: close" if journal.is_open else "Up/Down: scroll  F: AI  O: source  E/Esc: close"
        screen.blit(small_font.render(hint, False, SAMPLE_BLUE), (box.x+22, box.bottom-30))

    if mission.completed and not upgrade_menu and not journal.is_open and not stats_menu:
        notice = pygame.Rect(270, HEIGHT-100, 370, 64)
        pygame.draw.rect(screen, PANEL_BG, notice, border_radius=6)
        pygame.draw.rect(screen, GREEN, notice, 2, border_radius=6)
        screen.blit(small_font.render("MISSION COMPLETE - cargo analyzed", False, GREEN), (notice.x+15, notice.y+10))
        screen.blit(small_font.render("U: upgrades   |   N: launch next mission", False, WHITE), (notice.x+15, notice.y+36))

    if stats_menu:
        box = pygame.Rect(170, 120, 560, 360)
        pygame.draw.rect(screen, PANEL_BG, box, border_radius=8)
        pygame.draw.rect(screen, SAMPLE_BLUE, box, 2, border_radius=8)
        screen.blit(title_font.render("EXPEDITION RECORD", False, SAMPLE_BLUE), (box.x+20, box.y+15))
        lines = [f"Missions completed: {int(stats['missions'])}",
                 f"Distance traveled: {stats['distance']:.0f}", f"Samples recovered: {int(stats['samples'])}",
                 f"Discoveries investigated: {len(journal.found)}", f"Regions explored: {int(stats['regions'])}",
                 f"Credits earned: {int(stats['credits'])}", f"Upgrades purchased: {int(stats['upgrades'])}",
                 "Achievements: " + (", ".join(sorted(achievements)) or "none yet")]
        draw_scrolling_text(screen, pygame.Rect(box.x+20, box.y+55, box.width-40, box.height-95),
                            [(line, WHITE) for line in lines], small_font, scroll_states["stats"], 30)
        screen.blit(small_font.render("Up / Down: scroll  |  I / Esc: close", False, SAMPLE_BLUE), (box.x+20, box.bottom-30))
    if not started or paused:
        shade = pygame.Surface((GAME_WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((9, 15, 24, 205))
        screen.blit(shade, (0, 0))
        heading = "MARSOPS AI" if not started else "EXPEDITION PAUSED"
        screen.blit(title_font.render(heading, False, SAMPLE_BLUE), (300, 170))
        lines = (["EXPEDITION v0.6", "A condensed educational simulation of Mars.",
                  "WASD: drive   E: collect / investigate   F: scan", "J: journal   U: upgrades   H: copilot",
                  "Enter: begin / resume expedition"] if not started else
                 ["Esc: resume", "V: toggle weather / dust effects", "[ / ]: change day length by 60 seconds", "Progress saves automatically and on exit."])
        for i, line in enumerate(lines):
            screen.blit(small_font.render(line, False, WHITE), (230, 230+i*32))

    save_timer += dt
    if started and save_timer >= 20:
        save_progress(make_snapshot(mission, expedition, journal, rover, rover_systems, stats, achievements))
        save_timer = 0
    # A short dim-to-clear transition softens menu and mission state changes.
    current_view = (started, paused, upgrade_menu, journal.is_open,
                    active_discovery is not None, stats_menu, mission.completed)
    if previous_view is not None and current_view != previous_view:
        ui_fade = 115.0
    previous_view = current_view
    if ui_fade > 0:
        transition = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        transition.fill((10, 15, 24, int(ui_fade)))
        screen.blit(transition, (0, 0))
        ui_fade = max(0.0, ui_fade - 500*dt)

    pygame.display.flip()

if started:
    save_progress(make_snapshot(mission, expedition, journal, rover, rover_systems, stats, achievements))
pygame.quit()
