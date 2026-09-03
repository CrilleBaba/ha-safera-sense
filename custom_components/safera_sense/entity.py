"""Base entity for the Safera Sense integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SaferaSenseCoordinator


class SaferaSenseEntity(CoordinatorEntity[SaferaSenseCoordinator]):
    """Base entity tied to one Safera Sense device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SaferaSenseCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        info = self.coordinator.device_info
        wifi = self.coordinator.wifi_status
        name = "Safera Sense"
        if wifi is not None and wifi.device_name:
            name = wifi.device_name
        device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, self.coordinator.address)},
            name=name,
            manufacturer="Safera Oy",
        )
        if info is not None:
            device_info.update(
                DeviceInfo(
                    model=info.model,
                    serial_number=info.serial_number,
                    hw_version=info.hardware_rev,
                    sw_version=info.software_rev,
                )
            )
        return device_info
