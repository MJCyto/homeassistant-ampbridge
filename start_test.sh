#!/bin/bash

# Start local Home Assistant for AmpBridge integration testing
echo "🚀 Starting local Home Assistant for AmpBridge testing..."
echo "📡 Will connect to your AmpBridge server at 192.168.1.233:1885"
echo "🌐 Home Assistant will be available at http://localhost:8123"
echo ""

# Create necessary directories
mkdir -p test_config
mkdir -p test_config/custom_components

# Copy the integration to the test config
cp -r custom_components/ampbridge test_config/custom_components/

# Start the containers
docker-compose up -d

echo ""
echo "✅ Home Assistant is starting up..."
echo "⏳ Wait about 30-60 seconds for Home Assistant to fully start"
echo "🔗 Then visit: http://localhost:8123"
echo ""
echo "📋 To add the integration:"
echo "   1. Go to Settings > Devices & Services"
echo "   2. Click 'Add Integration'"
echo "   3. Search for 'AmpBridge'"
echo "   4. Enter your server details (192.168.1.233:1885)"
echo ""
echo "🛑 To stop: docker-compose down"
echo "📊 To view logs: docker-compose logs -f homeassistant"
