from homeassistant.components.event import EventEntity
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
            NatureRemoMotionEvent(
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


class NatureRemoMotionEvent(CoordinatorEntity[NatureRemoCoordinator], EventEntity):
    def __init__(self, coordinator, device_id, name, device):
        super().__init__(coordinator)
        self._device = device
        self._device_id = device_id
        self._attr_name = f"Nature Remo {name} Motion Event"
        self._attr_unique_id = f"{device_id}_motion_event"
        self._last_motion = None

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

    def _handle_coordinator_update(self) -> None:
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion:
            last_motion = motion.get("last_motion")
            if last_motion is not None and last_motion != self._last_motion:
                self._last_motion = last_motion
                self._trigger_event(
                    "nature_remo_motion_detected",
                    {
                        "device_id": self._device_id,
                        "last_motion": last_motion.isoformat(),
                    },
                )
        super()._handle_coordinator_update()
