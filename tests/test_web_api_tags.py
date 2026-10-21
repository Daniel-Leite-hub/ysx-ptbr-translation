import unittest
import uuid
from pathlib import Path

from ysx_studio import project
from ysx_studio.web_api import WebApi


class WebApiTagSearchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent
        self.path = self.root / f"_runtime_tags_{uuid.uuid4().hex}.ysxproj"
        db = project.connect(self.path)
        try:
            db.executemany("""INSERT INTO dialogues(
                file_name,kind,source_start,source_end,original,original_bytes,
                original_width,original_lines,tags,context)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (
                ("table_eng/t_item.tbl", "item", 1, 2, "Potion", 6, 6, 1, "[]",
                 "ItemTableData · registro 1 · campo name"),
                ("table_eng/t_item.tbl", "item", 3, 4, "Restores HP", 11, 11, 1, "[]",
                 "ItemTableData · registro 1 · campo long_desc"),
                ("talk_main.ing", "diálogo", 5, 6, "Adol speaks", 11, 11, 1, "[]", "system[5,11](...)"),
            ))
            db.commit()
        finally:
            db.close()
        self.api = WebApi(self.root)
        self.api.project_path = self.path

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            if candidate.exists():
                candidate.unlink()

    def test_tag_search_accepts_accents_aliases_and_multiple_tags(self):
        descriptions = self.api.rows(search="tag:descrições")
        self.assertEqual(descriptions["total"], 1)
        self.assertIn("descricoes", descriptions["items"][0]["content_tags"])
        item_names = self.api.rows(search="Potion tag:item tag:nomes")
        self.assertEqual(item_names["total"], 1)
        self.assertEqual(item_names["items"][0]["original"], "Potion")
        self.assertEqual(self.api.rows(search="tag:vozes")["total"], 0)


if __name__ == "__main__":
    unittest.main()
