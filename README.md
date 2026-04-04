# Home Assistant AmpBridge Integration

This is a Home Assistant custom integration for AmpBridge.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

## Features

- Zone discovery via the AmpBridge HTTP API (`/api/zones`)
- Real-time volume, mute, and source control over MQTT
- Source names and order come from AmpBridge (no hardcoded source labels)
- Configurable HTTP API port, HTTPS, and MQTT base topic

## Installation

1. Copy this repository to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration via the UI (Settings > Devices & Services > Add Integration)

## Configuration

| Field | Default | Description |
|--------|---------|-------------|
| Host | (required) | AmpBridge hostname or IP |
| MQTT broker port | 1885 | MQTT broker port AmpBridge connects to (often 1885 in Docker) |
| HTTP API port | 4000 | Phoenix/API port used for zone discovery |
| Use HTTPS for API | off | Enable if you terminate TLS in front of AmpBridge |
| MQTT base topic | `ampbridge/zones` | Must match AmpBridge `base_topic` in its MQTT config |

On setup, the integration checks that `GET /api/zones` succeeds before creating the entry.

## MQTT Topics

With default base topic `ampbridge/zones`:

- State: `ampbridge/zones/{zone_id}/volume`
- State: `ampbridge/zones/{zone_id}/mute`
- State: `ampbridge/zones/{zone_id}/source`
- State: `ampbridge/zones/{zone_id}/connected`
- Command: `ampbridge/zones/{zone_id}/volume/set`
- Command: `ampbridge/zones/{zone_id}/mute/set`
- Command: `ampbridge/zones/{zone_id}/source/set`

If you change the base topic in AmpBridge, set the same value in the integration.

## Development

This integration is designed to work with the AmpBridge server on your network. The server publishes zone states via MQTT and listens for control commands on the configured base topic.
