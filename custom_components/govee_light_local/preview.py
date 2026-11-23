from __future__ import annotations

import base64
import binascii
from typing import Any

RGBIC_SCENE = 2
FALLBACK_COLOR = "#ffc48c"
RAINBOW = ["#ff0000", "#ff7f00", "#ffff00", "#00ff00", "#0000ff", "#8b00ff"]
MOTIONS = [
    ("flicker", ("fire", "flame", "candle", "volcano", "lightning", "siren", "flash")),
    (
        "twinkle",
        ("star", "firework", "snow", "glitter", "meteor", "party", "disco", "twinkl", "sparkl"),
    ),
    (
        "breathe",
        (
            "sunrise",
            "sunset",
            "breath",
            "meditation",
            "sleep",
            "night",
            "moon",
            "reading",
            "romantic",
            "peaceful",
            "warm",
            "quiet",
            "soothing",
        ),
    ),
]


def _decode(param: str | None) -> bytes:
    if not param:
        return b""
    try:
        return base64.b64decode(param + "=" * (-len(param) % 4))
    except (binascii.Error, ValueError):
        return b""


def _hex(rgb: Any) -> str:
    red, green, blue = rgb
    return f"#{red:02x}{green:02x}{blue:02x}"


def _vivid(rgb: tuple[int, ...]) -> bool:
    return max(rgb) >= 0x40


def _rgbic_layers(data: bytes) -> list[dict[str, Any]]:
    layers = []
    pos = 1
    for _ in range(data[0]):
        size = data[pos]
        record = data[pos + 1 : pos + 1 + size]
        if len(record) != size:
            raise ValueError
        pos += 1 + size
        bright_count = record[5]
        bright = record[6:12]
        at = 6 + 6 * bright_count
        count = record[at + 3]
        triples = record[at + 4 : at + 4 + 3 * count]
        if len(triples) != 3 * count or len(bright) != 6:
            raise ValueError
        layers.append(
            {
                "colors": [_hex(triples[i : i + 3]) for i in range(0, len(triples), 3)],
                "mode": record[1],
                "pattern": record[at],
                "speed": record[at + 1],
                "bright": {
                    "max": bright[0],
                    "min": bright[1],
                    "kind": bright[2],
                    "rate": bright[3],
                },
                "reverse": record[3] in (2, 4, 6, 8),
            }
        )
    if not layers or pos != len(data):
        raise ValueError
    return layers


def _scan(data: bytes) -> list[tuple[int, ...]]:
    best: list[tuple[int, ...]] = []
    best_score = (0, 0)
    for index, count in enumerate(data):
        if not 2 <= count <= 16 or index + 1 + 3 * count > len(data):
            continue
        triples = [tuple(data[index + 1 + 3 * k : index + 4 + 3 * k]) for k in range(count)]
        if sum(1 for t in triples if _vivid(t)) < max(2, count - 1):
            continue
        score = (sum(1 for t in triples if 0xFF in t), count)
        if score > best_score:
            best, best_score = triples, score
    return best


def _scene_layers(scene: dict[str, Any]) -> list[dict[str, Any]] | None:
    data = _decode(scene.get("param"))
    if not data or int(scene.get("type") or 0) != RGBIC_SCENE:
        return None
    try:
        return _rgbic_layers(data)
    except (IndexError, ValueError):
        return None


def palette(scene: dict[str, Any]) -> list[str]:
    layers = _scene_layers(scene)
    if layers:
        colors = [color for layer in layers for color in layer["colors"]]
    else:
        colors = [_hex(t) for t in _scan(_decode(scene.get("param")))]
    unique: list[str] = []
    for color in colors:
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        if color not in unique and _vivid(rgb):
            unique.append(color)
    if not unique and "rainbow" in str(scene.get("name", "")).lower():
        unique = list(RAINBOW)
    return unique[:8]


def motion(name: str) -> str:
    low = name.lower()
    for kind, words in MOTIONS:
        if any(word in low for word in words):
            return kind
    return "flow"


def _layer(colors, mode, pattern, speed, top, low, kind, rate, reverse=False):
    return {
        "colors": colors,
        "mode": mode,
        "pattern": pattern,
        "speed": speed,
        "bright": {"max": top, "min": low, "kind": kind, "rate": rate},
        "reverse": reverse,
    }


def animation(scene: dict[str, Any]) -> list[dict[str, Any]]:
    layers = _scene_layers(scene)
    if layers:
        return layers
    data = _decode(scene.get("param"))
    colors = palette(scene) or [FALLBACK_COLOR]
    kind = motion(str(scene.get("name", "")))
    seed = sum(data)
    speed = 120 + (data[5] if len(data) > 5 else seed % 120)
    speed = min(speed, 255)
    if kind == "flicker":
        return [_layer(colors, 0, 2, speed, 255, 90, 3, 200)]
    if kind == "breathe":
        return [_layer(colors, 0, 2, 40, 255, 60, 1, 120)]
    if kind == "twinkle":
        return [
            _layer(colors, 0, 3, 60, 120, 120, 0, 0),
            _layer(["#ffffff", *colors], 2, 0, speed, 255, 255, 0, 0),
        ]
    pattern = 3 if len(data) > 1 and data[1] > 1 else 2
    return [_layer(colors, 0, pattern, speed, 255, 255, 0, 0, bool(seed % 2))]
