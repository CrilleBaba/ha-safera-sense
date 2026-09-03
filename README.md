# Safera Sense for Home Assistant

[![Validate](https://github.com/christophebaraer/ha-safera-sense/actions/workflows/validate.yml/badge.svg)](https://github.com/christophebaraer/ha-safera-sense/actions/workflows/validate.yml)
[![Tests](https://github.com/christophebaraer/ha-safera-sense/actions/workflows/test.yml/badge.svg)](https://github.com/christophebaraer/ha-safera-sense/actions/workflows/test.yml)

Local Bluetooth (BLE) integration for **Safera Sense** cooking sensors, as
built into **Røros Hetta** cooker hoods (Safera Sense Integral) and sold
as Safera stove guards. Fully local — no cloud, no vendor app needed.

## Credits

The idea and much of the protocol reverse engineering was done by
**Håvard Gulldahl** in the
[rorossense-ble](https://github.com/havardgulldahl/rorossense-ble)
project. This integration is an independent implementation that fixes
the issues in that repo's proof-of-concept custom component and extends
the protocol with **grease filter saturation** monitoring and reset
(a field decoded during this project's development).

Communication is handled by the
[safera-sense-ble](https://github.com/christophebaraer/safera-sense-ble)
Python library. Unofficial project — not affiliated with Safera Oy or
Røros Metall AS.

## Entities

| Platform | Entities |
| --- | --- |
| Fan | Hood fan: speeds 1–3, **Auto** and **Boost** preset modes |
| Light | Hood light: 3 brightness levels |
| Sensor | Ambient / surface / pan temperature, humidity, ambient light, eCO2, tVOC, air quality index, particle index, stove power, cooking activity level, alarm level, **grease filter %**, device state, Wi-Fi SSID |
| Binary sensor | Cooking, safety alarm, stove power cut (stove-guard installs), sensor problem (with error details) |
| Button | Identify, **Filter cleaned** (resets the grease filter counter) |

Data arrives via BLE notifications about once per second, with a 60 s
polling fallback and automatic reconnection. The device requires BLE
bonding; the integration pairs automatically on first contact.

## Requirements

- Home Assistant 2026.7 or newer.
- A Bluetooth adapter usable by Home Assistant, or an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy/)
  with *active connections* enabled, in range of the hood.
- The vendor mobile app must be closed while Home Assistant is
  connected (the device accepts a single BLE connection).

## Installation

### HACS (recommended)

1. HACS → ⋮ → *Custom repositories* → add
   `https://github.com/christophebaraer/ha-safera-sense` as an
   *Integration*.
2. Install **Safera Sense** and restart Home Assistant.

### Manual

Copy `custom_components/safera_sense/` into
`<HA config>/custom_components/` and restart Home Assistant.

## Setup

The device is normally discovered automatically (Settings → Devices &
Services). When adding manually, devices matching the Safera fingerprint
are listed first; if none match, all visible BLE devices are offered so
an unexpected advertised name can still be selected.

If setup loops on "Insufficient authentication", put the hood into
Bluetooth pairing mode (the procedure used when first connecting the
vendor app) and reload the integration.

## Known limitations

- Fan/light/grease-filter state come from the extended sensor report
  that only hood-integrated devices send; a bare stove guard will show
  those entities as unknown.
- Light auto mode is reported but cannot yet be commanded.
- PM2.5 and the event log are documented in the protocol but not yet
  exposed as entities.

## License

MIT — see [LICENSE](LICENSE).
