"""ESPHome API Server.

This module implements the main ESPHome API server that handles client connections
and implements the 4-step handshake protocol.
"""

import asyncio
import logging
import signal
import sys
from asyncio import StreamReader, StreamWriter
from typing import List, Optional

from .connection import APIConnection
from .device_info import DeviceInfoProvider

logger = logging.getLogger(__name__)


class ESPHomeAPIServer:
    """Main ESPHome API server implementing the 4-step handshake."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 6053,
        name: str = "python-bluetooth-proxy",
        friendly_name: str = "Python Bluetooth Proxy",
        password: Optional[str] = None,
        active_connections: bool = False,
    ):
        """Initialize the API server.

        Args:
            host: Host to bind to
            port: Port to bind to
            name: Device name
            friendly_name: Human-readable device name
            password: Optional API password
            active_connections: Whether to support active BLE connections
        """
        self.host = host
        self.port = port
        self.password = password

        # Device information provider
        self.device_info_provider = DeviceInfoProvider(
            name=name,
            friendly_name=friendly_name,
            password=password,
            active_connections=active_connections,
        )

        # Connection management
        self.connections: List[APIConnection] = []
        self.server: Optional[asyncio.Server] = None
        self.running = False
        self._shutdown_requested = False

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        if self._shutdown_requested:
            return  # Already shutting down, ignore additional signals

        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_requested = True
        self.running = False

        # Set the shutdown flag for the event loop to handle
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self._shutdown()))
        except RuntimeError:
            # No running loop, exit immediately
            sys.exit(0)

    async def start(self) -> None:
        """Start the API server."""
        if self.running:
            logger.warning("Server is already running")
            return

        try:
            self.server = await asyncio.start_server(
                self._handle_client, self.host, self.port
            )

            self.running = True

            addr = self.server.sockets[0].getsockname()
            logger.info(f"ESPHome API server started on {addr[0]}:{addr[1]}")
            logger.info(f"Device: {self.device_info_provider.friendly_name}")
            logger.info(f"MAC: {self.device_info_provider.mac_address}")
            logger.info(
                f"Bluetooth MAC: {self.device_info_provider.bluetooth_mac_address}"
            )
            logger.info(
                f"Features: 0x{self.device_info_provider.get_feature_flags():02x}"
            )

            if self.password:
                logger.info("API password protection enabled")
            else:
                logger.info("API password protection disabled")

            # Start serving
            async with self.server:
                try:
                    await self.server.serve_forever()
                except asyncio.CancelledError:
                    logger.info("Server serve_forever cancelled")
                    pass

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise

    async def _shutdown(self) -> None:
        """Internal shutdown method called from signal handler."""
        await self.stop()

        # Get current task to avoid cancelling ourselves
        current_task = asyncio.current_task()
        tasks = [
            task
            for task in asyncio.all_tasks()
            if not task.done() and task is not current_task
        ]

        if tasks:
            logger.info(f"Cancelling {len(tasks)} remaining tasks...")
            for task in tasks:
                if not task.cancelled():
                    task.cancel()

            # Wait for tasks to complete cancellation with timeout
            if tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True), timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Some tasks did not complete cancellation within timeout"
                    )
                except Exception as e:
                    logger.warning(f"Error during task cancellation: {e}")

        # Stop the event loop
        try:
            loop = asyncio.get_running_loop()
            loop.stop()
        except Exception as e:
            logger.warning(f"Error stopping event loop: {e}")

    async def stop(self) -> None:
        """Stop the API server."""
        if not self.running:
            return

        logger.info("Stopping API server...")
        self.running = False

        # Close all client connections
        close_tasks = []
        for connection in self.connections[
            :
        ]:  # Copy list to avoid modification during iteration
            close_tasks.append(connection.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        # Stop the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("API server stopped")

    async def _handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        """Handle a new client connection."""
        connection = APIConnection(
            reader=reader,
            writer=writer,
            device_info_provider=self.device_info_provider.get_device_info,
            password=self.password,
        )

        # Add to connection list
        self.connections.append(connection)

        try:
            # Handle the connection
            await connection.handle_connection()
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
        finally:
            # Remove from connection list
            if connection in self.connections:
                self.connections.remove(connection)

    def get_authenticated_connections(self) -> List[APIConnection]:
        """Get list of authenticated connections."""
        return [conn for conn in self.connections if conn.is_authenticated()]

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len([conn for conn in self.connections if conn.is_connected()])

    async def broadcast_message(self, msg_type: int, payload: bytes) -> None:
        """Broadcast a message to all authenticated connections."""
        authenticated_connections = self.get_authenticated_connections()

        if not authenticated_connections:
            return

        # Send to all authenticated connections
        send_tasks = []
        for connection in authenticated_connections:
            send_tasks.append(connection.send_message(msg_type, payload))

        # Wait for all sends to complete
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    def set_active_connections(self, active: bool) -> None:
        """Enable or disable active connection support."""
        self.device_info_provider.set_active_connections(active)
        logger.info(f"Active connections {'enabled' if active else 'disabled'}")

    def has_active_connections(self) -> bool:
        """Check if active connections are supported."""
        return self.device_info_provider.has_active_connections()


async def main() -> None:
    """Main entry point for testing the API server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and start server
    server = ESPHomeAPIServer(
        name="test-bluetooth-proxy",
        friendly_name="Test Python Bluetooth Proxy",
        password=None,  # No password for testing
        active_connections=False,  # Start with passive scanning only
    )

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except asyncio.CancelledError:
        logger.info("Main task cancelled")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        if server.running:
            await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
