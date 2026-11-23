from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

STATIC_URL = f"/{DOMAIN}/frontend"
STATIC_DIR = Path(__file__).with_name("frontend")
FRONTEND_VERSION = "1.1.0b1"
PANEL_URL = "govee"
DATA_STATIC = f"{DOMAIN}_static"


def asset_url(name: str) -> str:
    return f"{STATIC_URL}/{name}?v={FRONTEND_VERSION}"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    if hass.data.get(DATA_STATIC):
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(STATIC_DIR), cache_headers=False)]
    )
    frontend.add_extra_js_url(hass, asset_url("govee-more-info.js"))
    hass.data[DATA_STATIC] = True


async def async_update_panel(hass: HomeAssistant, show: bool) -> None:
    registered = PANEL_URL in hass.data.get(frontend.DATA_PANELS, {})
    if show and not registered:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name="govee-panel",
            sidebar_title="Govee",
            sidebar_icon="mdi:led-strip-variant",
            module_url=asset_url("govee-panel.js"),
            require_admin=False,
        )
    elif not show and registered:
        frontend.async_remove_panel(hass, PANEL_URL)
