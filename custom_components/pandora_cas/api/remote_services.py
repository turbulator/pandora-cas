"""Trigger remote services on a vehicle."""

from enum import Enum
import datetime
import logging
import time
import requests


_LOGGER = logging.getLogger(__name__)

#: time in seconds to wait before updating the vehicle state from the server
_UPDATE_AFTER_REMOTE_SERVICE_DELAY = 10



class _Services(Enum):
    """Enumeration of possible services to be executed."""
    REMOTE_LOCK = "1"
    REMOTE_UNLOCK = "2"
    REMOTE_START_ENGINE = "4"
    REMOTE_STOP_ENGINE = "8"
    REMOTE_TURN_ON_COOLANT_HEATER = "21"
    REMOTE_TURN_OFF_COOLANT_HEATER = "22"
    REMOTE_TURN_ON_EXT_CHANNEL = "33"
    REMOTE_TURN_OFF_EXT_CHANNEL = "34"


class RemoteServiceStatus:  # pylint: disable=too-few-public-methods
    """Wraps the status of the execution of a remote service."""

    def __init__(self, response: dict):
        """Construct a new object from a dict."""
        status = response['executionStatus']
        self.state = ExecutionState(status['status'])
        self.event_id = status['eventId']


class RemoteServices:
    """Trigger remote services on a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle


    def trigger_remote_seat_heater(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_SEAT_HEATER)
        self._trigger_state_update()
        return result


    def trigger_remote_lock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_LOCK)
        self._trigger_state_update()
        return result



    def trigger_remote_unlock(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_UNLOCK)
        self._trigger_state_update()
        return result


    def trigger_remote_start_engine(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_START_ENGINE)
        self._trigger_state_update()
        return result


    def trigger_remote_stop_engine(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_STOP_ENGINE)
        self._trigger_state_update()
        return result


    def trigger_remote_turn_on_coolant_heater(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote coolant heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_TURN_ON_COOLANT_HEATER)
        self._trigger_state_update()
        return result


    def trigger_remote_turn_off_coolant_heater(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote coolant heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_TURN_OFF_COOLANT_HEATER)
        self._trigger_state_update()
        return result


    def trigger_remote_turn_on_ext_channel(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_TURN_ON_EXT_CHANNEL)
        self._trigger_state_update()
        return result


    def trigger_remote_turn_off_ext_channel(self) -> RemoteServiceStatus:
        """Trigger the vehicle to sound its horn.

        A state update is NOT triggered after this, as the vehicle state is unchanged.
        """
        _LOGGER.debug('Triggering remote seat heater')
        # needs to be called via POST, GET is not working
        result = self._trigger_remote_service(_Services.REMOTE_TURN_OFF_EXT_CHANNEL)
        self._trigger_state_update()
        return result


    def _trigger_remote_service(self, service_id: _Services) -> requests.Response:
        """Trigger a generic remote service.

        You can choose if you want a POST or a GET operation.
        """
        data = {
            'id': self._vehicle.id,
            'command': service_id.value }

        response = self._account.send_request('https://p-on.ru/api/devices/command', data=data, post=True, tolerant=True)

        return response


    def _trigger_state_update(self) -> None:
        time.sleep(_UPDATE_AFTER_REMOTE_SERVICE_DELAY)
        self._account.update_vehicle_states()
