"""TODO"""

from datetime import timedelta

from homeassistant.const import PERCENTAGE, VOLUME_LITERS

DOMAIN = "pandora_cas"

ATTR_IS_CONNECTION_SENSITIVE = "is_connection_sensitive"
ATTR_DEVICE_ATTR = "device_attr"
ATTR_UNITS = "unit_of_measurement"
ATTR_SHIFT_BITS = "shift_bits"
ATTR_INVERSE = "inverse"
ATTR_FORMATTER = "formatter"
ATTR_SCHEMA = "schema"
ATTR_ID = "id"
ATTR_COMMAND = "command"

CONF_POLLING_INTERVAL = "polling_interval"
MIN_POLLING_INTERVAL = timedelta(seconds=10)
DEFAULT_POLLING_INTERVAL = timedelta(minutes=1)

FUEL_UNITS = [PERCENTAGE, VOLUME_LITERS]
MILEAGE_SOURCES = ["GPS", "CAN"]
OPTION_FUEL_UNITS = "fuel_units"
OPTION_MILEAGE_SOURCE = "mileage_source"
OPTION_MILEAGE_ADJUSTMENT = "mileage_adjustment"
OPTION_EXPIRE_AFTER = "expire_after"
