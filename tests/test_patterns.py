import importlib
from pathlib import Path
import sys
import types
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "custom_components" / "govee_light_local"
if "govee_light_local" not in sys.modules:
    package = types.ModuleType("govee_light_local")
    package.__path__ = [str(PACKAGE)]
    sys.modules["govee_light_local"] = package
patterns = importlib.import_module("govee_light_local.patterns")


class PatternBookTest(unittest.TestCase):
    def setUp(self):
        self.book = patterns.PatternBook()

    def test_upsert_replaces_a_pattern_with_the_same_name(self):
        self.book.upsert("Noël", ["#ff0000"])
        self.book.upsert("  Noël ", ["#00ff00", None])
        self.assertEqual(self.book.patterns, {"Noël": ["#00ff00", None]})

    def test_empty_name_is_refused(self):
        for name in ("", "   ", None):
            with self.assertRaises(ValueError):
                self.book.upsert(name, ["#ff0000"])

    def test_empty_or_bad_colors_are_refused(self):
        with self.assertRaises(ValueError):
            self.book.upsert("Vide", [])
        with self.assertRaises(ValueError):
            self.book.upsert("Faux", ["rouge"])

    def test_remove_unknown_name_is_silent(self):
        self.book.remove("absent")
        self.assertEqual(self.book.patterns, {})

    def test_segment_count_defaults_then_overrides(self):
        self.assertEqual(self.book.segment_count("aa:bb", "H61D5"), 14)
        self.book.set_segment_count("aa:bb", 20)
        self.assertEqual(self.book.segment_count("aa:bb", "H61D5"), 20)
        with self.assertRaises(ValueError):
            self.book.set_segment_count("aa:bb", 0)
        with self.assertRaises(ValueError):
            self.book.set_segment_count("aa:bb", 57)

    def test_data_round_trip(self):
        self.book.upsert("A", ["#ff0000"])
        self.book.set_segment_count("x", 9)
        copy = patterns.PatternBook(self.book.data)
        self.assertEqual(copy.patterns, {"A": ["#ff0000"]})
        self.assertEqual(copy.segment_count("x", "H6076"), 9)


class PatternNameTest(unittest.TestCase):
    def test_both_language_labels_resolve_the_same_pattern(self):
        names = {"Noël", "Sunset · warm"}
        self.assertEqual(patterns.pattern_name("Mes motifs · Noël", names), "Noël")
        self.assertEqual(patterns.pattern_name("My patterns · Noël", names), "Noël")
        self.assertEqual(
            patterns.pattern_name("My patterns · Sunset · warm", names), "Sunset · warm"
        )

    def test_unknown_or_foreign_effects_do_not_resolve(self):
        names = {"Noël"}
        self.assertIsNone(patterns.pattern_name("My patterns · Absent", names))
        self.assertIsNone(patterns.pattern_name("Nature · Noël", names))
        self.assertIsNone(patterns.pattern_name("Noël", names))
        self.assertIsNone(patterns.pattern_name(None, names))


if __name__ == "__main__":
    unittest.main()
