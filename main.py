
import pygame
import threading
import queue
import math

from terrain import WORLD_SIZE, BASE, TARGETS, make_world, draw_base
from mission import Mission, MAX_LEVEL, REWARD
from movement import move_rover

from ai_copilot import get_mission_advice, discovery_briefing
from discoveries import DISCOVERIES, DiscoveryJournal, interaction_choice

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
world, rocks = make_world()
rover = pygame.Rect(BASE[0] - 25, BASE[1] - 25, 50, 50)
mission = Mission()
journal = DiscoveryJournal()
active_discovery = None
upgrade_menu = False
menu_notice = ""
rover_x, rover_y = float(rover.x), float(rover.y)
camera_x = max(0, min(WORLD_SIZE[0] - GAME_WIDTH, rover.centerx - GAME_WIDTH / 2))
camera_y = max(0, min(WORLD_SIZE[1] - HEIGHT, rover.centery - HEIGHT / 2))
TOTAL_SAMPLES = len(TARGETS)
minimap = pygame.transform.smoothscale(world, (200, 150))

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
ai_request_id = 0
ai_scroll = 0

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
            at_base=at_base
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


# ======================================
# TEXT WRAPPING
# ======================================

def draw_wrapped_text(
    surface,
    message,
    x,
    y,
    max_width,
    text_font,
    color,
    line_height=25,
    bottom_limit=HEIGHT - 20
):
    """
    Draw text within a fixed width.

    Newlines are preserved, and text is
    wrapped based on rendered pixel width.
    """

    for paragraph in message.splitlines():

        if not paragraph.strip():
            y += line_height
            continue

        words = paragraph.split()
        line = ""

        for word in words:
            candidate = (line + " " + word).strip()

            if text_font.size(candidate)[0] <= max_width:
                line = candidate
            else:
                if line:
                    if y + line_height > bottom_limit:
                        return y

                    rendered = text_font.render(
                        line, False, color
                    )
                    surface.blit(rendered, (x, y))
                    y += line_height
                    line = ""

                # Split unusually long words
                while (
                    word and
                    text_font.size(word)[0] > max_width
                ):
                    cut = len(word)

                    while (
                        cut > 1 and
                        text_font.size(word[:cut])[0]
                        > max_width
                    ):
                        cut -= 1

                    if y + line_height > bottom_limit:
                        return y

                    rendered = text_font.render(
                        word[:cut], False, color
                    )
                    surface.blit(rendered, (x, y))
                    y += line_height
                    word = word[cut:]

                line = word

        if line:
            if y + line_height > bottom_limit:
                return y

            rendered = text_font.render(
                line, False, color
            )
            surface.blit(rendered, (x, y))
            y += line_height

    return y


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
                ai_scroll = 0
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

        if event.type == pygame.MOUSEWHEEL and pygame.mouse.get_pos()[0] >= GAME_WIDTH:
            ai_scroll = max(0, min(480, ai_scroll - event.y * 48))

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP:
                ai_scroll = max(0, ai_scroll - 72)
            elif event.key == pygame.K_PAGEDOWN:
                ai_scroll = min(480, ai_scroll + 72)

            if event.key == pygame.K_j:
                journal.toggle()
                active_discovery = None
                upgrade_menu = False
                continue
            if journal.is_open:
                if event.key in (pygame.K_LEFT, pygame.K_UP):
                    journal.move(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                    journal.move(1)
                elif event.key == pygame.K_ESCAPE:
                    journal.is_open = False
                continue
            if active_discovery is not None:
                if event.key in (pygame.K_ESCAPE, pygame.K_e):
                    active_discovery = None
                elif event.key == pygame.K_f:
                    ai_request_id += 1
                    ai_loading = True
                    ai_message = f"Contacting Gemma 4 about {active_discovery.name}..."
                    threading.Thread(target=request_discovery_advice,
                                     args=(active_discovery, True, ("discovery", ai_request_id)),
                                     daemon=True).start()
                continue

            if event.key == pygame.K_u:
                if upgrade_menu:
                    upgrade_menu = False
                elif mission.at_base(rover.center):
                    upgrade_menu = True
                    menu_notice = ""
                else:
                    ai_message = "Return to the research base to access upgrades."

            if upgrade_menu and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                kind = {pygame.K_1: "battery", pygame.K_2: "speed", pygame.K_3: "scanner"}[event.key]
                if mission.upgrade(kind):
                    menu_notice = f"{kind.title()} upgraded!"
                elif mission.levels[kind] >= MAX_LEVEL:
                    menu_notice = f"{kind.title()} is already at maximum level."
                else:
                    menu_notice = "Not enough research credits."

            if event.key == pygame.K_n and mission.completed:
                mission.start()
                rover.center = BASE
                rover_x, rover_y = float(rover.x), float(rover.y)
                upgrade_menu = False
                ai_message = "New mission started. Explore and collect three samples."

            if event.key == pygame.K_r and mission.battery <= 0:
                mission.start()
                rover.center = BASE
                rover_x, rover_y = float(rover.x), float(rover.y)
                upgrade_menu = False
                ai_message = "Mission restarted at base. No credits awarded."

            if event.key == pygame.K_e and not upgrade_menu:
                choice, discovery = interaction_choice(rover, mission.samples, mission.scanner_range)
                if choice == "sample":
                    mission.collect(rover)
                    if not mission.samples:
                        ai_message = "All samples secured. Return to base to complete the mission."
                elif choice == "discovery":
                    active_discovery = discovery
                    journal.investigate(discovery)
                    ai_request_id += 1
                    ai_loading = True
                    ai_message = f"Contacting Gemma 4 about {discovery.name}..."
                    threading.Thread(target=request_discovery_advice,
                                     args=(discovery, False, ("discovery", ai_request_id)),
                                     daemon=True).start()

            if event.key == pygame.K_h and not ai_loading:
                ai_request_id += 1
                ai_loading = True
                ai_message = "Contacting Gemma 4...\n\nAnalyzing mission telemetry."
                worker = threading.Thread(
                    target=request_ai_advice,
                    args=(mission.battery, mission.collected, rover.centerx, rover.centery,
                          [sample.center for sample in mission.samples], mission.objective,
                          mission.capacity, mission.credits, mission.at_base(rover.center),
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

    if mission.battery > 0 and not upgrade_menu and not journal.is_open and active_discovery is None and not mission.completed:

        if keys[pygame.K_w]:
            dy -= 1

        if keys[pygame.K_s]:
            dy += 1

        if keys[pygame.K_a]:
            dx -= 1

        if keys[pygame.K_d]:
            dx += 1

    rover_x, rover_y, moved = move_rover(
        rover, rover_x, rover_y, dx, dy, mission.speed, dt, rocks, WORLD_SIZE
    )

    if mission.update(rover.center, dt, moved):
        ai_message = f"Mission complete! {REWARD} research credits awarded. Press U to upgrade or N for a new mission."

    # A frame-rate-independent camera eases toward the rover and stays in the map.
    target_x = max(0, min(WORLD_SIZE[0] - GAME_WIDTH, rover.centerx - GAME_WIDTH / 2))
    target_y = max(0, min(WORLD_SIZE[1] - HEIGHT, rover.centery - HEIGHT / 2))
    smoothing = 1 - math.exp(-5 * dt)
    camera_x += (target_x - camera_x) * smoothing
    camera_y += (target_y - camera_y) * smoothing
    offset = (round(camera_x), round(camera_y))
    screen.set_clip(pygame.Rect(0, 0, GAME_WIDTH, HEIGHT))
    screen.blit(world, (0, 0), pygame.Rect(*offset, GAME_WIDTH, HEIGHT))
    draw_base(screen, offset)

    # Small procedural landmarks and a pulsing scan ring; no per-frame terrain generation.
    pulse = int(3 * (1 + math.sin(pygame.time.get_ticks() / 450)))
    for discovery in DISCOVERIES:
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
        pygame.draw.circle(screen, (54, 109, 111), (x, y), 15, 2)
        pygame.draw.polygon(screen, (77, 223, 233), [(x, y-10), (x+8, y-3), (x+6, y+8), (x-5, y+10), (x-9, y+1)])
        pygame.draw.line(screen, (211, 255, 246), (x, y-8), (x-3, y+4), 2)

    r = rover.move(-offset[0], -offset[1])
    pygame.draw.ellipse(screen, (78, 47, 39), r.move(6, 9))
    for wheel_x in (r.x - 7, r.right):
        for wheel_y in (r.y + 7, r.y + 31):
            pygame.draw.rect(screen, WHEEL_BLACK, (wheel_x, wheel_y, 8, 12), border_radius=2)
    pygame.draw.rect(screen, (196, 192, 175), r, border_radius=8)
    pygame.draw.rect(screen, (232, 229, 208), r.inflate(-8, -8), border_radius=5)
    pygame.draw.rect(screen, (70, 93, 100), (r.x+10, r.y+11, 30, 20), border_radius=3)
    pygame.draw.line(screen, (172, 205, 204), (r.x+13, r.y+15), (r.x+36, r.y+15), 2)
    pygame.draw.circle(screen, (239, 180, 101), (r.centerx, r.y+38), 4)
    screen.set_clip(None)

    # ==================================
    # MISSION HUD
    # ==================================

    # Solid backplates keep telemetry readable over every terrain color.
    hud_lines = [
        (f"Battery: {mission.battery:.1f}/{mission.capacity}", WHITE),
        (f"Samples: {mission.collected}/{TOTAL_SAMPLES}    Credits: {mission.credits}", WHITE),
        (mission.objective.upper(), GREEN if mission.completed else YELLOW),
    ]
    if mission.completed:
        hud_lines.append(("U: upgrades  |  N: new mission", SAMPLE_BLUE))
    elif mission.at_base(rover.center):
        charge_status = "RECHARGING" if mission.battery < mission.capacity else "BATTERY FULL"
        hud_lines.append((f"BASE: {charge_status}  |  U: UPGRADES", SAMPLE_BLUE))
    elif mission.battery <= 0:
        hud_lines.append(("BATTERY DEPLETED - R: RESTART", YELLOW))
    hud_surfaces = [small_font.render(label, False, color) for label, color in hud_lines]
    hud_width = max(surface.get_width() for surface in hud_surfaces) + 20
    pygame.draw.rect(screen, (28, 34, 37), (10, 10, hud_width, len(hud_lines) * 26 + 10), border_radius=7)
    for index, surface in enumerate(hud_surfaces):
        screen.blit(surface, (20, 18 + index * 26))

    choice, nearby_discovery = interaction_choice(rover, mission.samples, mission.scanner_range)
    if not upgrade_menu and not journal.is_open and active_discovery is None:
        if choice == "sample":
            hint = "Press E to collect sample (samples first)"
        elif choice == "discovery":
            hint = "Press E to investigate: " + nearby_discovery.name
        else:
            hint = "J: Discovery journal"
        hint_surface = small_font.render(hint, False, SAMPLE_BLUE)
        pygame.draw.rect(screen, (28, 34, 37), (10, HEIGHT-38, hint_surface.get_width()+20, 30), border_radius=5)
        screen.blit(hint_surface, (20, HEIGHT-32))

    # Overview uses the same cached terrain; markers remain in world coordinates.
    map_x, map_y = GAME_WIDTH - 220, HEIGHT - 170
    pygame.draw.rect(screen, (28, 34, 37), (map_x-5, map_y-25, 210, 180), border_radius=5)
    screen.blit(small_font.render("MISSION MAP", False, WHITE), (map_x, map_y-22))
    screen.blit(minimap, (map_x, map_y))
    def map_point(point):
        return (map_x + round(point[0] * 200 / WORLD_SIZE[0]),
                map_y + round(point[1] * 150 / WORLD_SIZE[1]))
    pygame.draw.rect(screen, (225, 217, 189), (*map_point(BASE), 5, 5))
    for sample in mission.samples:
        pygame.draw.circle(screen, SAMPLE_BLUE, map_point(sample.center), 4)
    for discovery in DISCOVERIES:
        color = GREEN if journal.is_found(discovery) else YELLOW
        pygame.draw.circle(screen, color, map_point(discovery.position), 3, 0 if journal.is_found(discovery) else 1)
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
        f"Samples: {mission.collected}/{TOTAL_SAMPLES}",
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
    status_color = YELLOW if ai_loading else GREEN
    status_text = (
        "AI: ANALYZING..."
        if ai_loading
        else "AI: READY"
    )

    status = small_font.render(
        status_text, False, status_color
    )

    screen.blit(status, (panel_x, 255))
    screen.blit(small_font.render("PgUp / PgDn: scroll", False, PANEL_GRAY), (panel_x + 125, 255))

    # Clip the scrollable briefing to its panel so long AI or fallback text remains readable.
    screen.set_clip(pygame.Rect(panel_x, 292, content_width, HEIGHT - 357))
    draw_wrapped_text(
        screen,
        ai_message,
        panel_x,
        295 - ai_scroll,
        content_width,
        small_font,
        WHITE,
        line_height=24,
        bottom_limit=HEIGHT - 65
    )
    screen.set_clip(None)

    # Bottom help text
    pygame.draw.line(
        screen,
        PANEL_GRAY,
        (panel_x, HEIGHT - 55),
        (WIDTH - 20, HEIGHT - 55),
        1
    )

    screen.blit(small_font.render("WASD: Drive  |  E: Collect", False, SAMPLE_BLUE), (panel_x, HEIGHT - 50))
    screen.blit(small_font.render("U: Upgrade  H: AI  J: Journal", False, SAMPLE_BLUE), (panel_x, HEIGHT - 28))

    if upgrade_menu:
        box = pygame.Rect(220, 120, 460, 350)
        pygame.draw.rect(screen, (24, 30, 42), box, border_radius=10)
        pygame.draw.rect(screen, SAMPLE_BLUE, box, 2, border_radius=10)
        lines = [
            ("ROVER UPGRADES", title_font, SAMPLE_BLUE),
            (f"Research credits: {mission.credits}", font, WHITE),
            ("1  Battery: +25 capacity", small_font, WHITE),
            ("2  Speed: +30 pixels / second", small_font, WHITE),
            ("3  Scanner: +15 collection reach", small_font, WHITE),
        ]
        y = box.y + 18
        for label, face, color in lines:
            screen.blit(face.render(label, False, color), (box.x + 22, y))
            y += 38 if face != small_font else 24
        for kind in ("battery", "speed", "scanner"):
            level = mission.levels[kind]
            cost = "MAX" if level >= MAX_LEVEL else f"{mission.upgrade_cost(kind)} credits"
            screen.blit(small_font.render(f"{kind.title()}: level {level}/{MAX_LEVEL}  |  {cost}", False, PANEL_GRAY), (box.x + 22, y))
            y += 24
        screen.blit(small_font.render(menu_notice, False, YELLOW), (box.x + 22, box.bottom - 64))
        hint = "N: new mission   U: close" if mission.completed else "U: close  |  Complete missions to earn credits"
        screen.blit(small_font.render(hint, False, SAMPLE_BLUE), (box.x + 22, box.bottom - 35))
    if journal.is_open or active_discovery is not None:
        item = journal.current if journal.is_open else active_discovery
        box = pygame.Rect(100, 105, 700, 410)
        pygame.draw.rect(screen, (24, 30, 42), box, border_radius=10)
        pygame.draw.rect(screen, SAMPLE_BLUE, box, 2, border_radius=10)
        heading = "DISCOVERY JOURNAL" if journal.is_open else "DISCOVERY INVESTIGATED"
        screen.blit(title_font.render(heading, False, SAMPLE_BLUE), (box.x+22, box.y+16))
        screen.blit(small_font.render(f"Found: {len(journal.found)}/{len(DISCOVERIES)}", False, GREEN), (box.x+22, box.y+52))
        if journal.is_open:
            y = box.y + 79
            for index, entry in enumerate(DISCOVERIES):
                status = "FOUND" if journal.is_found(entry) else "UNDISCOVERED"
                prefix = "> " if index == journal.selected else "  "
                screen.blit(small_font.render(f"{prefix}{entry.name}  [{status}]", False, YELLOW if index == journal.selected else PANEL_GRAY), (box.x+22, y))
                y += 22
            y += 7
        else:
            y = box.y + 86
        screen.blit(font.render(item.name, False, WHITE), (box.x+22, y))
        y += 31
        y = draw_wrapped_text(screen, item.description + " " + item.significance,
                              box.x+22, y, box.width-44, small_font, WHITE,
                              line_height=21, bottom_limit=box.bottom-82)
        y += 5
        draw_wrapped_text(screen, "NASA source: " + item.source_url,
                          box.x+22, y, box.width-44, small_font, PANEL_GRAY,
                          line_height=20, bottom_limit=box.bottom-43)
        hint = "Arrow keys: select  |  J / Esc: close" if journal.is_open else "F: ask for more  |  E / Esc: close  |  J: journal"
        screen.blit(small_font.render(hint, False, SAMPLE_BLUE), (box.x+22, box.bottom-30))

    pygame.display.flip()

pygame.quit()
