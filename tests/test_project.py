import sqlite3
import unittest
import uuid
from pathlib import Path

from ysx_studio import project


class ProjectPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).parent / f"_runtime_project_{uuid.uuid4().hex}.ysxproj"
        self.db = project.connect(self.path)
        self.db.execute("""INSERT INTO dialogues(
            file_name,kind,source_start,source_end,original,original_bytes,
            original_width,original_lines,tags,context)
            VALUES('sample.ing','diálogo',1,2,'Hello',5,5,1,'[]','teste')""")
        self.db.commit()
        self.row_id = self.db.execute("SELECT id FROM dialogues").fetchone()[0]

    def tearDown(self):
        project.checkpoint(self.db)
        self.db.close()
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            if candidate.exists():
                candidate.unlink()

    def test_revised_text_is_committed_exactly_and_versioned(self):
        reviewed = "  Ação, café e coração.\n"
        changed = project.save_text(self.db, self.row_id, "Rascunho", reviewed, False, "autosave")
        self.assertTrue(changed)
        project.checkpoint(self.db)

        reopened = sqlite3.connect(self.path)
        try:
            saved = reopened.execute(
                "SELECT translation,reviewed,revision,updated_at FROM dialogues WHERE id=?",
                (self.row_id,),
            ).fetchone()
            history = reopened.execute(
                "SELECT reviewed,source FROM edit_history WHERE dialogue_id=?",
                (self.row_id,),
            ).fetchone()
        finally:
            reopened.close()
        self.assertEqual(saved[0], "Rascunho")
        self.assertEqual(saved[1], "Ação, café e coração.")
        self.assertEqual(saved[2], 1)
        self.assertTrue(saved[3])
        self.assertEqual(history, ("Ação, café e coração.", "autosave"))

    def test_unchanged_autosave_does_not_create_duplicate_history(self):
        project.save_text(self.db, self.row_id, "Olá", "Revisado", False, "autosave")
        self.db.execute("UPDATE dialogues SET error='Erro antigo',size_ok=0 WHERE id=?", (self.row_id,))
        self.db.commit()
        changed = project.save_text(self.db, self.row_id, "Olá", "Revisado", False, "autosave")
        count = self.db.execute(
            "SELECT COUNT(*) FROM edit_history WHERE dialogue_id=?", (self.row_id,)
        ).fetchone()[0]
        self.assertFalse(changed)
        self.assertEqual(count, 1)
        refreshed = self.db.execute(
            "SELECT error,size_ok FROM dialogues WHERE id=?", (self.row_id,)
        ).fetchone()
        self.assertEqual(refreshed["error"], "")
        self.assertTrue(refreshed["size_ok"])

    def test_build_uses_translation_until_review_is_ready(self):
        project.save_text(self.db, self.row_id, "Apenas rascunho", "", False, "autosave")
        row = self.db.execute("SELECT * FROM dialogues WHERE id=?", (self.row_id,)).fetchone()
        self.assertEqual(project.effective_text(row), "Apenas rascunho")
        rows = project.rows_for_build(self.db)
        self.assertEqual(rows["sample.ing"][0]["translation"], "Apenas rascunho")
        project.save_text(self.db, self.row_id, "Apenas rascunho", "Texto revisado", False, "manual")
        row = self.db.execute("SELECT * FROM dialogues WHERE id=?", (self.row_id,)).fetchone()
        self.assertEqual(project.effective_text(row), "Texto revisado")
        rows = project.rows_for_build(self.db)
        self.assertEqual(rows["sample.ing"][0]["reviewed"], "Texto revisado")

    def test_individual_validation_can_clear_strict_size_error(self):
        project.save_text(self.db, self.row_id, "Olá mundo", "", True, "manual")
        self.assertFalse(self.db.execute(
            "SELECT size_ok FROM dialogues WHERE id=?", (self.row_id,)
        ).fetchone()[0])
        row = project.validate_row(self.db, self.row_id, False)
        self.assertTrue(row["size_ok"])
        self.assertEqual(row["error"], "")

    def test_save_wraps_at_72_columns_before_persisting(self):
        translation = "A" * 68 + " palavra"
        project.save_text(self.db, self.row_id, translation, "", False, "manual")
        saved = self.db.execute(
            "SELECT translation,translated_width,translated_lines FROM dialogues WHERE id=?",
            (self.row_id,),
        ).fetchone()
        self.assertEqual(saved["translation"], "A" * 68 + "\npalavra")
        self.assertEqual(saved["translated_width"], 68)
        self.assertEqual(saved["translated_lines"], 2)

    def test_official_language_context_does_not_replace_portuguese(self):
        project.save_text(self.db, self.row_id, "Rascunho", "Revisão", False)
        before = tuple(self.db.execute("SELECT * FROM dialogues WHERE id=?", (self.row_id,)).fetchone())
        self.db.execute("INSERT INTO language_context VALUES(?,?,?,?,?,?,?,?)",
                        (self.row_id, 'ja', 'こんにちは', 'script/a.dat', '{}', 'abc', 'verified', '2026-10-04'))
        self.db.commit()
        self.assertEqual(project.language_context(self.db, self.row_id)['ja']['text'], 'こんにちは')
        after = self.db.execute("SELECT * FROM dialogues WHERE id=?", (self.row_id,)).fetchone()
        self.assertEqual(before, tuple(after))
        self.assertEqual(project.effective_text(after), 'Revisão')

    def test_clear_automatic_translations_preserves_reviewed_and_history(self):
        project.save_text(self.db, self.row_id, "Rascunho antigo", "Texto revisado", False, "manual")
        cleared = project.clear_automatic_translations(self.db)
        saved = self.db.execute(
            "SELECT translation,reviewed,provider,size_ok FROM dialogues WHERE id=?", (self.row_id,)
        ).fetchone()
        history = self.db.execute(
            "SELECT COUNT(*) FROM edit_history WHERE dialogue_id=?", (self.row_id,)
        ).fetchone()[0]
        self.assertEqual(cleared, 1)
        self.assertEqual(saved["translation"], "")
        self.assertEqual(saved["reviewed"], "Texto revisado")
        self.assertEqual(saved["provider"], "")
        self.assertTrue(saved["size_ok"])
        self.assertEqual(history, 1)


if __name__ == "__main__":
    unittest.main()
