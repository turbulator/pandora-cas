"""
TODO

DETAILS
"""
import logging

from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .api import PandoraDevice
from .const import DOMAIN, ATTR_DEVICE_ATTR, ATTR_IS_CONNECTION_SENSITIVE


_LOGGER = logging.getLogger(__name__)


class PandoraEntity(Entity):
    """ TODO """

    ENTITY_ID_FORMAT: str = NotImplemented

    def __init__(
        self, hass, device: PandoraDevice, entity_id: str, entity_config: dict,
    ):
        """Constructor."""
        self._hass = hass
        self._device = device
        self._id = entity_id
        self._config = entity_config
        self._state = None
        self._expired = True

    @property
    def unique_id(self) -> str:
        """Return the entity_id of the binary sensor."""
        return "{}_{}_{}".format(DOMAIN, slugify(self._device.pandora_id), self._id)

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return "{} {}".format(self._device.name, self._config[ATTR_NAME])

    @property
    def is_connection_sensitive(self) -> bool:
        """Return the name of the binary sensor."""
        return self._config.get(ATTR_IS_CONNECTION_SENSITIVE, True)

    @property
    def device_attr(self) -> str:
        """Return the name of the binary sensor."""
        return self._config[ATTR_DEVICE_ATTR]

    @property
    def device_class(self) -> str:
        """Return the class of the binary sensor."""
        return self._config[ATTR_DEVICE_CLASS]

    @property
    def available(self):
        """Return True if entity is available.

        It will be True in three cases:
            - Entiny isn't sensitive to connection status. Like balance
            - Selected "never expire" option
            - Entity was updated recently and wasn't expired
        """
        return self.is_connection_sensitive is False or self._device.expire_after == 0 or not self._expired

    @property
    def should_poll(self) -> bool:
        """Return False."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {"car": self._device.name}

    @property
    def device_info(self):
        """Unified device info dictionary."""
        return self._device.device_info
