from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .segments import MAX_SEGMENTS, default_count, parse_color

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

STORAGE_KEY = "govee_light_local.patterns"
STORAGE_VERSION = 1


def normalize_name(name: str | None) -> str:
    cleaned = " ".join(str(name or "").split())
    if not cleaned:
        raise ValueError("A pattern needs a name")
    return cleaned


def normalize_colors(colors: list[str | None]) -> list[str | None]:
    if not colors or len(colors) > MAX_SEGMENTS:
        raise ValueError(f"A pattern needs between 1 and {MAX_SEGMENTS} colors")
    result: list[str | None] = []
    for color in colors:
        if color:
            red, green, blue = parse_color(color)
            result.append(f"#{red:02x}{green:02x}{blue:02x}")
        else:
            result.append(None)
    return result


class PatternBook:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        data = data or {}
        self._patterns: dict[str, list[str | None]] = dict(data.get("patterns", {}))
        self._segments: dict[str, int] = dict(data.get("segments", {}))

    @property
    def data(self) -> dict[str, Any]:
        return {"patterns": dict(self._patterns), "segments": dict(self._segments)}

    @property
    def patterns(self) -> dict[str, list[str | None]]:
        return dict(self._patterns)

    def upsert(self, name: str | None, colors: list[str | None]) -> str:
        key = normalize_name(name)
        self._patterns[key] = normalize_colors(colors)
        return key

    def remove(self, name: str | None) -> None:
        self._patterns.pop(" ".join(str(name or "").split()), None)

    def segment_count(self, fingerprint: str, sku: str) -> int:
        return self._segments.get(fingerprint, default_count(sku))

    def set_segment_count(self, fingerprint: str, count: int) -> None:
        if not 1 <= int(count) <= MAX_SEGMENTS:
            raise ValueError(f"Segment count must be between 1 and {MAX_SEGMENTS}")
        self._segments[fingerprint] = int(count)


class PatternStore(PatternBook):
    def __init__(self, hass: HomeAssistant) -> None:
        from homeassistant.helpers.storage import Store

        super().__init__()
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        PatternBook.__init__(self, await self._store.async_load())

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def _async_commit(self) -> None:
        await self._store.async_save(self.data)
        for listener in list(self._listeners):
            listener()

    async def async_save_pattern(self, name: str, colors: list[str | None]) -> str:
        key = self.upsert(name, colors)
        await self._async_commit()
        return key

    async def async_delete_pattern(self, name: str) -> None:
        self.remove(name)
        await self._async_commit()

    async def async_set_segment_count(self, fingerprint: str, count: int) -> None:
        self.set_segment_count(fingerprint, count)
        await self._async_commit()
