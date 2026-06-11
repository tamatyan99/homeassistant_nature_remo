"""Tests for the Nature Remo sensor platform."""

from unittest.mock import AsyncMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_sensor_async_setup_entry_creates_entities(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that async_setup_entry creates expected sensor entities."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    assert hass.states.get("sensor.living_room_temperature") is not None
    assert hass.states.get("sensor.living_room_humidity") is not None
    assert hass.states.get("sensor.living_room_illuminance") is not None
    assert hass.states.get("sensor.living_room_pressure") is not None
    assert hass.states.get("sensor.living_room_buy_power") is not None
    assert hass.states.get("sensor.living_room_sold_power") is not None
    assert hass.states.get("sensor.living_room_current_power") is not None
    assert hass.states.get("sensor.bedroom_sensor_last_motion") is not None


async def test_sensor_entity_properties(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test sensor entity properties."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    entity_reg = er.async_get(hass)

    temp_entity = entity_reg.async_get("sensor.living_room_temperature")
    assert temp_entity is not None
    assert temp_entity.unique_id == "nature_remo_sensor_dev-1_te"

    state = hass.states.get("sensor.living_room_temperature")
    assert state.state == "22.5"
    assert state.attributes["device_class"] == SensorDeviceClass.TEMPERATURE
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
    assert state.attributes["unit_of_measurement"] == "°C"

    buy_entity = entity_reg.async_get("sensor.living_room_buy_power")
    assert buy_entity.unique_id == "nature_remo_sensor_sm-1_buy_power"

    buy_state = hass.states.get("sensor.living_room_buy_power")
    assert buy_state.attributes["device_class"] == SensorDeviceClass.ENERGY
    assert buy_state.attributes["state_class"] == SensorStateClass.TOTAL_INCREASING
    assert buy_state.attributes["unit_of_measurement"] == "kWh"

    motion_entity = entity_reg.async_get("sensor.bedroom_sensor_last_motion")
    assert motion_entity.unique_id == "nature_remo_dev-2_last_motion"
    assert motion_entity.original_device_class == SensorDeviceClass.TIMESTAMP

    motion_state = hass.states.get("sensor.bedroom_sensor_last_motion")
    assert motion_state.attributes["device_class"] == SensorDeviceClass.TIMESTAMP


async def test_sensor_illuminance_attributes(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test illuminance sensor has extra attributes."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    state = hass.states.get("sensor.living_room_illuminance")
    assert state.attributes["raw_sensor_scale"] == "0-200"
    assert "Nature Remo" in state.attributes["note"]


async def test_sensor_coordinator_update_changes_state(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test that coordinator update changes sensor state."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    assert hass.states.get("sensor.living_room_temperature").state == "22.5"

    new_devices = [dict(d) for d in coordinator_data["devices"]]
    for dev in new_devices:
        if dev["id"] == "dev-1":
            dev["newest_events"]["te"]["val"] = 25.0

    mock_api.get_devices = AsyncMock(return_value=new_devices)
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.living_room_temperature")
    assert state.state == "25.0"


async def test_sensor_available_when_device_disappears(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test sensor availability when the source device is removed from coordinator."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    assert hass.states.get("sensor.living_room_temperature").state == "22.5"

    mock_api.get_devices = AsyncMock(return_value=[])
    mock_api.get_appliances = AsyncMock(return_value=coordinator_data["appliances"])

    await hass.data["nature_remo"][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.living_room_temperature")
    assert state.state == "unavailable"

    motion_state = hass.states.get("sensor.bedroom_sensor_last_motion")
    assert motion_state.state == "unavailable"


async def test_sensor_smart_meter_values(
    hass: HomeAssistant, setup_integration, coordinator_data, mock_api
):
    """Test smart meter sensor values."""
    await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    assert hass.states.get("sensor.living_room_buy_power").state == "0"
    assert hass.states.get("sensor.living_room_sold_power").state == "0"
    assert hass.states.get("sensor.living_room_current_power").state == "0"
