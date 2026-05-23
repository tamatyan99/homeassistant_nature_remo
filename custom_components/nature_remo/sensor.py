from datetime import datetime, timezone, timedelta
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN


SENSOR_TYPES = {
    "te": {
        "name": "Temperature",
        "unit": "°C",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "hu": {
        "name": "Humidity",
        "unit": "%",
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "il": {
        "name": "Illuminance",
        "unit": None,
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "pr": {
        "name": "Pressure",
        "unit": "hPa",
        "device_class": SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "buy_power": {
        "name": "Buy Power",
        "unit": "kWh",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "sold_power": {
        "name": "Sold Power",
        "unit": "kWh",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "current_power": {
        "name": "Current Power",
        "unit": "W",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
}

ECHONET_LITE_SENSOR_DEFS = {
    "EL_STORAGE_BATTERY": {
        "e2": {
            "name": "Instant Power",
            "unit": "W",
            "device_class": SensorDeviceClass.POWER,
            "state_class": SensorStateClass.MEASUREMENT,
        },
        "e7": {
            "name": "Battery Level",
            "unit": "%",
            "device_class": SensorDeviceClass.BATTERY,
            "state_class": SensorStateClass.MEASUREMENT,
        },
        "cf": {
            "name": "Operation Status",
            "unit": None,
            "device_class": None,
            "state_class": None,
        },
    },
    "EL_SOLAR_POWER": {
        "e3": {
            "name": "Power Generation",
            "unit": "W",
            "device_class": SensorDeviceClass.POWER,
            "state_class": SensorStateClass.MEASUREMENT,
        },
        "e4": {
            "name": "Cumulative Energy",
            "unit": "kWh",
            "device_class": SensorDeviceClass.ENERGY,
            "state_class": SensorStateClass.TOTAL_INCREASING,
        },
    },
    "EL_EVCD": {
        "e2": {
            "name": "Instant Power",
            "unit": "W",
            "device_class": SensorDeviceClass.POWER,
            "state_class": SensorStateClass.MEASUREMENT,
        },
    },
    "EL_ELECTRIC_WATER_HEATER": {
        "e2": {
            "name": "Instant Power",
            "unit": "W",
            "device_class": SensorDeviceClass.POWER,
            "state_class": SensorStateClass.MEASUREMENT,
        },
    },
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities = []

    for appliance_id, data in coordinator.smart_meters.items():
        for key, desc in SENSOR_TYPES.items():
            if key in data:
                entities.append(
                    NatureRemoSensor(
                        coordinator,
                        appliance_id,
                        data["name"],
                        data["device"],
                        key,
                        desc,
                    )
                )

    for device_id, data in coordinator.devices.items():
        for key in ("te", "hu", "il", "pr"):
            if key in data["events"]:
                entities.append(
                    NatureRemoSensor(
                        coordinator,
                        device_id,
                        data["name"],
                        {
                            "device_id": data["device_id"],
                            "name": data["name"],
                            "firmware_version": data["firmware_version"],
                            "serial_number": data.get("serial_number", ""),
                            "mac_address": data.get("mac_address", ""),
                        },
                        key,
                        SENSOR_TYPES[key],
                    )
                )

    for device_id, data in coordinator.motion_sensors.items():
        entities.append(
            NatureRemoMotionTimeSensor(
                coordinator,
                device_id,
                data["name"],
                {
                    "device_id": data["device_id"],
                    "name": data["name"],
                    "firmware_version": data["firmware_version"],
                    "serial_number": data.get("serial_number", ""),
                    "mac_address": data.get("mac_address", ""),
                },
            )
        )

    for appliance_id, data in coordinator.echonetlite_appliances.items():
        appliance_type = data["type"]
        sensor_defs = ECHONET_LITE_SENSOR_DEFS.get(appliance_type, {})
        for epc_key, sensor_def in sensor_defs.items():
            if epc_key in data.get("properties", {}):
                entities.append(
                    NatureRemoEchonetLiteSensor(
                        coordinator,
                        appliance_id,
                        data["name"],
                        data["device"],
                        epc_key,
                        sensor_def,
                    )
                )

    async_add_entities(entities)


class NatureRemoSensor(CoordinatorEntity[NatureRemoCoordinator], SensorEntity):
    def __init__(self, coordinator, appliance_id, name, device, key, description):
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_sensor_{appliance_id}_{key}"
        self._attr_name = f"Nature Remo {name} {description['name']}"
        self._device = device
        self._appliance_id = appliance_id
        self._attr_native_unit_of_measurement = description["unit"]
        self._attr_device_class = description["device_class"]
        self._attr_state_class = description["state_class"]
        self._key = key

    @property
    def device_info(self):
        di = {
            "identifiers": {(DOMAIN, self._device["device_id"])},
            "name": self._device["name"],
            "manufacturer": "Nature",
            "model": self._device.get("firmware_version", "Nature Remo"),
        }
        if self._device.get("serial_number"):
            di["serial_number"] = self._device["serial_number"]
        if self._device.get("mac_address"):
            di["hw_version"] = self._device["mac_address"]
        return di

    @property
    def native_value(self):
        if self._key in ("te", "hu", "il", "pr"):
            device = self.coordinator.devices.get(self._appliance_id)
            if device is None:
                return None
            return device.get("events", {}).get(self._key, {}).get("val")

        smart_meter = self.coordinator.smart_meters.get(self._appliance_id)
        if smart_meter is None:
            return None
        return smart_meter.get(self._key)

    @property
    def extra_state_attributes(self):
        attributes = {}

        if self._key == "il":
            attributes["raw_sensor_scale"] = "0-200"
            attributes["note"] = "This is a relative scale used by Nature Remo."

        return attributes


class NatureRemoMotionTimeSensor(
    CoordinatorEntity[NatureRemoCoordinator], SensorEntity
):
    def __init__(self, coordinator, device_id, name, device):
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._attr_name = f"Nature Remo {name} Last Motion"
        self._attr_unique_id = f"{device_id}_last_motion"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_native_unit_of_measurement = None

    @property
    def device_info(self):
        di = {
            "identifiers": {(DOMAIN, self._device["device_id"])},
            "name": self._device["name"],
            "manufacturer": "Nature",
            "model": self._device.get("firmware_version", "Nature Remo"),
        }
        if self._device.get("serial_number"):
            di["serial_number"] = self._device["serial_number"]
        if self._device.get("mac_address"):
            di["hw_version"] = self._device["mac_address"]
        return di

    @property
    def native_value(self):
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion and "last_motion" in motion:
            return motion["last_motion"]
        return None


class NatureRemoEchonetLiteSensor(
    CoordinatorEntity[NatureRemoCoordinator], SensorEntity
):
    def __init__(
        self, coordinator, appliance_id, appliance_name, device, epc_key, sensor_def
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_el_{appliance_id}_{epc_key}"
        self._attr_name = f"Nature Remo {appliance_name} {sensor_def['name']}"
        self._attr_native_unit_of_measurement = sensor_def["unit"]
        self._attr_device_class = sensor_def["device_class"]
        self._attr_state_class = sensor_def["state_class"]
        self._appliance_id = appliance_id
        self._device = device
        self._epc_key = epc_key

    @property
    def device_info(self):
        di = {
            "identifiers": {(DOMAIN, self._device["device_id"])},
            "name": self._device["name"],
            "manufacturer": "Nature",
            "model": self._device.get("firmware_version", "Nature Remo E"),
        }
        if self._device.get("serial_number"):
            di["serial_number"] = self._device["serial_number"]
        if self._device.get("mac_address"):
            di["hw_version"] = self._device["mac_address"]
        return di

    @property
    def native_value(self):
        appliance = self.coordinator.echonetlite_appliances.get(self._appliance_id)
        if appliance is None:
            return None
        prop_data = appliance.get("properties", {}).get(self._epc_key)
        if prop_data is None or prop_data.get("parsed_val") is None:
            return None
        if self._epc_key == "cf":
            raw_val = prop_data.get("raw_val", "")
            return "on" if raw_val == "30" else "off"
        return prop_data["parsed_val"]

    @property
    def extra_state_attributes(self):
        appliance = self.coordinator.echonetlite_appliances.get(self._appliance_id)
        if appliance is None:
            return {}
        prop_data = appliance.get("properties", {}).get(self._epc_key)
        if prop_data is None:
            return {}
        attrs = {}
        if prop_data.get("updated_at"):
            attrs["updated_at"] = prop_data["updated_at"]
        if prop_data.get("raw_val"):
            attrs["raw_epc_value"] = prop_data["raw_val"]
        return attrs