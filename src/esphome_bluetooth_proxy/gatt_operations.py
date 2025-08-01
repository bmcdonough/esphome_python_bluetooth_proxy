"""GATT Operations Handler.

This module handles GATT read/write operations and notifications,
corresponding to the GATT functionality in the ESPHome C++ implementation.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional

from .ble_connection import BLEConnection
from .protocol import (
    BluetoothGATTNotifyDataResponse,
    BluetoothGATTReadResponse,
    BluetoothGATTWriteResponse,
    MessageEncoder,
    MessageType,
)

logger = logging.getLogger(__name__)


@dataclass
class GATTOperation:
    """Represents a pending GATT operation."""

    operation_type: str  # 'read', 'write', 'read_descriptor', 'write_descriptor'
    handle: int
    data: Optional[bytes] = None
    response_required: bool = True
    future: Optional[asyncio.Future] = None


class GATTOperationHandler:
    """Handles GATT read/write operations and notifications.

    This class manages GATT operations for BLE connections, providing
    the interface between the ESPHome API and the actual BLE operations.
    """

    def __init__(self, bluetooth_proxy):
        """Initialize GATT operation handler.

        Args:
            bluetooth_proxy: Reference to main Bluetooth proxy
        """
        self.bluetooth_proxy = bluetooth_proxy
        self.pending_operations: Dict[str, GATTOperation] = {}
        self.notification_subscriptions: Dict[int, Dict[int, bool]] = (
            {}
        )  # address -> {handle -> enabled}
        self.encoder = MessageEncoder()

        logger.debug("GATT operation handler initialized")

    async def handle_gatt_read_request(self, address: int, handle: int) -> None:
        """Handle GATT characteristic read request.

        Args:
            address: Device address
            handle: Characteristic handle
        """
        logger.debug(f"GATT read request: device={address:012X} handle={handle}")

        try:
            # Get connection
            connection = self._get_connection(address)
            if not connection:
                await self._send_gatt_error(address, handle, "Device not connected")
                return

            # Perform read operation
            data = await connection.read_characteristic(handle)

            # Send response
            await self._send_gatt_read_response(address, handle, data)

        except Exception as e:
            logger.error(f"GATT read failed for {address:012X} handle {handle}: {e}")
            await self._send_gatt_error(address, handle, str(e))

    async def handle_gatt_write_request(
        self, address: int, handle: int, data: bytes, response: bool = True
    ) -> None:
        """Handle GATT characteristic write request.

        Args:
            address: Device address
            handle: Characteristic handle
            data: Data to write
            response: Whether write response is required
        """
        logger.debug(
            f"GATT write request: device={address:012X} handle={handle} "
            f"data={len(data)} bytes response={response}"
        )

        try:
            # Get connection
            connection = self._get_connection(address)
            if not connection:
                await self._send_gatt_error(address, handle, "Device not connected")
                return

            # Perform write operation
            success = await connection.write_characteristic(handle, data, response)

            # Send response if required
            if response:
                if success:
                    await self._send_gatt_write_response(address, handle)
                else:
                    await self._send_gatt_error(address, handle, "Write failed")

        except Exception as e:
            logger.error(f"GATT write failed for {address:012X} handle {handle}: {e}")
            if response:
                await self._send_gatt_error(address, handle, str(e))

    async def handle_gatt_read_descriptor_request(
        self, address: int, handle: int
    ) -> None:
        """Handle GATT descriptor read request.

        Args:
            address: Device address
            handle: Descriptor handle
        """
        logger.debug(
            f"GATT descriptor read request: device={address:012X} handle={handle}"
        )

        try:
            # Get connection
            connection = self._get_connection(address)
            if not connection:
                await self._send_gatt_error(address, handle, "Device not connected")
                return

            # Perform descriptor read operation
            data = await connection.read_descriptor(handle)

            # Send response
            await self._send_gatt_read_response(address, handle, data)

        except Exception as e:
            logger.error(
                f"GATT descriptor read failed for {address:012X} handle {handle}: {e}"
            )
            await self._send_gatt_error(address, handle, str(e))

    async def handle_gatt_write_descriptor_request(
        self, address: int, handle: int, data: bytes, response: bool = True
    ) -> None:
        """Handle GATT descriptor write request.

        Args:
            address: Device address
            handle: Descriptor handle
            data: Data to write
            response: Whether write response is required
        """
        logger.debug(
            f"GATT descriptor write request: device={address:012X} handle={handle} "
            f"data={len(data)} bytes response={response}"
        )

        try:
            # Get connection
            connection = self._get_connection(address)
            if not connection:
                await self._send_gatt_error(address, handle, "Device not connected")
                return

            # Perform descriptor write operation
            success = await connection.write_descriptor(handle, data)

            # Send response if required
            if response:
                if success:
                    await self._send_gatt_write_response(address, handle)
                else:
                    await self._send_gatt_error(address, handle, "Write failed")

        except Exception as e:
            logger.error(
                f"GATT descriptor write failed for {address:012X} handle {handle}: {e}"
            )
            if response:
                await self._send_gatt_error(address, handle, str(e))

    async def handle_gatt_notify_request(
        self, address: int, handle: int, enable: bool
    ) -> None:
        """Handle GATT notification subscription request.

        Args:
            address: Device address
            handle: Characteristic handle
            enable: Whether to enable or disable notifications
        """
        logger.debug(
            f"GATT notify request: device={address:012X} handle={handle} "
            f"enable={enable}"
        )

        try:
            # Get connection
            connection = self._get_connection(address)
            if not connection:
                await self._send_gatt_error(address, handle, "Device not connected")
                return

            # Update subscription state
            if address not in self.notification_subscriptions:
                self.notification_subscriptions[address] = {}
            self.notification_subscriptions[address][handle] = enable

            # Handle notification subscription
            if enable:
                # Create callback that forwards notifications
                def notification_callback(data: bytes):
                    # Schedule the async notification forwarding
                    asyncio.create_task(
                        self.handle_notification_data(address, handle, data)
                    )

                # Start notifications
                success = await connection.start_notify(handle, notification_callback)
                if not success:
                    await self._send_gatt_error(
                        address, handle, "Failed to enable notifications"
                    )
                    return
            else:
                # Stop notifications
                success = await connection.stop_notify(handle)
                if not success:
                    await self._send_gatt_error(
                        address, handle, "Failed to disable notifications"
                    )
                    return

            logger.debug(
                f"Notification {'enabled' if enable else 'disabled'} for "
                f"device {address:012X} handle {handle}"
            )

        except Exception as e:
            logger.error(
                f"GATT notify request failed for {address:012X} handle {handle}: {e}"
            )
            await self._send_gatt_error(address, handle, str(e))

    async def handle_notification_data(
        self, address: int, handle: int, data: bytes
    ) -> None:
        """Handle incoming notification data from device.

        Args:
            address: Device address
            handle: Characteristic handle
            data: Notification data
        """
        logger.debug(
            f"Notification data: device={address:012X} handle={handle} "
            f"data={len(data)} bytes"
        )

        # Check if notifications are enabled for this handle
        if (
            address in self.notification_subscriptions
            and handle in self.notification_subscriptions[address]
            and self.notification_subscriptions[address][handle]
        ):
            # Send notification to subscribed API connections
            await self._send_gatt_notification(address, handle, data)
        else:
            logger.debug(f"Ignoring notification for unsubscribed handle {handle}")

    def _get_connection(self, address: int) -> Optional[BLEConnection]:
        """Get BLE connection for address.

        Args:
            address: Device address

        Returns:
            Optional[BLEConnection]: Connection if found and connected
        """
        if not self.bluetooth_proxy:
            return None

        connection = self.bluetooth_proxy.connections.get(address)
        if connection and connection.is_connected():
            return connection

        return None

    async def _send_gatt_read_response(
        self, address: int, handle: int, data: bytes
    ) -> None:
        """Send GATT read response.

        Args:
            address: Device address
            handle: Characteristic handle
            data: Read data
        """
        try:
            response = BluetoothGATTReadResponse(
                address=address, handle=handle, data=data, error=0
            )
            payload = self.encoder.encode_bluetooth_gatt_read_response(response)

            # Send to all subscribed API connections
            if self.bluetooth_proxy and self.bluetooth_proxy.api_server:
                for connection in self.bluetooth_proxy.api_server.connections:
                    if connection.is_authenticated():
                        await connection.send_message(
                            MessageType.BLUETOOTH_GATT_READ_RESPONSE, payload
                        )

            logger.debug(
                f"Sent GATT read response: device={address:012X} handle={handle} "
                f"data={len(data)} bytes"
            )
        except Exception as e:
            logger.error(f"Error sending GATT read response: {e}")

    async def _send_gatt_write_response(self, address: int, handle: int) -> None:
        """Send GATT write response.

        Args:
            address: Device address
            handle: Characteristic handle
        """
        try:
            response = BluetoothGATTWriteResponse(
                address=address, handle=handle, error=0
            )
            payload = self.encoder.encode_bluetooth_gatt_write_response(response)

            # Send to all subscribed API connections
            if self.bluetooth_proxy and self.bluetooth_proxy.api_server:
                for connection in self.bluetooth_proxy.api_server.connections:
                    if connection.is_authenticated():
                        await connection.send_message(
                            MessageType.BLUETOOTH_GATT_WRITE_RESPONSE, payload
                        )

            logger.debug(
                f"Sent GATT write response: device={address:012X} handle={handle}"
            )
        except Exception as e:
            logger.error(f"Error sending GATT write response: {e}")

    async def _send_gatt_notification(
        self, address: int, handle: int, data: bytes
    ) -> None:
        """Send GATT notification to API connections.

        Args:
            address: Device address
            handle: Characteristic handle
            data: Notification data
        """
        try:
            response = BluetoothGATTNotifyDataResponse(
                address=address, handle=handle, data=data
            )
            payload = self.encoder.encode_bluetooth_gatt_notify_data_response(response)

            # Send to all subscribed API connections
            if self.bluetooth_proxy and self.bluetooth_proxy.api_server:
                for connection in self.bluetooth_proxy.api_server.connections:
                    if connection.is_authenticated():
                        await connection.send_message(
                            MessageType.BLUETOOTH_GATT_NOTIFY_DATA_RESPONSE, payload
                        )

            logger.debug(
                f"Sent GATT notification: device={address:012X} handle={handle} "
                f"data={len(data)} bytes"
            )
        except Exception as e:
            logger.error(f"Error sending GATT notification: {e}")

    async def _send_gatt_error(self, address: int, handle: int, error: str) -> None:
        """Send GATT error response.

        Args:
            address: Device address
            handle: Characteristic/descriptor handle
            error: Error message
        """
        try:
            # Send error as read response with error code
            response = BluetoothGATTReadResponse(
                address=address, handle=handle, data=b"", error=1  # Generic error
            )
            payload = self.encoder.encode_bluetooth_gatt_read_response(response)

            # Send to all subscribed API connections
            if self.bluetooth_proxy and self.bluetooth_proxy.api_server:
                for connection in self.bluetooth_proxy.api_server.connections:
                    if connection.is_authenticated():
                        await connection.send_message(
                            MessageType.BLUETOOTH_GATT_READ_RESPONSE, payload
                        )

            logger.error(
                f"GATT error: device={address:012X} handle={handle} error={error}"
            )
        except Exception as e:
            logger.error(f"Error sending GATT error response: {e}")

    def cleanup_device(self, address: int) -> None:
        """Clean up state for disconnected device.

        Args:
            address: Device address
        """
        # Remove notification subscriptions
        if address in self.notification_subscriptions:
            del self.notification_subscriptions[address]
            logger.debug(f"Cleaned up GATT state for device {address:012X}")

    def get_stats(self) -> dict:
        """Get GATT operation statistics.

        Returns:
            dict: Statistics about GATT operations
        """
        total_subscriptions = sum(
            len(subs) for subs in self.notification_subscriptions.values()
        )

        return {
            "pending_operations": len(self.pending_operations),
            "notification_subscriptions": len(self.notification_subscriptions),
            "total_subscribed_handles": total_subscriptions,
        }
