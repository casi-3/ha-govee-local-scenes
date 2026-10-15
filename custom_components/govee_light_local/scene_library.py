from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
import socket
from typing import TYPE_CHECKING, Any
import urllib.request

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CATALOG_URL = "https://app2.govee.com/appsku/v1/light-effect-libraries?sku={sku}"
CATALOG_HEADERS = {"AppVersion": "6.5.70", "User-Agent": "GoveeHome/6.5.70"}
BUNDLED_DIR = Path(__file__).with_name("catalogs")
CACHE_DIR = "govee_light_local_catalogs"
CATALOG_VERSION = 2
LAN_PORT = 4003

CATEGORY_LABELS = {
    "fr": {
        "Natural": "Nature",
        "Life": "Vie",
        "Emotion": "Émotion",
        "Festival": "Fêtes",
        "Funny": "Fun",
        "Art Styles": "Art",
    },
}

CATEGORY_ORDER = ["Natural", "Life", "Funny", "Emotion", "Festival", "Art Styles"]


def _finish(data: list[int]) -> bytes:
    checksum = 0
    for byte in data:
        checksum ^= byte
    return bytes(data) + bytes(19 - len(data)) + bytes([checksum])


def scene_packets(code: int, param: str | None, scene_type: int) -> list[bytes]:
    lines: list[bytes] = []
    if param:
        data = [0xA3, 0x00, 0x01, 0x00, scene_type & 0xFF]
        count = 0
        marker = 1
        for byte in base64.b64decode(param):
            if len(data) % 19 == 0:
                count += 1
                data.append(0xA3)
                marker = len(data)
                data.append(count)
            data.append(byte)
        data[marker] = 0xFF
        data[3] = count + 1
        for start in range(0, len(data), 19):
            lines.append(_finish(data[start : start + 19]))
    lines.append(_finish([0x33, 0x05, 0x04, code & 0xFF, (code >> 8) & 0xFF]))
    return lines


def send_scene(ip: str, scene: dict[str, Any]) -> None:
    lines = scene_packets(scene["code"], scene.get("param"), scene.get("type", 0))
    message = {
        "msg": {
            "cmd": "ptReal",
            "data": {"command": [base64.b64encode(line).decode() for line in lines]},
        }
    }
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(json.dumps(message).encode(), (ip, LAN_PORT))


def parse_library(sku: str, payload: dict[str, Any]) -> dict[str, Any]:
    scenes = []
    for category in payload.get("data", {}).get("categories", []):
        for scene in category.get("scenes", []):
            effect = (scene.get("lightEffects") or [{}])[0]
            code = effect.get("sceneCode") or scene.get("sceneCode")
            if not code:
                continue
            scenes.append(
                {
                    "category": category.get("categoryName", ""),
                    "name": scene.get("sceneName", str(code)),
                    "code": int(code),
                    "param": effect.get("scenceParam") or None,
                    "type": int(effect.get("sceneType") or 0),
                }
            )
    return {"sku": sku, "version": CATALOG_VERSION, "scenes": scenes}


def effect_names(catalog: dict[str, Any], language: str) -> dict[str, dict[str, Any]]:
    labels = CATEGORY_LABELS.get(language.split("-")[0].lower(), {})
    order = {name: index for index, name in enumerate(CATEGORY_ORDER)}
    ranked = sorted(
        catalog.get("scenes", []),
        key=lambda s: (order.get(s["category"], len(order)), s["name"].lower()),
    )
    named: dict[str, dict[str, Any]] = {}
    for scene in ranked:
        category = labels.get(scene["category"], scene["category"])
        label = f"{category} · {scene['name']}" if category else scene["name"]
        if label in named:
            label = f"{label} ({scene['code']})"
        named[label] = scene
    return named


class SceneLibrary:
    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_dir = Path(hass.config.path(".storage", CACHE_DIR))

    async def async_effects(self, sku: str) -> dict[str, dict[str, Any]]:
        sku = str(sku).upper()
        if sku not in self._cache:
            catalog = await self._hass.async_add_executor_job(self._load, sku)
            if catalog is None:
                return {}
            self._cache[sku] = catalog
        return effect_names(self._cache[sku], self._hass.config.language)

    def _load(self, sku: str) -> dict[str, Any] | None:
        for path in (BUNDLED_DIR / f"{sku}.json", self._cache_dir / f"{sku}.json"):
            if path.is_file():
                catalog = json.loads(path.read_text(encoding="utf-8"))
                if catalog.get("version") == CATALOG_VERSION:
                    return catalog
        try:
            request = urllib.request.Request(CATALOG_URL.format(sku=sku), headers=CATALOG_HEADERS)
            with urllib.request.urlopen(request, timeout=15) as response:
                catalog = parse_library(sku, json.loads(response.read()))
        except (OSError, ValueError) as err:
            _LOGGER.warning("Scene catalog for %s unavailable: %s", sku, err)
            return None
        if not catalog["scenes"]:
            return None
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        (self._cache_dir / f"{sku}.json").write_text(
            json.dumps(catalog, ensure_ascii=False), encoding="utf-8"
        )
        return catalog
