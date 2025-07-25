#!/usr/bin/env python3
"""
Phase 2 Test: Device Info and Service Discovery

This test validates that the ESPHome API server can properly handle
device info requests and list entities requests from Home Assistant,
eliminating the timeout issues from Phase 1.

Expected behavior:
- Home Assistant connects successfully
- Device info is provided when requested
- Entity list is provided when requested
- No connection timeouts
- Device appears properly in Home Assistant
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.api_server import ESPHomeAPIServer
from esphome_bluetooth_proxy.device_info import DeviceInfoProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Run Phase 2 test."""
    logger.info("Starting Phase 2 test: Device Info and Service Discovery")
    logger.info("=" * 60)
    logger.info("ESPHome Python Bluetooth Proxy - Phase 2 Test")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Phase 2 adds proper device info and service discovery responses.")
    logger.info("This should eliminate the timeout issues from Phase 1.")
    logger.info("")
    logger.info("The server is now running and ready for connections.")
    logger.info("You can test it by:")
    logger.info("")
    logger.info("1. Adding it to Home Assistant:")
    logger.info("   - Go to Settings > Devices & Services")
    logger.info("   - Click 'Add Integration'")
    logger.info("   - Search for 'ESPHome'")
    logger.info("   - Enter the IP address of this machine")
    logger.info("   - Port: 6053")
    logger.info("   - Leave password empty")
    logger.info("")
    logger.info("2. Expected behavior (Phase 2):")
    logger.info("   - Home Assistant should successfully connect")
    logger.info("   - Device should appear as 'Test Python Bluetooth Proxy'")
    logger.info("   - Device info should show Bluetooth proxy capabilities")
    logger.info("   - NO MORE TIMEOUTS - connection should be stable")
    logger.info("   - Device should show as 'Online' in Home Assistant")
    logger.info("   - No entities should be created yet (Phase 2 limitation)")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)

    # Create and start the API server
    server = ESPHomeAPIServer(
        host="0.0.0.0",
        port=6053,
        name="Test Python Bluetooth Proxy",
        friendly_name="Test Python Bluetooth Proxy",
        password=None,  # No password for testing
        active_connections=False,  # Not needed for Phase 2
    )

    # Set up signal handler for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping server...")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(server.stop()))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping server...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await server.stop()
        logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
