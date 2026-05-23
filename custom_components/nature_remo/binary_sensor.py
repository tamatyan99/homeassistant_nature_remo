from datetime import datetime, timezone, timedelta
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities = []

    for device_id, data in coordinator.motion_sensors.items():
        entities.append(
            NatureRemoMotionBinarySensor(
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

    async_add_entities(entities)


class NatureRemoMotionBinarySensor(
    CoordinatorEntity[NatureRemoCoordinator], BinarySensorEntity
):
    def __init__(self, coordinator, device_id, name, device):
        super().__init__(coordinator)
        self._device = device
        self._device_id = device_id
        self._attr_name = f"Nature Remo {name} Motion"
        self._attr_unique_id = f"{device_id}_motion"
        self._attr_device_class = BinarySensorDeviceClass.MOTION

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
        return di

    @property
    def is_on(self):
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion:
            return motion.get("is_active", False)
        return False