"""ESPHome API Connection Management.

This module handles individual API client connections, including state management,
authentication, and message handling for the ESPHome protocol.
"""

import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from enum import IntEnum
from typing import Callable, Optional

from .protocol import (
    BluetoothDeviceConnectionResponse,
    BluetoothGATTGetServicesResponse,
    BluetoothGATTService,
    BluetoothLEAdvertisementResponse,
    BluetoothLERawAdvertisementsResponse,
    BluetoothScannerStateResponse,
    ConnectResponse,
    DeviceInfoResponse,
    HelloResponse,
    ListEntitiesDoneResponse,
    SubscribeStatesRequest,
    MessageDecoder,
    MessageEncoder,
    MessageType,
    ProtocolError,
    create_message_frame,
    parse_message_frame,
)

logger = logging.getLogger(__name__)


class ConnectionState(IntEnum):
    """Connection state enumeration."""

    CONNECTING = 0
    CONNECTED = 1
    AUTHENTICATED = 2


class APIConnection:
    """Manages individual API client connections."""

    def __init__(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        device_info_provider: Callable[[], DeviceInfoResponse],
        password: Optional[str] = None,
    ):
        """Initialize API connection.

        Args:
            reader: Async stream reader
            writer: Async stream writer
            device_info_provider: Function to get device info
            password: Optional API password for authentication
        """
        self.reader = reader
        self.writer = writer
        self.device_info_provider = device_info_provider
        self.password = password

        self.state = ConnectionState.CONNECTING
        self.client_info = ""
        self.client_api_version_major = 1
        self.client_api_version_minor = 10
        self.subscribed_to_states = False

        self.encoder = MessageEncoder()
        self.decoder = MessageDecoder()

        # Get client address for logging
        peername = writer.get_extra_info("peername")
        self.client_address = f"{peername[0]}:{peername[1]}" if peername else "unknown"

        logger.info(f"New connection from {self.client_address}")

    async def handle_connection(self) -> None:
        """Handle the complete connection lifecycle."""
        try:
            await self._handle_messages()
        except Exception as e:
            logger.error(f"Connection {self.client_address} error: {e}")
        finally:
            await self.close()

    async def _handle_messages(self) -> None:
        """Handle incoming messages from the client."""
        buffer = bytearray()

        while not self.writer.is_closing():
            try:
                # Read data from client
                data = await asyncio.wait_for(self.reader.read(4096), timeout=30.0)
                if not data:
                    logger.info(f"Client {self.client_address} disconnected")
                    break

                buffer.extend(data)

                # Process complete messages from buffer
                while len(buffer) >= 3:  # Minimum frame size
                    try:
                        msg_type, payload, frame_size = parse_message_frame(
                            bytes(buffer)
                        )

                        # Remove processed frame from buffer
                        buffer = buffer[frame_size:]

                        # Handle the message
                        await self._handle_message(msg_type, payload)

                    except ProtocolError as e:
                        if "Incomplete message frame" in str(e):
                            # Need more data
                            break
                        else:
                            logger.error(
                                f"Protocol error from {self.client_address}: {e}"
                            )
                            return

            except asyncio.TimeoutError:
                logger.warning(f"Connection {self.client_address} timed out")
                break
            except Exception as e:
                logger.error(f"Error reading from {self.client_address}: {e}")
                break

    async def _handle_message(self, msg_type: int, payload: bytes) -> None:
        """Handle a single message from the client."""
        logger.info(f"Received message type {msg_type} from {self.client_address}")

        try:
            if msg_type == MessageType.HELLO_REQUEST:
                await self._handle_hello_request(payload)
            elif msg_type == MessageType.CONNECT_REQUEST:
                await self._handle_connect_request(payload)
            elif msg_type == MessageType.DISCONNECT_REQUEST:
                await self._handle_disconnect_request(payload)
            elif msg_type == MessageType.DEVICE_INFO_REQUEST:
                await self._handle_device_info_request(payload)
            elif msg_type == MessageType.LIST_ENTITIES_REQUEST:
                await self._handle_list_entities_request(payload)
            elif msg_type == MessageType.PING_REQUEST:
                await self._handle_ping_request()
            elif msg_type == MessageType.BLUETOOTH_DEVICE_REQUEST:
                await self._handle_bluetooth_device_request(payload)
            elif msg_type == MessageType.BLUETOOTH_GATT_GET_SERVICES_REQUEST:
                await self._handle_bluetooth_gatt_get_services_request(payload)
            elif msg_type == MessageType.BLUETOOTH_GATT_READ_REQUEST:
                await self._handle_bluetooth_gatt_read_request(payload)
            elif msg_type == MessageType.BLUETOOTH_GATT_WRITE_REQUEST:
                await self._handle_bluetooth_gatt_write_request(payload)
            elif msg_type == MessageType.BLUETOOTH_GATT_NOTIFY_REQUEST:
                await self._handle_bluetooth_gatt_notify_request(payload)
            elif msg_type == MessageType.BLUETOOTH_GATT_READ_DESCRIPTOR_REQUEST:
                await self._handle_bluetooth_gatt_read_descriptor_request(payload)
            elif msg_type == MessageType.BLUETOOTH_GATT_WRITE_DESCRIPTOR_REQUEST:
                await self._handle_bluetooth_gatt_write_descriptor_request(payload)
            elif msg_type == MessageType.SUBSCRIBE_STATES_REQUEST:
                await self._handle_subscribe_states_request(payload)
            else:
                logger.warning(
                    f"Unknown message type {msg_type} from {self.client_address}"
                )

        except Exception as e:
            logger.error(
                f"Error handling message type {msg_type} from "
                f"{self.client_address}: {e}"
            )

    async def _handle_hello_request(self, payload: bytes) -> None:
        """Handle HelloRequest message."""
        if self.state != ConnectionState.CONNECTING:
            logger.warning(
                f"Unexpected HelloRequest from {self.client_address} in state "
                f"{self.state}"
            )
            return

        try:
            request = self.decoder.decode_hello_request(payload)
            self.client_info = request.client_info
            self.client_api_version_major = request.api_version_major
            self.client_api_version_minor = request.api_version_minor

            logger.info(
                f"Hello from {self.client_address}: '{request.client_info}' "
                f"API v{request.api_version_major}.{request.api_version_minor}"
            )

            # Send HelloResponse
            response = HelloResponse(
                api_version_major=1,
                api_version_minor=10,
                server_info="ESPHome Python Bluetooth Proxy v0.1.0",
                name="python-bluetooth-proxy",
            )

            await self._send_message(
                MessageType.HELLO_RESPONSE, self.encoder.encode_hello_response(response)
            )

            # Update state - always wait for ConnectRequest regardless of password
            # This ensures proper protocol flow even when no password is required
            self.state = ConnectionState.CONNECTED
            logger.debug(
                f"Client {self.client_address} connected, waiting for ConnectRequest"
            )

        except Exception as e:
            logger.error(f"Error handling HelloRequest from {self.client_address}: {e}")

    async def _handle_connect_request(self, payload: bytes) -> None:
        """Handle ConnectRequest message."""
        if self.state == ConnectionState.AUTHENTICATED:
            # Already authenticated, ignore duplicate ConnectRequest
            logger.debug(
                f"Ignoring duplicate ConnectRequest from {self.client_address} "
                f"(already authenticated)"
            )
            return
        elif self.state != ConnectionState.CONNECTED:
            logger.warning(
                f"Unexpected ConnectRequest from {self.client_address} "
                f"in state {self.state}"
            )
            return

        try:
            request = self.decoder.decode_connect_request(payload)

            # Check password
            password_valid = (self.password is None) or (
                request.password == self.password
            )

            response = ConnectResponse(invalid_password=not password_valid)
            await self._send_message(
                MessageType.CONNECT_RESPONSE,
                self.encoder.encode_connect_response(response),
            )

            if password_valid:
                self.state = ConnectionState.AUTHENTICATED
                logger.info(f"Client {self.client_address} authenticated (no password)")
                logger.debug(
                    f"Client {self.client_address} ready for "
                    f"DeviceInfo/ListEntities requests"
                )
            else:
                logger.warning(
                    f"Client {self.client_address} provided invalid password"
                )
                await self.close()

        except Exception as e:
            logger.error(
                f"Error handling ConnectRequest from {self.client_address}: {e}"
            )

    async def _handle_disconnect_request(self, payload: bytes) -> None:
        """Handle DisconnectRequest message."""
        logger.info(f"Client {self.client_address} requested disconnect")

        try:
            # Send DisconnectResponse
            await self._send_message(MessageType.DISCONNECT_RESPONSE, b"")

            # Close the connection
            await self.close()

        except Exception as e:
            logger.error(
                f"Error handling DisconnectRequest from {self.client_address}: {e}"
            )

    async def _handle_device_info_request(self, payload: bytes) -> None:
        """Handle DeviceInfoRequest message."""
        logger.info(f"Received DeviceInfoRequest from {self.client_address}")

        # Allow DeviceInfo requests in CONNECTED state if no password is required
        # This supports aioesphomeapi client flow: Hello → DeviceInfo (skip Connect)
        if self.state == ConnectionState.CONNECTED and self.password is None:
            logger.debug(
                f"Allowing DeviceInfo request from {self.client_address} "
                f"(no password required)"
            )
        elif self.state != ConnectionState.AUTHENTICATED:
            logger.warning(
                f"DeviceInfoRequest from unauthenticated client "
                f"{self.client_address} in state {self.state}"
            )
            return

        try:
            # Get device info from provider (now async)
            logger.debug(f"Getting device info from provider for {self.client_address}")
            device_info = await self.device_info_provider()
            logger.debug(f"Got device info: {device_info}")

            # Encode the response
            encoded_response = self.encoder.encode_device_info_response(device_info)
            logger.debug(f"Encoded device info response: {len(encoded_response)} bytes")

            await self._send_message(
                MessageType.DEVICE_INFO_RESPONSE,
                encoded_response,
            )

            logger.info(f"Sent device info response to {self.client_address}")

        except Exception as e:
            logger.error(
                f"Error handling DeviceInfoRequest from {self.client_address}: {e}"
            )
            import traceback

            logger.error(traceback.format_exc())

    async def _handle_ping_request(self) -> None:
        """Handle PingRequest message."""
        try:
            # Empty PingResponse
            logger.debug(f"Sending ping response to {self.client_address}")
            await self._send_message(MessageType.PING_RESPONSE, b"")

        except Exception as e:
            logger.error(f"Error handling PingRequest from {self.client_address}: {e}")

    async def _handle_subscribe_states_request(self, payload: bytes) -> None:
        """Handle SubscribeStatesRequest message.
        
        This message indicates the client wants to subscribe to state updates.
        Upon receiving this message, we should:
        1. Mark the connection as subscribed to state updates
        2. Send initial state updates for all entities
        3. Continue sending state updates whenever entity states change
        """
        logger.info(f"Received SubscribeStatesRequest from {self.client_address}")
        
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning(
                f"SubscribeStatesRequest from unauthenticated client "
                f"{self.client_address} in state {self.state}"
            )
            return
            
        try:
            # Decode the message (though it's empty)
            self.decoder.decode_subscribe_states_request(payload)
            
            # Mark this connection as subscribed to states
            self.subscribed_to_states = True
            logger.info(f"Client {self.client_address} subscribed to state updates")
            
            # Send initial state updates - for Bluetooth proxy, this includes:
            # 1. Current Bluetooth scanner state
            await self._send_bluetooth_scanner_state()
            
            # 2. TODO: Add other state information if needed in future updates
            # (e.g., connected devices list, etc.)
            
            logger.info(f"Sent initial state updates to {self.client_address}")
            
        except Exception as e:
            logger.error(
                f"Error handling SubscribeStatesRequest from {self.client_address}: {e}"
            )

    async def _handle_bluetooth_device_request(self, payload: bytes) -> None:
        """Handle BluetoothDeviceRequest message."""
        try:
            request = self.decoder.decode_bluetooth_device_request(payload)
            logger.debug(
                f"Bluetooth device request from {self.client_address}: "
                f"address={request.address:012X} action={request.action}"
            )

            # Forward to Bluetooth proxy if available
            if hasattr(self, "bluetooth_proxy") and self.bluetooth_proxy:
                if request.action == 0:  # Connect
                    success = await self.bluetooth_proxy.connect_device(
                        request.address, request.address_type
                    )
                elif request.action == 1:  # Disconnect
                    success = await self.bluetooth_proxy.disconnect_device(
                        request.address
                    )
                else:
                    logger.warning(f"Unknown device action: {request.action}")
                    success = False

                # Send response (connection state will be sent separately)
                if not success:
                    response = BluetoothDeviceConnectionResponse(
                        address=request.address,
                        connected=False,
                        error=1,  # Generic error
                    )
                    payload = self.encoder.encode_bluetooth_device_connection_response(
                        response
                    )
                    await self._send_message(
                        MessageType.BLUETOOTH_DEVICE_CONNECTION_RESPONSE, payload
                    )
            else:
                logger.warning("No Bluetooth proxy available for device request")

        except Exception as e:
            logger.error(f"Error handling Bluetooth device request: {e}")

    async def _handle_bluetooth_gatt_get_services_request(self, payload: bytes) -> None:
        """Handle BluetoothGATTGetServicesRequest message."""
        try:
            request = self.decoder.decode_bluetooth_gatt_get_services_request(payload)
            logger.debug(
                f"GATT get services request from {self.client_address}: "
                f"address={request.address:012X}"
            )

            # Forward to Bluetooth proxy if available
            if hasattr(self, "bluetooth_proxy") and self.bluetooth_proxy:
                connection = self.bluetooth_proxy.connections.get(request.address)
                if connection and connection.is_connected():
                    try:
                        # Discover services
                        services = await connection.discover_services()

                        # Convert to protocol format
                        protocol_services = []
                        for service in services:
                            protocol_service = BluetoothGATTService(
                                uuid=service.uuid, handle=service.handle
                            )
                            protocol_services.append(protocol_service)

                        # Send response
                        response = BluetoothGATTGetServicesResponse(
                            address=request.address, services=protocol_services
                        )
                        payload = (
                            self.encoder.encode_bluetooth_gatt_get_services_response(
                                response
                            )
                        )
                        await self._send_message(
                            MessageType.BLUETOOTH_GATT_GET_SERVICES_RESPONSE, payload
                        )

                    except Exception as e:
                        logger.error(f"Service discovery failed: {e}")
                        # Send empty response on error
                        response = BluetoothGATTGetServicesResponse(
                            address=request.address, services=[]
                        )
                        payload = (
                            self.encoder.encode_bluetooth_gatt_get_services_response(
                                response
                            )
                        )
                        await self._send_message(
                            MessageType.BLUETOOTH_GATT_GET_SERVICES_RESPONSE, payload
                        )
                else:
                    logger.warning(f"Device {request.address:012X} not connected")
            else:
                logger.warning("No Bluetooth proxy available for GATT services request")

        except Exception as e:
            logger.error(f"Error handling GATT get services request: {e}")

    async def _handle_bluetooth_gatt_read_request(self, payload: bytes) -> None:
        """Handle BluetoothGATTReadRequest message."""
        try:
            request = self.decoder.decode_bluetooth_gatt_read_request(payload)
            logger.debug(
                f"GATT read request from {self.client_address}: "
                f"address={request.address:012X} handle={request.handle}"
            )

            # Forward to GATT operations handler if available
            if hasattr(self, "gatt_handler") and self.gatt_handler:
                await self.gatt_handler.handle_gatt_read_request(
                    request.address, request.handle
                )
            else:
                logger.warning("No GATT handler available for read request")

        except Exception as e:
            logger.error(f"Error handling GATT read request: {e}")

    async def _handle_bluetooth_gatt_write_request(self, payload: bytes) -> None:
        """Handle BluetoothGATTWriteRequest message."""
        try:
            request = self.decoder.decode_bluetooth_gatt_write_request(payload)
            logger.debug(
                f"GATT write request from {self.client_address}: "
                f"address={request.address:012X} handle={request.handle} "
                f"data={len(request.data)} bytes response={request.response}"
            )

            # Forward to GATT operations handler if available
            if hasattr(self, "gatt_handler") and self.gatt_handler:
                await self.gatt_handler.handle_gatt_write_request(
                    request.address, request.handle, request.data, request.response
                )
            else:
                logger.warning("No GATT handler available for write request")

        except Exception as e:
            logger.error(f"Error handling GATT write request: {e}")

    async def _handle_bluetooth_gatt_notify_request(self, payload: bytes) -> None:
        """Handle BluetoothGATTNotifyRequest message."""
        try:
            request = self.decoder.decode_bluetooth_gatt_notify_request(payload)
            logger.debug(
                f"GATT notify request from {self.client_address}: "
                f"address={request.address:012X} handle={request.handle} "
                f"enable={request.enable}"
            )

            # Forward to GATT operations handler if available
            if hasattr(self, "gatt_handler") and self.gatt_handler:
                await self.gatt_handler.handle_gatt_notify_request(
                    request.address, request.handle, request.enable
                )
            else:
                logger.warning("No GATT handler available for notify request")

        except Exception as e:
            logger.error(f"Error handling GATT notify request: {e}")

    async def _handle_bluetooth_gatt_read_descriptor_request(
        self, payload: bytes
    ) -> None:
        """Handle BluetoothGATTReadDescriptorRequest message."""
        try:
            request = self.decoder.decode_bluetooth_gatt_read_descriptor_request(
                payload
            )
            logger.debug(
                f"GATT read descriptor request from {self.client_address}: "
                f"address={request.address:012X} handle={request.handle}"
            )

            # Forward to GATT operations handler if available
            if hasattr(self, "gatt_handler") and self.gatt_handler:
                await self.gatt_handler.handle_gatt_read_descriptor_request(
                    request.address, request.handle
                )
            else:
                logger.warning("No GATT handler available for read descriptor request")

        except Exception as e:
            logger.error(f"Error handling GATT read descriptor request: {e}")

    async def _handle_bluetooth_gatt_write_descriptor_request(
        self, payload: bytes
    ) -> None:
        """Handle BluetoothGATTWriteDescriptorRequest message."""
        try:
            request = self.decoder.decode_bluetooth_gatt_write_descriptor_request(
                payload
            )
            logger.debug(
                f"GATT write descriptor request from {self.client_address}: "
                f"address={request.address:012X} handle={request.handle} "
                f"data={len(request.data)} bytes"
            )

            # Forward to GATT operations handler if available
            if hasattr(self, "gatt_handler") and self.gatt_handler:
                await self.gatt_handler.handle_gatt_write_descriptor_request(
                    request.address, request.handle, request.data
                )
            else:
                logger.warning("No GATT handler available for write descriptor request")

        except Exception as e:
            logger.error(f"Error handling GATT write descriptor request: {e}")

    async def _send_message(self, msg_type: int, payload: bytes) -> None:
        """Send a message to the client."""
        try:
            frame = create_message_frame(msg_type, payload)
            self.writer.write(frame)
            await self.writer.drain()

            logger.debug(
                f"Sent message type {msg_type} to {self.client_address} "
                f"({len(payload)} bytes payload)"
            )

        except Exception as e:
            logger.error(f"Error sending message to {self.client_address}: {e}")
            raise

    async def send_message(self, msg_type: int, payload: bytes) -> None:
        """Public method to send a message to the client."""
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning(
                f"Attempt to send message to unauthenticated client "
                f"{self.client_address}"
            )
            return

        await self._send_message(msg_type, payload)

    def is_authenticated(self) -> bool:
        """Check if the connection is authenticated."""
        return self.state == ConnectionState.AUTHENTICATED

    def is_connected(self) -> bool:
        """Check if the connection is still active."""
        return not self.writer.is_closing()

    async def send_bluetooth_le_advertisements(self, advertisements: list) -> None:
        """Send batch of BLE advertisements to client.

        Args:
            advertisements: List of BLEAdvertisement objects
        """
        if self.state not in [ConnectionState.AUTHENTICATED, ConnectionState.CONNECTED]:
            logger.debug(
                f"Skipping BLE advertisements to {self.client_address} "
                f"(state: {self.state})"
            )
            return

        try:
            # Convert BLEAdvertisement objects to protocol messages
            protocol_advertisements = []
            for adv in advertisements:
                protocol_adv = BluetoothLEAdvertisementResponse(
                    address=adv.address,
                    rssi=adv.rssi,
                    address_type=adv.address_type,
                    data=adv.data,
                )
                protocol_advertisements.append(protocol_adv)

            # Create batch response message
            batch_response = BluetoothLERawAdvertisementsResponse(
                advertisements=protocol_advertisements
            )

            # Encode and send
            payload = self.encoder.encode_bluetooth_le_raw_advertisements_response(
                batch_response
            )
            frame = create_message_frame(
                MessageType.BLUETOOTH_LE_RAW_ADVERTISEMENTS_RESPONSE, payload
            )

            self.writer.write(frame)
            await self.writer.drain()

            logger.debug(
                f"Sent {len(advertisements)} BLE advertisements to "
                f"{self.client_address}"
            )

        except Exception as e:
            logger.error(
                f"Error sending BLE advertisements to {self.client_address}: {e}"
            )

    def is_bluetooth_subscribed(self) -> bool:
        """Check if connection is subscribed to Bluetooth events.

        Returns:
            bool: True if subscribed to Bluetooth events
        """
        # For now, assume all authenticated connections want BLE advertisements
        # In a full implementation, this would check subscription flags
        return self.state in [ConnectionState.AUTHENTICATED, ConnectionState.CONNECTED]

    async def close(self) -> None:
        """Close the connection."""
        if not self.writer.is_closing():
            try:
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(f"Connection {self.client_address} closed")
            except Exception as e:
                logger.error(f"Error closing connection {self.client_address}: {e}")

    async def _send_bluetooth_scanner_state(self) -> None:
        """Send current Bluetooth scanner state to client.
        
        This is called on initial subscription and whenever the scanner state changes.
        """
        if not self.subscribed_to_states:
            return
            
        try:
            # Create state response with current scanner state
            # For now using default values - in a full implementation, this would
            # get the real state from the Bluetooth proxy component
            scanner_state = BluetoothScannerStateResponse(
                active=True,  # Bluetooth proxy is active
                scanning=True,  # Currently scanning
                mode=1,        # BLE mode
            )
            
            # Encode and send
            payload = self.encoder.encode_bluetooth_scanner_state_response(scanner_state)
            await self.send_message(MessageType.BLUETOOTH_SCANNER_STATE_RESPONSE, payload)
            
            logger.debug(f"Sent Bluetooth scanner state to {self.client_address}")
            
        except Exception as e:
            logger.error(f"Error sending Bluetooth scanner state: {e}")
    
    def __str__(self) -> str:
        """String representation of the connection."""
        return (
            f"APIConnection({self.client_address}, "
            f"{self.state.name}, "
            f"{self.client_info})"
        )
