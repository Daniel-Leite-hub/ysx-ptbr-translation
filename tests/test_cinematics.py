import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from ysx_studio import core, cinematics


class CinematicsTests(unittest.TestCase):
    def test_event_roundtrip(self):
        original = {"TRACK": [{"EVENT_TIME": 3.2, "DIALOGUE_ID": "DLG_DUMMY",
                              "SUBTITLE": [{"": "Hello"}, {"": "there<w3000>"}]},
                             {"EVENT_TIME": 9, "DIALOGUE_ID": "DLG_DUMMY",
                              "SUBTITLE": [{"": "Bye"}]}], "ANIMATION": [1, 2, 3]}
        with patch.object(cinematics, "load", return_value=copy.deepcopy(original)):
            rows = core.extract_file(Path("example.maya_scene"))
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0].source_start, rows[1].source_start)
        result = cinematics.patch(copy.deepcopy(original), [
            dict(original=r.original, context=r.context, translation=t, reviewed="")
            for r, t in zip(rows, ["Olá\naí<w3000>", "Tchau"], strict=True)])
        result["TRACK"][0]["SUBTITLE"] = original["TRACK"][0]["SUBTITLE"]
        result["TRACK"][1]["SUBTITLE"] = original["TRACK"][1]["SUBTITLE"]
        self.assertEqual(result, original)

    def test_line_count_and_controls(self):
        self.assertFalse(core.validate_text("a\nb<w10>", "ab<w10>", kind=cinematics.KIND)[-1])
        self.assertFalse(core.validate_text("a<w10>", "a", kind=cinematics.KIND)[-1])
        self.assertFalse(core.validate_text("a\nb<w10>", "a<w10>\nb", kind=cinematics.KIND)[-1])
        self.assertEqual(core.normalize_text_for_kind("a\nb", cinematics.KIND), "a\nb")


if __name__ == "__main__":
    unittest.main()
