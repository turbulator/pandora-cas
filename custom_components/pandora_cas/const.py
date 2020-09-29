"""TODO"""

from datetime import timedelta

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
