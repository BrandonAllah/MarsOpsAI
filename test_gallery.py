import tempfile
import unittest
from pathlib import Path
import pygame
from discoveries import DISCOVERIES, DiscoveryJournal
from gallery import DiscoveryImageCache, gallery_blocks, journal_is_unlocked, draw_gallery
from ui_navigation import ScrollState


class GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.font = pygame.font.Font(None, 18)

    def test_all_real_photos_have_local_assets_and_metadata(self):
        cache = DiscoveryImageCache()
        for item in DISCOVERIES:
            with self.subTest(item=item.id):
                self.assertTrue(item.image_file and item.image_url.startswith('https://assets.science.nasa.gov/'))
                self.assertTrue(item.image_source_url.startswith('https://science.nasa.gov/'))
                self.assertTrue(item.image_credit and item.image_caption and item.image_mission)
                image, available = cache.get(item.image_file, (620, 270), self.font)
                self.assertTrue(available)
                self.assertLessEqual(image.get_width(), 620)
                self.assertLessEqual(image.get_height(), 270)
                original = cache.originals[item.image_file]
                self.assertAlmostEqual(image.get_width()/image.get_height(), original.get_width()/original.get_height(), delta=.03)
                self.assertIs(cache.get(item.image_file, (620, 270), self.font)[0], image)

    def test_missing_and_corrupt_images_use_cached_placeholder(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            Path(temp, 'bad.jpg').write_bytes(b'not an image')
            cache = DiscoveryImageCache(temp)
            for filename in ('missing.jpg', 'bad.jpg'):
                image, available = cache.get(filename, (400, 200), self.font)
                self.assertFalse(available)
                self.assertIs(cache.get(filename, (400, 200), self.font)[0], image)

    def test_journal_locks_content_until_investigated(self):
        journal = DiscoveryJournal()
        item = DISCOVERIES[0]
        self.assertFalse(journal_is_unlocked(journal, item))
        blocks = gallery_blocks(item, False)
        self.assertFalse(any(b[0] == 'image' or item.name in b[1] for b in blocks))
        journal.investigate(item)
        self.assertTrue(journal_is_unlocked(journal, item))
        blocks = gallery_blocks(item, True, 'Gemma test response')
        self.assertTrue(any(b[0] == 'image' and b[1] == item.image_file for b in blocks))
        text = ' '.join(b[1] for b in blocks if b[0] == 'text')
        self.assertIn(item.image_credit, text)
        self.assertIn(item.image_source_url, text)
        self.assertIn(item.description, text)
        self.assertIn('Gemma test response', text)
        self.assertIn('not verified by NASA', text)

    def test_gallery_scroll_and_clipping(self):
        target = pygame.Surface((800, 500))
        viewport = pygame.Rect(50, 70, 650, 250)
        scroll, cache = ScrollState(), DiscoveryImageCache()
        blocks = gallery_blocks(DISCOVERIES[1], True, 'AI explanation')
        draw_gallery(target, viewport, blocks, self.font, scroll, cache)
        self.assertGreater(scroll.maximum, 0)
        scroll.move(100000)
        draw_gallery(target, viewport, blocks, self.font, scroll, cache)
        self.assertEqual(scroll.offset, scroll.maximum)
        self.assertEqual(target.get_at((100, 30))[:3], (0, 0, 0))
        self.assertEqual(target.get_at((100, 350))[:3], (0, 0, 0))


if __name__ == '__main__': unittest.main()
