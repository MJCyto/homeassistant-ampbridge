"""Constants for the AmpBridge integration."""

DOMAIN = "ampbridge"

# Config entry keys (beyond CONF_HOST / CONF_PORT from homeassistant.const)
CONF_API_PORT = "api_port"
CONF_USE_SSL = "use_ssl"
CONF_MQTT_BASE_TOPIC = "mqtt_base_topic"

DEFAULT_API_PORT = 4000
DEFAULT_MQTT_PORT = 1885

# MQTT Topics (default; override via config entry CONF_MQTT_BASE_TOPIC)
MQTT_BASE_TOPIC = "ampbridge/zones"
MQTT_STATUS_TOPIC = f"{MQTT_BASE_TOPIC}/status"

# Zone attributes
ZONE_ATTRIBUTES = ["volume", "mute", "source", "connected", "name"]

# Device info
DEVICE_MANUFACTURER = "AmpBridge"
DEVICE_MODEL = "Multi-Zone Amplifier Controller"
DEVICE_SW_VERSION = "1.0.0"

# Icons
ICON_VOLUME = "mdi:volume-high"
ICON_MUTE = "mdi:volume-off"
ICON_SOURCE = "mdi:input-hdmi"
ICON_SWITCH = "mdi:toggle-switch"
ICON_NUMBER = "mdi:volume-plus"
ICON_CONNECTIVITY = "mdi:lan-connect"
