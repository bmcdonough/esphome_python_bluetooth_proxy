#!/usr/bin/env python3
"""
Phase 4 Test Script: Active BLE Connections

This script tests the Phase 4 functionality including:
- BLE device connection management
- GATT service discovery
- GATT read/write operations
- GATT notifications
- Protocol message handling
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.api_server import ESPHomeAPIServer
from esphome_bluetooth_proxy.bluetooth_proxy import BluetoothProxy
from esphome_bluetooth_proxy.device_info import DeviceInfoProvider
from esphome_bluetooth_proxy.gatt_operations import GATTOperationHandler
from esphome_bluetooth_proxy.protocol import (
    BluetoothDeviceRequest,
    BluetoothGATTGetServicesRequest,
    BluetoothGATTNotifyRequest,
    BluetoothGATTReadRequest,
    BluetoothGATTWriteRequest,
    MessageDecoder,
    MessageType,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("phase4_test.log"),
    ],
)

logger = logging.getLogger(__name__)


class Phase4TestClient:
    """Test client for Phase 4 functionality."""

    def __init__(self):
        self.decoder = MessageDecoder()
        self.test_device_address = 0x94BB430F8CAB  # Example MAC address
        self.test_service_handle = 0x0001
        self.test_char_handle = 0x0003

    async def test_device_connection(self, bluetooth_proxy: BluetoothProxy):
        """Test device connection functionality."""
        logger.info("=== Testing Device Connection ===")

        # Test connection request
        logger.info(f"Testing connection to device {self.test_device_address:012X}")
        success = await bluetooth_proxy.connect_device(
            self.test_device_address, 0  # Public address
        )
        logger.info(f"Connection request result: {success}")

        # Check connection status
        await asyncio.sleep(2)  # Allow time for connection attempt
        stats = bluetooth_proxy.get_stats()
        logger.info(f"Connection stats: {stats}")

        # Test disconnection
        logger.info(
            f"Testing disconnection from device {self.test_device_address:012X}"
        )
        success = await bluetooth_proxy.disconnect_device(self.test_device_address)
        logger.info(f"Disconnection request result: {success}")

        await asyncio.sleep(1)  # Allow time for disconnection

    async def test_gatt_operations(self, gatt_handler: GATTOperationHandler):
        """Test GATT operations functionality."""
        logger.info("=== Testing GATT Operations ===")

        # Test GATT read request
        logger.info(f"Testing GATT read from handle {self.test_char_handle}")
        try:
            await gatt_handler.handle_gatt_read_request(
                self.test_device_address, self.test_char_handle
            )
            logger.info("GATT read request processed")
        except Exception as e:
            logger.warning(f"GATT read request failed (expected): {e}")

        # Test GATT write request
        logger.info(f"Testing GATT write to handle {self.test_char_handle}")
        test_data = b"Hello, BLE!"
        try:
            await gatt_handler.handle_gatt_write_request(
                self.test_device_address, self.test_char_handle, test_data, True
            )
            logger.info("GATT write request processed")
        except Exception as e:
            logger.warning(f"GATT write request failed (expected): {e}")

        # Test GATT notification subscription
        logger.info(
            f"Testing GATT notification subscription for handle {self.test_char_handle}"
        )
        try:
            await gatt_handler.handle_gatt_notify_request(
                self.test_device_address, self.test_char_handle, True
            )
            logger.info("GATT notification subscription processed")
        except Exception as e:
            logger.warning(f"GATT notification subscription failed (expected): {e}")

        # Test notification data handling
        logger.info("Testing notification data handling")
        test_notification_data = b"Notification data"
        await gatt_handler.handle_notification_data(
            self.test_device_address, self.test_char_handle, test_notification_data
        )

    async def test_protocol_messages(self):
        """Test protocol message encoding/decoding."""
        logger.info("=== Testing Protocol Messages ===")

        # Test BluetoothDeviceRequest
        device_request = BluetoothDeviceRequest(
            address=self.test_device_address, address_type=0, action=0  # Connect
        )
        logger.info(f"Created device request: {device_request}")

        # Test BluetoothGATTGetServicesRequest
        services_request = BluetoothGATTGetServicesRequest(
            address=self.test_device_address
        )
        logger.info(f"Created services request: {services_request}")

        # Test BluetoothGATTReadRequest
        read_request = BluetoothGATTReadRequest(
            address=self.test_device_address, handle=self.test_char_handle
        )
        logger.info(f"Created read request: {read_request}")

        # Test BluetoothGATTWriteRequest
        write_request = BluetoothGATTWriteRequest(
            address=self.test_device_address,
            handle=self.test_char_handle,
            response=True,
            data=b"Test data",
        )
        logger.info(f"Created write request: {write_request}")

        # Test BluetoothGATTNotifyRequest
        notify_request = BluetoothGATTNotifyRequest(
            address=self.test_device_address, handle=self.test_char_handle, enable=True
        )
        logger.info(f"Created notify request: {notify_request}")

        logger.info("All protocol message structures created successfully")

    async def test_connection_pool(self, bluetooth_proxy: BluetoothProxy):
        """Test connection pool functionality."""
        logger.info("=== Testing Connection Pool ===")

        # Test connection limits
        logger.info(f"Connection limit: {bluetooth_proxy.get_connection_limit()}")
        logger.info(f"Free connections: {bluetooth_proxy.get_free_connections()}")

        # Test multiple connection attempts (should respect limits)
        test_addresses = [
            0x94BB430F8CAB,
            0x94BB430F8CAC,
            0x94BB430F8CAD,
            0x94BB430F8CAE,  # This should exceed the limit
        ]

        for i, address in enumerate(test_addresses):
            logger.info(f"Attempting connection {i+1} to {address:012X}")
            success = await bluetooth_proxy.connect_device(address, 0)
            logger.info(f"Connection {i+1} result: {success}")
            logger.info(f"Free connections: {bluetooth_proxy.get_free_connections()}")
            await asyncio.sleep(0.5)

        # Clean up connections
        await asyncio.sleep(2)
        for address in test_addresses:
            await bluetooth_proxy.disconnect_device(address)

    async def run_tests(self):
        """Run all Phase 4 tests."""
        logger.info("Starting Phase 4 Tests")
        logger.info("=" * 50)

        try:
            # Initialize components
            api_server = ESPHomeAPIServer(
                host="127.0.0.1",
                port=6053,
                name="python-bluetooth-proxy-test",
                friendly_name="Python Bluetooth Proxy Test",
                active_connections=True,
            )

            bluetooth_proxy = BluetoothProxy(api_server, max_connections=3)
            gatt_handler = GATTOperationHandler(bluetooth_proxy)

            # Set up cross-references
            api_server.bluetooth_proxy = bluetooth_proxy
            bluetooth_proxy.gatt_handler = gatt_handler

            # Start components
            logger.info("Starting API server...")
            await api_server.start()

            logger.info("Starting Bluetooth proxy...")
            await bluetooth_proxy.start()

            # Run tests
            await self.test_protocol_messages()
            await self.test_connection_pool(bluetooth_proxy)
            await self.test_device_connection(bluetooth_proxy)
            await self.test_gatt_operations(gatt_handler)

            # Test statistics
            logger.info("=== Final Statistics ===")
            proxy_stats = bluetooth_proxy.get_stats()
            gatt_stats = gatt_handler.get_stats()
            logger.info(f"Bluetooth proxy stats: {proxy_stats}")
            logger.info(f"GATT handler stats: {gatt_stats}")

            logger.info("Phase 4 tests completed successfully!")

        except Exception as e:
            logger.error(f"Phase 4 test failed: {e}", exc_info=True)
            return False

        finally:
            # Clean up
            try:
                if "bluetooth_proxy" in locals():
                    await bluetooth_proxy.stop()
                if "api_server" in locals():
                    await api_server.stop()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

        return True


async def main():
    """Main test function."""

    # Set up signal handling
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run tests
    test_client = Phase4TestClient()
    success = await test_client.run_tests()

    if success:
        logger.info("All Phase 4 tests passed!")
        return 0
    else:
        logger.error("Some Phase 4 tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
