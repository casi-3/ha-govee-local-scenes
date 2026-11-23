"""Govee light local."""

import logging
from typing import Any, override

from govee_local_api import GoveeDevice, GoveeLightFeatures

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
    filter_supported_color_modes,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DATA_LIGHTS, DATA_STORE, DEVICE_TIMEOUT, DOMAIN, MANUFACTURER
from .coordinator import GoveeLocalApiCoordinator, GoveeLocalConfigEntry
from .patterns import PatternStore, pattern_label, pattern_name
from .preview import animation
from .scene_library import SceneLibrary, send_lines, send_scene
from .segments import resample, segment_packets

_LOGGER = logging.getLogger(__name__)

_NONE_SCENE = "none"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: GoveeLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Govee light setup."""

    coordinator = config_entry.runtime_data
    library = SceneLibrary(hass)
    store: PatternStore = hass.data[DOMAIN][DATA_STORE]

    async def build(device: GoveeDevice) -> GoveeLight:
        return GoveeLight(coordinator, device, await library.async_effects(device.sku), store)

    async def add(device: GoveeDevice) -> None:
        async_add_entities([await build(device)])

    def discovery_callback(device: GoveeDevice, is_new: bool) -> bool:
        if is_new:
            hass.async_create_task(add(device))
        return True

    async_add_entities([await build(device) for device in coordinator.devices])

    await coordinator.set_discovery_callback(discovery_callback)


class GoveeLight(CoordinatorEntity[GoveeLocalApiCoordinator], LightEntity):
    """Govee Light."""

    _attr_translation_key = "govee_light"
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes: set[ColorMode]
    _fixed_color_mode: ColorMode | None = None
    _attr_effect_list: list[str] | None = None
    _attr_effect: str | None = None
    _attr_supported_features: LightEntityFeature = LightEntityFeature(0)
    _last_color_state: (
        tuple[
            ColorMode | str | None,
            int | None,
            tuple[int, int, int] | tuple[int | None] | None,
        ]
        | None
    ) = None

    def __init__(
        self,
        coordinator: GoveeLocalApiCoordinator,
        device: GoveeDevice,
        effects: dict[str, dict[str, Any]] | None = None,
        store: PatternStore | None = None,
    ) -> None:
        """Govee Light constructor."""

        super().__init__(coordinator)
        self._device = device

        self._attr_unique_id = device.fingerprint

        capabilities = device.capabilities
        color_modes = {ColorMode.ONOFF}
        if capabilities:
            if GoveeLightFeatures.COLOR_RGB & capabilities.features:
                color_modes.add(ColorMode.RGB)
            if GoveeLightFeatures.COLOR_KELVIN_TEMPERATURE & capabilities.features:
                color_modes.add(ColorMode.COLOR_TEMP)
                self._attr_max_color_temp_kelvin = 9000
                self._attr_min_color_temp_kelvin = 2000
            if GoveeLightFeatures.BRIGHTNESS & capabilities.features:
                color_modes.add(ColorMode.BRIGHTNESS)

            if GoveeLightFeatures.SCENES & capabilities.features and capabilities.scenes:
                self._attr_supported_features = LightEntityFeature.EFFECT
                self._attr_effect_list = [_NONE_SCENE, *capabilities.scenes.keys()]

        self._local_effects = effects or {}
        self._store = store
        self._pattern_effects: dict[str, str] = {}
        self._base_effects = list(self._attr_effect_list or [])
        if self._local_effects:
            self._attr_supported_features = LightEntityFeature.EFFECT
            self._attr_effect_list = [_NONE_SCENE, *self._local_effects]
            self._base_effects = list(self._attr_effect_list)
        self._previews: list[dict[str, Any]] | None = None

        self._attr_supported_color_modes = filter_supported_color_modes(color_modes)
        if len(self._attr_supported_color_modes) == 1:
            # If the light supports only a single color mode, set it now
            self._fixed_color_mode = next(iter(self._attr_supported_color_modes))

        self._attr_device_info = DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, device.fingerprint)
            },
            name=device.sku,
            manufacturer=MANUFACTURER,
            model_id=device.sku,
            serial_number=device.fingerprint,
        )

    @property
    @override
    def available(self) -> bool:
        """Return if the device is reachable.

        The underlying library updates ``lastseen`` whenever the device
        replies to a status request. The coordinator polls every
        ``SCAN_INTERVAL``, so if we have not heard back within
        ``DEVICE_TIMEOUT`` we consider the device offline.
        """
        if not super().available:
            return False
        return dt_util.utcnow() - self._device.lastseen < DEVICE_TIMEOUT

    @property
    @override
    def is_on(self) -> bool:
        """Return true if device is on (brightness above 0)."""
        return self._device.on

    @property
    @override
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return int((self._device.brightness / 100.0) * 255.0)

    @property
    @override
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._device.temperature_color

    @property
    @override
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color."""
        return self._device.rgb_color

    @property
    @override
    def color_mode(self) -> ColorMode:
        """Return the color mode."""
        if self._fixed_color_mode:
            # The light supports only a single color mode, return it
            return self._fixed_color_mode

        # The light supports both color temperature and RGB, determine which
        # mode the light is in
        if self._device.temperature_color is not None and self._device.temperature_color > 0:
            return ColorMode.COLOR_TEMP
        return ColorMode.RGB

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness: int = int((float(kwargs[ATTR_BRIGHTNESS]) / 255.0) * 100.0)
            await self.coordinator.set_brightness(self._device, brightness)

        effect = kwargs.get(ATTR_EFFECT)
        pattern = pattern_name(effect, self._store.patterns if self._store else ())
        if pattern is not None:
            label = f"{pattern_label(self.hass.config.language)} · {pattern}"
            if label not in self._pattern_effects:
                self._refresh_patterns()
            effect = label
            kwargs[ATTR_EFFECT] = label
        if (
            effect
            and effect != _NONE_SCENE
            and self._attr_effect_list
            and effect in self._attr_effect_list
        ):
            self._attr_effect = effect
            self._save_last_color_state()
            if effect in self._pattern_effects:
                if not self.is_on:
                    await self.coordinator.turn_on(self._device)
                await self._async_send_colors(self._pattern_colors(effect))
            elif effect in self._local_effects:
                if not self.is_on:
                    await self.coordinator.turn_on(self._device)
                await self.hass.async_add_executor_job(
                    send_scene, self._device.ip, self._local_effects[effect]
                )
            else:
                await self.coordinator.set_scene(self._device, effect)
        elif ATTR_RGB_COLOR in kwargs:
            self._attr_color_mode = ColorMode.RGB
            self._attr_effect = None
            self._last_color_state = None
            red, green, blue = kwargs[ATTR_RGB_COLOR]
            await self.coordinator.set_rgb_color(self._device, red, green, blue)
        elif ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self._attr_effect = None
            self._last_color_state = None
            temperature: float = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self.coordinator.set_temperature(self._device, int(temperature))
        elif effect == _NONE_SCENE and self._attr_effect_list:
            self._attr_effect = None
            await self._restore_last_color_state()

        if not self.is_on or not kwargs:
            await self.coordinator.turn_on(self._device)

        self.async_write_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self.coordinator.turn_off(self._device)
        self.async_write_ha_state()

    @override
    async def async_added_to_hass(self) -> None:
        """Register update callback when entity is added."""
        await super().async_added_to_hass()
        self._device.set_update_callback(self._update_callback)
        self.hass.data[DOMAIN][DATA_LIGHTS][self.entity_id] = self
        if self._store:
            self._refresh_patterns()
            self.async_on_remove(self._store.add_listener(self._patterns_changed))

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Unregister update callback when entity is removed."""
        self._device.set_update_callback(None)
        self.hass.data[DOMAIN][DATA_LIGHTS].pop(self.entity_id, None)
        await super().async_will_remove_from_hass()

    @property
    def fingerprint(self) -> str:
        return str(self._device.fingerprint)

    @property
    def sku(self) -> str:
        return str(self._device.sku)

    @property
    def segment_count(self) -> int:
        if not self._store:
            return 15
        return self._store.segment_count(self._device.fingerprint, self.sku)

    @property
    def scene_previews(self) -> list[dict[str, Any]]:
        if self._previews is None:
            previews = []
            for effect, scene in self._local_effects.items():
                category, _, name = effect.rpartition(" · ")
                previews.append(
                    {
                        "effect": effect,
                        "category": category,
                        "name": name or effect,
                        "anim": animation(scene),
                    }
                )
            self._previews = previews
        return self._previews

    def _refresh_patterns(self) -> None:
        label = pattern_label(self.hass.config.language)
        patterns = self._store.patterns if self._store else {}
        self._pattern_effects = {f"{label} · {name}": name for name in patterns}
        effects = list(self._base_effects)
        if self._pattern_effects:
            effects = [*(effects or [_NONE_SCENE]), *self._pattern_effects]
        self._attr_effect_list = effects or None
        if effects:
            self._attr_supported_features |= LightEntityFeature.EFFECT
        if self._attr_effect and self._attr_effect not in effects:
            self._attr_effect = None

    @callback
    def _patterns_changed(self) -> None:
        self._refresh_patterns()
        self.async_write_ha_state()

    def _pattern_colors(self, effect: str) -> list[str | None]:
        name = self._pattern_effects[effect]
        colors = self._store.patterns.get(name, []) if self._store else []
        return resample(colors, self.segment_count)

    async def _async_send_colors(self, colors: list[str | None]) -> None:
        await self.hass.async_add_executor_job(send_lines, self._device.ip, segment_packets(colors))

    async def async_paint(self, colors: list[str | None], final: bool = True) -> None:
        if not self.available:
            raise HomeAssistantError(f"{self.entity_id} is not responding")
        packets = segment_packets(colors[: self.segment_count])
        if not self.is_on:
            await self.coordinator.turn_on(self._device)
        await self.hass.async_add_executor_job(send_lines, self._device.ip, packets)
        if final:
            self._attr_effect = None
            self._last_color_state = None
            self.async_write_ha_state()

    @callback
    def _update_callback(self, device: GoveeDevice) -> None:
        """Handle device state updates pushed by the library."""
        self.async_write_ha_state()

    def _save_last_color_state(self) -> None:
        color_mode = self.color_mode
        self._last_color_state = (
            color_mode,
            self.brightness,
            (self.color_temp_kelvin,) if color_mode == ColorMode.COLOR_TEMP else self.rgb_color,
        )

    async def _restore_last_color_state(self) -> None:
        if self._last_color_state:
            color_mode, brightness, color = self._last_color_state
            if color:
                if color_mode == ColorMode.RGB:
                    await self.coordinator.set_rgb_color(self._device, *color)
                elif color_mode == ColorMode.COLOR_TEMP:
                    await self.coordinator.set_temperature(self._device, *color)
            if brightness:
                await self.coordinator.set_brightness(
                    self._device, int((float(brightness) / 255.0) * 100.0)
                )
            self._last_color_state = None
