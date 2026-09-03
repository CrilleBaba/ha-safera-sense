"""Data update coordinator for the Safera Sense integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from safera_sense_ble import DeviceInfo, SaferaSenseClient, SensorReport, WifiStatus

from .const import DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Fields whose changes always propagate to HA immediately, bypassing the
# update-interval throttle: safety, cooking activity and device controls.
EVENTFUL_FIELDS = (
    "device_state",
    "alarm_status",
    "alarm_level",
    "sensor_errors",
    "pcu_errors",
    "activity_type",
    "connected_accessories",
    "fan_speed_raw",
    "hood_flags",
    "light_raw",
    "grease_filter",
)


def is_eventful_change(old: SensorReport | None, new: SensorReport) -> bool:
    """Return True when an immediately-relevant field changed."""
    if old is None:
        return True
    return any(getattr(old, field) != getattr(new, field) for field in EVENTFUL_FIELDS)


class SaferaSenseCoordinator(DataUpdateCoordinator[SensorReport]):
    """Maintains the BLE connection and distributes sensor reports.

    BLE notifications arrive about once per second. Eventful changes
    (alarms, cooking, fan/light/filter state) are forwarded to HA
    immediately; environmental drift is forwarded at most once per
    `update_interval` seconds to limit state churn.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        ble_device,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        self.ble_device = ble_device
        self.client = SaferaSenseClient(ble_device)
        self.device_info: DeviceInfo | None = None
        self.wifi_status: WifiStatus | None = None
        self._shutdown = False
        self._throttle_seconds = update_interval
        self._last_push = 0.0

        super().__init__(
            hass,
            _LOGGER,
            name=f"Safera Sense {ble_device.address}",
            # The poll is a connection watchdog; notifications reset this
            # timer on every push, so it only fires when the stream stalls.
            update_interval=timedelta(seconds=update_interval + 60),
        )

    @property
    def address(self) -> str:
        return self.client.address

    async def _async_setup(self) -> None:
        """Called once before the first refresh."""
        await self._async_ensure_connected()

    async def _async_ensure_connected(self) -> None:
        """(Re)connect, read static info and subscribe to notifications."""
        if self.client.is_connected:
            return

        # Ask HA's Bluetooth stack for a fresh BLEDevice: after a
        # disconnect the device may now be reachable via a different
        # adapter or proxy.
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is not None:
            self.client.set_ble_device(ble_device)

        await self.client.connect(disconnected_callback=self._handle_disconnect)

        if self.device_info is None:
            try:
                self.device_info = await self.client.fetch_device_info()
                _LOGGER.debug("Device info: %s", self.device_info)
            except Exception:  # noqa: BLE001
                _LOGGER.warning("Could not read device information", exc_info=True)

        try:
            self.wifi_status = await self.client.fetch_wifi_status()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not read Wi-Fi status", exc_info=True)

        await self.client.subscribe_sensor_reports(self._handle_report)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            # Protocol investigation: dump all readable characteristics
            # once per connection to help decode remaining unknown fields.
            try:
                for name, hexdump in (
                    await self.client.dump_characteristics()
                ).items():
                    _LOGGER.debug("CHAR DUMP %s = %s", name, hexdump)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Characteristic dump failed", exc_info=True)

    def _handle_report(self, report: SensorReport) -> None:
        """Handle a pushed sensor report (called from the event loop)."""
        now = time.monotonic()
        if (
            is_eventful_change(self.data, report)
            or now - self._last_push >= self._throttle_seconds
        ):
            self._last_push = now
            self.async_set_updated_data(report)

    def _handle_disconnect(self, _client) -> None:
        """Handle an unexpected disconnect; schedule a reconnect."""
        if self._shutdown:
            return
        _LOGGER.debug("%s disconnected; scheduling reconnect", self.address)
        self.hass.loop.call_soon_threadsafe(
            lambda: self.hass.async_create_task(self.async_request_refresh())
        )

    async def _async_update_data(self) -> SensorReport:
        """Polling fallback: reconnect if needed and read a snapshot."""
        try:
            await self._async_ensure_connected()
            return await self.client.fetch_sensor_report()
        except Exception as err:
            raise UpdateFailed(f"Cannot reach device: {err}") from err

    async def async_shutdown(self) -> None:
        """Disconnect cleanly on unload/stop."""
        self._shutdown = True
        await super().async_shutdown()
        try:
            await self.client.disconnect()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Error during disconnect", exc_info=True)
