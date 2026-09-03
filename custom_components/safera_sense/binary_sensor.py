"""Binary sensor platform for Safera Sense."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SaferaSenseConfigEntry
from safera_sense_ble import ALARM_DEVICE_STATES, ActivityType, SensorReport
from .coordinator import SaferaSenseCoordinator
from .entity import SaferaSenseEntity


@dataclass(frozen=True, kw_only=True)
class SaferaBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Safera binary sensor."""

    value_fn: Callable[[SensorReport], bool | None]
    attributes_fn: Callable[[SensorReport], dict[str, Any]] | None = None


def _is_alarm(report: SensorReport) -> bool:
    if report.device_state in ALARM_DEVICE_STATES:
        return True
    return report.alarm_level >= 100


BINARY_SENSORS: tuple[SaferaBinarySensorDescription, ...] = (
    SaferaBinarySensorDescription(
        key="cooking",
        translation_key="cooking",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda r: r.activity_type == ActivityType.COOKING,
    ),
    SaferaBinarySensorDescription(
        key="alarm",
        translation_key="alarm",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=_is_alarm,
    ),
    SaferaBinarySensorDescription(
        key="stove_power_cut",
        translation_key="stove_power_cut",
        device_class=BinarySensorDeviceClass.PROBLEM,
        # alarm_status is only meaningful when a stove-guard power unit
        # (PCU) is attached; hood-only installs report 0 permanently.
        value_fn=lambda r: (
            r.alarm_status == 0 if r.connected_accessories & 0x01 else None
        ),
    ),
    SaferaBinarySensorDescription(
        key="sensor_problem",
        translation_key="sensor_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: bool(r.sensor_errors or r.pcu_errors),
        attributes_fn=lambda r: {
            "sensor_errors": r.sensor_error_messages,
            "pcu_errors": r.pcu_error_messages,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaferaSenseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        SaferaBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class SaferaBinarySensor(SaferaSenseEntity, BinarySensorEntity):
    """A binary sensor fed from the SENSOR_REPORT record."""

    entity_description: SaferaBinarySensorDescription

    def __init__(
        self,
        coordinator: SaferaSenseCoordinator,
        description: SaferaBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if (
            self.entity_description.attributes_fn is None
            or self.coordinator.data is None
        ):
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
