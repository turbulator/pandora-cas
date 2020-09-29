"""
TODO

DETAILS
"""
import logging

from homeassistant.components.device_tracker import DOMAIN as PLATFORM_DOMAIN, SOURCE_TYPE_GPS
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import slugify
from homeassistant.core import callback

from .api import PandoraDevice
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)

# pylint: disable=unused-argument
async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities):
    """Set up the tracker."""

    api = hass.data[DOMAIN]

    trackers = []
    for _, device in api.devices.items():
        trackers.append(PandoraTrackerEntity(hass, device))

    async_add_entities(trackers, False)


class PandoraTrackerEntity(TrackerEntity):
    """"""

    def __init__(self, hass: HomeAssistantType, device: PandoraDevice):
        self._hass = hass
        self._device = device
        self._latitude = None
        self._longitude = None

        self.entity_id = "{}.{}".format(PLATFORM_DOMAIN, slugify(device.pandora_id))

    @property
    def unique_id(self) -> str:
        """Return the entity_id of the binary sensor."""
        return "{}_{}".format(PLATFORM_DOMAIN, slugify(self._device.pandora_id))

    @property
    def name(self) -> str:
        """Return device name for this tracker entity."""
        return self._device.name

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return self._longitude

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:car"

    @property
    def should_poll(self):
        """No polling for entities that have location pushed."""
        return False

    @callback
    def _update_callback(self, force=False):
        """"""
        if self._latitude != self._device.x or self._longitude != self._device.y:
            self._latitude = self._device.x
            self._longitude = self._device.y
            self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(self._hass.data[DOMAIN].async_add_listener(self._update_callback))
        self._update_callback(True)
