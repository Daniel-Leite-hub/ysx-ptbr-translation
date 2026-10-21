import unittest
from pathlib import Path
from unittest.mock import patch
from ysx_studio import sharing, core


class SharingTests(unittest.TestCase):
    def test_invalid_mode_rejected_before_writes(self):
        with self.assertRaises(core.StudioError):
            sharing.generate(Path('absent'), Path('.'), Path('.'), 'invalid')

    def test_missing_patch_rejected(self):
        with self.assertRaises(core.StudioError):
            sharing.generate(Path('absent'), Path('.'), Path('.'), 'zip')

    def test_ui_has_both_options(self):
        source = (Path(__file__).parents[1] / 'frontend/app.js').read_text(encoding='utf-8')
        self.assertIn('id="share-zip"', source)
        self.assertIn('id="share-exe"', source)
        self.assertIn("api('share',{mode})", source)


if __name__ == '__main__':
    unittest.main()
