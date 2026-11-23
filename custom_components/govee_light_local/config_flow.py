"""Config flow for Govee light local."""

import asyncio
from contextlib import suppress
import logging

from govee_local_api import GoveeController
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_entry_flow

from . import async_get_source_ips
from .const import (
    CONF_LISTENING_PORT_DEFAULT,
    CONF_MULTICAST_ADDRESS_DEFAULT,
    CONF_SHOW_PANEL,
    CONF_TARGET_PORT_DEFAULT,
    DISCOVERY_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _async_discover(hass: HomeAssistant, adapter_ip: str) -> bool:
    controller: GoveeController = GoveeController(
        loop=hass.loop,
        logger=_LOGGER,
        listening_addresses=adapter_ip,
        broadcast_address=CONF_MULTICAST_ADDRESS_DEFAULT,
        broadcast_port=CONF_TARGET_PORT_DEFAULT,
        listening_port=CONF_LISTENING_PORT_DEFAULT,
        discovery_enabled=True,
        discovery_interval=1,
        update_enabled=False,
    )

    try:
        _LOGGER.debug("Starting discovery with IP %s", adapter_ip)
        await controller.start()
    except OSError as ex:
        _LOGGER.error("Start failed on IP %s, errno: %d", adapter_ip, ex.errno)
        return False

    try:
        async with asyncio.timeout(delay=DISCOVERY_TIMEOUT):
            while not controller.devices:
                await asyncio.sleep(delay=1)
    except TimeoutError:
        _LOGGER.debug("No devices found with IP %s", adapter_ip)

    devices_count = len(controller.devices)
    cleanup_complete: asyncio.Event = controller.cleanup()
    with suppress(TimeoutError):
        await asyncio.wait_for(cleanup_complete.wait(), 1)

    return devices_count > 0


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""

    source_ips = await async_get_source_ips(hass)
    results = await asyncio.gather(*[_async_discover(hass, ip) for ip in source_ips])

    return any(results)


class GoveeConfigFlow(config_entry_flow.DiscoveryFlowHandler[bool], domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        super().__init__(DOMAIN, "Govee light local", _async_has_devices)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GoveeOptionsFlow()


class GoveeOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SHOW_PANEL, True)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Optional(CONF_SHOW_PANEL, default=current): bool}),
        )
