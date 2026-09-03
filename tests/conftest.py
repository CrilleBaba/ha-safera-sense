"""Shared fixtures for the Safera Sense tests."""

from unittest.mock import PropertyMock, patch

import pytest


@pytest.fixture(autouse=True, scope="session")
def mock_adapters_history():
    """Mock the BlueZ advertisement history.

    The phcc bluetooth mocks emulate Linux adapters but leave the
    dbus-backed history property unpatched, which fails on hosts
    without dbus (macOS dev machines).
    """
    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        new_callable=PropertyMock,
        return_value={},
    ):
        yield


@pytest.fixture
def expected_lingering_timers() -> bool:
    """Tolerate the Bluetooth manager's unavailability-check timer."""
    return True
