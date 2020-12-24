"""
TODO

DETAILS
"""
import logging

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_DOOR,
    ENTITY_ID_FORMAT,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ICON, ATTR_NAME
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify

from .api import PandoraDevice
from .base import PandoraEntity
from .const import DOMAIN, ATTR_DEVICE_ATTR, ATTR_INVERSE, ATTR_IS_CONNECTION_SENSITIVE, ATTR_SHIFT_BITS


_LOGGER = logging.getLogger(__name__)


ENTITY_CONFIGS = {
    "connection_state": {
        ATTR_NAME: "connection",
        ATTR_ICON: None,
        ATTR_DEVICE_CLASS: DEVICE_CLASS_CONNECTIVITY,
        ATTR_IS_CONNECTION_SENSITIVE: False,
        ATTR_DEVICE_ATTR: "online",
        ATTR_SHIFT_BITS: 0,
        ATTR_INVERSE: 0,
    },
    "engine_state": {
        ATTR_NAME: "engine",
        ATTR_ICON: {True: "mdi:fan", False: "mdi:fan-off"},
        ATTR_DEVICE_CLASS: "pandora_cas__engine",
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 2,
        ATTR_INVERSE: 0,
    },
    "moving": {
        ATTR_NAME: "moving",
        ATTR_ICON: None,
        ATTR_DEVICE_CLASS: "pandora_cas__moving",
        ATTR_DEVICE_ATTR: "move",
        ATTR_SHIFT_BITS: 0,
        ATTR_INVERSE: 0,
    },
    "lock": {
        ATTR_NAME: "guard",
        ATTR_ICON: {True: "mdi:shield-off", False: "mdi:shield-check"},
        ATTR_DEVICE_CLASS: "pandora_cas__guard",
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 0,
        ATTR_INVERSE: 1,
    },
    "left_front_door": {
        ATTR_NAME: "front left door",
        ATTR_ICON: "mdi:car-door",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_DOOR,
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 21,
        ATTR_INVERSE: 0,
    },
    "right_front_door": {
        ATTR_NAME: "front right door",
        ATTR_ICON: "mdi:car-door",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_DOOR,
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 22,
        ATTR_INVERSE: 0,
    },
    "left_back_door": {
        ATTR_NAME: "back left door",
        ATTR_ICON: "mdi:car-door",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_DOOR,
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 23,
        ATTR_INVERSE: 0,
    },
    "right_back_door": {
        ATTR_NAME: "back right door",
        ATTR_ICON: "mdi:car-door",
        ATTR_DEVICE_CLASS: DEVICE_CLASS_DOOR,
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 24,
        ATTR_INVERSE: 0,
    },
    "trunk": {
        ATTR_NAME: "trunk",
        ATTR_ICON: "mdi:car-back",
        ATTR_DEVICE_CLASS: "pandora_cas__door_male",
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 25,
        ATTR_INVERSE: 0,
    },
    "hood": {
        ATTR_NAME: "hood",
        ATTR_ICON: "mdi:car",
        ATTR_DEVICE_CLASS: "pandora_cas__door_male",
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 26,
        ATTR_INVERSE: 0,
    },
    "coolant_heater": {
        ATTR_NAME: "coolant heater",
        ATTR_ICON: {True: "mdi:thermometer-plus", False: "mdi:thermometer"},
        ATTR_DEVICE_CLASS: None,
        ATTR_DEVICE_ATTR: "bit_state_1",
        ATTR_SHIFT_BITS: 29,
        ATTR_INVERSE: 0,
    },
}


# pylint: disable=unused-argument
async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry, async_add_entities):
    """"""

    api = hass.data[DOMAIN]

    binary_sensors = []
    for _, device in api.devices.items():
        for entity_id, entity_config in ENTITY_CONFIGS.items():
            binary_sensors.append(PandoraBinarySensorEntity(hass, device, entity_id, entity_config))

    async_add_entities(binary_sensors, False)


class PandoraBinarySensorEntity(PandoraEntity, BinarySensorEntity):
    """"""

    ENTITY_ID_FORMAT = ENTITY_ID_FORMAT

    def __init__(
        self, hass, device: PandoraDevice, entity_id: str, entity_config: dict,
    ):
        """Constructor."""
        super().__init__(hass, device, entity_id, entity_config)

        self._state = False
        self.entity_id = self.ENTITY_ID_FORMAT.format("{}_{}".format(slugify(device.pandora_id), entity_id))

    @property
    def icon(self) -> str:
        """Return the icon of the binary sensor."""

        icon = self._config[ATTR_ICON]
        if isinstance(icon, dict):
            return icon[self._state]

        return icon

    @property
    def shift_bits(self) -> int:
        """Return the name of the binary sensor."""
        return self._config[ATTR_SHIFT_BITS]

    @property
    def inverse(self) -> int:
        """Return the name of the binary sensor."""
        return self._config[ATTR_INVERSE]

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return self._state

    # pylint: disable=attribute-defined-outside-init
    @callback
    def _update_callback(self, force=False):
        """"""
        api = self._hass.data[DOMAIN]
        try:
            if (int(getattr(self._device, self.device_attr)) >> self.shift_bits) & 1 ^ self.inverse:
                state = True
            else:
                state = False

            if self.is_connection_sensitive:
                expired = api.timestamp - self._device.timestamp > self._device.expire_after
            else:
                expired = False

            if self._state != state or self._expired != expired:
                self._state = state
                self._expired = expired
                self.async_write_ha_state()
        except KeyError:
            _LOGGER.warning("%s: can't get data from linked device", self.name)

    async def async_added_to_hass(self):
        """When entity is added to hass."""

        self.async_on_remove(self._hass.data[DOMAIN].async_add_listener(self._update_callback))
        self._update_callback(True)
