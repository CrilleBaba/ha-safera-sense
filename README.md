# Safera Sense for Home Assistant

[![Validate](https://github.com/crillebaba/ha-safera-sense/actions/workflows/validate.yml/badge.svg)](https://github.com/crillebaba/ha-safera-sense/actions/workflows/validate.yml)
[![Tests](https://github.com/crillebaba/ha-safera-sense/actions/workflows/test.yml/badge.svg)](https://github.com/crillebaba/ha-safera-sense/actions/workflows/test.yml)

Local Bluetooth (BLE) integration for **Safera Sense** cooking sensors, as
built into **Røros Hetta** cooker hoods (Safera Sense Integral) and sold
as Safera stove guards. Fully local — no cloud, no vendor app needed.

## Credits

Most of the protocol reverse engineering comes from two projects that
did the heavy lifting:

- **[magicus/safera-ble](https://github.com/magicus/safera-ble)** — the
  byte-level protocol documentation, derived from packet captures and
  analysis of the decompiled Android app;
- **[havardgulldahl/rorossense-ble](https://github.com/havardgulldahl/rorossense-ble)** —
  a working Python client and further protocol exploration against a
  RørosHetta hood.

This integration is an independent implementation that extends the
protocol with findings of its own: the BLE bonding requirement,
**grease filter saturation** monitoring and reset (byte 59 of the
extended sensor report, confirmed experimentally), and the **PM2.5**
interpretation of the particle index field.

Communication is handled by the
[safera-sense-ble](https://github.com/crillebaba/safera-sense-ble)
Python library. Unofficial project — not affiliated with Safera Oy or
Røros Metall AS.

## Entities

| Platform | Entities |
| --- | --- |
| Fan | Hood fan: four speeds (level 4 = boost) plus an **Auto** preset mode |
| Light | Hood light: three brightness levels, with **Auto** exposed as a light effect |
| Sensor | Ambient / surface / pan temperature, humidity, ambient light, eCO2, tVOC, air quality index, **PM2.5** (µg/m³), stove power, cooking activity level, alarm level, **grease filter %**, device state, Wi-Fi SSID |
| Binary sensor | Cooking, safety alarm, stove power cut (stove-guard installs), sensor problem (with error details) |
| Button | Identify, **Filter cleaned** (resets the grease filter counter) |

## How updates work

The device pushes a sensor report over BLE about once per second. To
keep Home Assistant's database lean, the integration is deliberately
selective about what it forwards:

- **Safety and control changes update immediately**: alarms, device
  state, cooking activity, fan, light, grease filter and error flags
  reach Home Assistant within a second.
- **Environmental sensors are throttled**: temperature, humidity,
  air quality etc. update at most once per interval (default **30 s**,
  configurable 1–300 s via *Settings → Devices & Services → Safera
  Sense → Configure*).
- **Values are quantized** to meaningful precision (0.1 °C
  temperatures, whole-percent humidity, whole lux, 0.1 µg/m³ PM2.5),
  so sensor jitter doesn't generate database writes.

The BLE connection is held open with automatic pairing/bonding and
reconnection; a 60 s polling fallback doubles as a connection watchdog.

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
   `https://github.com/crillebaba/ha-safera-sense` as an
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

## Configuration

*Settings → Devices & Services → Safera Sense → Configure*:

| Option | Default | Description |
| --- | --- | --- |
| Environmental sensor update interval | 30 s | How often temperature, humidity, air-quality and similar sensors update. Safety and control changes always update immediately. Set to 1 for (nearly) every BLE report. |

## Automation ideas

- Boost the fan when the **cooking** binary sensor turns on and
  **tVOC** spikes.
- Notify when **grease filter** passes 80 %, and press **Filter
  cleaned** from the notification after washing it.
- Alert on the **safety alarm** or **stove power cut** binary sensors.

## Known limitations

- Fan/light/grease-filter state come from the extended sensor report
  that only hood-integrated devices send; a bare stove guard will show
  those entities as unknown.
- Light colour temperature is not yet exposed (the adjustment command
  needs confirming on real hardware).
- The event log ("Smart Cooking" timeline) is documented in the
  protocol but not yet exposed.

## License

MIT — see [LICENSE](LICENSE).
