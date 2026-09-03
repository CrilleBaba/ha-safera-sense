"""Button platform: identify the device."""

from __future__ import annotations

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SaferaSenseConfigEntry
from .coordinator import SaferaSenseCoordinator
from .entity import SaferaSenseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaferaSenseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities(
        [
            SaferaIdentifyButton(entry.runtime_data),
            SaferaFilterCleanedButton(entry.runtime_data),
        ]
    )


class SaferaIdentifyButton(SaferaSenseEntity, ButtonEntity):
    """Sends the IDENTIFY_DEVICE command."""

    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "identify")

    async def async_press(self) -> None:
        await self.coordinator.client.identify()


class SaferaFilterCleanedButton(SaferaSenseEntity, ButtonEntity):
    """Resets the grease filter saturation counter to 0%."""

    _attr_translation_key = "filter_cleaned"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "filter_cleaned")

    async def async_press(self) -> None:
        await self.coordinator.client.reset_grease_filter()
        await self.coordinator.async_request_refresh()
