"""Library to read data from the BMW Connected Drive portal.

The library bimmer_connected provides a Python interface to interact
with the BMW Connected Drive web service. It allows you to read
the current state of the vehicle and also trigger remote services.

Disclaimer:
This library is not affiliated with or endorsed by BMW Group.
"""

import datetime
import logging
import urllib
import os
import json
from threading import Lock
from typing import Callable, List
import requests

from .vehicle import PandoraOnlineVehicle

_LOGGER = logging.getLogger(__name__)


class PandoraOnlineAccount:  # pylint: disable=too-many-instance-attributes
    """Create a new connection to the BMW Connected Drive web service.

    :param username: Connected drive user name
    :param password: Connected drive password
    :param country: Country for which the account was created. For a list of valid countries,
                check https://www.bmw-connecteddrive.com .
                Use the name of the countries exactly as on the website.
    :param log_responses: If log_responses is set, all responses from the server will
                be loged into this directory. This can be used for later analysis of the different
                responses for different vehicles.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, username: str, password: str) -> None:
        self._session = None
        self._last_code = 0
        self._num_click = 0
        self._username = username
        self._password = password
        self._headers = {
            'Host': 'p-on.ru',
            'Connection': 'keep-alive',
            'Origin': 'https://p-on.ru',
            'Referer': 'https://p-on.ru/login',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Compress': 'null',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
        }
        #: list of vehicles associated with this account.
        self._vehicles = []
        self._lock = Lock()
        self._update_listeners = []

        self._get_vehicles()

    def send_request(self, url: str, data=None, headers=None, cookies=None, expected_response=200, post=False, tolerant=None):
        """Send an http request to the server.

        If the http headers are not set, default headers are generated.
        You can choose if you want a GET or POST request.
        """
        if self._session is None:
            self._session = requests.Session()

        if headers is None:
            headers = self._headers

        if post:
            response = self._session.post(url, headers = headers, data = data, cookies = cookies)
        else:
            response = self._session.get(url, headers = headers, data = data, cookies = cookies)


        if response.status_code != expected_response:
            msg = 'Unknown status code {}, expected {}'.format(response.status_code, expected_response)
            _LOGGER.error(msg)
            _LOGGER.error(response.text)

            if tolerant is not None:
                self._last_code = response.status_code
                raise IOError(msg)

        return response


    def _login(self) -> None:

        data = {
            'login': self._username,
            'password': self._password,
            'lang': 'ru'
            }

        cookies = {
            'lang': 'ru'
            }

        self.send_request('https://p-on.ru/api/users/login',
                                data=data, cookies=cookies, post=True)

        _LOGGER.error('Login successful')


    def _get_vehicles(self):
        """Retrieve list of vehicle for the account."""
        _LOGGER.error('Getting vehicle list from server')

        if self._last_code != 200:
            self._login()

        response = self.send_request('https://p-on.ru/api/devices')

        for vehicle in response.json():
            self._vehicles.append(PandoraOnlineVehicle(self, vehicle))

    @property
    def vehicles(self) -> List[PandoraOnlineVehicle]:
        """Get list of vehicle of this account"""
        return self._vehicles


    def get_vehicle(self, id: str) -> PandoraOnlineVehicle:
        """Get vehicle with given id.

        The search is NOT case sensitive.
        :param id: id of the vehicle you want to get.
        :return: Returns None if no such vehicle is found.
        """
        for car in self.vehicles:
            if str(car.id).upper() == id.upper():
                return car
        return None


    def update_vehicle_states(self) -> None:
        """Update the state of all vehicles.

        Notify all listeners of the vehicle state update.
        """

        _LOGGER.debug('Update vehicles states')

        if self._last_code != 200:
            self._login()

        response = self._session.get(
                'https://p-on.ru/api/updates?ts=-1',
                headers = self._headers,
            )

        self._last_code = response.status_code
        if self._last_code != 200:
            msg = 'Unknown status code {}, expected {}'.format(self._last_code, 200)
            _LOGGER.error(msg)
            _LOGGER.error(response.text)
            raise IOError(msg)

        stats = response.json()['stats']

        for vehicle in self.vehicles:
            vehicle.update_state(stats[str(vehicle.id)])

        for listener in self._update_listeners:
            listener()


    def add_update_listener(self, listener: Callable) -> None:
        """Add a listener for state updates."""
        self._update_listeners.append(listener)

    def __str__(self):
        """Use the user name as id for the account class."""
        return '{}: {}'.format(self.__class__, self._username)
