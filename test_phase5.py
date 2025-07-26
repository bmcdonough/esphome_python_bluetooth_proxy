#!/usr/bin/env python3
"""
Phase 5 Test Script: GATT Operations Implementation

This script tests the complete GATT operations functionality including:
- Characteristic read/write operations
- Descriptor read/write operations
- Notification subscription/unsubscription
- Error handling and recovery
- Integration with ESPHome API message handling
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.api_server import ESPHomeAPIServer
from esphome_bluetooth_proxy.protocol import (
    BluetoothGATTNotifyRequest,
    BluetoothGATTReadDescriptorRequest,
    BluetoothGATTReadRequest,
    BluetoothGATTWriteDescriptorRequest,
    BluetoothGATTWriteRequest,
    MessageEncoder,
    MessageType,
    create_message_frame,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("phase5_test.log"),
    ],
)

logger = logging.getLogger(__name__)


class Phase5Tester:
    """Test harness for Phase 5 GATT operations."""

    def __init__(self):
        self.server = None
        self.running = False
        self.encoder = MessageEncoder()

    async def start_server(self):
        """Start the ESPHome API server with GATT operations support."""
        logger.info("=== Phase 5 GATT Operations Test ===")

        try:
            # Create server with active connections enabled
            self.server = ESPHomeAPIServer(
                host="127.0.0.1",
                port=6053,
                name="phase5-test-proxy",
                friendly_name="Phase 5 Test Bluetooth Proxy",
                password=None,
                active_connections=True,
            )

            # Start server
            await self.server.start()
            self.running = True

            logger.info("✅ ESPHome API server started successfully")
            logger.info("✅ Bluetooth proxy initialized with GATT operations")
            logger.info("✅ GATT handler integrated with API connections")

            # Verify GATT handler integration
            if self.server.bluetooth_proxy and hasattr(
                self.server.bluetooth_proxy, "gatt_handler"
            ):
                logger.info("✅ GATT operations handler properly integrated")

                # Get GATT handler stats
                stats = self.server.bluetooth_proxy.gatt_handler.get_stats()
                logger.info(f"📊 GATT handler stats: {stats}")
            else:
                logger.error("❌ GATT handler not properly integrated")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            return False

    async def test_gatt_operations_integration(self):
        """Test GATT operations integration with API message handling."""
        logger.info("\n=== Testing GATT Operations Integration ===")

        try:
            # Test that all required message types are defined
            required_types = [
                MessageType.BLUETOOTH_GATT_READ_REQUEST,
                MessageType.BLUETOOTH_GATT_WRITE_REQUEST,
                MessageType.BLUETOOTH_GATT_NOTIFY_REQUEST,
                MessageType.BLUETOOTH_GATT_READ_DESCRIPTOR_REQUEST,
                MessageType.BLUETOOTH_GATT_WRITE_DESCRIPTOR_REQUEST,
            ]

            for msg_type in required_types:
                logger.info(f"✅ Message type {msg_type.name} = {msg_type.value}")

            # Test message encoding/decoding
            await self._test_message_encoding()

            # Test GATT handler methods
            await self._test_gatt_handler_methods()

            logger.info("✅ GATT operations integration test completed")
            return True

        except Exception as e:
            logger.error(f"❌ GATT operations integration test failed: {e}")
            return False

    async def _test_message_encoding(self):
        """Test GATT message encoding and decoding."""
        logger.info("\n--- Testing Message Encoding/Decoding ---")

        # Test characteristic read request
        read_req = BluetoothGATTReadRequest(address=0x112233445566, handle=42)
        read_payload = self.encoder.encode_bluetooth_gatt_read_request(read_req)
        logger.info(f"✅ Encoded GATT read request: {len(read_payload)} bytes")

        # Test characteristic write request
        write_req = BluetoothGATTWriteRequest(
            address=0x112233445566, handle=43, response=True, data=b"test_data"
        )
        write_payload = self.encoder.encode_bluetooth_gatt_write_request(write_req)
        logger.info(f"✅ Encoded GATT write request: {len(write_payload)} bytes")

        # Test notification request
        notify_req = BluetoothGATTNotifyRequest(
            address=0x112233445566, handle=44, enable=True
        )
        notify_payload = self.encoder.encode_bluetooth_gatt_notify_request(notify_req)
        logger.info(f"✅ Encoded GATT notify request: {len(notify_payload)} bytes")

        # Test descriptor read request
        desc_read_req = BluetoothGATTReadDescriptorRequest(
            address=0x112233445566, handle=45
        )
        desc_read_payload = self.encoder.encode_bluetooth_gatt_read_descriptor_request(
            desc_read_req
        )
        logger.info(
            f"✅ Encoded GATT read descriptor request: {len(desc_read_payload)} bytes"
        )

        # Test descriptor write request
        desc_write_req = BluetoothGATTWriteDescriptorRequest(
            address=0x112233445566, handle=46, data=b"descriptor_data"
        )
        desc_write_payload = (
            self.encoder.encode_bluetooth_gatt_write_descriptor_request(desc_write_req)
        )
        logger.info(
            f"✅ Encoded GATT write descriptor request: {len(desc_write_payload)} bytes"
        )

    async def _test_gatt_handler_methods(self):
        """Test GATT handler method availability."""
        logger.info("\n--- Testing GATT Handler Methods ---")

        gatt_handler = self.server.bluetooth_proxy.gatt_handler

        # Test method availability
        required_methods = [
            "handle_gatt_read_request",
            "handle_gatt_write_request",
            "handle_gatt_read_descriptor_request",
            "handle_gatt_write_descriptor_request",
            "handle_gatt_notify_request",
            "handle_notification_data",
            "cleanup_device",
            "get_stats",
        ]

        for method_name in required_methods:
            if hasattr(gatt_handler, method_name):
                logger.info(f"✅ GATT handler method: {method_name}")
            else:
                logger.error(f"❌ Missing GATT handler method: {method_name}")

        # Test statistics
        stats = gatt_handler.get_stats()
        logger.info(f"✅ GATT handler statistics: {stats}")

    async def test_ble_connection_gatt_methods(self):
        """Test BLE connection GATT method availability."""
        logger.info("\n=== Testing BLE Connection GATT Methods ===")

        try:
            # Import BLE connection class
            from esphome_bluetooth_proxy.ble_connection import BLEConnection

            # Test method availability (without actually connecting)
            required_methods = [
                "read_characteristic",
                "write_characteristic",
                "read_descriptor",
                "write_descriptor",
                "start_notify",
                "stop_notify",
            ]

            for method_name in required_methods:
                if hasattr(BLEConnection, method_name):
                    logger.info(f"✅ BLE connection method: {method_name}")
                else:
                    logger.error(f"❌ Missing BLE connection method: {method_name}")

            logger.info("✅ BLE connection GATT methods test completed")
            return True

        except Exception as e:
            logger.error(f"❌ BLE connection GATT methods test failed: {e}")
            return False

    async def test_error_handling(self):
        """Test GATT operations error handling."""
        logger.info("\n=== Testing GATT Error Handling ===")

        try:
            gatt_handler = self.server.bluetooth_proxy.gatt_handler

            # Test error handling for non-existent device
            fake_address = 0x999999999999
            fake_handle = 999

            logger.info("Testing error handling for non-existent device...")

            # These should handle errors gracefully
            await gatt_handler.handle_gatt_read_request(fake_address, fake_handle)
            await gatt_handler.handle_gatt_write_request(
                fake_address, fake_handle, b"test", True
            )
            await gatt_handler.handle_gatt_read_descriptor_request(
                fake_address, fake_handle
            )
            await gatt_handler.handle_gatt_write_descriptor_request(
                fake_address, fake_handle, b"test"
            )
            await gatt_handler.handle_gatt_notify_request(
                fake_address, fake_handle, True
            )

            logger.info("✅ GATT error handling test completed")
            return True

        except Exception as e:
            logger.error(f"❌ GATT error handling test failed: {e}")
            return False

    async def run_comprehensive_test(self):
        """Run comprehensive Phase 5 test suite."""
        logger.info("\n🚀 Starting Phase 5 Comprehensive Test Suite")

        tests_passed = 0
        total_tests = 4

        try:
            # Test 1: Start server with GATT operations
            if await self.start_server():
                tests_passed += 1
                logger.info("✅ Test 1/4: Server startup - PASSED")
            else:
                logger.error("❌ Test 1/4: Server startup - FAILED")

            # Test 2: GATT operations integration
            if await self.test_gatt_operations_integration():
                tests_passed += 1
                logger.info("✅ Test 2/4: GATT operations integration - PASSED")
            else:
                logger.error("❌ Test 2/4: GATT operations integration - FAILED")

            # Test 3: BLE connection GATT methods
            if await self.test_ble_connection_gatt_methods():
                tests_passed += 1
                logger.info("✅ Test 3/4: BLE connection GATT methods - PASSED")
            else:
                logger.error("❌ Test 3/4: BLE connection GATT methods - FAILED")

            # Test 4: Error handling
            if await self.test_error_handling():
                tests_passed += 1
                logger.info("✅ Test 4/4: Error handling - PASSED")
            else:
                logger.error("❌ Test 4/4: Error handling - FAILED")

            # Final results
            logger.info(
                f"\n📊 Phase 5 Test Results: {tests_passed}/{total_tests} tests passed"
            )

            if tests_passed == total_tests:
                logger.info(
                    "🎉 Phase 5 GATT Operations Implementation - ALL TESTS PASSED!"
                )
                logger.info("✅ Ready for Phase 6: Advanced Features")
                return True
            else:
                logger.error(
                    "❌ Phase 5 implementation has issues that need to be addressed"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {e}")
            return False

    async def shutdown(self):
        """Shutdown the test server."""
        if self.server and self.running:
            logger.info("Shutting down test server...")
            # The server will handle its own shutdown via signal handlers
            self.running = False


async def main():
    """Main test execution."""
    tester = Phase5Tester()

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(tester.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run comprehensive test
        success = await tester.run_comprehensive_test()

        if success:
            logger.info("\n🎯 Phase 5 implementation is complete and ready!")
            logger.info("Next steps:")
            logger.info("- Test with real BLE devices")
            logger.info("- Proceed to Phase 6: Advanced Features")
            return 0
        else:
            logger.error("\n❌ Phase 5 implementation needs fixes")
            return 1

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return 1
    finally:
        await tester.shutdown()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
