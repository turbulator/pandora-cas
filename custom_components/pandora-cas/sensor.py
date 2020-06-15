"""
Reads vehicle status from BMW connected drive portal.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.bmw_connected_drive/
"""
import logging

from . import DOMAIN as PANDORA_DOMAIN
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import (LENGTH_KILOMETERS,
                                 TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    'mileage': ["Milage", "mdi:map-marker-distance", LENGTH_KILOMETERS, True],
    'fuel': ["Fuel level", 'mdi:gauge', "%", False],
    'cabin_temp': ["Cabin temperature", 'mdi:thermometer', TEMP_CELSIUS, True],
    'engine_temp': ["Engine temperature", 'mdi:thermometer', TEMP_CELSIUS, True],
    'out_temp': ["Ambient temperature", 'mdi:thermometer', TEMP_CELSIUS, True],
    'balance': ["Balance", "mdi:cash", "₽", False],
    'speed': ["Speed", 'mdi:gauge', "km/h", True],
    'engine_rpm': ["Engine RPM", 'mdi:gauge', None, True],
    'gsm_level': ["GSM level", 'mdi:network-strength-2', None, True],
    'battery': ["Battery voltage", 'mdi:car-battery', "V", True],
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    account = hass.data[PANDORA_DOMAIN]
    devices = []

    for vehicle in account.account.vehicles:
        for parameter, _ in sorted(SENSOR_TYPES.items()):
            name = SENSOR_TYPES[parameter][0]
            icon = SENSOR_TYPES[parameter][1]
            unit = SENSOR_TYPES[parameter][2]
            state_sensitive = SENSOR_TYPES[parameter][3]

            device = PandoraSensor(account, 
                                    vehicle,
                                    parameter,
                                    name,
                                    icon,
                                    unit,
                                    state_sensitive)
            devices.append(device)

    add_entities(devices, True)


class PandoraSensor(Entity):
    """Representation of a BMW vehicle sensor."""

    def __init__(self, account, vehicle, parameter: str, name: str, icon: str, unit: str, state_sensitive: bool):
        """Constructor."""
        self._vehicle = vehicle
        self._account = account
        self._parameter = parameter
        self._name = "{} {}".format(self._vehicle.name, name)
        self._state = None
        self._icon = icon
        self._unit = unit
        self._state_sensitive = state_sensitive
        self.entity_id = ENTITY_ID_FORMAT.format(
            "{}_{}".format(slugify(str(self._vehicle.id)), slugify(name))
        )

    @property
    def should_poll(self) -> bool:
        """Return False.

        Data update is triggered from BMWConnectedDriveEntity.
        """
        return False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor.

        The return type of this call depends on the attribute that
        is configured.
        """
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        return self._unit

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            'car': self._vehicle.name
        }

    def update(self) -> None:
        """Read new state data from the library."""
        _LOGGER.debug('Updating %s', self._vehicle.name)
        vehicle_state = self._vehicle.state

        if vehicle_state.online == 1 or self._state_sensitive == False:
            self._available = True
            self._state = getattr(vehicle_state, self._parameter)
        else:
            self._available = False

    def update_callback(self):
        """Schedule a state update."""
        self.schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add callback after being added to hass.

        Show latest data after startup.
        """
        self._account.add_update_listener(self.update_callback)
