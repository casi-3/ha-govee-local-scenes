import importlib.util
from pathlib import Path
from typing import ClassVar
import unittest

MODULE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "govee_light_local"
    / "scene_library.py"
)
spec = importlib.util.spec_from_file_location("scene_library", MODULE)
scene_library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scene_library)

FOREST_PARAM = (
    "AyYAAQAKAgH/GQG0CgoCyBQF//8AAP//////AP//lP8AFAGWAAAAACMAAg8FAgH/FAH7AAAB"
    "+goEBP8AtP8AR///4/8AAAAAAAAAABoAAAABAgH/BQHIFBQC7hQBAP8AAAAAAAAAAA=="
)
FOREST_EXPECTED = """a3 00 01 07 02 03 26 00 01 00 0a 02 01 ff 19 01 b4 0a 0a d9
a3 01 02 c8 14 05 ff ff 00 00 ff ff ff ff ff 00 ff ff 94 12
a3 02 ff 00 14 01 96 00 00 00 00 23 00 02 0f 05 02 01 ff 0a
a3 03 14 01 fb 00 00 01 fa 0a 04 04 ff 00 b4 ff 00 47 ff b3
a3 04 ff e3 ff 00 00 00 00 00 00 00 00 1a 00 00 00 01 02 5d
a3 05 01 ff 05 01 c8 14 14 02 ee 14 01 00 ff 00 00 00 00 92
a3 ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 5c
33 05 04 d4 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 e6"""


def as_hex(lines):
    return "\n".join(" ".join(f"{b:02x}" for b in line) for line in lines)


class ScenePacketTests(unittest.TestCase):
    def test_scene_with_parameters_matches_reference(self):
        self.assertEqual(as_hex(scene_library.scene_packets(212, FOREST_PARAM, 2)), FOREST_EXPECTED)

    def test_builtin_scene_is_a_single_packet(self):
        lines = scene_library.scene_packets(22, None, 0)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            as_hex(lines), "33 05 04 16 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 24"
        )

    def test_header_carries_the_scene_type(self):
        lines = scene_library.scene_packets(2658, "gwH/yP8oAAL/AAD/fwA=", 1)
        self.assertEqual(
            as_hex(lines),
            "a3 ff 01 01 01 83 01 ff c8 ff 28 00 02 ff 00 00 ff 7f 00 42\n"
            "33 05 04 62 0a 00 00 00 00 00 00 00 00 00 00 00 00 00 00 5a",
        )

    def test_every_packet_is_twenty_bytes(self):
        for line in scene_library.scene_packets(212, FOREST_PARAM, 2):
            self.assertEqual(len(line), 20)


class CatalogTests(unittest.TestCase):
    payload: ClassVar[dict] = {
        "data": {
            "categories": [
                {
                    "categoryName": "Life",
                    "scenes": [
                        {
                            "sceneName": "Movie",
                            "lightEffects": [{"sceneCode": 2143, "scenceParam": "AQID"}],
                        }
                    ],
                },
                {
                    "categoryName": "Natural",
                    "scenes": [
                        {
                            "sceneName": "Rainbow",
                            "lightEffects": [{"sceneCode": 22, "scenceParam": ""}],
                        },
                        {"sceneName": "Broken", "lightEffects": [{"sceneCode": 0}]},
                    ],
                },
            ]
        }
    }

    def test_parse_keeps_valid_scenes_only(self):
        catalog = scene_library.parse_library("H0000", self.payload)
        self.assertEqual([s["name"] for s in catalog["scenes"]], ["Movie", "Rainbow"])
        self.assertIsNone(catalog["scenes"][1]["param"])
        self.assertEqual(catalog["version"], scene_library.CATALOG_VERSION)

    def test_effect_names_are_grouped_and_translated(self):
        catalog = scene_library.parse_library("H0000", self.payload)
        self.assertEqual(
            list(scene_library.effect_names(catalog, "en")), ["Natural · Rainbow", "Life · Movie"]
        )
        self.assertEqual(
            list(scene_library.effect_names(catalog, "fr")), ["Nature · Rainbow", "Vie · Movie"]
        )

    def test_duplicate_names_get_their_code(self):
        catalog = {
            "scenes": [
                {"category": "Natural", "name": "Sea", "code": 1, "param": None},
                {"category": "Natural", "name": "Sea", "code": 2, "param": None},
            ]
        }
        self.assertEqual(
            list(scene_library.effect_names(catalog, "en")), ["Natural · Sea", "Natural · Sea (2)"]
        )

    def test_bundled_catalog_is_valid(self):
        import json

        bundled = json.loads(
            (MODULE.parent / "catalogs" / "H6076.json").read_text(encoding="utf-8")
        )
        self.assertEqual(bundled["sku"], "H6076")
        self.assertEqual(len(bundled["scenes"]), 108)
        self.assertEqual(bundled["version"], scene_library.CATALOG_VERSION)
        self.assertTrue(all("type" in scene for scene in bundled["scenes"]))
        self.assertIn("Natural · Rainbow", scene_library.effect_names(bundled, "en"))


if __name__ == "__main__":
    unittest.main()
