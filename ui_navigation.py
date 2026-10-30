"""Panel focus, bounded scrolling and clipped, pixel-width text layout."""
import pygame


class ScrollState:
    def __init__(self):
        self.offset = 0.0
        self.maximum = 0.0

    def extent(self, content_height, viewport_height):
        self.maximum = max(0, content_height - viewport_height)
        self.offset = max(0, min(self.offset, self.maximum))

    def move(self, amount):
        self.offset = max(0, min(self.maximum, self.offset + amount))

    def reset(self):
        self.offset = 0.0


def focused_panel(started, paused, stats, journal, discovery, upgrades):
    """Select exactly the topmost panel, never the hidden copilot behind it."""
    if not started: return 'start'
    if paused: return 'pause'
    if stats: return 'stats'
    if journal: return 'journal'
    if discovery: return 'discovery'
    if upgrades: return 'upgrades'
    return 'ai'


def driving_allowed(started, paused, stats, journal, discovery, upgrades, completed, battery):
    return (focused_panel(started, paused, stats, journal, discovery, upgrades) == 'ai'
            and not completed and battery > 0)


def wrap_text(text, font, width):
    """Wrap words and long URLs to the actual font width without losing characters."""
    result = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            result.append('')
            continue
        line = ''
        for word in paragraph.split():
            while word:
                candidate = (line + ' ' + word).strip()
                if font.size(candidate)[0] <= width:
                    line = candidate
                    break
                if line:
                    result.append(line)
                    line = ''
                    continue
                cut = len(word)
                while cut > 1 and font.size(word[:cut])[0] > width:
                    cut -= 1
                result.append(word[:cut])
                word = word[cut:]
        if line:
            result.append(line)
    return result


def draw_scrolling_text(surface, rect, blocks, font, scroll, line_height=23):
    """Draw colored blocks clipped to rect, leaving headers and footers untouched."""
    lines = []
    for text, color in blocks:
        lines.extend((line, color) for line in wrap_text(text, font, rect.width - 16))
    scroll.extent(len(lines) * line_height, rect.height)
    old_clip = surface.get_clip()
    surface.set_clip(rect)
    for index, (line, color) in enumerate(lines):
        y = rect.y + index * line_height - int(scroll.offset)
        if y + line_height < rect.top or y >= rect.bottom:
            continue
        if line:
            surface.blit(font.render(line, False, color), (rect.x, y))
    surface.set_clip(old_clip)
    # Subtle chevrons indicate content beyond the viewport.
    marker = (150, 185, 190)
    x = rect.right - 7
    if scroll.offset > 0:
        pygame.draw.polygon(surface, marker, [(x-4, rect.top+7), (x+4, rect.top+7), (x, rect.top+2)])
    if scroll.offset < scroll.maximum:
        pygame.draw.polygon(surface, marker, [(x-4, rect.bottom-7), (x+4, rect.bottom-7), (x, rect.bottom-2)])


def draw_compass(surface, box, angle, origin, destination, is_base, font):
    """Draw a north-up compass with independent rover and destination indicators."""
    import math
    from navigation import heading_degrees, bearing_degrees

    background = (28, 34, 37)
    white = (238, 241, 236)
    cyan = (80, 220, 255)
    amber = (255, 201, 98)
    muted = (155, 173, 175)
    pygame.draw.rect(surface, background, box, border_radius=8)
    center = (box.centerx, box.y + 57)
    pygame.draw.circle(surface, muted, center, 35, 1)
    for label, offset in (('N', (0, -51)), ('E', (49, -10)),
                          ('S', (0, 32)), ('W', (-49, -10))):
        text = font.render(label, False, white)
        surface.blit(text, text.get_rect(center=(center[0]+offset[0], center[1]+offset[1]+10)))
    # Cyan needle shares the rover artwork's exact angle.
    tip = (center[0] + round(26 * math.sin(angle)), center[1] - round(26 * math.cos(angle)))
    tail = (center[0] - round(11 * math.sin(angle)), center[1] + round(11 * math.cos(angle)))
    pygame.draw.line(surface, cyan, tail, tip, 3)
    pygame.draw.circle(surface, white, center, 3)
    bearing = bearing_degrees(origin, destination)
    if bearing is not None:
        radians = math.radians(bearing)
        dx, dy = math.sin(radians), -math.cos(radians)
        point = (center[0] + dx*37, center[1] + dy*37)
        side = (-dy, dx)
        triangle = [(point[0] + dx*5, point[1] + dy*5),
                    (point[0] - dx*5 + side[0]*4, point[1] - dy*5 + side[1]*4),
                    (point[0] - dx*5 - side[0]*4, point[1] - dy*5 - side[1]*4)]
        pygame.draw.polygon(surface, amber, triangle)
    heading = f"HDG {round(heading_degrees(angle)) % 360:03d}°"
    target = ('BASE' if is_base else 'TARGET') + (f" {round(bearing) % 360:03d}°" if bearing is not None else ' HERE')
    for index, (label, color) in enumerate(((heading, cyan), (target, amber))):
        rendered = font.render(label, False, color)
        surface.blit(rendered, rendered.get_rect(center=(box.centerx, box.y+119+index*21)))
