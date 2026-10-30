"""Offline NASA image cache and scrollable discovery-gallery layout."""
from pathlib import Path
import pygame
from ui_navigation import wrap_text

ASSET_DIR = Path(__file__).resolve().parent / 'assets' / 'discoveries'


class DiscoveryImageCache:
    def __init__(self, directory=ASSET_DIR):
        self.directory = Path(directory)
        self.originals = {}
        self.scaled = {}

    def get(self, filename, bounds, font):
        """Return (surface, available); load each original and size only once."""
        key = (filename, tuple(bounds))
        if key in self.scaled:
            return self.scaled[key]
        if filename not in self.originals:
            try:
                self.originals[filename] = pygame.image.load(str(self.directory / filename)).convert()
            except (FileNotFoundError, OSError, pygame.error):
                self.originals[filename] = None
        original = self.originals[filename]
        if original is None:
            image = pygame.Surface((bounds[0], min(bounds[1], 170)))
            image.fill((38, 45, 53))
            label = font.render('NASA photograph unavailable offline', False, (196, 207, 210))
            image.blit(label, label.get_rect(center=image.get_rect().center))
            result = (image, False)
        else:
            scale = min(bounds[0] / original.get_width(), bounds[1] / original.get_height())
            size = (max(1, round(original.get_width()*scale)), max(1, round(original.get_height()*scale)))
            result = (pygame.transform.smoothscale(original, size), True)
        self.scaled[key] = result
        return result


def journal_is_unlocked(journal, discovery):
    return journal.is_found(discovery)


def gallery_blocks(discovery, unlocked, response=None, loading=False):
    """Keep authenticated facts, image credit and copilot text visibly separate."""
    white, muted = (255, 255, 255), (180, 190, 205)
    cyan, amber = (80, 220, 255), (255, 215, 100)
    if not unlocked:
        return [('text', 'UNDISCOVERED LOCATION', cyan),
                ('text', 'Investigate this site in the field to unlock its photograph and scientific record.', white)]
    blocks = [
        ('text', discovery.name, cyan),
        ('image', discovery.image_file, None),
        ('text', 'NASA PHOTOGRAPH / MISSION: ' + discovery.image_mission, cyan),
        ('text', discovery.image_caption, white),
        ('text', 'Image credit: ' + discovery.image_credit, muted),
        ('text', 'Photo source: ' + discovery.image_source_url, muted),
        ('text', 'Original image: ' + discovery.image_url, muted),
        ('text', '', white),
        ('text', 'VERIFIED DISCOVERY RECORD', cyan),
        ('text', 'Location: ' + discovery.location + '. ' + discovery.description, white),
        ('text', 'Significance: ' + discovery.significance, white),
        ('text', 'Science source: ' + discovery.source_url, muted),
        ('text', '', white),
        ('text', 'GEMMA COPILOT / OFFLINE RESPONSE', amber),
        ('text', 'AI output may be mistaken and is not verified by NASA.', muted),
        ('text', 'Contacting Gemma... A response can take over a minute.' if loading else (response or 'Press F to request an explanation.'), white),
        ('text', '', white),
        ('text', 'MarsOps AI is an educational simulation and is not endorsed by NASA.', muted),
    ]
    return blocks


def draw_gallery(surface, rect, blocks, font, scroll, cache, line_height=22):
    """Lay out text and images as a single bounded scroll area."""
    rows = []
    y = 0
    for kind, value, color in blocks:
        if kind == 'image':
            image, _ = cache.get(value, (rect.width-18, 270), font)
            rows.append(('image', image, y, image.get_height()))
            y += image.get_height() + 12
        else:
            for line in wrap_text(value, font, rect.width-18):
                rows.append(('text', (line, color), y, line_height))
                y += line_height
    scroll.extent(y, rect.height)
    old_clip = surface.get_clip()
    surface.set_clip(rect)
    for kind, value, offset, height in rows:
        top = rect.y + offset - int(scroll.offset)
        if top >= rect.bottom or top+height <= rect.top:
            continue
        if kind == 'image':
            surface.blit(value, (rect.x + (rect.width-value.get_width())//2, top))
        else:
            line, color = value
            if line:
                surface.blit(font.render(line, False, color), (rect.x, top))
    surface.set_clip(old_clip)
    x = rect.right - 7
    if scroll.offset > 0:
        pygame.draw.polygon(surface, (150,185,190), [(x-4,rect.top+7),(x+4,rect.top+7),(x,rect.top+2)])
    if scroll.offset < scroll.maximum:
        pygame.draw.polygon(surface, (150,185,190), [(x-4,rect.bottom-7),(x+4,rect.bottom-7),(x,rect.bottom-2)])
