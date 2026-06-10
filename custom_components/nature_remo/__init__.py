import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import NatureRemoAPI, NatureRemoAuthError
from .const import CONF_LOCAL_IP, DEFAULT_MOTION_THRESHOLD_MINUTES, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .coordinator import NatureRemoCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["climate", "light", "sensor", "remote", "switch", "binary_sensor", "event", "button", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Nature Remo integration entry")

    hass.data.setdefault(DOMAIN, {})

    local_ip = entry.options.get(CONF_LOCAL_IP, "")
    api = NatureRemoAPI(hass, entry.data["api_key"], local_ip=local_ip if local_ip else None)

    # Respect Nature Cloud API rate limit: 30 requests / 5 min.
    # Each refresh issues 2 requests (devices + appliances), so 30 s is the safe floor.
    min_update_interval = 30
    try:
        update_interval = int(entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL))
    except ValueError:
        _LOGGER.warning(
            "Invalid update_interval value for %s: %s. Falling back to %s seconds.",
            entry.entry_id,
            entry.options.get("update_interval"),
            DEFAULT_UPDATE_INTERVAL,
        )
        update_interval = DEFAULT_UPDATE_INTERVAL
    update_interval = max(min_update_interval, update_interval)
    coordinator = NatureRemoCoordinator(hass, api, update_interval)

    try:
        motion_threshold = int(
            entry.options.get("motion_threshold_minutes", DEFAULT_MOTION_THRESHOLD_MINUTES)
        )
    except ValueError:
        _LOGGER.warning(
            "Invalid motion_threshold_minutes value for %s: %s. Falling back to %s minutes.",
            entry.entry_id,
            entry.options.get("motion_threshold_minutes"),
            DEFAULT_MOTION_THRESHOLD_MINUTES,
        )
        motion_threshold = DEFAULT_MOTION_THRESHOLD_MINUTES
    if motion_threshold < 1:
        motion_threshold = 1
    coordinator.motion_threshold_minutes = motion_threshold

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        await entry.async_start_reauth(hass)
        return False
    except UpdateFailed as err:
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {err}") from err

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    async def handle_send_light_mode(call: ServiceCall):
        entity_ids = call.data.get("entity_id")
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        if not entity_ids:
            raise ServiceValidationError("entity_id is required")
        entity_id = entity_ids[0]
        mode = call.data.get("mode", "on")

        target_entry_data = None
        light_entity = None
        for entry_data in list(hass.data[DOMAIN].values()):
            if not isinstance(entry_data, dict):
                continue
            coordinator = entry_data["coordinator"]
            light_entity = coordinator.entity_map.get(entity_id)
            if light_entity is not None:
                target_entry_data = entry_data
                break
        else:
            raise ServiceValidationError(f"{entity_id} not found")

        if mode not in light_entity.supported_effects:
            raise ServiceValidationError(
                f"Effect '{mode}' is not supported"
            )

        api = target_entry_data["api"]
        try:
            await api.send_light_command(light_entity.appliance_id, mode)
        except NatureRemoAuthError as err:
            raise HomeAssistantError(f"Authentication failed: {err}") from err
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(f"Light command failed: {err}") from err
        light_entity.set_mode(mode)

        return {"status": "success", "appliance_id": light_entity.appliance_id}

    async def handle_learn_signal(call: ServiceCall):
        appliance_id = call.data.get("appliance_id")

        if not appliance_id:
            raise ServiceValidationError("appliance_id is required")

        target_api = None
        for entry_data in list(hass.data[DOMAIN].values()):
            if not isinstance(entry_data, dict):
                continue
            coordinator = entry_data["coordinator"]
            if (
                appliance_id in coordinator.aircons
                or appliance_id in coordinator.lights
                or appliance_id in coordinator.ir_remotes
            ):
                target_api = entry_data["api"]
                break

        if target_api is None:
            raise ServiceValidationError(
                f"appliance_id '{appliance_id}' not found in any configured entry"
            )

        try:
            result = await target_api.learn_signal(appliance_id)
            return result
        except NatureRemoAuthError as err:
            raise HomeAssistantError(f"Authentication failed: {err}") from err
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(f"Signal learn failed: {err}") from err

    services_registered = hass.data[DOMAIN].setdefault("_services_registered", False)
    if not services_registered:
        hass.services.async_register(
            DOMAIN,
            "send_light_mode",
            handle_send_light_mode,
            supports_response=SupportsResponse.OPTIONAL,
        )
        hass.services.async_register(
            DOMAIN,
            "learn_signal",
            handle_learn_signal,
            supports_response=SupportsResponse.OPTIONAL,
        )
        hass.data[DOMAIN]["_services_registered"] = True

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry.entry_id, {})
    coordinator: NatureRemoCoordinator | None = entry_data.get("coordinator")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and coordinator is not None:
        await coordinator.async_shutdown()
        domain_data.pop(entry.entry_id, None)
        # Only remove services when no config entries remain (keep the flag key)
        if domain_data == {"_services_registered": True}:
            hass.services.async_remove(DOMAIN, "send_light_mode")
            hass.services.async_remove(DOMAIN, "learn_signal")
            hass.data.pop(DOMAIN, None)
    return unload_ok
