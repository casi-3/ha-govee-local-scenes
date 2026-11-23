from __future__ import annotations

import re

MAX_SEGMENTS = 56
DEFAULT_SEGMENTS = 15
KNOWN_SEGMENTS = {"H61D5": 14}
MASK_BYTES = 7
HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{6})$")


def default_count(sku: str) -> int:
    return KNOWN_SEGMENTS.get(str(sku).upper(), DEFAULT_SEGMENTS)


def parse_color(value: str | None) -> tuple[int, int, int]:
    if not value:
        return (0, 0, 0)
    match = HEX_COLOR.match(value.strip())
    if not match:
        raise ValueError(f"Invalid color: {value}")
    raw = match.group(1)
    return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def _finish(data: list[int]) -> bytes:
    checksum = 0
    for byte in data:
        checksum ^= byte
    return bytes(data) + bytes(19 - len(data)) + bytes([checksum])


def segment_packets(colors: list[str | None]) -> list[bytes]:
    if len(colors) > MAX_SEGMENTS:
        raise ValueError(f"At most {MAX_SEGMENTS} segments are supported")
    groups: dict[tuple[int, int, int], list[int]] = {}
    for index, color in enumerate(colors):
        groups.setdefault(parse_color(color), []).append(index)
    lines = []
    for (red, green, blue), indexes in groups.items():
        mask = [0] * MASK_BYTES
        for index in indexes:
            mask[index // 8] |= 1 << (index % 8)
        lines.append(_finish([0x33, 0x05, 0x15, 0x01, red, green, blue, 0, 0, 0, 0, 0, *mask]))
    return lines


def resample(colors: list[str | None], count: int) -> list[str | None]:
    if not colors:
        return [None] * count
    size = len(colors)
    return [colors[min(size - 1, int((index + 0.5) * size / count))] for index in range(count)]
