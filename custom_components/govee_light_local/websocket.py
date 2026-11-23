from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_LIGHTS, DATA_STORE, DOMAIN
from .patterns import pattern_label

COLORS = vol.All(list, vol.Length(min=1, max=56), [vol.Any(None, str)])


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_lights)
    websocket_api.async_register_command(hass, ws_scenes)
    websocket_api.async_register_command(hass, ws_preview)
    websocket_api.async_register_command(hass, ws_patterns)


def _light(hass: HomeAssistant, connection, msg: dict[str, Any]):
    light = hass.data[DOMAIN][DATA_LIGHTS].get(msg["entity_id"])
    if light is None:
        connection.send_error(msg["id"], "not_found", "Unknown Govee light")
    return light


@websocket_api.websocket_command({vol.Required("type"): "govee_light_local/lights"})
@callback
def ws_lights(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    lights = []
    for entity_id, light in sorted(hass.data[DOMAIN][DATA_LIGHTS].items()):
        state = hass.states.get(entity_id)
        lights.append(
            {
                "entity_id": entity_id,
                "name": state.name if state else entity_id,
                "sku": light.sku,
                "segment_count": light.segment_count,
                "available": light.available,
            }
        )
    connection.send_result(msg["id"], lights)


@websocket_api.websocket_command(
    {vol.Required("type"): "govee_light_local/scenes", vol.Required("entity_id"): str}
)
@callback
def ws_scenes(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    if light := _light(hass, connection, msg):
        connection.send_result(msg["id"], light.scene_previews)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "govee_light_local/preview",
        vol.Required("entity_id"): str,
        vol.Required("colors"): COLORS,
    }
)
@websocket_api.async_response
async def ws_preview(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    if light := _light(hass, connection, msg):
        try:
            await light.async_paint(msg["colors"], final=False)
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "not_available", str(err))
            return
        except (OSError, ValueError) as err:
            connection.send_error(msg["id"], "send_failed", str(err))
            return
        connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "govee_light_local/patterns"})
@callback
def ws_patterns(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    connection.send_result(
        msg["id"],
        {
            "label": pattern_label(hass.config.language),
            "patterns": hass.data[DOMAIN][DATA_STORE].patterns,
        },
    )
