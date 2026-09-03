"""Light platform: the cooker hood lights.

The hood light has three discrete brightness levels plus an automatic
(presence-based) mode. It is modelled as a brightness light that snaps
to those three levels, with "Auto" exposed as a light effect.
"""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SaferaSenseConfigEntry
from safera_sense_ble import LightLevel
from .coordinator import SaferaSenseCoordinator
from .entity import SaferaSenseEntity

EFFECT_AUTO = "Auto"

LEVEL_COUNT = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaferaSenseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    async_add_entities([SaferaHoodLight(entry.runtime_data)])


class SaferaHoodLight(SaferaSenseEntity, LightEntity):
    """The hood light: three brightness levels plus automatic mode."""

    _attr_translation_key = "hood_light"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = [EFFECT_AUTO]

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "light")
        self._last_level: int | None = None

    @property
    def _level(self) -> int | None:
        data = self.coordinator.data
        return None if data is None else data.light_level

    @property
    def _auto(self) -> bool:
        data = self.coordinator.data
        return bool(data is not None and data.light_auto)

    @property
    def is_on(self) -> bool | None:
        # Reflect the PHYSICAL light: byte 53 carries the applied
        # brightness even in auto mode (0 while the hood keeps it dark).
        data = self.coordinator.data
        if data is None or data.light_raw is None:
            return None
        return data.light_raw > 0

    @property
    def brightness(self) -> int | None:
        level = self._level
        if level is None:
            return None
        return round(level * 255 / LEVEL_COUNT)

    @property
    def effect(self) -> str | None:
        return EFFECT_AUTO if self._auto else None

    async def _async_exit_auto(self) -> None:
        """Leave auto mode (the device command is a toggle)."""
        if self._auto:
            await self.coordinator.client.toggle_light_auto()

    async def async_turn_on(self, **kwargs: Any) -> None:
        if kwargs.get(ATTR_EFFECT) == EFFECT_AUTO:
            if not self._auto:
                await self.coordinator.client.toggle_light_auto()
            await self.coordinator.async_request_refresh()
            return

        if ATTR_BRIGHTNESS in kwargs:
            level = min(
                LEVEL_COUNT,
                max(1, round(kwargs[ATTR_BRIGHTNESS] * LEVEL_COUNT / 255)),
            )
        else:
            level = self._last_level or LEVEL_COUNT
        self._last_level = level
        await self._async_exit_auto()
        await self.coordinator.client.set_light_level(LightLevel(level))
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_exit_auto()
        await self.coordinator.client.set_light_level(LightLevel.OFF)
        await self.coordinator.async_request_refresh()
