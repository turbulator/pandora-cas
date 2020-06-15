"""Models state and remote services of one vehicle."""
from enum import Enum
import logging
from typing import List

from .state import VehicleState
from .remote_services import RemoteServices


_LOGGER = logging.getLogger(__name__)


class PandoraOnlineVehicle:
    """Models state and remote services of one vehicle.

    :param account: ConnectedDrive account this vehicle belongs to
    :param attributes: attributes of the vehicle as provided by the server
    """

    def __init__(self, account, attributes: dict) -> None:
        self._account = account
        self._attributes = attributes
        self.state = VehicleState(account, self)
        self.remote_services = RemoteServices(account, self)
        _LOGGER.error('New vehicle id ' + str(attributes['id']))


    def update_state(self, attributes: dict) -> None:
        """Update the state of a vehicle."""
        _LOGGER.debug('Vehicle id ' + str(self.id) + ' update state')
        self.state.update_data(attributes)


    @property
    def name(self) -> str:
        """Get the name of the vehicle."""
        return self._attributes['name']


    def __getattr__(self, item):
        """In the first version: just get the attributes from the dict.

        In a later version we might parse the attributes to provide a more advanced API.
        :param item: item to get, as defined in VEHICLE_ATTRIBUTES
        """
        return self._attributes.get(item)


    def __str__(self) -> str:
        """Use the name as identifier for the vehicle."""
        return '{}: {}'.format(self.__class__, self.name)
