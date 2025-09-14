"""Constants for the AmpBridge integration."""

DOMAIN = "ampbridge"

# MQTT Topics
MQTT_BASE_TOPIC = "ampbridge/zones"
MQTT_STATUS_TOPIC = f"{MQTT_BASE_TOPIC}/status"

# Zone attributes
ZONE_ATTRIBUTES = ["volume", "mute", "source", "connected", "name"]

# Device info
DEVICE_MANUFACTURER = "AmpBridge"
DEVICE_MODEL = "Multi-Zone Amplifier Controller"
DEVICE_SW_VERSION = "1.0.0"
