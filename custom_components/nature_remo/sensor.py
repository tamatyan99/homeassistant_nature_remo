from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN
from .entity import get_device_info


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
        "device_class": None,
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
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
                {
                    "device_id": data["device_id"],
                    "name": data["name"],
                    "firmware_version": data["firmware_version"],
                    "serial_number": data.get("serial_number", ""),
                    "mac_address": data.get("mac_address", ""),
                },
            )
        )

    async_add_entities(entities, True)


class NatureRemoSensor(CoordinatorEntity[NatureRemoCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, appliance_id, device, key, description):
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_sensor_{appliance_id}_{key}"
        self._attr_name = description["name"]
        self._device = device
        self._appliance_id = appliance_id
        self._attr_native_unit_of_measurement = description["unit"]
        self._attr_device_class = description["device_class"]
        self._attr_state_class = description["state_class"]
        self._key = key

    @property
    def device_info(self):
        return get_device_info(self._device)

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
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, device_id, device):
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._attr_name = "Last Motion"
        self._attr_unique_id = f"nature_remo_{device_id}_last_motion"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_native_unit_of_measurement = None

    @property
    def device_info(self):
        return get_device_info(self._device)

    @property
    def native_value(self):
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion and "last_motion" in motion:
            return motion["last_motion"]
        return None
