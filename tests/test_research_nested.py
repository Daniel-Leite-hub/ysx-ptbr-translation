import json
import unittest
from pathlib import Path
from unittest.mock import patch
from ysx_studio import core


class ResearchNestedTests(unittest.TestCase):
    def test_append_nested_without_changing_existing_offsets(self):
        document = {"data": [{"name": "ResearchName", "data": [{"text": "Bird"}]},
            {"name": "ResearchData", "data": [{"observations": "A bird.",
             "profile": [{"type": "Size: Small"}, {"type": ""}],
             "imressions": [{"character_id": 2, "text": "Look!"}],
             "picture": "asset_name", "unknown_u64": 999}]}]}
        with patch.object(Path, "read_text", return_value=json.dumps(document)):
            rows=core.extract_table_json(Path("t_research.json"))
        self.assertEqual([r.source_start for r in rows], [1,2,3,4])
        self.assertEqual([r.original for r in rows], ["Bird","A bird.","Size: Small","Look!"])
        self.assertEqual(core._table_locator(rows[3].context)["speaker_id"],2)
        self.assertEqual(core._table_locator(rows[3].context)["path"],[0,"text"])

    def test_research_lines_are_not_wrapped(self):
        context='ResearchData · campo imressions\n{"field":"imressions","path":[0,"text"]}'
        self.assertEqual(core.normalize_text_for_kind("Uma\nfrase.","bestiário",context),"Uma frase.")
        self.assertFalse(core.validate_text("A sentence.","Uma\nfrase.",kind="bestiário",context=context)[-1])
