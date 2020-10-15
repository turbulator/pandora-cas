"""
TODO

DETAILS
"""
from collections import OrderedDict
import logging
from typing import Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import CONN_CLASS_CLOUD_POLL
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, PERCENTAGE
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
    MILEAGE_SOURCES,
    OPTION_FUEL_UNITS,
    OPTION_MILEAGE_SOURCE,
    OPTION_MILEAGE_ADJUSTMENT,
    FUEL_UNITS,
)

_LOGGER = logging.getLogger(__name__)

PANDORA_ID = "pandora_id"

FLOW_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str, vol.Optional(CONF_POLLING_INTERVAL,): int,}
)


def _base_schema(discovery_info=None):
    """Generate base schema."""
    base_schema = {}

    if discovery_info:
        base_schema.update(
            {
                vol.Required(CONF_USERNAME, description={"suggested_value": discovery_info[CONF_USERNAME]}): str,
                vol.Required(CONF_PASSWORD, description={"suggested_value": discovery_info[CONF_PASSWORD]}): str,
                vol.Required(
                    CONF_POLLING_INTERVAL, description={"suggested_value": discovery_info[CONF_POLLING_INTERVAL]}
                ): int,
            }
        )
    else:
        base_schema.update(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(
                    CONF_POLLING_INTERVAL, description={"suggested_value": DEFAULT_POLLING_INTERVAL.total_seconds()},
                ): int,
            }
        )

    return vol.Schema(base_schema)


# pylint: disable=fixme
async def validate_input(user_input: Optional[ConfigType] = None):
    """ TODO """

    # TODO: Check username/password here

    if user_input[CONF_POLLING_INTERVAL] < MIN_POLLING_INTERVAL.total_seconds():
        raise ValueError


@config_entries.HANDLERS.register("pandora_cas")
class PandoraCasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pandora CAS"""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self.data_schema = {}

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: Optional[ConfigType] = None):
        errors = {}

        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            try:
                await validate_input(user_input)
            except ValueError:
                errors["base"] = "invalid_polling_interval"

            if "base" not in errors:
                username = user_input[CONF_USERNAME]
                return self.async_create_entry(title=username, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_base_schema(), errors=errors)

    async def async_step_discovery(self, discovery_info):
        """Handle discovery."""

        self.data_schema = _base_schema(discovery_info)

        # Check if already configured
        await self.async_set_unique_id(discovery_info[CONF_USERNAME])
        self._abort_if_unique_id_configured()

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input: Optional[ConfigType] = None):
        """Confirm discovery."""
        errors = {}

        if user_input is not None:
            try:
                await validate_input(user_input)
            except ValueError:
                errors["base"] = "invalid_polling_interval"

            if "base" not in errors:
                username = user_input[CONF_USERNAME]
                return self.async_create_entry(title=username, data=user_input)

        return self.async_show_form(step_id="discovery_confirm", data_schema=self.data_schema, errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.pandora_id = None

    async def async_step_init(self, user_input=None):
        return await self.async_step_device()

    async def async_step_device(self, user_input=None):
        IDS = []
        api = self.hass.data[DOMAIN]

        if user_input is not None:
            self.pandora_id = user_input[PANDORA_ID]
            return await self.async_step_options()

        for pandora_id in api.devices.keys():
            IDS.append(pandora_id)

        fields = OrderedDict()
        fields[vol.Required(PANDORA_ID, default=IDS[0])] = vol.In(IDS)

        return self.async_show_form(step_id="device", data_schema=vol.Schema(fields))

    async def async_step_options(self, user_input=None):
        """Manage the options."""
        api = self.hass.data[DOMAIN]
        device_options = {}

        if user_input is not None:
            device_options[self.pandora_id] = {}
            device_options[self.pandora_id][OPTION_FUEL_UNITS] = user_input.get(OPTION_FUEL_UNITS, FUEL_UNITS[0])
            device_options[self.pandora_id][OPTION_MILEAGE_SOURCE] = user_input.get(
                OPTION_MILEAGE_SOURCE, MILEAGE_SOURCES[0]
            )
            device_options[self.pandora_id][OPTION_MILEAGE_ADJUSTMENT] = user_input.get(OPTION_MILEAGE_ADJUSTMENT, 0)
            self.options.update(device_options)
            self.pandora_id = None  # invalidate pandora_id
            return self.async_create_entry(title="", data=self.options)

        fields = OrderedDict()
        device_options = self.options.get(self.pandora_id)
        if device_options is None:
            fields[vol.Optional(OPTION_FUEL_UNITS, default=FUEL_UNITS[0])] = vol.In(FUEL_UNITS)
            fields[vol.Optional(OPTION_MILEAGE_SOURCE, default=MILEAGE_SOURCES[0])] = vol.In(MILEAGE_SOURCES)
            fields[vol.Optional(OPTION_MILEAGE_ADJUSTMENT, default=0)] = vol.Coerce(int)
        else:
            fields[
                vol.Optional(OPTION_FUEL_UNITS, default=device_options.get(OPTION_FUEL_UNITS, FUEL_UNITS[0]))
            ] = vol.In(FUEL_UNITS)
            fields[
                vol.Optional(
                    OPTION_MILEAGE_SOURCE, default=device_options.get(OPTION_MILEAGE_SOURCE, MILEAGE_SOURCES[0])
                )
            ] = vol.In(MILEAGE_SOURCES)
            fields[
                vol.Optional(OPTION_MILEAGE_ADJUSTMENT, default=device_options.get(OPTION_MILEAGE_ADJUSTMENT, 0))
            ] = vol.Coerce(int)

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(fields),
            description_placeholders={"name": api.devices[self.pandora_id].name},
        )
