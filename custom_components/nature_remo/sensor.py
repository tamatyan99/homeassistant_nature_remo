from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NatureRemoCoordinator
from .entity import get_device_info


SENSOR_TYPES = {
    "te": {
        "translation_key": "temperature",
        "unit": "°C",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "hu": {
        "translation_key": "humidity",
        "unit": "%",
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "il": {
        "translation_key": "illuminance",
        "unit": "lx",
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "pr": {
        "translation_key": "pressure",
        "unit": "hPa",
        "device_class": SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "buy_power": {
        "translation_key": "buy_power",
        "unit": "kWh",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "sold_power": {
        "translation_key": "sold_power",
        "unit": "kWh",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "current_power": {
        "translation_key": "current_power",
        "unit": "W",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities: list[SensorEntity] = []

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

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        appliance_id: str,
        device: dict,
        key: str,
        description: dict,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_sensor_{appliance_id}_{key}"
        self._attr_translation_key = description["translation_key"]
        self._device = device
        self._appliance_id = appliance_id
        self._attr_native_unit_of_measurement = description["unit"]
        self._attr_device_class = description["device_class"]
        self._attr_state_class = description["state_class"]
        self._key = key

    @property
    def device_info(self) -> DeviceInfo:
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
    def extra_state_attributes(self) -> dict[str, str]:
        if self._key == "il":
            return {
                "raw_sensor_scale": "0-200",
                "note": "Relative illuminance scale used by Nature Remo (not lux).",
            }
        return {}


class NatureRemoMotionTimeSensor(
    CoordinatorEntity[NatureRemoCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "last_motion"

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        device_id: str,
        device: dict,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._device = device
        self._attr_unique_id = f"nature_remo_{device_id}_last_motion"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_native_unit_of_measurement = None

    @property
    def device_info(self) -> DeviceInfo:
        return get_device_info(self._device)

    @property
    def native_value(self):
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion and "last_motion" in motion:
            return motion["last_motion"]
        return None
