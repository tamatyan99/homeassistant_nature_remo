# Nature Remo - Home Assistant Custom Integration

[![Tests](https://github.com/tamatyan99/homeassistant_nature_remo/actions/workflows/test.yml/badge.svg)](https://github.com/tamatyan99/homeassistant_nature_remo/actions/workflows/test.yml)
[![HACS Validation](https://github.com/tamatyan99/homeassistant_nature_remo/actions/workflows/hacs.yml/badge.svg)](https://github.com/tamatyan99/homeassistant_nature_remo/actions/workflows/hacs.yml)

⭐ If this integration helps you, please consider giving it a star on GitHub!

This is a custom integration for linking Nature Remo devices with Home Assistant.
It enables you to control appliances like air conditioners and lights, and monitor
temperature, humidity, and more directly in your smart home setup.

This repository is a fork of [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo)
originally developed by [@nanosns](https://github.com/nanosns).
We appreciate the original author's work and continue development independently here.

---

## ⚠️ Disclaimer

This is an **unofficial** integration and is not affiliated with Nature Inc. or Home Assistant.
Please use this integration **at your own risk**.

---

## Features

- Control appliances (air conditioners, lights) registered to Nature Remo
- Retrieve temperature, humidity, illuminance, and motion sensor data
- Access smart meter data (consumption, generation, instant power) via Nature Remo E / E Lite
- Control lighting modes using custom service calls
- Send IR commands using remote entities created from defined signals
- External temperature and humidity sensor override for climate entities

---

## Installation (via HACS)

> This integration is currently available through HACS as a **custom repository**.
> We are working towards inclusion in the default HACS store.

Click the button below to add this repository to HACS.

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tamatyan99&repository=homeassistant_nature_remo&category=integration)

1. Open HACS in Home Assistant
2. Click the menu (⋮) in the top right corner
3. Select **"Custom repositories"**
4. Add this repository URL:
   `https://github.com/tamatyan99/homeassistant_nature_remo`
   Category: **Integration**
5. Install **Nature Remo**
6. **Restart Home Assistant completely**

---

## Installation (Manual)

1. Download the latest `nature_remo.zip` from the
   [Releases](https://github.com/tamatyan99/homeassistant_nature_remo/releases) page
2. Extract it so the following path exists:
   ```
   <config directory>/custom_components/nature_remo/manifest.json
   ```
   The directory structure should look like:
   ```
   custom_components/
   └── nature_remo/
       ├── manifest.json
       ├── __init__.py
       ├── api.py
       └── ...
   ```
3. **Restart Home Assistant completely**
4. Go to *Settings → Devices & Services → Add Integration* and search for `Nature Remo`

> ⚠️ A YAML reload or quick restart is **not sufficient**.
> Home Assistant must be fully restarted after adding custom components.

---

## Setup Instructions

1. Go to *Settings → Devices & Services → Add Integration* and search for `Nature Remo`
2. Enter your access token (API key) and integration name
   - You can issue an API token at [Nature Official Site](https://home.nature.global)
3. Your registered appliances will be automatically imported as entities

---

## Options

- You can set the update interval (in seconds)
  - Choices: `30`, `60`, `90` (default: `60`)
- You can configure a local IP address to communicate directly with your Nature Remo device
- You can assign external temperature and humidity sensors per device

⚠️ Nature Remo Cloud API has rate limits.
Setting a very short update interval may cause the integration to reach the API request limit.

---

## Supported Entities

| Type    | Description                                                        |
|---------|--------------------------------------------------------------------|
| climate | Control air conditioners (cooling, heating, dry)                   |
| light   | Control lights (on/off, mode selection)                            |
| sensor  | Temperature, humidity, illuminance, motion, power (buy/sell)      |
| remote  | Send infrared signals defined as "signals" for IR/AC/LIGHT types  |

*Additional entities may be supported in future updates.*

---

## Sample: Using Remote Entities

This integration supports `remote` entities generated from Nature Remo's defined `signals`.
These entities allow you to send IR commands directly from Home Assistant.

### Example: Service Call

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

By selecting entities from Home Assistant settings, the climate device will use the specified
sensors instead of the default values provided by Nature Remo.

### How it works

- Open the integration settings from Home Assistant
- Select a device
- Choose temperature and humidity entities from available sensors
- Save the configuration

### Notes

- If no external sensors are configured, the integration will continue to use the default values from Nature Remo
- Any sensor entity with appropriate temperature or humidity values can be used

---

## Troubleshooting

### Integration not appearing in the search

- Verify the files are in `<config>/custom_components/nature_remo/`
- Restart Home Assistant completely
- Clear your browser cache or use a private window

### Authentication Error

- Verify your API key is correct at [Nature Official Site](https://home.nature.global)
- Ensure the token has not expired

### Rate Limit Errors

- Nature Remo Cloud API has rate limits
- Try increasing the update interval in the integration options
- Avoid excessive manual refreshes

---

## Authors

- Original author: [@nanosns](https://github.com/nanosns) (NaNaRin) — [NaNaLinks](https://github.com/NaNaLinks)
- Fork maintainer: [@tamatyan99](https://github.com/tamatyan99)

---

## License

MIT License
