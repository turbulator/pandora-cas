"""
TODO

DETAILS
"""
import logging

from homeassistant.components.sensor import ENTITY_ID_FORMAT, DEVICE_CLASS_TEMPERATURE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ICON, ATTR_NAME, LENGTH_KILOMETERS, PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify

from .api import PandoraDevice
from .base import PandoraEntity
from .const import DOMAIN, ATTR_DEVICE_ATTR, ATTR_IS_CONNECTION_SENSITIVE, ATTR_UNITS, ATTR_FORMATTER


_LOGGER = logging.getLogger(__name__)


ENTITY_CONFIGS = {
    "mileage": {
        ATTR_NAME: "mileage",
        ATTR_ICON: "mdi:map-marker-distance",
        ATTR_DEVICE_CLASS: None,  # TODO: Make propper device class
        ATTR_UNITS: LENGTH_KILOMETERS,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "mileage",
        ATTR_FORMATTER: lambda v: round(float(v), 2),
    },
    "fuel_level": {
        ATTR_NAME: "fuel",
        ATTR_ICON: "mdi:gauge",
        ATTR_DEVICE_CLASS: None,
        ATTR_UNITS: PERCENTAGE,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "fuel",
    },
    "cabin_temperature": {
        ATTR_NAME: "cabin temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_UNITS: TEMP_CELSIUS,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "cabin_temp",
    },
    "engine_temperature": {
        ATTR_NAME: "Engine temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_UNITS: TEMP_CELSIUS,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "engine_temp",
    },
    "ambient_temperature": {
        ATTR_NAME: "Ambient temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_UNITS: TEMP_CELSIUS,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "out_temp",
    },
    "balance": {
        ATTR_NAME: "balance",
        ATTR_ICON: "mdi:cash",
        ATTR_DEVICE_CLASS: None,
        ATTR_UNITS: "₽",
        ATTR_IS_CONNECTION_SENSITIVE: False,
        ATTR_DEVICE_ATTR: "balance",
        ATTR_FORMATTER: lambda v: round(float(v["value"]), 2),
    },
    "speed": {
        ATTR_NAME: "speed",
        ATTR_ICON: "mdi:gauge",
        ATTR_DEVICE_CLASS: None,
        ATTR_UNITS: "km/h",
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "speed",
        ATTR_FORMATTER: lambda v: round(float(v), 1),
    },
    "engine_rpm": {
        ATTR_NAME: "engine RPM",
        ATTR_ICON: "mdi:gauge",
        ATTR_DEVICE_CLASS: None,
        ATTR_UNITS: None,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "engine_rpm",
    },
    "gsm_level": {
        ATTR_NAME: "GSM level",
        ATTR_ICON: "mdi:network-strength-2",
        ATTR_DEVICE_CLASS: None,
        ATTR_UNITS: None,
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "gsm_level",
    },
    "battery_voltage": {
        ATTR_NAME: "battery",
        ATTR_ICON: "mdi:car-battery",
        ATTR_DEVICE_CLASS: None,
        ATTR_UNITS: "V",
        ATTR_IS_CONNECTION_SENSITIVE: True,
        ATTR_DEVICE_ATTR: "voltage",
    },
}


# pylint: disable=unused-argument
async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry, async_add_entities):
    """Set up ecobee binary (occupancy) sensors."""

    api = hass.data[DOMAIN]

    sensors = []
    for _, device in api.devices.items():
        for entity_id, entity_config in ENTITY_CONFIGS.items():
            sensors.append(PandoraSensorEntity(hass, device, entity_id, entity_config))

    async_add_entities(sensors, False)


class PandoraSensorEntity(PandoraEntity):
    """Representation of a BMW vehicle sensor."""

    ENTITY_ID_FORMAT = ENTITY_ID_FORMAT

    def __init__(
        self, hass, device: PandoraDevice, entity_id: str, entity_config: dict,
    ):
        """Constructor."""
        super().__init__(hass, device, entity_id, entity_config)

        self.entity_id = self.ENTITY_ID_FORMAT.format("{}_{}".format(slugify(device.pandora_id), entity_id))

        user_defined_units = device.user_defined_units(self.device_attr)
        if user_defined_units is not None:
            self._config[ATTR_UNITS] = user_defined_units

    @property
    def icon(self) -> str:
        """Return the icon of the binary sensor."""

        icon = self._config[ATTR_ICON]
        if isinstance(icon, dict):
            return icon[self._state]

        return icon

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        return self._config[ATTR_UNITS]

    @property
    def state(self):
        """"""
        return self._state

    @callback
    def _update_callback(self, force=False):
        """"""
        try:
            state = None
            if self._device.is_online or not self.is_connection_sensitive:
                state = getattr(self._device, self.device_attr)
                formatter = self._config.get(ATTR_FORMATTER)
                state = formatter(state) if formatter else state
                available = True
            else:
                available = False

            if self._state != state or self._available != available:
                self._state = state
                self._available = available
                self.async_write_ha_state()
        except KeyError:
            _LOGGER.warning("%s: can't get data from linked device", self.name)

    async def async_added_to_hass(self):
        """When entity is added to hass."""

        self.async_on_remove(self._hass.data[DOMAIN].async_add_listener(self._update_callback))
        self._update_callback(True)
