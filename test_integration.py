#!/usr/bin/env python3
"""
Test script for AmpBridge Home Assistant integration
This script helps verify that the integration is working correctly
"""

import requests
import json
import time
import paho.mqtt.client as mqtt
import threading

class AmpBridgeTester:
    def __init__(self, ha_url="http://localhost:8123", mqtt_host="192.168.1.233", mqtt_port=1885):
        self.ha_url = ha_url
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_client = None
        self.mqtt_messages = []
        
    def test_ha_connection(self):
        """Test if Home Assistant is running"""
        try:
            response = requests.get(f"{self.ha_url}/api/", timeout=5)
            if response.status_code == 200:
                print("✅ Home Assistant is running")
                return True
            elif response.status_code == 401:
                print("✅ Home Assistant is running (authentication required)")
                return True
            else:
                print(f"❌ Home Assistant returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to Home Assistant: {e}")
            return False
    
    def test_mqtt_connection(self):
        """Test MQTT connection to AmpBridge server"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("✅ Connected to AmpBridge MQTT broker")
                client.subscribe("ampbridge/zones/#")
            else:
                print(f"❌ Failed to connect to MQTT broker: {rc}")
        
        def on_message(client, userdata, msg):
            self.mqtt_messages.append({
                'topic': msg.topic,
                'payload': msg.payload.decode(),
                'timestamp': time.time()
            })
            print(f"📨 MQTT: {msg.topic} = {msg.payload.decode()}")
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            time.sleep(2)  # Wait for connection and messages
            return True
        except Exception as e:
            print(f"❌ MQTT connection failed: {e}")
            return False
    
    def test_ampbridge_entities(self):
        """Test if AmpBridge entities are created in Home Assistant"""
        try:
            # This would require authentication in a real scenario
            # For now, we'll just check if we can access the API
            response = requests.get(f"{self.ha_url}/api/states", timeout=5)
            if response.status_code == 200:
                states = response.json()
                ampbridge_entities = [s for s in states if 'ampbridge' in s.get('entity_id', '')]
                print(f"✅ Found {len(ampbridge_entities)} AmpBridge entities")
                
                # Group entities by type
                entity_types = {}
                for entity in ampbridge_entities:
                    entity_type = entity['entity_id'].split('.')[0]
                    if entity_type not in entity_types:
                        entity_types[entity_type] = []
                    entity_types[entity_type].append(entity)
                
                for entity_type, entities in entity_types.items():
                    print(f"   {entity_type}: {len(entities)} entities")
                    for entity in entities[:3]:  # Show first 3 of each type
                        print(f"     - {entity['entity_id']}: {entity['state']}")
                    if len(entities) > 3:
                        print(f"     ... and {len(entities) - 3} more")
                
                return len(ampbridge_entities) > 0
            else:
                print(f"❌ Failed to get states: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to check entities: {e}")
            return False
    
    def send_test_command(self, zone_id=0, command="volume", value="50"):
        """Send a test command to AmpBridge"""
        topic = f"ampbridge/zones/{zone_id}/{command}/set"
        try:
            self.mqtt_client.publish(topic, value)
            print(f"📤 Sent command: {topic} = {value}")
            return True
        except Exception as e:
            print(f"❌ Failed to send command: {e}")
            return False
    
    def run_tests(self):
        """Run all tests"""
        print("🧪 Starting AmpBridge Integration Tests")
        print("=" * 50)
        
        # Test Home Assistant
        print("\n1. Testing Home Assistant connection...")
        ha_ok = self.test_ha_connection()
        
        # Test MQTT
        print("\n2. Testing MQTT connection to AmpBridge...")
        mqtt_ok = self.test_mqtt_connection()
        
        if mqtt_ok:
            print("\n3. Listening for MQTT messages (10 seconds)...")
            time.sleep(10)
            print(f"📊 Received {len(self.mqtt_messages)} MQTT messages")
        
        # Test entities
        print("\n4. Testing AmpBridge entities...")
        entities_ok = self.test_ampbridge_entities()
        
        # Test command sending
        if mqtt_ok:
            print("\n5. Testing command sending...")
            self.send_test_command(0, "volume", "75")
            time.sleep(2)
            self.send_test_command(0, "mute", "ON")
            time.sleep(2)
            self.send_test_command(0, "mute", "OFF")
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 Test Summary:")
        print(f"   Home Assistant: {'✅' if ha_ok else '❌'}")
        print(f"   MQTT Connection: {'✅' if mqtt_ok else '❌'}")
        print(f"   Entities Found: {'✅' if entities_ok else '❌'}")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

if __name__ == "__main__":
    tester = AmpBridgeTester()
    tester.run_tests()
