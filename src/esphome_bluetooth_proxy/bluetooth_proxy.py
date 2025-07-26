"""Main Bluetooth Proxy Coordinator.

This module implements the main BluetoothProxy class that coordinates all
Bluetooth operations, corresponding to the BluetoothProxy class in the
ESPHome C++ implementation.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from .advertisement_batcher import AdvertisementBatcher
from .ble_connection import BLEConnection
from .ble_scanner import BLEAdvertisement, BLEScanner
from .connection import APIConnection
from .gatt_operations import GATTOperationHandler

if TYPE_CHECKING:
    from .api_server import ESPHomeAPIServer

logger = logging.getLogger(__name__)


class BluetoothProxy:
    """Main Bluetooth proxy coordinator.

    This class corresponds to the BluetoothProxy class in the ESPHome C++
    implementation, managing all Bluetooth operations including scanning,
    connections, and GATT operations.
    """

    def __init__(self, api_server: "ESPHomeAPIServer", max_connections: int = 3):
        """Initialize Bluetooth proxy.

        Args:
            api_server: ESPHome API server instance
            max_connections: Maximum number of concurrent BLE connections
        """
        self.api_server = api_server
        self.max_connections = max_connections

        # Scanner and advertisement handling
        self.scanner: Optional[BLEScanner] = None
        self.advertisement_batcher: Optional[AdvertisementBatcher] = None
        self.scanning_enabled = False

        # Connection management
        self.connections: Dict[int, BLEConnection] = {}  # address -> connection
        self.connection_pool: List[BLEConnection] = []

        # GATT operations handler
        self.gatt_handler = GATTOperationHandler(self)

        # API connection tracking
        self.subscribed_connections: List[APIConnection] = []

        # State
        self.active = False
        self.running = False

        logger.info(f"Bluetooth proxy initialized (max_connections={max_connections})")

    async def start(self) -> None:
        """Start the Bluetooth proxy."""
        if self.running:
            logger.warning("Bluetooth proxy is already running")
            return

        logger.info("Starting Bluetooth proxy")

        try:
            # Initialize scanner
            self.scanner = BLEScanner(callback=self._on_advertisement)

            # Initialize advertisement batcher
            self.advertisement_batcher = AdvertisementBatcher(
                send_callback=self._send_advertisement_batch
            )

            # Initialize connection pool
            self._initialize_connection_pool()

            # Start BLE scanning
            await self._start_scanning()

            self.running = True
            logger.info("Bluetooth proxy started successfully")

        except Exception as e:
            logger.error(f"Failed to start Bluetooth proxy: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Bluetooth proxy."""
        if not self.running:
            return

        logger.info("Stopping Bluetooth proxy")

        try:
            # Stop scanning
            if self.scanner and self.scanner.is_scanning():
                await self.scanner.stop_scanning()

            # Disconnect all devices
            disconnect_tasks = []
            for connection in self.connections.values():
                if connection.is_connected():
                    disconnect_tasks.append(connection.disconnect())

            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)

            # Clear state
            self.connections.clear()
            self.subscribed_connections.clear()

            self.running = False
            logger.info("Bluetooth proxy stopped")

        except Exception as e:
            logger.error(f"Error stopping Bluetooth proxy: {e}")

    def _initialize_connection_pool(self) -> None:
        """Initialize the BLE connection pool."""
        self.connection_pool = []
        for i in range(self.max_connections):
            # Create placeholder connections (will be assigned addresses when needed)
            connection = BLEConnection(0, 0, self)
            self.connection_pool.append(connection)

        logger.debug(
            f"Initialized connection pool with {len(self.connection_pool)} slots"
        )

    async def subscribe_api_connection(
        self, api_connection: APIConnection, flags: int
    ) -> None:
        """Subscribe API connection for Bluetooth events.

        Args:
            api_connection: API connection to subscribe
            flags: Subscription flags
        """
        if api_connection in self.subscribed_connections:
            logger.warning(f"API connection {api_connection} already subscribed")
            return

        self.subscribed_connections.append(api_connection)
        logger.info(f"Subscribed API connection {api_connection} (flags=0x{flags:02x})")

        # Start scanning if this is the first subscription
        if len(self.subscribed_connections) == 1 and not self.scanning_enabled:
            await self._start_scanning()

        # Send current scanner state
        await self._send_scanner_state(api_connection)

    async def unsubscribe_api_connection(self, api_connection: APIConnection) -> None:
        """Unsubscribe API connection from Bluetooth events.

        Args:
            api_connection: API connection to unsubscribe
        """
        if api_connection not in self.subscribed_connections:
            logger.warning(f"API connection {api_connection} not subscribed")
            return

        self.subscribed_connections.remove(api_connection)
        logger.info(f"Unsubscribed API connection {api_connection}")

        # Stop scanning if no more subscriptions
        if len(self.subscribed_connections) == 0 and self.scanning_enabled:
            await self._stop_scanning()

    async def _start_scanning(self) -> None:
        """Start BLE scanning."""
        if self.scanning_enabled or not self.scanner:
            return

        logger.info("Starting BLE scanning")

        try:
            await self.scanner.start_scanning(
                active=True
            )  # Start with active scanning (more reliable)
            self.scanning_enabled = True

            # Notify all subscribed connections
            for connection in self.subscribed_connections:
                await self._send_scanner_state(connection)

        except Exception as e:
            logger.error(f"Failed to start BLE scanning: {e}")

    async def _stop_scanning(self) -> None:
        """Stop BLE scanning."""
        if not self.scanning_enabled or not self.scanner:
            return

        logger.info("Stopping BLE scanning")

        try:
            await self.scanner.stop_scanning()
            self.scanning_enabled = False

            # Flush any pending advertisements
            if self.advertisement_batcher:
                await self.advertisement_batcher.force_flush()

            # Notify all subscribed connections
            for connection in self.subscribed_connections:
                await self._send_scanner_state(connection)

        except Exception as e:
            logger.error(f"Failed to stop BLE scanning: {e}")

    def _on_advertisement(self, advertisement: BLEAdvertisement) -> None:
        """Handle received BLE advertisement.

        Args:
            advertisement: Received BLE advertisement
        """
        if not self.advertisement_batcher:
            return

        # Add to batch for efficient transmission
        self.advertisement_batcher.add_advertisement(advertisement)

    def _send_advertisement_batch(self, advertisements: List[BLEAdvertisement]):
        """Send batch of advertisements to subscribed connections.

        Args:
            advertisements: List of advertisements to send
        """
        logger.debug(
            f"Sending advertisement batch ({len(advertisements)} advertisements) "
            f"to {len(self.subscribed_connections)} connections"
        )

        # Send advertisements to subscribed API connections
        for api_connection in self.subscribed_connections:
            if api_connection.is_bluetooth_subscribed():
                asyncio.create_task(
                    api_connection.send_bluetooth_le_advertisements(advertisements)
                )

    async def _send_scanner_state(self, api_connection: APIConnection) -> None:
        """Send scanner state to API connection.

        Args:
            api_connection: API connection to send state to
        """
        # TODO: Implement scanner state message
        # This will be implemented when we add the protobuf messages
        logger.debug(
            f"Sending scanner state to {api_connection} "
            f"(scanning={self.scanning_enabled})"
        )

    async def connect_device(self, address: int, address_type: int) -> bool:
        """Connect to a BLE device.

        Args:
            address: Device MAC address as uint64
            address_type: Address type (0=Public, 1=Random)

        Returns:
            bool: True if connection initiated successfully
        """
        if address in self.connections:
            logger.warning(f"Device {address:012X} already connected or connecting")
            return False

        # Find available connection slot
        available_connection = None
        for connection in self.connection_pool:
            if not connection.is_connected() and connection.address == 0:
                available_connection = connection
                break

        if not available_connection:
            logger.warning(f"No available connection slots for device {address:012X}")
            return False

        # Configure connection for this device
        available_connection.address = address
        available_connection.address_type = address_type
        available_connection.address_str = available_connection._address_to_string(
            address
        )

        # Add to active connections
        self.connections[address] = available_connection

        # Start connection
        logger.info(f"Initiating connection to device {address:012X}")
        asyncio.create_task(available_connection.connect())

        return True

    async def disconnect_device(self, address: int) -> bool:
        """Disconnect from a BLE device.

        Args:
            address: Device MAC address as uint64

        Returns:
            bool: True if disconnection initiated successfully
        """
        if address not in self.connections:
            logger.warning(f"Device {address:012X} not connected")
            return False

        connection = self.connections[address]
        logger.info(f"Initiating disconnection from device {address:012X}")

        # Start disconnection
        asyncio.create_task(connection.disconnect())

        return True

    async def on_device_connected(
        self, address: int, connected: bool, mtu: int = 0, error: str = ""
    ) -> None:
        """Handle device connection state change.

        Args:
            address: Device MAC address
            connected: Whether device is connected
            mtu: Connection MTU (if connected)
            error: Error message (if connection failed)
        """
        logger.info(
            f"Device {address:012X} connection state: connected={connected} MTU={mtu}"
        )

        if not connected:
            # Remove from active connections and return to pool
            if address in self.connections:
                connection = self.connections[address]
                del self.connections[address]

                # Reset connection for reuse
                connection.address = 0
                connection.address_type = 0
                connection.address_str = ""

        # TODO: Send connection state to subscribed API connections
        # This will be implemented when we add the protobuf messages

    def get_free_connections(self) -> int:
        """Get number of free connection slots.

        Returns:
            int: Number of available connection slots
        """
        return self.max_connections - len(self.connections)

    def get_connection_limit(self) -> int:
        """Get maximum number of connections.

        Returns:
            int: Maximum connection limit
        """
        return self.max_connections

    def set_active(self, active: bool) -> None:
        """Set active connection support.

        Args:
            active: Whether to support active connections
        """
        if self.active != active:
            self.active = active
            self.api_server.set_active_connections(active)
            logger.info(f"Active connections {'enabled' if active else 'disabled'}")

    def has_active(self) -> bool:
        """Check if active connections are supported.

        Returns:
            bool: True if active connections are supported
        """
        return self.active

    async def set_scanner_mode(self, active: bool) -> None:
        """Set scanner mode (active/passive).

        Args:
            active: Whether to use active scanning
        """
        if self.scanner:
            self.scanner.set_scan_mode(active)
            logger.info(f"Scanner mode set to {'active' if active else 'passive'}")

    def get_stats(self) -> dict:
        """Get Bluetooth proxy statistics.

        Returns:
            dict: Statistics about proxy operation
        """
        stats = {
            "running": self.running,
            "scanning_enabled": self.scanning_enabled,
            "active_connections": self.active,
            "connected_devices": len(self.connections),
            "free_connections": self.get_free_connections(),
            "max_connections": self.max_connections,
            "subscribed_api_connections": len(self.subscribed_connections),
        }

        if self.scanner:
            stats["scanner_mode"] = self.scanner.get_scan_mode()
            stats["scanner_active"] = self.scanner.is_scanning()

        if self.advertisement_batcher:
            stats["advertisement_batcher"] = self.advertisement_batcher.get_stats()

        return stats
