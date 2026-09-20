import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from games.bad_apple.player import Clip, Player
from scope_arcade.protocol import validate_lines

ROOT = Path(__file__).resolve().parents[1]


class AnimationTests(unittest.TestCase):
    def test_entire_bundled_clip_and_portable_metadata(self):
        path = ROOT / 'games/bad_apple/animation.xyframes'
        clip = Clip.load(path)
        self.assertEqual(clip.fps, 30)
        self.assertEqual(len(clip.frames), 6571)
        self.assertAlmostEqual(clip.duration, 219.033333333)
        self.assertNotIn(':', clip.source_name)
        self.assertNotIn('\\', clip.source_name)
        self.assertNotIn('/', clip.source_name)
        for index in range(len(clip.frames)):
            validate_lines(clip.lines_at((index + .1) / clip.fps))
        self.assertEqual(clip.lines_at(-1), clip.lines_at(0))
        self.assertEqual(clip.lines_at(9999), clip.lines_at(clip.duration))

    def test_pause_seek_restart_loop_and_end(self):
        player = Player(Clip(1, (b'\x01\x02\x03\x04',) * 12, 'test'))
        player.update(2, set())
        self.assertEqual(player.position, 2)
        player.update(2, {'space'})
        self.assertFalse(player.playing)
        self.assertEqual(player.position, 2)
        player.update(0, {'right'})
        self.assertEqual(player.position, 7)
        player.update(0, {'left'})
        self.assertEqual(player.position, 2)
        player.seek(-99)
        self.assertEqual(player.position, 0)
        player.seek(99)
        self.assertEqual(player.position, 12)
        player.update(0, {'space'})
        self.assertTrue(player.playing)
        self.assertEqual(player.position, 0)
        player.update(13, set())
        self.assertEqual(player.position, 1)
        player.update(12, {'l'})
        self.assertFalse(player.loop)
        self.assertFalse(player.playing)
        self.assertEqual(player.position, 12)
        player.update(0, {'home'})
        self.assertTrue(player.playing)
        self.assertEqual(player.position, 0)

    def test_invalid_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'clip.xyframes'
            cases = [
                ({'fps': 0}, b'\x01\x00\x00\x00\x00'),
                ({'fps': float('nan')}, b'\x01\x00\x00\x00\x00'),
                ({'version': 2}, b'\x01\x00\x00\x00\x00'),
                ({'frame_count': 18001}, b''),
                ({}, b'\x00'),
                ({}, b'\x49' + b'\x00' * 292),
                ({}, b'\x01\x00'),
                ({}, b'\x01\x00\x00\x00\x00\x00'),
            ]
            for changes, raw in cases:
                metadata = {'version': 1, 'fps': 30, 'frame_count': 1, **changes}
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('metadata.json', json.dumps(metadata))
                    archive.writestr('frames.bin', raw)
                with self.subTest(changes=changes, size=len(raw)):
                    with self.assertRaises(ValueError):
                        Clip.load(path)


@unittest.skipUnless(importlib.util.find_spec('cv2'), 'Optional offline converter dependencies not installed')
class ConverterTests(unittest.TestCase):
    def test_video_conversion_in_unicode_directory(self):
        import cv2
        import numpy as np
        from tools.convert_video import convert, vectorize
        black = np.zeros((120, 160, 3), dtype=np.uint8)
        self.assertEqual(vectorize(black), [(0, 0, 0, 0)])
        white = black + 255
        self.assertGreater(len(vectorize(white)), 1)
        with tempfile.TemporaryDirectory(prefix='动画 测试 ') as folder:
            source = Path(folder) / 'test clip.avi'
            destination = Path(folder) / 'test.xyframes'
            writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'MJPG'), 60, (160, 120))
            self.assertTrue(writer.isOpened())
            try:
                for index in range(12):
                    frame = black.copy()
                    cv2.circle(frame, (30 + index * 4, 60), 25, (255, 255, 255), -1)
                    writer.write(frame)
            finally:
                writer.release()
            convert(source, destination)
            source.unlink()
            clip = Clip.load(destination)
            self.assertEqual(clip.fps, 30)
            self.assertEqual(len(clip.frames), 6)
            self.assertEqual(clip.source_name, 'test clip.avi')
            self.assertNotEqual(clip.frames[0], clip.frames[-1])
            for index in range(6):
                validate_lines(clip.lines_at((index + .1) / 30))
