
import pygame
import threading
import queue
import math

from terrain import WORLD_SIZE, BASE, TARGETS, make_world, draw_base

from ai_copilot import get_mission_advice

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
rover = pygame.Rect(BASE[0] - 25, BASE[1] + 75, 50, 50)
rover_speed = 240
rover_x, rover_y = float(rover.x), float(rover.y)
camera_x = max(0, min(WORLD_SIZE[0] - GAME_WIDTH, rover.centerx - GAME_WIDTH / 2))
camera_y = max(0, min(WORLD_SIZE[1] - HEIGHT, rover.centery - HEIGHT / 2))
battery = 100.0
samples_collected = 0
samples = [pygame.Rect(x - 10, y - 10, 20, 20) for x, y in TARGETS]
TOTAL_SAMPLES = len(samples)
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

# Thread-safe communication
ai_results = queue.Queue()


def request_ai_advice(
    current_battery,
    collected,
    x,
    y,
    remaining
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
            remaining_samples=remaining
        )

        ai_results.put(("success", advice))

    except Exception as error:
        # Avoid displaying credentials or
        # sensitive request details in the UI.
        print("AI request failed:", type(error).__name__)

        ai_results.put((
            "error",
            "Unable to contact Gemma right now. "
            "Check your internet connection, "
            "API key, and model availability."
        ))


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
            result_type, result_text = ai_results.get_nowait()

            ai_loading = False
            ai_message = result_text

    except queue.Empty:
        pass

    # ==================================
    # EVENTS
    # ==================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            # Collect scientific samples
            if event.key == pygame.K_e:

                for sample in samples[:]:
                    if rover.inflate(30, 30).colliderect(sample):
                        samples.remove(sample)
                        samples_collected += 1

            # Request AI mission briefing
            if event.key == pygame.K_h and not ai_loading:

                remaining_samples = [
                    sample.center for sample in samples
                ]

                ai_loading = True
                ai_message = (
                    "Contacting Gemma 4...\n\n"
                    "Analyzing mission telemetry."
                )

                worker = threading.Thread(
                    target=request_ai_advice,
                    args=(
                        battery,
                        samples_collected,
                        rover.centerx,
                        rover.centery,
                        remaining_samples
                    ),
                    daemon=True
                )

                worker.start()

    # ==================================
    # WASD MOVEMENT
    # ==================================

    keys = pygame.key.get_pressed()

    dx = 0.0
    dy = 0.0

    if battery > 0:

        if keys[pygame.K_w]:
            dy -= 1

        if keys[pygame.K_s]:
            dy += 1

        if keys[pygame.K_a]:
            dx -= 1

        if keys[pygame.K_d]:
            dx += 1

    # Normalize diagonal movement
    if dx != 0 or dy != 0:
        length = (dx ** 2 + dy ** 2) ** 0.5
        dx /= length
        dy /= length

    move_x = dx * rover_speed * dt
    move_y = dy * rover_speed * dt

    old_x = rover.x
    old_y = rover.y

    # Horizontal movement
    rover_x += move_x
    rover.x = round(rover_x)

    if any(rover.colliderect(rock) for rock in rocks):
        rover.x = old_x
        rover_x = float(old_x)

    # Vertical movement
    rover_y += move_y
    rover.y = round(rover_y)

    if any(rover.colliderect(rock) for rock in rocks):
        rover.y = old_y
        rover_y = float(old_y)

    # Stay inside the playable area
    game_bounds = pygame.Rect(
        0, 0, *WORLD_SIZE
    )

    rover.clamp_ip(game_bounds)

    rover_x = float(rover.x)
    rover_y = float(rover.y)

    # Battery drains only when position changes
    moved = (
        rover.x != old_x or
        rover.y != old_y
    )

    if moved:
        battery = max(0, battery - 2 * dt)

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

    for sample in samples:
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
    pygame.draw.rect(screen, (28, 34, 37), (10, 10, 235, 80), border_radius=7)
    if samples_collected == TOTAL_SAMPLES or battery <= 0:
        pygame.draw.rect(screen, (28, 34, 37), (340, 10, 290, 80), border_radius=7)

    battery_text = font.render(
        f"Battery: {battery:.1f}%",
        False, WHITE
    )

    sample_text = font.render(
        f"Samples: {samples_collected}/{TOTAL_SAMPLES}",
        False, WHITE
    )

    screen.blit(battery_text, (20, 20))
    screen.blit(sample_text, (20, 55))

    if samples_collected == TOTAL_SAMPLES:
        mission_text = font.render(
            "MISSION COMPLETE!",
            False, GREEN
        )
        screen.blit(mission_text, (350, 20))

    if battery <= 0:
        warning = font.render(
            "BATTERY DEPLETED!",
            False, YELLOW
        )
        screen.blit(warning, (350, 55))

    # Overview uses the same cached terrain; markers remain in world coordinates.
    map_x, map_y = GAME_WIDTH - 220, HEIGHT - 170
    pygame.draw.rect(screen, (28, 34, 37), (map_x-5, map_y-25, 210, 180), border_radius=5)
    screen.blit(small_font.render("MISSION MAP", False, WHITE), (map_x, map_y-22))
    screen.blit(minimap, (map_x, map_y))
    def map_point(point):
        return (map_x + round(point[0] * 200 / WORLD_SIZE[0]),
                map_y + round(point[1] * 150 / WORLD_SIZE[1]))
    pygame.draw.rect(screen, (225, 217, 189), (*map_point(BASE), 5, 5))
    for sample in samples:
        pygame.draw.circle(screen, SAMPLE_BLUE, map_point(sample.center), 4)
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
        f"Battery: {battery:.1f}%",
        f"Samples: {samples_collected}/{TOTAL_SAMPLES}",
        f"Position: {rover.centerx}, {rover.centery}",
        f"Remaining: {len(samples)}"
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

    # AI briefing text
    draw_wrapped_text(
        screen,
        ai_message,
        panel_x,
        295,
        content_width,
        small_font,
        WHITE,
        line_height=24,
        bottom_limit=HEIGHT - 65
    )

    # Bottom help text
    pygame.draw.line(
        screen,
        PANEL_GRAY,
        (panel_x, HEIGHT - 55),
        (WIDTH - 20, HEIGHT - 55),
        1
    )

    help_text = small_font.render(
        "WASD: Drive   E: Collect   H: AI",
        False, SAMPLE_BLUE
    )

    screen.blit(
        help_text,
        (panel_x, HEIGHT - 42)
    )

    pygame.display.flip()

pygame.quit()
