"""Street-name abbreviation is pure and used by both the index and map labels."""
import unittest

from names import abbreviate


class TestAbbreviate(unittest.TestCase):
    def test_known_word_is_abbreviated(self):
        self.assertEqual(abbreviate("AVENIDA CORRIENTES"), "AV. CORRIENTES")

    def test_accent_insensitive_match(self):
        # CAPITAN is keyed without accent; CAPITÁN must still match.
        self.assertEqual(abbreviate("CAPITÁN GENERAL RAMÓN"), "CAP. GRAL. RAMÓN")

    def test_unknown_word_untouched(self):
        self.assertEqual(abbreviate("CALLE FALSA"), "CALLE FALSA")

    def test_trailing_comma_preserved(self):
        self.assertEqual(abbreviate("GENERAL PAZ, ALTOS"), "GRAL. PAZ, ALTOS")

    def test_already_abbreviated_left_alone(self):
        self.assertEqual(abbreviate("AV. SANTA FE"), "AV. SANTA FE")


if __name__ == "__main__":
    unittest.main()
