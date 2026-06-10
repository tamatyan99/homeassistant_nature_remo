"""Tests for the Nature Remo options flow."""

from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.const import (
    CONF_LOCAL_IP,
    DEFAULT_MOTION_THRESHOLD_MINUTES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


def _unique_id(api_key: str) -> str:
    """Compute the unique_id used by the config flow."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]


def _create_entry(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    """Create and add a MockConfigEntry to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        unique_id=_unique_id("test_key"),
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


async def _setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the config entry for tests."""
    with patch(
        "custom_components.nature_remo.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _schema_field_names(schema: vol.Schema) -> list[str]:
    """Return the field names defined in a voluptuous schema."""
    return [marker.schema for marker in schema.schema]


def _get_schema_default(schema: vol.Schema, field: str):
    """Return the default value for a schema field."""
    for marker in schema.schema:
        if marker.schema == field:
            return marker.default()
    raise KeyError(field)


def _get_schema_validator(schema: vol.Schema, field: str):
    """Return the validator for a schema field."""
    return schema.schema[vol.Optional(field)]


@pytest.fixture
async def init_integration(hass: HomeAssistant):
    """Set up the Nature Remo integration for tests."""
    entry = _create_entry(hass)
    await _setup_entry(hass, entry)
    return entry


@pytest.mark.usefixtures("init_integration")
async def test_options_flow_init(hass: HomeAssistant, init_integration):
    """Test options flow initialization."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.usefixtures("init_integration")
async def test_options_flow_fields_present(hass: HomeAssistant, init_integration):
    """Test that the expected fields are present in the options schema."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    schema = result["data_schema"]
    fields = _schema_field_names(schema)

    assert "update_interval" in fields
    assert "motion_threshold_minutes" in fields
    assert CONF_LOCAL_IP in fields


@pytest.mark.usefixtures("init_integration")
async def test_options_flow_valid_submission(hass: HomeAssistant, init_integration):
    """Test that submitting valid options persists them to the config entry."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "update_interval": 30,
            "motion_threshold_minutes": 1,
            CONF_LOCAL_IP: "192.168.1.100",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "update_interval": 30,
        "motion_threshold_minutes": 1,
        CONF_LOCAL_IP: "192.168.1.100",
    }
    assert init_integration.options == result["data"]


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    ("user_input", "expected_error_field"),
    [
        (
            {
                "update_interval": 45,
                "motion_threshold_minutes": DEFAULT_MOTION_THRESHOLD_MINUTES,
                CONF_LOCAL_IP: "",
            },
            "update_interval",
        ),
        (
            {
                "update_interval": DEFAULT_UPDATE_INTERVAL,
                "motion_threshold_minutes": 99,
                CONF_LOCAL_IP: "",
            },
            "motion_threshold_minutes",
        ),
        (
            {
                "update_interval": DEFAULT_UPDATE_INTERVAL,
                "motion_threshold_minutes": DEFAULT_MOTION_THRESHOLD_MINUTES,
                CONF_LOCAL_IP: "not-an-ip",
            },
            CONF_LOCAL_IP,
        ),
    ],
)
async def test_options_flow_invalid_values(
    hass: HomeAssistant,
    init_integration,
    user_input: dict,
    expected_error_field: str,
):
    """Test that invalid option values are rejected with schema errors."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    with pytest.raises(InvalidData) as exc:
        await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input
        )

    assert expected_error_field in exc.value.schema_errors


@pytest.mark.usefixtures("init_integration")
async def test_options_flow_empty_local_ip_allowed(
    hass: HomeAssistant, init_integration
):
    """Test that an empty local_ip value is accepted."""
    result = await hass.config_entries.options.async_init(init_integration.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "update_interval": DEFAULT_UPDATE_INTERVAL,
            "motion_threshold_minutes": DEFAULT_MOTION_THRESHOLD_MINUTES,
            CONF_LOCAL_IP: "",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_LOCAL_IP] == ""


async def test_options_flow_defaults_from_existing_options(hass: HomeAssistant):
    """Test that existing entry options are used as schema defaults."""
    entry = _create_entry(
        hass,
        options={
            "update_interval": 90,
            "motion_threshold_minutes": 15,
            CONF_LOCAL_IP: "10.0.0.1",
        },
    )
    await _setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"]

    assert _get_schema_default(schema, "update_interval") == 90
    assert _get_schema_default(schema, "motion_threshold_minutes") == 15
    assert _get_schema_default(schema, CONF_LOCAL_IP) == "10.0.0.1"


async def test_options_flow_per_device_selectors(hass: HomeAssistant):
    """Test that per-device external temperature/humidity selectors are rendered."""
    entry = _create_entry(hass)
    await _setup_entry(hass, entry)

    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "remo-1")},
        name="Remo 1",
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"]
    fields = _schema_field_names(schema)

    assert "external_temperature_remo-1" in fields
    assert "external_humidity_remo-1" in fields

    temp_selector = _get_schema_validator(schema, "external_temperature_remo-1")
    assert isinstance(temp_selector, selector.EntitySelector)
    assert temp_selector.config["domain"] == ["sensor"]
    assert SensorDeviceClass.TEMPERATURE in temp_selector.config["device_class"]

    humidity_selector = _get_schema_validator(schema, "external_humidity_remo-1")
    assert isinstance(humidity_selector, selector.EntitySelector)
    assert humidity_selector.config["domain"] == ["sensor"]
    assert SensorDeviceClass.HUMIDITY in humidity_selector.config["device_class"]


async def test_options_flow_per_device_defaults_and_persistence(
    hass: HomeAssistant,
):
    """Test that per-device options defaults are populated and persisted."""
    entry = _create_entry(
        hass,
        options={
            "update_interval": DEFAULT_UPDATE_INTERVAL,
            "motion_threshold_minutes": DEFAULT_MOTION_THRESHOLD_MINUTES,
            CONF_LOCAL_IP: "",
            "external_temperature_remo-2": "sensor.outside_temp",
            "external_humidity_remo-2": "sensor.outside_humidity",
        },
    )
    await _setup_entry(hass, entry)

    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "remo-2")},
        name="Remo 2",
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"]

    assert _get_schema_default(schema, "external_temperature_remo-2") == "sensor.outside_temp"
    assert _get_schema_default(schema, "external_humidity_remo-2") == "sensor.outside_humidity"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "update_interval": 60,
            "motion_threshold_minutes": 5,
            CONF_LOCAL_IP: "192.168.1.50",
            "external_temperature_remo-2": "sensor.balcony_temp",
            "external_humidity_remo-2": "sensor.balcony_humidity",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "update_interval": 60,
        "motion_threshold_minutes": 5,
        CONF_LOCAL_IP: "192.168.1.50",
        "external_temperature_remo-2": "sensor.balcony_temp",
        "external_humidity_remo-2": "sensor.balcony_humidity",
    }
    assert entry.options == result["data"]
