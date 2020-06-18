"""Models the state of a vehicle."""

import datetime
import logging
from enum import Enum
from typing import List


_LOGGER = logging.getLogger(__name__)


class VehicleState:  # pylint: disable=too-many-public-methods
    """Models the state of a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle
        self._attributes = None


    def update_data(self, attributes: dict) -> None:
        """Read new status data from the server."""

        self._attributes = attributes
        _LOGGER.debug('received new data from connected drive')


    @property
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._attributes


    @property
    def gps_position(self) -> (float, float):
        """Get the last known position of the vehicle.

        Returns a tuple of (latitue, longitude).
        This only provides data, if the vehicle tracking is enabled!
        """
        return float(self._attributes['x']), float(self._attributes['y'])

    @property
    def mileage(self) -> float:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return round(float(self._attributes['mileage']), 1)

    @property
    def fuel(self) -> int:
        """Get the remaining fuel of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._attributes['fuel'])

    @property
    def cabin_temp(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._attributes['cabin_temp'])

    @property
    def engine_temp(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._attributes['engine_temp'])

    @property
    def out_temp(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._attributes['out_temp'])

    @property
    def balance(self) -> float:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return round(float(self._attributes['balance']['value']), 2)

    @property
    def speed(self) -> float:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return round(float(self._attributes['speed']), 1)

    @property
    def engine_rpm(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._attributes['engine_rpm'])

    @property
    def gsm_level(self) -> int:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return int(self._attributes['gsm_level'])

    @property
    def battery(self) -> float:
        """Get the mileage of the vehicle.

        Returns a tuple of (value, unit_of_measurement)
        """
        return round(float(self._attributes['voltage']), 1)

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._attributes[item]

