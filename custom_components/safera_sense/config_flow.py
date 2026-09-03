"""Config flow for the Safera Sense integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback

from safera_sense_ble import SAFERA_SERVICE_UUID
from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Names Safera devices have been observed to advertise.
_KNOWN_NAME_HINTS = ("isense", "sense", "safera", "røroshetta", "roroshetta")


def _is_safera_device(discovery_info: BluetoothServiceInfoBleak) -> bool:
    """Match on the proprietary service UUID or a known name pattern."""
    if SAFERA_SERVICE_UUID in discovery_info.service_uuids:
        return True
    name = (discovery_info.name or "").lower()
    return any(hint in name for hint in _KNOWN_NAME_HINTS)


class SaferaSenseOptionsFlow(OptionsFlow):
    """Handle the options flow (sensor update interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                    ),
                }
            ),
        )


class SaferaSenseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SaferaSenseOptionsFlow:
        """Create the options flow."""
        return SaferaSenseOptionsFlow()

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle automatic Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        if not _is_safera_device(discovery_info):
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        assert self._discovery_info is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or self._discovery_info.address,
                data={CONF_ADDRESS: self._discovery_info.address},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or self._discovery_info.address
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup started by the user."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address],
                data={CONF_ADDRESS: address},
            )

        current_addresses = self._async_current_ids(include_ignore=False)
        all_devices: dict[str, str] = {}
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses:
                continue
            label = f"{discovery_info.name or 'Unknown'} ({address})"
            _LOGGER.debug(
                "BLE device seen: %s rssi=%s uuids=%s",
                label,
                discovery_info.rssi,
                discovery_info.service_uuids,
            )
            all_devices[address] = label
            if _is_safera_device(discovery_info):
                self._discovered_devices[address] = label

        if not self._discovered_devices:
            # No device matched the Safera fingerprint. Offer everything
            # HA's Bluetooth stack can currently see, so a device that
            # advertises an unexpected name can still be selected.
            _LOGGER.warning(
                "No Safera device matched; offering all %d visible BLE devices",
                len(all_devices),
            )
            self._discovered_devices = all_devices

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )
