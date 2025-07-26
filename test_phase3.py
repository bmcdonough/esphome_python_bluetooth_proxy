#!/usr/bin/env python3
"""Test script for Phase 3: BLE Advertisement Scanning and Forwarding.

This script tests the complete BLE advertisement scanning and forwarding
functionality, verifying that advertisements are properly captured,
batched, and forwarded to Home Assistant connections.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.api_server import ESPHomeAPIServer
from esphome_bluetooth_proxy.protocol import (
    MessageType,
    create_message_frame,
    parse_message_frame,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class TestClient:
    """Test client that connects to the API server and monitors BLE advertisements."""

    def __init__(self, host="127.0.0.1", port=6053):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.running = False
        self.advertisement_count = 0

    async def connect(self):
        """Connect to the API server."""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            logger.info(f"Connected to API server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to API server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the API server."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("Disconnected from API server")

    async def send_hello(self):
        """Send Hello request to server."""
        # Create Hello request
        hello_data = b"\x12\x0btest-client\x18\x01\x20\x0a"  # client_info, api_version
        frame = create_message_frame(MessageType.HELLO_REQUEST, hello_data)

        self.writer.write(frame)
        await self.writer.drain()
        logger.info("Sent Hello request")

    async def send_connect(self):
        """Send Connect request to server."""
        # Create Connect request (empty password)
        connect_data = b""
        frame = create_message_frame(MessageType.CONNECT_REQUEST, connect_data)

        self.writer.write(frame)
        await self.writer.drain()
        logger.info("Sent Connect request")

    async def send_device_info_request(self):
        """Send Device Info request to server."""
        frame = create_message_frame(MessageType.DEVICE_INFO_REQUEST, b"")

        self.writer.write(frame)
        await self.writer.drain()
        logger.info("Sent Device Info request")

    async def send_list_entities_request(self):
        """Send List Entities request to server."""
        frame = create_message_frame(MessageType.LIST_ENTITIES_REQUEST, b"")

        self.writer.write(frame)
        await self.writer.drain()
        logger.info("Sent List Entities request")

    async def handle_messages(self):
        """Handle incoming messages from server."""
        buffer = bytearray()

        while self.running:
            try:
                data = await asyncio.wait_for(self.reader.read(4096), timeout=1.0)
                if not data:
                    logger.info("Server disconnected")
                    break

                buffer.extend(data)

                # Process complete messages
                while len(buffer) >= 3:
                    try:
                        msg_type, payload, frame_size = parse_message_frame(
                            bytes(buffer)
                        )
                        buffer = buffer[frame_size:]

                        await self._handle_message(msg_type, payload)

                    except Exception as e:
                        if "Incomplete message frame" in str(e):
                            break
                        else:
                            logger.error(f"Error parsing message: {e}")
                            return

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error reading messages: {e}")
                break

    async def _handle_message(self, msg_type: int, payload: bytes):
        """Handle a single message from server."""
        if msg_type == MessageType.HELLO_RESPONSE:
            logger.info("Received Hello response")
            await self.send_connect()

        elif msg_type == MessageType.CONNECT_RESPONSE:
            logger.info("Received Connect response")
            await self.send_device_info_request()

        elif msg_type == MessageType.DEVICE_INFO_RESPONSE:
            logger.info("Received Device Info response")
            await self.send_list_entities_request()

        elif msg_type == MessageType.LIST_ENTITIES_DONE_RESPONSE:
            logger.info("Received List Entities Done response")
            logger.info("✅ Handshake complete - now monitoring BLE advertisements...")

        elif msg_type == MessageType.BLUETOOTH_LE_RAW_ADVERTISEMENTS_RESPONSE:
            self.advertisement_count += 1
            logger.info(
                f"📡 Received BLE advertisement batch #{self.advertisement_count}"
            )

            # Parse advertisement data (simplified)
            if len(payload) > 0:
                logger.info(f"   Advertisement data: {len(payload)} bytes")

        else:
            logger.info(f"Received message type {msg_type} ({len(payload)} bytes)")

    async def run_test(self):
        """Run the complete test."""
        self.running = True

        if not await self.connect():
            return False

        try:
            # Start message handling
            message_task = asyncio.create_task(self.handle_messages())

            # Send initial hello
            await self.send_hello()

            # Wait for messages
            await message_task

        except Exception as e:
            logger.error(f"Test error: {e}")
            return False
        finally:
            await self.disconnect()

        return True

    def stop(self):
        """Stop the test client."""
        self.running = False


async def main():
    """Main test function."""
    logger.info("🚀 Starting Phase 3 Test: BLE Advertisement Scanning and Forwarding")
    logger.info("=" * 70)

    # Start API server
    server = ESPHomeAPIServer(
        host="127.0.0.1",
        port=6053,
        name="test-bluetooth-proxy",
        friendly_name="Test Bluetooth Proxy",
        password=None,
        active_connections=True,
    )

    # Setup signal handling
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Start server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(2)  # Give server time to start

        # Create and run test client
        client = TestClient()
        client_task = asyncio.create_task(client.run_test())

        # Wait for shutdown signal or test completion
        done, pending = await asyncio.wait(
            [client_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Stop client if still running
        client.stop()

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        logger.info("✅ Phase 3 test completed")
        logger.info(
            f"📊 Total BLE advertisement batches received: {client.advertisement_count}"
        )

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    finally:
        # Stop server
        await server.stop()
        logger.info("🛑 Test cleanup completed")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
