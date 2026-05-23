# Nature Remo - Home Assistant Custom Integration

⭐ If this integration helps you, please consider giving it a star on GitHub!

📄 日本語版のREADMEはこちら 👉 [README_ja.md](README_ja.md)

This is a custom integration for linking Nature Remo devices with Home Assistant.  
It enables you to control appliances like air conditioners and lights, and monitor temperature, humidity, and more directly in your smart home setup.

This repository is a fork of [NaNaLinks/homeassistant_nature_remo](https://github.com/NaNaLinks/homeassistant_nature_remo) originally developed by [@nanosns](https://github.com/nanosns).  
We appreciate the original author's work and continue development independently here.

---

## ⚠️ Disclaimer

This is an **unofficial** integration and is not affiliated with Nature Inc. or Home Assistant.  
Please use this integration **at your own risk**.

---

## Features

- Control appliances (air conditioners, lights) registered to Nature Remo
- Retrieve temperature, humidity, illuminance, atmospheric pressure, and motion sensor data
- Access smart meter data (consumption, generation, instant power) via Nature Remo E / E Lite
- Control lighting modes using custom service calls
- Send IR commands using remote entities created from defined signals
- Switch entities for appliances with on/off signals
- Binary motion sensor with configurable detection threshold
- ECHONET Lite appliance support (storage battery, solar power, EV charger, electric water heater)
- External temperature and humidity sensor override for climate entities
- Local API support for data retrieval (read-only; control commands always use the cloud API)

---

## Installation (via HACS)

Click the button below to easily add this repository to HACS.

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tamatyan99&repository=homeassistant_nature_remo&category=integration)

1. Open HACS in Home Assistant
2. Click the menu (⋮) in the top right corner
3. Select "Custom repositories"
4. Add this repository URL:
   `https://github.com/tamatyan99/homeassistant_nature_remo`  
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

- You can select the update interval from preset choices (seconds)
  - Choices: `30`, `60`, `90` (default: `60`)
- You can select the motion detection threshold from preset choices (minutes)
  - Choices: `1`, `3`, `5`, `10`, `15` (default: `5`)
- You can configure a local IP address to communicate directly with your Nature Remo device
- You can assign external temperature and humidity sensors per device

⚠️ Nature Remo Cloud API has rate limits.  
Setting a very short update interval may cause the integration to reach the API request limit.

---

## Supported Entities

| Type          | Description                                                        |
|---------------|--------------------------------------------------------------------|
| climate       | Control air conditioners (cooling, heating, dry, fan-only, auto, eco preset) |
| light         | Control lights (on/off, mode selection, effects)                   |
| sensor        | Temperature, humidity, illuminance, pressure, power (buy/sell/instant), motion timestamp |
| remote        | Send infrared signals or turn on/off for IR/AC/LIGHT types        |
| switch        | On/off toggle for appliances with power signals                    |
| binary_sensor | Motion detection with configurable timeout                         |

*Additional entities may be supported in future updates.*

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

Note: These values are used for display only. Climate control commands are still sent to the Nature Remo API using the device's own readings.

### Notes

- If no external sensors are configured, the integration will continue to use the default values from Nature Remo
- Any sensor entity with appropriate temperature or humidity values can be used

---

## Custom Services

The integration provides the following custom services under the `nature_remo` domain:

| Service                | Description                                    |
|------------------------|------------------------------------------------|
| `send_light_mode`      | Send a specific mode command to a light entity |
| `echonetlite_refresh`  | Refresh ECHONET Lite appliance properties      |
| `learn_signal`         | Start learning an infrared signal              |

---

## Development & Contributing

Contributions, bug reports, and feature requests are welcome!

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please open an issue first for significant changes or new features to discuss the approach.

---

## Authors

- Original author: [@nanosns](https://github.com/nanosns) (NaNaRin) — [NaNaLinks](https://github.com/NaNaLinks)
- Fork maintainer: [@tamatyan99](https://github.com/tamatyan99)

---

## License

MIT License
