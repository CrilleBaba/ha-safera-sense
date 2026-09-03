"""Config flow tests for the Safera Sense integration."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.safera_sense.const import DOMAIN

SAFERA_SERVICE_UUID = "0000f00d-1212-efde-1523-785fef13d123"
ADDRESS = "D7:B2:CA:5F:C0:8D"


class FakeServiceInfo:
    """Minimal stand-in for BluetoothServiceInfoBleak."""

    def __init__(self, address: str, name: str | None, uuids: list[str]) -> None:
        self.address = address
        self.name = name
        self.service_uuids = uuids
        self.rssi = -60


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, mock_bluetooth):
    """Enable custom integrations and mock the Bluetooth stack."""
    yield


async def test_user_flow_lists_safera_device(hass: HomeAssistant) -> None:
    """A device advertising the Safera service UUID is offered and selectable."""
    discovered = [FakeServiceInfo(ADDRESS, "Røroshetta", [SAFERA_SERVICE_UUID])]
    with patch(
        "custom_components.safera_sense.config_flow.async_discovered_service_info",
        return_value=discovered,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_ADDRESS: ADDRESS}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Røroshetta ({ADDRESS})"
    assert result["data"] == {CONF_ADDRESS: ADDRESS}
    assert result["result"].unique_id == ADDRESS


async def test_user_flow_falls_back_to_all_devices(hass: HomeAssistant) -> None:
    """With no Safera fingerprint match, every visible device is offered."""
    discovered = [FakeServiceInfo(ADDRESS, "MysteryHood", [])]
    with patch(
        "custom_components.safera_sense.config_flow.async_discovered_service_info",
        return_value=discovered,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_ADDRESS: ADDRESS}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADDRESS: ADDRESS}


async def test_user_flow_no_devices(hass: HomeAssistant) -> None:
    """No visible BLE devices at all aborts with no_devices_found."""
    with patch(
        "custom_components.safera_sense.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
