# Home Assistant AmpBridge Integration

This is a Home Assistant custom integration for the AmpBridge multi-zone amplifier controller.

## Features

- Auto-discovery of zones via MQTT
- Real-time volume, mute, and source control
- Device-based organization in Home Assistant
- MQTT-based communication with AmpBridge server

## Installation

1. Copy this repository to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration via the UI (Settings > Devices & Services > Add Integration)

## Configuration

The integration will automatically discover your AmpBridge server via MQTT. Make sure your AmpBridge server is running and publishing to the MQTT broker.

## MQTT Topics

- State: `ampbridge/zones/{zone_id}/volume`
- State: `ampbridge/zones/{zone_id}/mute`
- State: `ampbridge/zones/{zone_id}/source`
- State: `ampbridge/zones/{zone_id}/connected`
- Command: `ampbridge/zones/{zone_id}/volume/set`
- Command: `ampbridge/zones/{zone_id}/mute/set`
- Command: `ampbridge/zones/{zone_id}/source/set`

## Development

This integration is designed to work with the AmpBridge server running on your network. The server should be publishing zone states via MQTT and listening for control commands.
