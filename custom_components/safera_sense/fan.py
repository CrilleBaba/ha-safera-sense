"""Fan platform: the cooker hood extractor fan."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SaferaSenseConfigEntry
from safera_sense_ble import FanSpeed
from .coordinator import SaferaSenseCoordinator
from .entity import SaferaSenseEntity

PRESET_AUTO = "auto"
PRESET_BOOST = "boost"

SPEED_COUNT = 3  # manual levels 1-3; boost and auto are presets


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaferaSenseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan platform."""
    async_add_entities([SaferaHoodFan(entry.runtime_data)])


class SaferaHoodFan(SaferaSenseEntity, FanEntity):
    """The hood extractor fan."""

    _attr_translation_key = "hood_fan"
    _attr_name = None  # main feature of the device: take the device name
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = [PRESET_AUTO, PRESET_BOOST]
    _attr_speed_count = SPEED_COUNT

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "fan")

    @property
    def _level(self) -> int | None:
        data = self.coordinator.data
        return None if data is None else data.fan_speed_level

    @property
    def is_on(self) -> bool | None:
        level = self._level
        return None if level is None else level > 0

    @property
    def percentage(self) -> int | None:
        level = self._level
        if level is None:
            return None
        return round(min(level, SPEED_COUNT) * 100 / SPEED_COUNT)

    @property
    def preset_mode(self) -> str | None:
        data = self.coordinator.data
        if data is None:
            return None
        if data.fan_auto:
            return PRESET_AUTO
        if data.fan_speed_level == 4:
            return PRESET_BOOST
        return None

    async def async_set_percentage(self, percentage: int) -> None:
        level = math.ceil(percentage * SPEED_COUNT / 100)
        await self.coordinator.client.set_fan_speed(FanSpeed(level))
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_AUTO:
            await self.coordinator.client.set_fan_auto()
        else:
            await self.coordinator.client.set_fan_speed(FanSpeed.BOOST)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return
        await self.async_set_percentage(percentage if percentage is not None else 34)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_fan_speed(FanSpeed.OFF)
        await self.coordinator.async_request_refresh()
