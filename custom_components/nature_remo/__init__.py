import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from .api import NatureRemoAPI
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["climate", "light", "sensor", "remote", "switch", "binary_sensor", "event", "button", "select", "diagnostics"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Nature Remo integration entry")

    hass.data.setdefault(DOMAIN, {})

    local_ip = entry.options.get("local_ip", "")
    api = NatureRemoAPI(hass, entry.data["api_key"], local_ip=local_ip if local_ip else None)

    update_interval = int(entry.options.get("update_interval", 60))
    coordinator = NatureRemoCoordinator(hass, api, update_interval)

    coordinator.motion_threshold_minutes = int(
        entry.options.get("motion_threshold_minutes", 5)
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    async def handle_send_light_mode(call: ServiceCall):
        entity_id = call.data.get("entity_id")
        mode = call.data.get("mode", "on")

        _LOGGER.debug("coordinator.entity_map: %s", coordinator.entity_map)
        light_entity = coordinator.entity_map.get(entity_id)
        if light_entity is None:
            raise ServiceValidationError(
                f"{entity_id} not found in coordinator.entity_map"
            )

        if mode not in light_entity.supported_effects:
            raise ServiceValidationError(
                f"Effect '{mode}' is not supported by this light"
            )

        await api.send_light_command(light_entity.appliance_id, mode)
        light_entity.set_mode(mode)

        return {"status": "success", "appliance_id": light_entity.appliance_id}

    async def handle_learn_signal(call: ServiceCall):
        appliance_id = call.data.get("appliance_id")

        if not appliance_id:
            raise ServiceValidationError("appliance_id is required")

        result = await api.learn_signal(appliance_id)
        return result

    if not hass.services.has_service(DOMAIN, "send_light_mode"):
        hass.services.async_register(
            DOMAIN,
            "send_light_mode",
            handle_send_light_mode,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, "learn_signal"):
        hass.services.async_register(
            DOMAIN,
            "learn_signal",
            handle_learn_signal,
            supports_response=SupportsResponse.OPTIONAL,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "send_light_mode")
            hass.services.async_remove(DOMAIN, "learn_signal")
            hass.data.pop(DOMAIN, None)
    return unload_ok