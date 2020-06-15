"""Device tracker for BMW Connected Drive vehicles.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.bmw_connected_drive/
"""
import logging

from . import DOMAIN as PANDORA_DOMAIN
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)


def setup_scanner(hass, config, see, discovery_info=None):
    """Set up the BMW tracker."""
    account = hass.data[PANDORA_DOMAIN]

    for vehicle in account.account.vehicles:
        tracker = PandoraTracker(see, vehicle)
        account.add_update_listener(tracker.update)
        tracker.update()
    return True


class PandoraTracker:
    """BMW Connected Drive device tracker."""

    def __init__(self, see, vehicle):
        """Initialize the Tracker."""
        self._see = see
        self.vehicle = vehicle

    def update(self) -> None:
        """Update the device info.

        Only update the state in home assistant if tracking in
        the car is enabled.
        """
        dev_id = slugify(str(self.vehicle.id))

        _LOGGER.debug('Updating %s', dev_id)
        attrs = {
            'voltage': self.vehicle.state.voltage,
            'gsm_level': self.vehicle.state.gsm_level,
        }

        self._see(
            dev_id=dev_id, host_name=self.vehicle.name,
            gps=self.vehicle.state.gps_position, attributes=attrs,
            icon='mdi:car'
        )
