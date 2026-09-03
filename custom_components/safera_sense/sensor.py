"""Sensor platform for Safera Sense."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfDensity,
    UnitOfPower,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import SaferaSenseConfigEntry
from safera_sense_ble import DeviceState, SensorReport
from .coordinator import SaferaSenseCoordinator
from .entity import SaferaSenseEntity


@dataclass(frozen=True, kw_only=True)
class SaferaSensorDescription(SensorEntityDescription):
    """Describes a Safera sensor."""

    value_fn: Callable[[SensorReport], StateType]


def _device_state(report: SensorReport) -> str | None:
    try:
        return DeviceState(report.device_state).name.lower()
    except ValueError:
        return None


SENSORS: tuple[SaferaSensorDescription, ...] = (
    SaferaSensorDescription(
        key="ambient_temperature",
        translation_key="ambient_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.ambient_temperature,
    ),
    SaferaSensorDescription(
        key="surface_temperature",
        translation_key="surface_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.surface_temperature,
    ),
    SaferaSensorDescription(
        key="pan_temperature",
        translation_key="pan_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.heat_index,
    ),
    SaferaSensorDescription(
        key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.humidity,
    ),
    SaferaSensorDescription(
        key="ambient_light",
        translation_key="ambient_light",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.ambient_light,
    ),
    SaferaSensorDescription(
        key="co2",
        translation_key="eco2",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.co2_ppm,
    ),
    SaferaSensorDescription(
        key="tvoc",
        translation_key="tvoc",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_BILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.tvoc_ppb,
    ),
    SaferaSensorDescription(
        key="air_quality_index",
        translation_key="air_quality_index",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.air_quality_index,
    ),
    SaferaSensorDescription(
        # Key kept as "particle_index" so the existing entity and its
        # history survive; the value tracks the vendor app's PM2.5.
        key="particle_index",
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda r: r.particle_index,
    ),
    SaferaSensorDescription(
        key="stove_power",
        translation_key="stove_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.power_consumption,
    ),
    SaferaSensorDescription(
        key="activity_level",
        translation_key="activity_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.activity_level,
    ),
    SaferaSensorDescription(
        key="alarm_level",
        translation_key="alarm_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.alarm_level,
    ),
    SaferaSensorDescription(
        key="grease_filter",
        translation_key="grease_filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=lambda r: r.grease_filter,
    ),
    SaferaSensorDescription(
        key="device_state",
        translation_key="device_state",
        device_class=SensorDeviceClass.ENUM,
        options=[state.name.lower() for state in DeviceState],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_device_state,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SaferaSenseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        SaferaSensor(coordinator, description) for description in SENSORS
    ]
    entities.append(SaferaWifiSsidSensor(coordinator))
    async_add_entities(entities)


class SaferaSensor(SaferaSenseEntity, SensorEntity):
    """A sensor fed from the SENSOR_REPORT record."""

    entity_description: SaferaSensorDescription

    def __init__(
        self,
        coordinator: SaferaSenseCoordinator,
        description: SaferaSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class SaferaWifiSsidSensor(SaferaSenseEntity, SensorEntity):
    """Diagnostic sensor: the Wi-Fi SSID the device is configured for."""

    _attr_translation_key = "wifi_ssid"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: SaferaSenseCoordinator) -> None:
        super().__init__(coordinator, "wifi_ssid")

    @property
    def native_value(self) -> str | None:
        wifi = self.coordinator.wifi_status
        return wifi.ssid if wifi is not None and wifi.ssid else None
