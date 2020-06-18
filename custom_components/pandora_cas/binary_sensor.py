"""
Reads vehicle status from BMW connected drive portal.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.bmw_connected_drive/
"""
import logging

from homeassistant.components.binary_sensor import (BinarySensorDevice, 
                                                    ENTITY_ID_FORMAT)
from . import DOMAIN as PANDORA_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)


SENSOR_TYPES = {
    'connection_state': ["Connection state", "", "",  'connectivity', False, "online", 0, 0],
    'engine_state': ["Engine state", "mdi:fan", "mdi:fan-off", "", True, "bit_state_1", 2, 0],
    'moving': ["Moving", "", "",  'motion', True, "move", 0, 0],
    'lock_state': ["Lock", "mdi:lock-open", "mdi:lock", "lock", True, "bit_state_1", 0, 1],
    'left_front_door': ["Left Front Door", "mdi:car-door", "mdi:car-door", "door", True, "bit_state_1", 21, 0],
    'right_front_door': ["Right Front Door", "mdi:car-door", "mdi:car-door", "door", True, "bit_state_1", 22, 0],
    'left_back_door': ["Left Back Door", "mdi:car-door", "mdi:car-door", "door", True, "bit_state_1", 23, 0],
    'right_back_door': ["Right Back Door", "mdi:car-door", "mdi:car-door", "door", True, "bit_state_1", 24, 0],
    'trunk': ["Trunk", "mdi:car-back", "mdi:car-back", "door", True, "bit_state_1", 25, 0],
    'hood': ["Hood", "mdi:car", "mdi:car", "door", True, "bit_state_1", 26, 0],
    'coolant_heater': ["Coolant Heater", "mdi:thermometer-plus", "mdi:thermometer-plus", "", True, "bit_state_1", 29, 0],
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the BMW sensors."""
    account = hass.data[PANDORA_DOMAIN]

    devices = []
    for vehicle in account.account.vehicles:
        for parameter, _ in sorted(SENSOR_TYPES.items()):
            name = SENSOR_TYPES[parameter][0]
            icon_on = SENSOR_TYPES[parameter][1]
            icon_off = SENSOR_TYPES[parameter][2]
            device_class = SENSOR_TYPES[parameter][3]
            attribute = SENSOR_TYPES[parameter][5]
            shift_bits = SENSOR_TYPES[parameter][6]
            is_negative = SENSOR_TYPES[parameter][7]
            is_state_sensitive = SENSOR_TYPES[parameter][4]

            device = PandoraSensor(account, 
                                    vehicle,
                                    name,
                                    icon_on,
                                    icon_off,
                                    device_class,
                                    attribute,
                                    shift_bits,
                                    is_negative,
                                    is_state_sensitive)
            devices.append(device)

    add_entities(devices, True)


class PandoraSensor(BinarySensorDevice):
    """Representation of a BMW vehicle binary sensor."""

    def __init__(self, account, vehicle, name: str, icon_on: str, icon_off: str, device_class: str, attribute: str, shift_bits: int, is_negative: int, is_state_sensitive: bool):
        """Constructor."""
        self._vehicle = vehicle
        self._account = account
        self._name = "{} {}".format(self._vehicle.name, name)
        self._state = None
        self._icon_on = icon_on
        self._icon_off = icon_off
        self._device_class = device_class
        self._attribute = attribute
        self._shift_bits = shift_bits
        self._is_negative = is_negative
        self._is_state_sensitive = is_state_sensitive
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
        """Return the name of the binary sensor."""
        return self._name

    @property
    def device_class(self) -> str:
        """Return the class of the binary sensor."""
        return self._device_class

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self) -> str:
        """Return the icon of the binary sensor."""
        if self._state:
            return self._icon_on
        else:
            return self._icon_off

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            'car': self._vehicle.name
        }

    def update(self):
        """Read new state data from the library."""
        vehicle_state = self._vehicle.state

        if vehicle_state.online == 1 or self._is_state_sensitive == False:
            self._available = True
            if (int(getattr(vehicle_state, self._attribute)) >> self._shift_bits) & 0x0000000000000001 ^ self._is_negative:
                self._state = True
            else:
                self._state = False
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
