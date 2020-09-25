"""
TODO

DETAILS
"""
import asyncio
import logging
import sys

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import discovery
from homeassistant.helpers.event import async_track_time_interval, track_time_interval
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PandoraApi, PandoraApiException
from .const import (
    DOMAIN,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
    ATTR_SCHEMA,
    ATTR_ID,
    ATTR_COMMAND,
)


_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL): (
                    vol.All(cv.time_period, vol.Clamp(min=MIN_POLLING_INTERVAL))
                ),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SCHEMA = vol.Schema({vol.Required(ATTR_ID): cv.string,})

SERVICE_MAP = {
    "lock": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "1"},
    "unlock": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "2"},
    "start_engine": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "4"},
    "stop_engine": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "8"},
    "turn_on_coolant_heater": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "21"},
    "turn_off_coolant_heater": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "22"},
    "turn_on_ext_channel": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "33"},
    "turn_off_ext_channel": {ATTR_SCHEMA: SERVICE_SCHEMA, ATTR_COMMAND: "34"},
}


PANDORA_CAS_PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Activate Pandora Car Alarm System component"""

    hass.data[DOMAIN] = {}
    if DOMAIN not in config:
        return True

    try:
        domain_config = config.get(DOMAIN, {})

        # Convert timedelta to seconds
        seconds = domain_config[CONF_POLLING_INTERVAL].total_seconds()
        domain_config.pop(CONF_POLLING_INTERVAL, None)
        domain_config[CONF_POLLING_INTERVAL] = seconds

        if not hass.config_entries.async_entries(DOMAIN):
            hass.async_create_task(
                hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_DISCOVERY}, data=domain_config)
            )
        else:
            _LOGGER.warning("You have to remove obsolete %s section from configuration.yaml", DOMAIN)
    except KeyError:
        _LOGGER.warning("Import %s failed", DOMAIN)

    return True


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry) -> bool:
    """Setup configuration entry for Pandora Car Alarm System."""

    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    polling_interval = config_entry.data[CONF_POLLING_INTERVAL]

    _LOGGER.debug("Setting up entry %s for account %s", config_entry.entry_id, username)

    async def _execute_command(call) -> bool:
        api = hass.data[DOMAIN]
        if api is not None:
            return await api.async_command(call.data[ATTR_ID], SERVICE_MAP[call.service][ATTR_COMMAND])

    for service, service_config in SERVICE_MAP.items():
        hass.services.async_register(DOMAIN, service, _execute_command, schema=service_config[ATTR_SCHEMA])

    try:
        api = hass.data[DOMAIN] = PandoraApi(hass, username, password, polling_interval)
        await api.load_devices()
        await api.async_refresh()
    except PandoraApiException as ex:
        _LOGGER.error("Setting up entry %s failed: %s", username, str(ex))
        return False

    for platform in PANDORA_CAS_PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(config_entry, platform))

    return True


async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigEntry) -> bool:
    """Unload the config entry and platforms."""
    hass.data.pop(DOMAIN)

    tasks = []
    for platform in PANDORA_CAS_PLATFORMS:
        tasks.append(hass.config_entries.async_forward_entry_unload(config_entry, platform))

    return all(await asyncio.gather(*tasks))
