import importlib.util
from pathlib import Path
import unittest

MODULE = (
    Path(__file__).resolve().parents[1] / "custom_components" / "govee_light_local" / "preview.py"
)
spec = importlib.util.spec_from_file_location("preview", MODULE)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)

AURORA = {"name": "Aurora", "type": 5, "param": "LgEAABM5AAAUAAMBAQADAP8xAP/WAP8A"}
WAVE = {
    "name": "Wave",
    "type": 2,
    "param": "ASMAAAACAAH//wAAAAAC/TIEAAD/AH7/AOz/AAD/EwH8AAAAAA==",
}
LAYER_KEYS = {"colors", "mode", "pattern", "speed", "bright", "reverse"}


class PreviewTest(unittest.TestCase):
    def test_aurora_type5_palette(self):
        self.assertEqual(preview.palette(AURORA), ["#00ff31", "#00ffd6", "#00ff00"])

    def test_rgbic_layers_are_decoded(self):
        layers = preview.animation(WAVE)
        self.assertEqual(len(layers), 1)
        layer = layers[0]
        self.assertEqual(layer["mode"], 0)
        self.assertEqual(layer["pattern"], 2)
        self.assertEqual(layer["colors"], ["#0000ff", "#007eff", "#00ecff", "#0000ff"])
        self.assertEqual(layer["bright"]["kind"], 0)
        self.assertEqual(preview.palette(WAVE), ["#0000ff", "#007eff", "#00ecff"])

    def test_corrupt_param_never_raises(self):
        for param in ("AAAA", "////", "", None, "AQ", "BQEC"):
            for scene_type in (0, 2, 5, 6):
                layers = preview.animation({"name": "X", "type": scene_type, "param": param})
                self.assertTrue(layers)
                for layer in layers:
                    self.assertEqual(set(layer), LAYER_KEYS)
                    self.assertTrue(layer["colors"])

    def test_static_scene_without_param_gets_a_fallback(self):
        rainbow = preview.palette({"name": "Rainbow", "type": 0, "param": None})
        self.assertEqual(len(rainbow), 6)
        layers = preview.animation({"name": "Romantic", "type": 0, "param": None})
        self.assertEqual(layers[0]["colors"], ["#ffc48c"])


if __name__ == "__main__":
    unittest.main()
