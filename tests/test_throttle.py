"""Tests for the event-aware update throttle."""

from dataclasses import replace

from safera_sense_ble import SensorReport

from custom_components.safera_sense.coordinator import is_eventful_change

REPORT = SensorReport.from_bytes(
    bytes.fromhex(
        "231c721c0416da07430c090009000aba014b0000000000001100"
        "64ff00ef001e0002000081687000000003000001000000000100"
        "0000000000000d060000000000000000ff"
    )
)


def test_first_report_is_eventful() -> None:
    assert is_eventful_change(None, REPORT) is True


def test_identical_report_is_not_eventful() -> None:
    assert is_eventful_change(REPORT, REPORT) is False


def test_environmental_drift_is_not_eventful() -> None:
    drifted = replace(
        REPORT,
        ambient_temperature=REPORT.ambient_temperature + 0.5,
        humidity=REPORT.humidity + 2,
        co2_ppm=REPORT.co2_ppm + 50,
        tvoc_ppb=REPORT.tvoc_ppb + 20,
        ambient_light=REPORT.ambient_light + 100,
    )
    assert is_eventful_change(REPORT, drifted) is False


def test_safety_and_control_changes_are_eventful() -> None:
    for field, value in [
        ("device_state", 0x09),  # FIRE_WARNING
        ("alarm_status", 118),  # alarm countdown start
        ("alarm_level", 50),
        ("activity_type", 2),  # cooking
        ("sensor_errors", 0x1000),
        ("fan_speed_raw", 60),
        ("fan_auto", True),
        ("light_raw", 90),
        ("grease_filter", 7),
    ]:
        changed = replace(REPORT, **{field: value})
        assert is_eventful_change(REPORT, changed) is True, field
