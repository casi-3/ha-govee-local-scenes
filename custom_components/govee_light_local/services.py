from __future__ import annotations

import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import DATA_LIGHTS, DATA_STORE, DOMAIN
from .segments import MAX_SEGMENTS

ATTR_COLORS = "colors"
ATTR_NAME = "name"
ATTR_COUNT = "count"
COLORS = vol.All(cv.ensure_list, vol.Length(min=1, max=MAX_SEGMENTS), [vol.Any(None, cv.string)])


def _lights(hass: HomeAssistant, call: ServiceCall):
    lights = hass.data[DOMAIN][DATA_LIGHTS]
    found = [lights[e] for e in call.data[ATTR_ENTITY_ID] if e in lights]
    if not found:
        raise ServiceValidationError("No Govee light matches this entity")
    return found


@callback
def async_register(hass: HomeAssistant) -> None:
    store = hass.data[DOMAIN][DATA_STORE]

    async def set_segments(call: ServiceCall) -> None:
        for light in _lights(hass, call):
            try:
                await light.async_paint(call.data[ATTR_COLORS])
            except ValueError as err:
                raise ServiceValidationError(str(err)) from err
            except OSError as err:
                raise HomeAssistantError(str(err)) from err

    async def save_pattern(call: ServiceCall) -> None:
        try:
            await store.async_save_pattern(call.data[ATTR_NAME], call.data[ATTR_COLORS])
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def delete_pattern(call: ServiceCall) -> None:
        await store.async_delete_pattern(call.data[ATTR_NAME])

    async def set_count(call: ServiceCall) -> None:
        for light in _lights(hass, call):
            await store.async_set_segment_count(light.fingerprint, call.data[ATTR_COUNT])

    entity = {vol.Required(ATTR_ENTITY_ID): cv.entity_ids}
    hass.services.async_register(
        DOMAIN,
        "set_segments",
        set_segments,
        vol.Schema({**entity, vol.Required(ATTR_COLORS): COLORS}),
    )
    hass.services.async_register(
        DOMAIN,
        "save_segment_pattern",
        save_pattern,
        vol.Schema({vol.Required(ATTR_NAME): cv.string, vol.Required(ATTR_COLORS): COLORS}),
    )
    hass.services.async_register(
        DOMAIN,
        "delete_segment_pattern",
        delete_pattern,
        vol.Schema({vol.Required(ATTR_NAME): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        "set_segment_count",
        set_count,
        vol.Schema(
            {
                **entity,
                vol.Required(ATTR_COUNT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=MAX_SEGMENTS)
                ),
            }
        ),
    )
