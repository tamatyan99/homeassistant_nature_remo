# Nature Remo - Home Assistant Custom Integration

⭐ If this integration helps you, please consider giving it a star on GitHub!

📄 日本語版のREADMEはこちら 👉 [README_ja.md](README_ja.md)

**This is a fork of the original [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo) project.**
This fork includes additional features and improvements beyond the original.

This is a custom integration for linking Nature Remo devices with Home Assistant.  
It enables you to control appliances like air conditioners and lights, and monitor temperature, humidity, and more directly in your smart home setup.

---

## ⚠️ Disclaimer
This is an **unofficial** integration and is not affiliated with Nature Inc. or Home Assistant.  
Please use this integration **at your own risk**.

---

## What's New in v0.4.0

- **Switch Platform** - Control IR appliances with ON/OFF signals as Home Assistant switches
- **ECHONET Lite Support** - Read sensors from Remo E connected appliances (storage battery, solar power, EV charger, electric water heater)
- **Local API** - Optional direct LAN connection to Remo devices for faster response
- **Atmospheric Pressure Sensor** - Support for `pr` events from compatible Remo devices
- **Motion Threshold** - Configurable motion detection timeout (1/3/5/10/15 minutes)
- **Signal Learning Service** - `nature_remo.learn_signal` service to learn new IR signals
- **ECHONET Lite Refresh Service** - `nature_remo.echonetlite_refresh` service to refresh property values
- **Eco Preset Mode** - Climate entities now support eco preset (automatically sets 26°C)
- **Enhanced Device Info** - Serial number and MAC address displayed in device information

---

## Features

- Control appliances (air conditioners, lights) registered to Nature Remo
- Retrieve temperature, humidity, illuminance, atmospheric pressure, and motion sensor data
- Access smart meter data (consumption, generation, instant power) via Nature Remo E / E Lite
- Access ECHONET Lite appliance data (storage battery, solar, EV charger, water heater) via Remo E
- Control lighting modes using custom service calls
- Send IR commands using remote entities created from defined signals
- Switch platform for appliances with identifiable ON/OFF signals
- Optional Local API for direct LAN communication

---

## Installation (via HACS)

Click the button below to easily add this repository to HACS.

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tamatyan99&repository=homeassistant_nature_remo&category=integration)

1. Open HACS in Home Assistant
2. Click the menu (⋮) in the top right corner
3. Select "Custom repositories"
4. Add this repository URL:
   https://github.com/tamatyan99/homeassistant_nature_remo  
   Category: Integration
5. Install "Nature Remo"
6. Restart Home Assistant

---

## Installation (Manual)

1. Download or clone this repository and place it in the following path:

```
<config directory>/custom_components/nature_remo/
```

2. Restart Home Assistant.

---

## Setup Instructions

1. Go to *Settings → Devices & Services → Add Integration* and search for `Nature Remo`
2. Enter your access token (API key) and integration name
   - You can issue an API token at [Nature Official Site](https://home.nature.global)
3. Your registered appliances will be automatically imported as entities

---

## Options

- **Update Interval** - Set the data refresh interval (in seconds)
  - Default: `60 seconds`
  - Range: 10-300 seconds
- **Motion Threshold** - Configure how long motion remains active after detection
  - Options: 1/3/5/10/15 minutes
  - Default: `5 minutes`
- **Local IP** - Optional: Set your Remo's local IP address for direct LAN communication
  - Leave empty to use cloud API (default)
- **External Sensors** - Configure external temperature and humidity sensors for each device

⚠️ Nature Remo Cloud API has rate limits.  
Setting a very short update interval may cause the integration to reach the API request limit.

---

## Supported Entities

| Type          | Description                                                              |
|---------------|--------------------------------------------------------------------------|
| climate       | Control air conditioners (cooling, heating, dry, fan, auto) + eco preset |
| light         | Control lights (on/off, mode selection)                                  |
| sensor        | Temperature, humidity, illuminance, pressure, motion, power (buy/sell)   |
| binary_sensor | Motion detection with configurable timeout                               |
| remote        | Send infrared signals defined as "signals" for IR/AC/LIGHT types        |
| switch        | ON/OFF control for IR appliances with identifiable signals               |

*Additional entities may be supported in future updates.*

---

## Services

### nature_remo.send_light_mode
Send a specific button mode to a light entity.

```yaml
service: nature_remo.send_light_mode
data:
  entity_id: light.living_room_light
  mode: "night"
```

### nature_remo.echonetlite_refresh
Refresh ECHONET Lite appliance property values.

```yaml
service: nature_remo.echonetlite_refresh
data:
  appliance_id: "your-appliance-id"
  epcs: "e2,e7"  # Optional: comma-separated EPC list
```

### nature_remo.learn_signal
Start learning a new infrared signal for an appliance.

```yaml
service: nature_remo.learn_signal
data:
  appliance_id: "your-appliance-id"
```

---

## Sample: Using Remote Entities

This integration supports `remote` entities generated from Nature Remo's defined `signals`. These entities allow you to send IR commands directly from Home Assistant.

### Example: Service Call

You can call a signal like this using `remote.send_command`:

```yaml
service: remote.send_command
target:
  entity_id: remote.living_room_remote  # Your remote entity ID
data:
  command: "Power On"  # The name of the signal as defined in Remo
```

---

## External Temperature and Humidity Sensors

You can configure external temperature and humidity sensors for each device.

By selecting entities from Home Assistant settings, the climate device will use the specified sensors instead of the default values provided by Nature Remo.

### How it works

- Open the integration settings from Home Assistant
- Select a device
- Choose temperature and humidity entities from available sensors
- Save the configuration

Once configured, the selected external sensors will be used for:

- Displaying temperature and humidity in the climate entity
- Providing more accurate environmental data for air conditioner control

### Notes

- If no external sensors are configured, the integration will continue to use the default values from Nature Remo
- Any sensor entity with appropriate temperature or humidity values can be used

---

## Author

- Original Author: [@nanosns](https://github.com/nanosns) (NaNaRin) / [@NaNaLinks](https://github.com/NaNaLinks)
- Fork Maintainer: [@tamatyan99](https://github.com/tamatyan99)

---

## License

MIT License

---

## Fork Information

This repository is a fork of [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo).
This fork includes additional features such as ECHONET Lite support, switch platform, Local API, atmospheric pressure sensor, motion threshold configuration, signal learning service, and various bug fixes.
If you want the original version, please use the upstream repository.