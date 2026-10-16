import json
from pathlib import Path
import unittest

from test_scene_library import scene_library


class H60A6EncodingTests(unittest.TestCase):
    def test_reference_scene_formats(self):
        fixtures = json.loads(
            (Path(__file__).parent / "fixtures/h60a6_scene_encoding.json").read_text()
        )
        for scene in fixtures["scenes"]:
            with self.subTest(scene=scene["name"]):
                actual = scene_library.scene_packets(
                    scene["code"], scene["param"], scene["type"], "H60A6"
                )
                self.assertEqual([f.hex() for f in actual], scene["expected_hex"])

    def test_other_skus_keep_legacy_encoding(self):
        param = "gwH/yP8oAAL/AAD/fwA="
        expected = scene_library.scene_packets(2658, param, 1)
        self.assertEqual(scene_library.scene_packets(2658, param, 1, "H6076"), expected)

    def test_invalid_h60a6_type5_is_explicit(self):
        with self.assertRaises(ValueError):
            scene_library.scene_packets(19076, "AQID", 5, "H60A6")


if __name__ == "__main__":
    unittest.main()
