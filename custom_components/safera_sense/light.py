"""Light platform: the cooker hood lights."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SaferaSenseConfigEntry
from safera_sense_ble import LightLevel
from .coordinator import SaferaSenseCoordinator
from .entity import SaferaSenseEntity

LEVEL_COUNT = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaferaSenseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    async_add_entities([SaferaHoodLight(entry.runtime_data)])


class SaferaHoodLight(SaferaSenseEntity, LightEntity):
    """The hood light (3 brightness levels)."""

    _attr_translation_key = "hood_light"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "light")
        self._last_level: int | None = None

    @property
    def _level(self) -> int | None:
        data = self.coordinator.data
        if data is None:
            return None
        return data.light_level

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None or data.light_raw is None:
            return None
        if data.light_auto:
            # In auto mode we cannot tell the momentary state; report on.
            return True
        level = data.light_level
        return None if level is None else level > 0

    @property
    def brightness(self) -> int | None:
        level = self._level
        if level is None:
            return None
        return round(level * 255 / LEVEL_COUNT)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            level = max(1, math.ceil(kwargs[ATTR_BRIGHTNESS] * LEVEL_COUNT / 255))
        else:
            level = self._last_level or LEVEL_COUNT
        self._last_level = level
        await self.coordinator.client.set_light_level(LightLevel(level))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_light_level(LightLevel.OFF)
        await self.coordinator.async_request_refresh()
