"""Tests for the options flow."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.safera_sense.const import CONF_UPDATE_INTERVAL, DOMAIN

ADDRESS = "D7:B2:CA:5F:C0:8D"


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, mock_bluetooth):
    """Enable custom integrations and mock the Bluetooth stack."""
    yield


async def test_options_flow_sets_interval(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={"address": ADDRESS}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_UPDATE_INTERVAL: 120}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_UPDATE_INTERVAL: 120}


async def test_options_flow_rejects_out_of_range(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={"address": ADDRESS}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(Exception):  # noqa: B017 - voluptuous validation error
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_UPDATE_INTERVAL: 0}
        )
