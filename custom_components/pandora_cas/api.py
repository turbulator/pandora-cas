"""Pandora Car Alarm System API."""
import logging
from datetime import timedelta
from json import JSONDecodeError
from typing import Callable

import aiohttp
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import utcnow

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


HOST = "p-on.ru"
BASE_URL = "https://" + HOST
LOGIN_PATH = "/api/users/login"
DEVICES_PATH = "/api/devices"
UPDATE_PATH = "/api/updates?ts=-1"
COMMAND_PATH = "/api/devices/command"


USER_AGENT = "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0"


class PandoraApiException(Exception):
    """An exception class of Pandora API."""


class PandoraApi:
    """Pandora API class."""

    def __init__(self, hass: HomeAssistantType, username: str, password: str, polling_interval: int) -> None:
        """Constructor"""
        self._hass = hass
        self._username = username
        self._password = password
        self._session = None
        self._session_id = None
        self._devices = {}
        self._coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
            update_method=self._async_update,
        )

    @property
    def devices(self) -> dict:
        """Accessor"""

        return self._devices

    async def _request(self, path, data=None, method="GET"):
        """Request an information from server."""

        url = BASE_URL + path
        headers = {"User-Agent": USER_AGENT}

        try:
            async with self._session.request(method, url, data=data, headers=headers) as response:
                _LOGGER.debug("Response HTTP Status Code: %d", response.status)
                _LOGGER.debug("Response HTTP Response Body: %s", await response.text())

                # Responses should be JSON
                j = await response.json()

                # We can get "status":"fail" in critical cases, so just raise an exception
                if "status" in j and j["status"] == "fail":
                    raise PandoraApiException(str(j["error_text"]))

        # JSON decode error
        except JSONDecodeError as ex:
            raise PandoraApiException("JSON decode error") from None
        # Connection related error
        except aiohttp.ClientConnectionError as ex:
            raise PandoraApiException(type(ex).__name__) from None
        # Response related error
        except aiohttp.ClientResponseError as ex:
            raise PandoraApiException(type(ex).__name__) from None
        # Something goes wrong in server-side logic
        except PandoraApiException as ex:
            raise PandoraApiException(ex) from None

        return j

    async def login(self) -> None:
        """Login on server."""

        if self._session is None:
            self._session = async_create_clientsession(self._hass)

        data = {"login": self._username, "password": self._password, "lang": "ru"}

        response = await self._request(LOGIN_PATH, data=data, method="POST")
        # _session_id isn't used now
        self._session_id = PandoraApiLoginResponseParser(response).session_id

        _LOGGER.info("Login successful")

    async def _request_safe(self, path, data=None, method="GET"):
        """ High-level request function.

        It will make login on server if it isn't done before.
        It also checks the expiration/validity of the cookies. If problems - tries to make relogin.
        """

        if not self._session:
            await self.login()

        response = await self._request(path, data, method)

        if "status" in response:
            if response["status"] in {
                "Session is expired",
                "Invalid session",
                "sid-expired",
            }:
                _LOGGER.info("PandoraApi: %s. Making relogin.", response["error_text"])
                self._session_id = None
                await self.login()
                response = await self._request(path, data, method)

        return response

    async def load_devices(self):
        """Load device list.

        It shoud be done next after constructor.
        """

        response = PandoraApiDevicesResponseParser(await self._request_safe(DEVICES_PATH))

        for pandora_id, info in response.devices.items():
            self._devices[pandora_id] = PandoraDevice(pandora_id, info)

    async def _async_update(self, *_) -> bool:
        """Update attributes of devices."""

        try:
            response = PandoraApiUpdateResponseParser(await self._request_safe(UPDATE_PATH)).update

            try:
                for pandora_id, attrs in response.items():
                    await self._devices[pandora_id].update(attrs)
            except KeyError:
                _LOGGER.info("Got data for unexpected PANDORA_ID '%s'. Skipping...", pandora_id)

        except PandoraApiException as ex:
            _LOGGER.info("Update failed: %s", str(ex))

        return True

    async def async_command(self, pandora_id: str, command: str):
        """Send the command to device.

        The response should be like this: {"PANDORA_ID": "sent"}. PANDORA_ID must be the same as in request.
        Finally, the series of refreshes is scheduled. It will help to process sensors more accurately.
        """

        data = {"id": pandora_id, "command": command}

        status = PandoraApiCommandResponseParser(
            await self._request_safe(COMMAND_PATH, data=data, method="POST")
        ).result[pandora_id]

        if status != "sent":
            _LOGGER.warning("async_command: %s", status)
            raise PandoraApiException(status)

        async def _handle_refresh(*_):
            await self._coordinator.async_refresh()

        # I made some experiments with my car. How long does it take between sending command
        # and getting proper state of corresponding entity?  Results is placed below:
        # ----------------------------------------------------------------------------------
        # Stop engine: about 10s
        # Start engine: about 25s
        # ----------------------------------------------------------------------------------
        # Ten updates from 10-th to 30-th second with 2 second pause will enough, I think.

        now = utcnow().replace(microsecond=0)
        for delay in range(10, 30, 2):
            async_track_point_in_utc_time(self._hass, _handle_refresh, now + timedelta(seconds=delay))

        _LOGGER.info("Command %s is sent to device %s", command, pandora_id)

    async def async_refresh(self):
        """Refresh data through update coordinator helper."""
        await self._coordinator.async_refresh()

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> Callable[[], None]:
        """Listen for data updates."""
        return self._coordinator.async_add_listener(update_callback)


class PandoraDevice:
    """Pandora device class."""

    def __init__(self, pandora_id: str, info: dict):
        self._pandora_id = pandora_id
        self._name = info["name"]
        self._info = info
        self._attributes = {}
        _LOGGER.info("Device %s (PANDORA_ID=%s) created", info["name"], pandora_id)

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self._name

    @property
    def pandora_id(self) -> str:
        """Get the PANDORA_ID of the device."""
        return self._pandora_id

    @property
    def is_online(self) -> bool:
        """Is device online now?"""
        return bool(self.online)

    @property
    def fuel_tank(self) -> int:
        """Get the capacity of fuel tank."""
        return int(self._info["fuel_tank"])

    @property
    def device_info(self) -> dict:
        """Unified device info dictionary."""
        return {
            "identifiers": {(DOMAIN, self._pandora_id)},
            "name": self._name,
            "manufacturer": "Pandora",
            "model": self._info["model"],
            "sw_version": self._info["firmware"],
        }

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._attributes[item]

    async def update(self, attributes: dict) -> None:
        """Read new status data from the server."""

        # Update will be more suitable here. If we get empty or partial update
        # self._attributes will still contain previous data.
        self._attributes.update(attributes)
        _LOGGER.info("Device %s (PANDORA_ID=%s) updated", self._name, self._pandora_id)


class PandoraApiLoginResponseParser:
    """
    {
        "message":"",
        "status":"success",
        "user_id":567890,
        "lang":"ru",
        "session_id":"943a85be7c446e87b55ffbece22ee134"
    }
    """

    def __init__(self, response):
        self.session_id = response["session_id"]


class PandoraApiDevicesResponseParser:
    """
    [
    {
        "id":1234,
        "type":"alarm",
        "car_type":0,
        "name":"Honda Pilot",
        "photo":"wZa0x4FDoLThP6w+8Jmvsw==",
        "color":"rgb(255,255,255)",
        "auto_marka":"",
        "auto_model":"",
        "tanks":[],
        "features":{
            "auto_check":1,
            "value_100":1,
            "events":1,
            "tracking":1,
            "connection":1,
            "sensors":1,
            "autostart":1,
            "heater":1,
            "schedule":1,
            "notification":1,
            "beep":1,
            "light":1,
            "channel":1,
            "trunk":1,
            "active_security":1,
            "keep_alive":1,
            "custom_phones":1
        },
        "fuel_tank":50,
        "permissions":{
            "control":3,
            "settings":3,
            "settings_save":3,
            "events":3,
            "tracks":3,
            "status":3,
            "oauth":3,
            "rules":3,
            "tanks":3,
            "tanks_save":3,
            "detach":3
        },
        "is_shared":false,
        "phone":"+71234567890",
        "phone1":"",
        "active_sim":0,
        "model":"DXL-5570",
        "voice_version":"1.23F361",
        "firmware":"2.33",
        "start_ownership":1493996199,
        "owner_id":-1
    }
    ]
    """

    def __init__(self, response):
        self.devices = {}

        for enity in response:
            self.devices[str(enity["id"])] = enity


class PandoraApiUpdateResponseParser:
    """
    {
        "ts":1599698262,
        "lenta": [{
            "type": 0,
            "time": 1600553265,
            "obj": {
                "dev_id": 1234,
                "id": 862125457,
                "x": 54.924888,
                "y": 82.981296,
                "speed": 0,
                "dtime": 1600553265,
                "dtime_rec": 1600528068,
                "bit_state_1": 230273,
                "engine_rpm": 0,
                "engine_temp": 18,
                "cabin_temp": 14,
                "out_temp": 13,
                "fuel": 43,
                "voltage": 12.3,
                "gsm_level": 2,
                "eventid1": 14,
                "eventid2": 3,
                "weather": 0,
                "body": null
            }
        }],
        "time":{
            "1234":{
                "online":1599696535,
                "onlined":1599721730,
                "command":1599695573,
                "setting":1598267291
            }
        },
        "stats":{
            "1234":{
                "online":0,
                "move":0,
                "dtime":1599721704,
                "dtime_rec":1599696508,
                "voltage":13.5,
                "engine_temp":43,
                "x":55.080632,
                "y":82.929008,
                "bit_state_1":230284,
                "out_temp":17,
                "balance":{
                    "value":"142.75",
                    "cur":"RUB"
                },
                "balance1":{
                    "value":"0.00",
                    "cur":"RUB"
                },
                "sims":[
                    {
                    "phoneNumber":"+79851017237",
                    "isActive":true,
                    "balance":{
                        "value":"142.75",
                        "cur":"RUB"
                    }
                    }
                ],
                "active_sim":0,
                "speed":57.412,
                "tanks":[],
                "engine_rpm":112,
                "rot":63,
                "fuel":57,
                "cabin_temp":24,
                "evaq":0,
                "gsm_level":3,
                "props":[],
                "mileage":"28381.474447810226",
                "mileage_CAN":0,
                "metka":0,
                "brelok":0,
                "relay":0,
                "smeter":0,
                "tconsum":0,
                "land":0,
                "bunker":0,
                "ex_status":0,
                "engine_remains":0
            }
        },
        "ucr":{  <--- what does it mean?
            "1234":3
        }
    }
    """

    def __init__(self, response):
        self.update = response["stats"]


class PandoraApiCommandResponseParser:
    """
    {
        "action_result": {
            "1234": "sent"
        }
    }
    """

    def __init__(self, response):
        self.result = response["action_result"]
