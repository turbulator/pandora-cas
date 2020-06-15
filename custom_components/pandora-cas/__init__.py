"""
Reads vehicle status from BMW connected drive portal.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/bmw_connected_drive/
"""
import logging
from datetime import datetime, timedelta

import voluptuous as vol

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD)
from homeassistant.helpers import discovery
from homeassistant.helpers.event import track_time_interval
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = []

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'pandora-cas'
CONF_POLLING_INTERVAL = 'polling_interval'
MIN_POLLING_INTERVAL = timedelta(seconds = 10)
DEFAULT_POLLING_INTERVAL = timedelta(minutes = 1)
CONF_READ_ONLY = 'read_only'
ATTR_ID = 'id'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_POLLING_INTERVAL, default = DEFAULT_POLLING_INTERVAL): (
                            vol.All(cv.time_period, vol.Clamp(min = MIN_POLLING_INTERVAL))
                       ),
    }),
}, extra=vol.ALLOW_EXTRA)

SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ID): cv.string,
})


PANDORA_COMPONENTS = ['device_tracker', 'binary_sensor', 'sensor']

SERVICE_UPDATE_STATE = 'update_state'


_SERVICE_MAP = {
    'lock': 'trigger_remote_lock',
    'unlock': 'trigger_remote_unlock',
    'start_engine': 'trigger_remote_start_engine',
    'stop_engine': 'trigger_remote_stop_engine',
    'turn_on_coolant_heater': 'trigger_remote_turn_on_coolant_heater',
    'turn_off_coolant_heater': 'trigger_remote_turn_off_coolant_heater',
    'turn_on_ext_channel': 'trigger_remote_turn_on_ext_channel',
    'turn_off_ext_channel': 'trigger_remote_turn_off_ext_channel',
}

def setup(hass, config: dict):
    """Set up the BMW connected drive components."""

    hass.data[DOMAIN] = setup_account(config[DOMAIN], hass)

    def _update_all(call) -> None:
        """Update all pandora accounts."""
        hass.data[DOMAIN].update()

    # Service to manually trigger updates for all accounts.
    hass.services.register(DOMAIN, SERVICE_UPDATE_STATE, _update_all)

    _update_all(None)

    for component in PANDORA_COMPONENTS:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True


def setup_account(account_config: dict, hass) \
        -> 'PandoraOnlineAccount':
    """Set up a new BMWConnectedDriveAccount based on the config."""
    username = account_config[CONF_USERNAME]
    password = account_config[CONF_PASSWORD]
    polling_interval = account_config[CONF_POLLING_INTERVAL]

    po_account = PandoraOnlineAccount(username, password)

    def execute_service(call):
        """Execute a service for a vehicle.

        This must be a member function as we need access to the cd_account
        object here.
        """
        id = call.data[ATTR_ID]
        vehicle = po_account.account.get_vehicle(id)
        if not vehicle:
            _LOGGER.error('Could not find a vehicle for id "%s"!', id)
            return
        function_name = _SERVICE_MAP[call.service]
        function_call = getattr(vehicle.remote_services, function_name)
        function_call()

    # register the remote services
    for service in _SERVICE_MAP:
        hass.services.register(
            DOMAIN, service,
            execute_service,
            schema=SERVICE_SCHEMA)

    track_time_interval(hass, po_account.update, polling_interval)

    return po_account


class PandoraOnlineAccount:
    """Representation of a Pandora Online vehicle."""

    def __init__(self, username: str, password: str) -> None:
        """Constructor."""
        from .api.account import PandoraOnlineAccount

        self.account = PandoraOnlineAccount(username, password)
        self._update_listeners = []

    def update(self, *_):
        """Update the state of all vehicles.

        Notify all listeners about the update.
        """
        _LOGGER.debug('Updating vehicle state, notifying %d listeners',
                      len(self._update_listeners))
        try:
            self.account.update_vehicle_states()
            for listener in self._update_listeners:
                listener()
        except IOError as exception:
            _LOGGER.error('Error updating the vehicle state.')
            _LOGGER.exception(exception)

    def add_update_listener(self, listener):
        """Add a listener for update notifications."""
        self._update_listeners.append(listener)
