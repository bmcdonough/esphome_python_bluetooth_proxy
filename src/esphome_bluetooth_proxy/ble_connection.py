"""BLE Device Connection Management.

This module handles individual BLE device connections and GATT operations,
corresponding to the BluetoothConnection class in the ESPHome C++ implementation.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Dict, List, Optional

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

logger = logging.getLogger(__name__)


class ConnectionState(IntEnum):
    """BLE connection state."""

    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3


@dataclass
class BLEService:
    """BLE GATT service information."""

    uuid: bytes  # 16-byte UUID
    handle: int
    characteristics: List["BLECharacteristic"]


@dataclass
class BLECharacteristic:
    """BLE GATT characteristic information."""

    uuid: bytes  # 16-byte UUID
    handle: int
    properties: int  # Read/Write/Notify flags
    descriptors: List["BLEDescriptor"]


@dataclass
class BLEDescriptor:
    """BLE GATT descriptor information."""

    uuid: bytes  # 16-byte UUID
    handle: int


class BLEConnection:
    """Individual BLE device connection handler.

    This class corresponds to the BluetoothConnection class in the
    ESPHome C++ implementation, managing GATT operations for a single device.
    """

    def __init__(self, address: int, address_type: int, proxy):
        """Initialize BLE connection.

        Args:
            address: Device MAC address as uint64
            address_type: Address type (0=Public, 1=Random)
            proxy: Reference to main Bluetooth proxy
        """
        self.address = address
        self.address_type = address_type
        self.proxy = proxy

        # Convert address to string format for bleak
        self.address_str = self._address_to_string(address)

        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.client: Optional[BleakClient] = None
        self.mtu = 23  # Default MTU

        # Service discovery state
        self.services: List[BLEService] = []
        self.service_discovery_complete = False
        self.send_service_index = -2  # Match ESPHome: -2 = not started, -1 = done

        # GATT operation tracking
        self.pending_operations: Dict[int, asyncio.Future] = {}
        self.notification_handlers: Dict[int, Callable[[bytes], None]] = {}

        logger.debug(f"Created BLE connection for {self.address_str}")

    def _address_to_string(self, address: int) -> str:
        """Convert uint64 address to MAC string format.

        Args:
            address: MAC address as uint64

        Returns:
            str: MAC address in XX:XX:XX:XX:XX:XX format
        """
        mac_bytes = []
        for i in range(6):
            mac_bytes.append((address >> (i * 8)) & 0xFF)
        mac_bytes.reverse()
        return ":".join(f"{b:02X}" for b in mac_bytes)

    async def connect(self) -> bool:
        """Connect to the BLE device.

        Returns:
            bool: True if connection successful
        """
        if self.state != ConnectionState.DISCONNECTED:
            logger.warning(
                f"Connection to {self.address_str} already in progress or connected"
            )
            return False

        logger.info(f"Connecting to BLE device {self.address_str}")
        self.state = ConnectionState.CONNECTING

        try:
            self.client = BleakClient(self.address_str)
            await self.client.connect()

            self.state = ConnectionState.CONNECTED
            self.mtu = await self._get_mtu()

            logger.info(f"Connected to {self.address_str} (MTU: {self.mtu})")

            # Notify proxy of connection
            if self.proxy:
                await self.proxy.on_device_connected(self.address, True, self.mtu)

            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.address_str}: {e}")
            self.state = ConnectionState.DISCONNECTED
            self.client = None

            # Notify proxy of connection failure
            if self.proxy:
                await self.proxy.on_device_connected(self.address, False, 0, str(e))

            return False

    async def disconnect(self) -> None:
        """Disconnect from the BLE device."""
        if self.state == ConnectionState.DISCONNECTED:
            return

        logger.info(f"Disconnecting from BLE device {self.address_str}")
        self.state = ConnectionState.DISCONNECTING

        try:
            # Cancel pending operations
            for future in self.pending_operations.values():
                if not future.done():
                    future.cancel()
            self.pending_operations.clear()

            # Clear notification handlers
            self.notification_handlers.clear()

            # Disconnect client
            if self.client and self.client.is_connected:
                await self.client.disconnect()

            self.state = ConnectionState.DISCONNECTED
            self.client = None

            logger.info(f"Disconnected from {self.address_str}")

            # Notify proxy of disconnection
            if self.proxy:
                await self.proxy.on_device_connected(self.address, False, 0)

        except Exception as e:
            logger.error(f"Error disconnecting from {self.address_str}: {e}")
            self.state = ConnectionState.DISCONNECTED
            self.client = None

    async def discover_services(self) -> List[BLEService]:
        """Discover GATT services on the device.

        Returns:
            List[BLEService]: List of discovered services
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        logger.info(f"Discovering services for {self.address_str}")

        try:
            # Get services from bleak
            bleak_services = self.client.services

            # Convert to our format
            self.services = []
            for service in bleak_services:
                characteristics = []

                for char in service.characteristics:
                    descriptors = []
                    for desc in char.descriptors:
                        descriptors.append(
                            BLEDescriptor(
                                uuid=self._uuid_to_bytes(desc.uuid), handle=desc.handle
                            )
                        )

                    characteristics.append(
                        BLECharacteristic(
                            uuid=self._uuid_to_bytes(char.uuid),
                            handle=char.handle,
                            properties=self._convert_properties(char.properties),
                            descriptors=descriptors,
                        )
                    )

                self.services.append(
                    BLEService(
                        uuid=self._uuid_to_bytes(service.uuid),
                        handle=service.handle,
                        characteristics=characteristics,
                    )
                )

            self.service_discovery_complete = True
            self.send_service_index = 0  # Start sending services

            logger.info(
                f"Discovered {len(self.services)} services for {self.address_str}"
            )
            return self.services

        except Exception as e:
            logger.error(f"Service discovery failed for {self.address_str}: {e}")
            raise

    def _uuid_to_bytes(self, uuid_str: str) -> bytes:
        """Convert UUID string to 16-byte array.

        Args:
            uuid_str: UUID string

        Returns:
            bytes: 16-byte UUID
        """
        # Remove hyphens and convert to bytes
        uuid_hex = uuid_str.replace("-", "")
        if len(uuid_hex) == 4:  # 16-bit UUID
            uuid_hex = "0000" + uuid_hex + "00001000800000805f9b34fb"
        elif len(uuid_hex) == 8:  # 32-bit UUID
            uuid_hex = uuid_hex + "00001000800000805f9b34fb"

        return bytes.fromhex(uuid_hex)

    def _convert_properties(self, bleak_properties: List[str]) -> int:
        """Convert bleak properties to ESPHome format.

        Args:
            bleak_properties: List of property strings from bleak

        Returns:
            int: Properties as bit flags
        """
        properties = 0
        prop_map = {
            "read": 0x02,
            "write-without-response": 0x04,
            "write": 0x08,
            "notify": 0x10,
            "indicate": 0x20,
        }

        for prop in bleak_properties:
            if prop in prop_map:
                properties |= prop_map[prop]

        return properties

    async def _get_mtu(self) -> int:
        """Get connection MTU.

        Returns:
            int: MTU size
        """
        try:
            # Try to get MTU from client (not all backends support this)
            if hasattr(self.client, "mtu_size"):
                return self.client.mtu_size
            return 23  # Default MTU
        except Exception:
            return 23

    async def read_characteristic(self, handle: int) -> bytes:
        """Read characteristic value.

        Args:
            handle: Characteristic handle

        Returns:
            bytes: Characteristic value
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        try:
            # Find characteristic by handle
            char = self._find_characteristic_by_handle(handle)
            if not char:
                raise ValueError(f"Characteristic with handle {handle} not found")

            # Read value
            value = await self.client.read_gatt_char(char.uuid)
            logger.debug(
                f"Read {len(value)} bytes from handle {handle} on {self.address_str}"
            )
            return value

        except Exception as e:
            logger.error(
                f"Failed to read characteristic {handle} on {self.address_str}: {e}"
            )
            raise

    async def write_characteristic(
        self, handle: int, data: bytes, response: bool = True
    ) -> bool:
        """Write characteristic value.

        Args:
            handle: Characteristic handle
            data: Data to write
            response: Whether to wait for write response

        Returns:
            bool: True if write successful
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        try:
            # Find characteristic by handle
            char = self._find_characteristic_by_handle(handle)
            if not char:
                raise ValueError(f"Characteristic with handle {handle} not found")

            # Write value
            await self.client.write_gatt_char(char.uuid, data, response=response)
            logger.debug(
                f"Wrote {len(data)} bytes to handle {handle} on {self.address_str}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to write characteristic {handle} on {self.address_str}: {e}"
            )
            return False

    def _find_characteristic_by_handle(
        self, handle: int
    ) -> Optional[BleakGATTCharacteristic]:
        """Find bleak characteristic by handle.

        Args:
            handle: Characteristic handle

        Returns:
            Optional[BleakGATTCharacteristic]: Characteristic if found
        """
        if not self.client:
            return None

        for service in self.client.services:
            for char in service.characteristics:
                if char.handle == handle:
                    return char
        return None

    def _find_descriptor_by_handle(self, handle: int):
        """Find bleak descriptor by handle.

        Args:
            handle: Descriptor handle

        Returns:
            Optional[BleakGATTDescriptor]: Descriptor if found
        """
        if not self.client:
            return None

        for service in self.client.services:
            for char in service.characteristics:
                for desc in char.descriptors:
                    if desc.handle == handle:
                        return desc
        return None

    async def read_descriptor(self, handle: int) -> bytes:
        """Read descriptor value.

        Args:
            handle: Descriptor handle

        Returns:
            bytes: Descriptor value
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        try:
            # Find descriptor by handle
            desc = self._find_descriptor_by_handle(handle)
            if not desc:
                raise ValueError(f"Descriptor with handle {handle} not found")

            # Read value
            value = await self.client.read_gatt_descriptor(desc.uuid)
            logger.debug(
                f"Read {len(value)} bytes from descriptor {handle} on {self.address_str}"
            )
            return value

        except Exception as e:
            logger.error(
                f"Failed to read descriptor {handle} on {self.address_str}: {e}"
            )
            raise

    async def write_descriptor(self, handle: int, data: bytes) -> bool:
        """Write descriptor value.

        Args:
            handle: Descriptor handle
            data: Data to write

        Returns:
            bool: True if write successful
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        try:
            # Find descriptor by handle
            desc = self._find_descriptor_by_handle(handle)
            if not desc:
                raise ValueError(f"Descriptor with handle {handle} not found")

            # Write value
            await self.client.write_gatt_descriptor(desc.uuid, data)
            logger.debug(
                f"Wrote {len(data)} bytes to descriptor {handle} on {self.address_str}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to write descriptor {handle} on {self.address_str}: {e}"
            )
            return False

    async def start_notify(self, handle: int, callback: Callable[[bytes], None]) -> bool:
        """Start notifications for a characteristic.

        Args:
            handle: Characteristic handle
            callback: Callback function for notification data

        Returns:
            bool: True if notification started successfully
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        try:
            # Find characteristic by handle
            char = self._find_characteristic_by_handle(handle)
            if not char:
                raise ValueError(f"Characteristic with handle {handle} not found")

            # Start notifications
            await self.client.start_notify(char.uuid, callback)
            self.notification_handlers[handle] = callback
            
            logger.debug(
                f"Started notifications for handle {handle} on {self.address_str}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to start notifications for handle {handle} on {self.address_str}: {e}"
            )
            return False

    async def stop_notify(self, handle: int) -> bool:
        """Stop notifications for a characteristic.

        Args:
            handle: Characteristic handle

        Returns:
            bool: True if notification stopped successfully
        """
        if not self.is_connected():
            raise RuntimeError("Device not connected")

        try:
            # Find characteristic by handle
            char = self._find_characteristic_by_handle(handle)
            if not char:
                raise ValueError(f"Characteristic with handle {handle} not found")

            # Stop notifications
            await self.client.stop_notify(char.uuid)
            
            # Remove callback
            if handle in self.notification_handlers:
                del self.notification_handlers[handle]
            
            logger.debug(
                f"Stopped notifications for handle {handle} on {self.address_str}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to stop notifications for handle {handle} on {self.address_str}: {e}"
            )
            return False

    def is_connected(self) -> bool:
        """Check if device is connected.

        Returns:
            bool: True if connected
        """
        return (
            self.state == ConnectionState.CONNECTED
            and self.client
            and self.client.is_connected
        )

    def get_mtu(self) -> int:
        """Get connection MTU.

        Returns:
            int: MTU size
        """
        return self.mtu

    def __str__(self) -> str:
        """String representation of connection."""
        return f"BLEConnection({self.address_str}, {self.state.name})"
