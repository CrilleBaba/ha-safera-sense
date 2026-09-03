"""The Safera Sense integration.

Local BLE integration for Safera Sense cooking sensors, as built into
Røros Hetta (and other) cooker hoods. Protocol reverse engineered by
https://github.com/magicus/safera-ble and
https://github.com/havardgulldahl/rorossense-ble
"""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .coordinator import SaferaSenseCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
]

type SaferaSenseConfigEntry = ConfigEntry[SaferaSenseCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: SaferaSenseConfigEntry
) -> bool:
    """Set up Safera Sense from a config entry."""
    address: str = entry.unique_id or entry.data["address"]

    ble_device = bluetooth.async_ble_device_from_address(
        hass, address, connectable=True
    )
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Safera Sense device {address} is not present; make sure a "
            "Bluetooth adapter or proxy is in range"
        )

    coordinator = SaferaSenseCoordinator(
        hass,
        ble_device,
        update_interval=entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(
    hass: HomeAssistant, entry: SaferaSenseConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: SaferaSenseConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        await entry.runtime_data.async_shutdown()
    return unload_ok
