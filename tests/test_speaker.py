import sqlite3
import unittest

from ysx_studio import speaker


class SpeakerTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE sample (kind TEXT, context TEXT)")

    def tearDown(self):
        self.db.close()

    def row(self, kind, context):
        self.db.execute("DELETE FROM sample")
        self.db.execute("INSERT INTO sample VALUES (?,?)", (kind, context))
        return self.db.execute("SELECT * FROM sample").fetchone()

    def test_choice_is_adol_with_confirmed_masculine_gender(self):
        data = speaker.classify(self.row("escolha", ""), None, {})
        self.assertEqual(data[1:3], ("Adol", "masculino"))

    def test_narration_has_no_gender(self):
        data = speaker.classify(self.row("diálogo", "system[5,11](65535, \"Texto\")"), None, {})
        self.assertEqual(data[1:3], ("Narrador", ""))

    def test_profile_mapping_identifies_karja(self):
        data = speaker.classify(
            self.row("diálogo", "system[5,11](2, \"Texto\")"), None,
            {"2": ("Karja", "feminino", "confirmado pelo perfil")},
        )
        self.assertEqual(data[1:3], ("Karja", "feminino"))


if __name__ == "__main__":
    unittest.main()
