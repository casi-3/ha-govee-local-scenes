import importlib.util
from pathlib import Path
import unittest

MODULE = (
    Path(__file__).resolve().parents[1] / "custom_components" / "govee_light_local" / "segments.py"
)
spec = importlib.util.spec_from_file_location("segments", MODULE)
segments = importlib.util.module_from_spec(spec)
spec.loader.exec_module(segments)


def xor(data):
    value = 0
    for byte in data:
        value ^= byte
    return value


class SegmentPacketsTest(unittest.TestCase):
    def test_two_colors_make_two_frames_grouped_by_color(self):
        lines = segments.segment_packets(["#ff0000", "#0000ff", "#ff0000"])
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0][:19].hex(" "),
            "33 05 15 01 ff 00 00 00 00 00 00 00 05 00 00 00 00 00 00",
        )
        self.assertEqual(lines[1][4:7], bytes([0, 0, 0xFF]))
        self.assertEqual(lines[1][12], 0x02)

    def test_mask_reaches_the_third_byte_past_sixteen_segments(self):
        lines = segments.segment_packets([None] * 17 + ["#ffffff"])
        white = next(line for line in lines if line[4:7] == bytes([0xFF] * 3))
        self.assertEqual(white[12:15], bytes([0x00, 0x00, 0x02]))

    def test_off_segments_are_sent_black(self):
        self.assertEqual(segments.segment_packets([None])[0][4:7], bytes(3))

    def test_every_frame_is_twenty_bytes_with_xor_checksum(self):
        colors = [f"#{i * 4:02x}{255 - i:02x}10" for i in range(56)]
        for line in segments.segment_packets(colors):
            self.assertEqual(len(line), 20)
            self.assertEqual(line[19], xor(line[:19]))

    def test_more_than_max_segments_is_refused(self):
        with self.assertRaises(ValueError):
            segments.segment_packets(["#ffffff"] * 57)

    def test_bad_color_is_refused(self):
        with self.assertRaises(ValueError):
            segments.parse_color("rouge")


class ResampleTest(unittest.TestCase):
    def test_resample_keeps_proportions(self):
        source = ["#ff0000"] * 6 + ["#0000ff"] * 6
        self.assertEqual(segments.resample(source, 4), ["#ff0000"] * 2 + ["#0000ff"] * 2)
        self.assertEqual(len(segments.resample(["#ff0000"] * 14, 15)), 15)

    def test_resample_stretches_a_single_color(self):
        self.assertEqual(segments.resample(["#ff0000"], 15), ["#ff0000"] * 15)

    def test_resample_of_nothing_is_all_off(self):
        self.assertEqual(segments.resample([], 3), [None, None, None])

    def test_known_model_count(self):
        self.assertEqual(segments.default_count("h61d5"), 14)
        self.assertEqual(segments.default_count("H6076"), 15)


if __name__ == "__main__":
    unittest.main()
