import unittest
from pathlib import Path

from ysx_studio import core


class CoreTests(unittest.TestCase):
    def test_content_tags_map_categories_and_descriptions(self):
        item = core.content_tags(
            "table_eng/t_item.tbl", "item",
            'ItemTableData · registro 1 · campo long_desc\n{"field":"long_desc"}',
        )
        self.assertIn("itens", item)
        self.assertIn("descricoes", item)
        self.assertIn("habilidades", core.content_tags(
            "table_eng/t_skill.tbl", "habilidade", "SSkillTable · campo name"))
        self.assertIn("tutoriais", core.content_tags(
            "table_eng/t_help.tbl", "interface/ajuda", "HelpPage · campo text3"))
        self.assertIn("perfis", core.content_tags(
            "table_eng/t_character_lib.tbl", "personagem/jornal", "CharaLibData · campo text2"))
        self.assertEqual(core.normalize_content_tag("Missão"), "missoes")

    def test_dynamic_message_preserves_numeric_arguments(self):
        context = 'system[5,11](65535, "Adol equipped the ", 17, 5198, ".");'
        self.assertTrue(core.requires_dynamic_segment(context))
        segment = '"Adol equipped the ", 17, 5198, "."'
        result = core.replacement_preserving_dynamic(segment, 'Adol equipou o \n.')
        self.assertIn(', 17, 5198,', result)
        self.assertIn('"Adol equipou o "', result)

    def test_extract_message_and_choice(self):
        path = Path(__file__).parent / "fixtures" / "sample.ing"
        rows = core.extract_file(path)
        self.assertEqual([row.original for row in rows], ["Hello,\nworld!", "Yes.", "No."])

    def test_extracts_selection_interface_variants(self):
        path = Path(__file__).parent / "fixtures" / "selection_variants.ing"
        rows = core.extract_file(path)
        self.assertEqual([row.original for row in rows], [
            "First choice", "Second choice", "Third choice", "<C1>Obtained ",
            "Move to\nthe next island!", "Use this item?", "Yes", "No",
        ])
        self.assertEqual(rows[3].kind, "texto de sistema")
        self.assertEqual(rows[4].kind, "diálogo/voz")

    def test_tags_and_size_policy(self):
        result = core.validate_text("<C1>Hello", "<C1>Olá")
        self.assertTrue(result[-1])
        self.assertFalse(core.validate_text("<C1>Hello", "Olá")[-1])
        self.assertFalse(core.validate_text("Hi", "Olá mundo", True)[-1])

    def test_replacement_expression(self):
        self.assertEqual(core.replacement_expression("Olá\nmundo"), '"Olá", 10, "mundo"')

    def test_replacement_preserves_spaces_and_final_line_break(self):
        self.assertEqual(core.replacement_expression("  Olá\n"), '"  Olá", 10, ""')
        self.assertEqual(core.text_metrics("  Olá\n")[-1], 2)

    def test_portuguese_glyph_set(self):
        self.assertIn("ã", core.PORTUGUESE_GLYPHS)
        self.assertIn("Õ", core.PORTUGUESE_GLYPHS)

    def test_visual_wrap_moves_whole_word_to_next_line(self):
        text = "A" * 68 + " palavra"
        wrapped = core.wrap_visual_lines(text)
        self.assertEqual(wrapped, "A" * 68 + "\npalavra")
        self.assertEqual(core.text_metrics(wrapped)[1], 68)

    def test_visual_wrap_preserves_tags_and_reflows_premature_breaks(self):
        text = "<C1>" + "A" * 68 + " palavra\nSegunda linha"
        wrapped = core.wrap_visual_lines(text)
        self.assertEqual(wrapped, "<C1>" + "A" * 68 + "\npalavra Segunda linha")
        self.assertEqual(core.tags_signature(text), core.tags_signature(wrapped))

    def test_third_line_only_exists_after_second_overflows(self):
        text = "\n".join(["um " * 8, "dois " * 6, "três " * 6]).strip()
        wrapped = core.wrap_visual_lines(text, limit=30)
        lines = wrapped.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertGreater(core.visible_width(" ".join(lines)), 60)
        self.assertLessEqual(max(map(core.visible_width, lines)), 30)

    def test_printf_controls_are_protected(self):
        self.assertTrue(core.validate_text("Tempo: %dh %dm", "Tempo: %dh %dm")[4])
        self.assertFalse(core.validate_text("Tempo: %dh %dm", "Tempo: %d")[4])

    def test_major_table_text_sources_are_catalogued(self):
        expected = {"t_item.tbl", "t_character_lib.tbl", "t_dialogue.tbl", "t_active_voice.tbl",
                    "t_help.tbl", "t_quest.tbl", "t_monster_lib.tbl", "t_text.tbl", "t_tips.tbl"}
        self.assertTrue(expected.issubset(core.TABLE_TEXT_FIELDS))
        self.assertNotIn("data", core.TABLE_TEXT_FIELDS.get("t_challenge_dungeon.tbl", {}))

    def test_visual_wrap_does_not_split_a_single_long_word(self):
        word = "A" * 73
        self.assertEqual(core.wrap_visual_lines(word), word)
        self.assertFalse(core.validate_text("Short", word)[-1])

    def test_choice_requires_one_line_and_its_own_visual_limit(self):
        self.assertEqual(
            core.normalize_text_for_kind("Escolha\ncurta", "escolha"),
            "Escolha curta",
        )
        self.assertTrue(core.validate_text("Original", "A" * 67, kind="escolha")[-1])
        self.assertFalse(core.validate_text("Original", "A" * 68, kind="escolha")[-1])
        self.assertFalse(core.validate_text("Original", "Uma\nescolha", kind="escolha")[-1])

    def test_tip_body_uses_dedicated_visual_limit(self):
        context = 'TipsTable · registro 1 · campo text3\n{"field":"text3"}'
        text = "Uma dica bastante longa deve ser quebrada por palavra sem transbordar o painel visual."
        result = core.normalize_text_for_kind(text, "interface/ajuda", context)
        self.assertTrue(all(
            core.visible_width(line) <= core.DICAS_VISUAL_LIMIT
            for line in result.splitlines()
        ))

    def test_quest_body_uses_dedicated_visual_limit(self):
        context = 'QuestText · registro 1 · campo text\n{"field":"text"}'
        text = "Uma descrição de missão longa deve quebrar por palavras e permanecer dentro do quadro de aceite."
        result = core.normalize_text_for_kind(text, "missão/jornal", context)
        self.assertTrue(all(
            core.visible_width(line) <= core.MISSOES_VISUAL_LIMIT
            for line in result.splitlines()
        ))

    def test_map_island_description_preserves_balanced_breaks(self):
        context = 'MapIslandTable · registro 10 · campo island_desc\n{"field":"island_desc"}'
        text = (
            "A maior cidade do Golfo de Obelia.\n"
            "Um movimentado centro comercial que\n"
            "abriga inúmeros gllianos."
        )
        result = core.normalize_text_for_kind(text, "mapa", context)
        self.assertEqual(result, text)
        self.assertTrue(core.validate_text(
            "Original em\ntrês linhas\naqui", result, kind="mapa", context=context
        )[-1])
        self.assertTrue(all(
            core.visible_width(line) <= core.MAP_ISLAND_DESC_VISUAL_LIMIT
            for line in result.splitlines()
        ))

    def test_item_panel_fields_are_kept_on_one_line(self):
        for field in ("name", "short_desc", "long_desc"):
            context = (
                f'ItemTableData · registro 1 · campo {field}\n'
                f'{{"section":"ItemTableData","index":1,"field":"{field}"}}'
            )
            result = core.normalize_text_for_kind(
                "Primeira parte\nsegunda parte", "item", context
            )
            self.assertEqual(result, "Primeira parte segunda parte")
            self.assertTrue(core.validate_text(
                "Original", result, kind="item", context=context
            )[-1])


if __name__ == "__main__":
    unittest.main()
