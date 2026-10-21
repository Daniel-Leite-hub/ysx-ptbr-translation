import unittest
from pathlib import Path


class FrontendBehaviorTests(unittest.TestCase):
    def test_typing_marks_dirty_without_timed_autosave(self):
        script = (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
        function = script.split("function scheduleSave()", 1)[1].split("}\n", 1)[0]
        self.assertIn("state.dirty=true", function)
        self.assertNotIn("setTimeout", function)
        self.assertNotIn("saveSelected", function)

    def test_original_has_copy_enhancement(self):
        script = (Path(__file__).parents[1] / "frontend" / "ui_enhancements.js").read_text(encoding="utf-8")
        self.assertIn("original-copy", script)
        self.assertIn("copy-original", script)
        self.assertIn("Texto usado no jogo: tradução automática", script)
        self.assertIn("if (effective.textContent !== text)", script)
        self.assertIn("enhancementObserver.disconnect()", script)
        self.assertIn("YS X STUDIO / 2.3.1", script)
        self.assertIn("Sincronizar textos brutos", script)
        self.assertIn("tag:dialogos", script)
        self.assertIn("Buscar por texto, arquivo ou tag", script)

    def test_filter_selects_first_visible_row(self):
        script = (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn("else if(!fresh&&!state.dirty)state.selected=state.rows[0]||null", script)

    def test_deepl_context_is_editable_and_explains_line_normalization(self):
        script = (Path(__file__).parents[1] / "frontend" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="deepl-context"', script)
        self.assertIn("deepl_context:'deepl-context'", script)
        self.assertIn("Quebras visuais são unidas antes do envio", script)


if __name__ == "__main__":
    unittest.main()
