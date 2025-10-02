"""Constants for the AmpBridge integration."""

DOMAIN = "ampbridge"

# MQTT Topics
MQTT_BASE_TOPIC = "ampbridge/zones"
MQTT_GROUPS_BASE_TOPIC = "ampbridge/groups"
MQTT_STATUS_TOPIC = f"{MQTT_BASE_TOPIC}/status"

# Zone attributes
ZONE_ATTRIBUTES = ["volume", "mute", "source", "connected", "name"]

# Group attributes
GROUP_ATTRIBUTES = ["volume", "mute", "source", "name", "description", "zone_count"]

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
