"""Fan platform: the cooker hood extractor fan.

The hood exposes four speed steps (HOOD_MOTOR_SPEED_COUNT = 4), so the
fan has four discrete speeds -- level 4 is the "boost" step -- plus an
automatic (air-quality controlled) preset mode.
"""

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

SPEED_COUNT = 4  # levels 1-4 (4 = boost); auto is a preset


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
    _attr_preset_modes = [PRESET_AUTO]
    _attr_speed_count = SPEED_COUNT

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "fan")

    @property
    def _level(self) -> int | None:
        data = self.coordinator.data
        return None if data is None else data.fan_speed_level

    @property
    def is_on(self) -> bool | None:
        # In auto the mode is engaged even while the fan idles; reflect
        # the physical fan for is_on and surface auto via preset_mode.
        level = self._level
        if level is None:
            return None
        return level > 0

    @property
    def percentage(self) -> int | None:
        level = self._level
        if level is None:
            return None
        return round(level * 100 / SPEED_COUNT)

    @property
    def preset_mode(self) -> str | None:
        data = self.coordinator.data
        if data is None:
            return None
        return PRESET_AUTO if data.fan_auto else None

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        level = math.ceil(percentage * SPEED_COUNT / 100)
        await self.coordinator.client.set_fan_speed(FanSpeed(level))
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        # Only PRESET_AUTO is offered.
        await self.coordinator.client.set_fan_auto()
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
        await self.async_set_percentage(percentage if percentage is not None else 25)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_fan_speed(FanSpeed.OFF)
        await self.coordinator.async_request_refresh()
