#!/usr/bin/env python3
"""Test script for Phase 1: ESPHome API Server Foundation.

This script tests the basic ESPHome API server functionality including
the 4-step handshake process.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.api_server import ESPHomeAPIServer


async def test_server():
    """Test the API server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Phase 1 test: ESPHome API Server Foundation")
    
    # Create server
    server = ESPHomeAPIServer(
        name="test-bluetooth-proxy",
        friendly_name="Test Python Bluetooth Proxy",
        password=None,  # No password for easier testing
        active_connections=False  # Phase 1: passive only
    )
    
    logger.info("=" * 60)
    logger.info("ESPHome Python Bluetooth Proxy - Phase 1 Test")
    logger.info("=" * 60)
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
    logger.info("2. Expected behavior:")
    logger.info("   - Home Assistant should successfully connect")
    logger.info("   - Device should appear as 'Test Python Bluetooth Proxy'")
    logger.info("   - Device info should show Bluetooth proxy capabilities")
    logger.info("   - No entities should be created (Phase 1 limitation)")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await server.stop()
        logger.info("Test completed")


if __name__ == "__main__":
    asyncio.run(test_server())
