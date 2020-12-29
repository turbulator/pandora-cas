"""Pandora Car Alarm System API."""

import asyncio
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

from .const import (
    DOMAIN,
    MILEAGE_SOURCES,
    OPTION_FUEL_UNITS,
    OPTION_MILEAGE_SOURCE,
    OPTION_MILEAGE_ADJUSTMENT,
    OPTION_EXPIRE_AFTER,
    FUEL_UNITS,
)


_LOGGER = logging.getLogger(__name__)


HOST = "p-on.ru"
BASE_URL = "https://" + HOST
LOGIN_PATH = "/api/users/login"
DEVICES_PATH = "/api/devices"
UPDATE_PATH = "/api/updates?ts="
COMMAND_PATH = "/api/devices/command"

USER_AGENT = "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0"

FORCE_UPDATE_INTERVAL = 300
DENSE_POLLING_INTERVAL = 1
COMMAND_RESPONSE_TIMEOUT = 35


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
        self._update_ts = 0
        self._force_update_ts = 0
        self._command_response = asyncio.Event()
        self._dense_poll = False
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

    @property
    def timestamp(self) -> int:
        """Get last update timestamp."""

        return self._update_ts

    async def _request(self, path, method="GET", data=None):
        """Request an information from server."""

        url = BASE_URL + path
        # Heve to do it here because async_create_clientsession uses self User-Agent which rejects by p-on.ru
        headers = {"User-Agent": USER_AGENT}

        _LOGGER.debug("Request: %s", url)

        try:
            async with self._session.request(method, url, data=data, headers=headers) as response:
                _LOGGER.debug("Response Code: %d, Body: %s", response.status, await response.text())

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

        response = await self._request(LOGIN_PATH, method="POST", data=data)
        # _session_id isn't used now
        self._session_id = PandoraApiLoginResponseParser(response).session_id

        _LOGGER.info("Login successful")

    async def _request_safe(self, path, method="GET", data=None, relogin=False):
        """ High-level request function.

        It will make login on server if it isn't done before.
        It also checks the expiration/validity of the cookies. If problems - tries to make relogin.
        """

        if not self._session or relogin:
            self._session_id = None
            await self.login()

        response = await self._request(path, method=method, data=data)

        if "status" in response:
            if response["status"] in {
                "Session is expired",
                "Invalid session",
                "sid-expired",
            }:
                _LOGGER.info("PandoraApi: %s. Making relogin.", response["error_text"])
                response = await self._request_safe(path, method=method, data=data, relogin=True)

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
            if self._update_ts >= self._force_update_ts + FORCE_UPDATE_INTERVAL:
                self._update_ts = 0

            response = PandoraApiUpdateResponseParser(await self._request_safe(UPDATE_PATH + str(self._update_ts - 1)))

            stats = response.stats
            if self._update_ts == 0:
                self._force_update_ts = response.timestamp
            self._update_ts = response.timestamp

            # UCR means that device received the command and sent response (user command response?)
            # Lot's of commands executes quick: like on/off tracking, ext. cannel and so on.
            # And only engine_start requires additional 10-15 seconds on device side.
            if response.ucr is not None:
                self._command_response.set()

            try:
                for pandora_id, attrs in stats.items():
                    await self._devices[pandora_id].update(attrs, response.time[pandora_id]["online"])
            except KeyError:
                _LOGGER.info("Got data for unexpected PANDORA_ID '%s'. Skipping...", pandora_id)

        except PandoraApiException as ex:
            _LOGGER.info("Update failed: %s", str(ex))

        # I made some experiments with my car. How long does it take between sending command
        # and getting proper state of corresponding entity?  Results is placed below:
        # ----------------------------------------------------------------------------------
        # Stop engine: about 10s
        # Start engine: about 25s
        # ----------------------------------------------------------------------------------
        # Pandora makes one request per second until ucr receives. Timeout - 35 seconds

        async def _force_refresh(*_):
            await self._coordinator.async_refresh()

        if self._dense_poll > 0:
            self._dense_poll -= 1
            now = utcnow().replace(microsecond=0)
            async_track_point_in_utc_time(self._hass, _force_refresh, now + timedelta(seconds=DENSE_POLLING_INTERVAL))

        return True

    async def async_command(self, pandora_id: str, command: str) -> bool:
        """Send the command to device.

        The response should be like this: {"PANDORA_ID": "sent"}. PANDORA_ID must be the same as in request.
        """

        if self._dense_poll:
            raise PandoraApiException("Awaiting previous command")

        self._dense_poll = COMMAND_RESPONSE_TIMEOUT
        self._command_response.clear()

        data = {"id": pandora_id, "command": command}

        try:
            status = PandoraApiCommandResponseParser(
                await self._request_safe(COMMAND_PATH, method="POST", data=data)
            ).result[pandora_id]

            if status != "sent":
                raise PandoraApiException(status)
        except PandoraApiException as ex:
            self._dense_poll = 0
            _LOGGER.debug("async_command: %s", str(ex))
            raise PandoraApiException(str(ex)) from None

        _LOGGER.info("Command %s is sent to device %s", command, pandora_id)

        try:
            await asyncio.wait_for(self._command_response.wait(), COMMAND_RESPONSE_TIMEOUT)
        except asyncio.TimeoutError as ex:
            self._dense_poll = 0
            _LOGGER.warning("async_command: command timeout")
            raise PandoraApiException(str(ex)) from None

        self._dense_poll = 0
        _LOGGER.info("Got response for command %s on device %s", command, pandora_id)

        return True

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
        self._online_ts = 0
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
    def expire_after(self) -> int:
        """Get expiring timeout."""
        return int(self._info.get(OPTION_EXPIRE_AFTER, 0))

    @property
    def timestamp(self) -> int:
        """Get last online timestamp."""
        return int(self._online_ts)

    @property
    def fuel_percentage(self) -> int:
        """Get fuel in percentage."""
        return int(self._attributes["fuel"])

    @property
    def fuel_litres(self) -> int:
        """Get fuel in liters."""
        return int(self._info["fuel_tank"]) * self.fuel_percentage / 100

    @property
    def fuel(self) -> int:
        """Get fuel in user-defined units."""
        if self._info.get(OPTION_FUEL_UNITS, FUEL_UNITS[0]) == FUEL_UNITS[0]:
            return self.fuel_percentage

        return self.fuel_litres

    @property
    def mileage(self) -> float:
        """Get mileage from user-defined source with user-defined adjustment."""
        adjustment = float(self._info.get(OPTION_MILEAGE_ADJUSTMENT, 0))

        if self._info.get(OPTION_MILEAGE_SOURCE, MILEAGE_SOURCES[0]) == MILEAGE_SOURCES[0]:
            return adjustment + float(self._attributes["mileage"])

        return adjustment + float(self._attributes["mileage_CAN"])

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

    def user_defined_units(self, item):
        """Get units of attribute."""
        return self._info.get(item + "_units")

    def __getattr__(self, item):
        """Generic get function for all backend attributes."""
        return self._attributes[item]

    async def config_options(self, options: dict) -> None:
        """Save options from config_entry."""
        self._info.update(options)

    async def update(self, attributes: dict, online_ts: int) -> None:
        """Read new status data from the server."""

        # Update will be more suitable here. If we get empty or partial update
        # self._attributes will still contain previous data.
        self._attributes.update(attributes)
        self._online_ts = online_ts
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
        "ts":1599698262, <--- Current timestamp
        "lenta": [{  <--- The list of events
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
                "dtime_rec":1599696508,  <--- timestamp of the data in stats section
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
        "ucr":{  <--- what does it mean? User command response?
            "1234":3
        }
    }

    device-control.js:unpackStatusFlags
        r.b_locked = bb.shiftRight(0).and(1).toJSNumber(); // под охраной;
        r.b_alarm = bb.shiftRight(1).and(1).toJSNumber(); // тревога;
        r.b_engine = bb.shiftRight(2).and(1).toJSNumber(); // двигатель заведен;
        r.b_ignition = bb.shiftRight(3).and(1).toJSNumber(); // зажигание включено;
        r.b_autostart_init = bb.shiftRight(4).and(1).toJSNumber(); // процедура АЗ активна;
        r.b_hf_lock = bb.shiftRight(5).and(1).toJSNumber(); // HandsFree постановка под охрану при удалении от авто
        r.b_hf_unlock = bb.shiftRight(6).and(1).toJSNumber(); // HandsFree снятие с охраны при приближении к авто
        r.b_gsm = bb.shiftRight(7).and(1).toJSNumber(); // Gsm-модем включен

        r.b_gps = bb.shiftRight(8).and(1).toJSNumber(); // Gps-приемник включен
        r.b_tracking = bb.shiftRight(9).and(1).toJSNumber(); // трекинг включен
        r.b_immo = bb.shiftRight(10).and(1).toJSNumber(); // Двигатель заблокирован
        r.b_ext_sensor_alert_zone = bb.shiftRight(11).and(1).toJSNumber(); // Отключен контроль доп. датчика, предупредительная зона
        r.b_ext_sensor_main_zone = bb.shiftRight(12).and(1).toJSNumber(); // Отключен контроль доп. датчика, основная зона
        r.b_sensor_alert_zone = bb.shiftRight(13).and(1).toJSNumber(); // Отключен контроль датчика удара, предупредительная зона
        r.b_sensor_main_zone = bb.shiftRight(14).and(1).toJSNumber(); // Отключен контроль датчика удара, основная зона
        r.b_autostart = bb.shiftRight(15).and(1).toJSNumber(); // Запрограммирован АЗ двигателя

        r.b_sms = bb.shiftRight(16).and(1).toJSNumber(); // Разрешена отправка СМС – сообщений
        r.b_call = bb.shiftRight(17).and(1).toJSNumber(); // Разрешены голосовые вызовы
        r.b_light = bb.shiftRight(18).and(1).toJSNumber(); // Включены габаритные огни (фары, свет.)
        r.b_sound1 = bb.shiftRight(19).and(1).toJSNumber(); // Выкл. Предупредительные сигналы сирены
        r.b_sound2 = bb.shiftRight(20).and(1).toJSNumber(); // Выкл. Все звуковые сигналы сирены
        r.b_door_front_left = bb.shiftRight(21).and(1).toJSNumber();
        r.b_door_front_right = bb.shiftRight(22).and(1).toJSNumber();
        r.b_door_back_left = bb.shiftRight(23).and(1).toJSNumber();

        r.b_door_back_right = bb.shiftRight(24).and(1).toJSNumber();
        r.b_trunk = bb.shiftRight(25).and(1).toJSNumber(); // багажник
        r.b_hood = bb.shiftRight(26).and(1).toJSNumber(); // капот
        r.b_handbrake = bb.shiftRight(27).and(1).toJSNumber(); // ручной тормоз
        r.b_brakes = bb.shiftRight(28).and(1).toJSNumber(); // тормоз
        r.b_temp = bb.shiftRight(29).and(1).toJSNumber(); // предпусковой подогреватель
        r.b_active_secure = bb.shiftRight(30).and(1).toJSNumber(); // активная охрана
        r.b_heat = bb.shiftRight(31).and(1).toJSNumber(); // Запрограммирован пред. подогреватель

        r.b_evaq = bb.shiftRight(33).and(1).toJSNumber(); // режим эвакуации включен
        r.b_to = bb.shiftRight(34).and(1).toJSNumber(); // режим ТО включен
        r.b_stay_home = bb.shiftRight(35).and(1).toJSNumber(); // stay home
        r.b_zapret_oprosa_metok = bb.shiftRight(60).and(1).toJSNumber(); // запрет опроса меток
        r.b_zapret_snyatia_s_ohrani_bez_metki = bb.shiftRight(61).and(1).toJSNumber(); // запрет снятия с охраны при отсутствии метки в зоне
    """

    def __init__(self, response):
        self.stats = response.get("stats")
        self.time = response.get("time")
        self.ucr = response.get("ucr")
        self.timestamp = response.get("ts")


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
