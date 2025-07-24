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
    ConnectResponse,
    DeviceInfoResponse,
    HelloResponse,
    ListEntitiesDoneResponse,
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
        logger.debug(f"Received message type {msg_type} from {self.client_address}")

        try:
            if msg_type == MessageType.HELLO_REQUEST:
                await self._handle_hello_request(payload)
            elif msg_type == MessageType.CONNECT_REQUEST:
                await self._handle_connect_request(payload)
            elif msg_type == MessageType.DEVICE_INFO_REQUEST:
                await self._handle_device_info_request(payload)
            elif msg_type == MessageType.LIST_ENTITIES_REQUEST:
                await self._handle_list_entities_request(payload)
            elif msg_type == MessageType.PING_REQUEST:
                await self._handle_ping_request()
            else:
                logger.warning(
                    f"Unhandled message type {msg_type} from {self.client_address}"
                )

        except Exception as e:
            logger.error(
                f"Error handling message type {msg_type} from {self.client_address}: {e}"
            )

    async def _handle_hello_request(self, payload: bytes) -> None:
        """Handle HelloRequest message."""
        if self.state != ConnectionState.CONNECTING:
            logger.warning(
                f"Unexpected HelloRequest from {self.client_address} in state {self.state}"
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

            # Update state
            if self.password is None:
                # No password required, auto-authenticate
                self.state = ConnectionState.AUTHENTICATED
                logger.info(f"Client {self.client_address} authenticated (no password)")
            else:
                # Password required, wait for ConnectRequest
                self.state = ConnectionState.CONNECTED
                logger.debug(
                    f"Client {self.client_address} connected, waiting for authentication"
                )

        except Exception as e:
            logger.error(f"Error handling HelloRequest from {self.client_address}: {e}")

    async def _handle_connect_request(self, payload: bytes) -> None:
        """Handle ConnectRequest message."""
        if self.state != ConnectionState.CONNECTED:
            logger.warning(
                f"Unexpected ConnectRequest from {self.client_address} in state {self.state}"
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
                logger.info(f"Client {self.client_address} authenticated successfully")
            else:
                logger.warning(
                    f"Client {self.client_address} provided invalid password"
                )
                await self.close()

        except Exception as e:
            logger.error(
                f"Error handling ConnectRequest from {self.client_address}: {e}"
            )

    async def _handle_device_info_request(self, payload: bytes) -> None:
        """Handle DeviceInfoRequest message."""
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning(
                f"DeviceInfoRequest from unauthenticated client {self.client_address}"
            )
            return

        try:
            # Get device info from provider
            device_info = self.device_info_provider()

            await self._send_message(
                MessageType.DEVICE_INFO_RESPONSE,
                self.encoder.encode_device_info_response(device_info),
            )

            logger.debug(f"Sent device info to {self.client_address}")

        except Exception as e:
            logger.error(
                f"Error handling DeviceInfoRequest from {self.client_address}: {e}"
            )

    async def _handle_list_entities_request(self, payload: bytes) -> None:
        """Handle ListEntitiesRequest message."""
        if self.state != ConnectionState.AUTHENTICATED:
            logger.warning(
                f"ListEntitiesRequest from unauthenticated client {self.client_address}"
            )
            return

        try:
            # For now, just send empty entity list (no entities to report)
            # In future phases, this will include Bluetooth proxy entities

            response = ListEntitiesDoneResponse()
            await self._send_message(
                MessageType.LIST_ENTITIES_DONE_RESPONSE,
                self.encoder.encode_list_entities_done_response(response),
            )

            logger.debug(f"Sent entity list to {self.client_address}")

        except Exception as e:
            logger.error(
                f"Error handling ListEntitiesRequest from {self.client_address}: {e}"
            )

    async def _handle_ping_request(self) -> None:
        """Handle PingRequest message."""
        try:
            # Send empty PingResponse
            await self._send_message(MessageType.PING_RESPONSE, b"")
            logger.debug(f"Sent ping response to {self.client_address}")

        except Exception as e:
            logger.error(f"Error handling PingRequest from {self.client_address}: {e}")

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
                f"Attempt to send message to unauthenticated client {self.client_address}"
            )
            return

        await self._send_message(msg_type, payload)

    def is_authenticated(self) -> bool:
        """Check if the connection is authenticated."""
        return self.state == ConnectionState.AUTHENTICATED

    def is_connected(self) -> bool:
        """Check if the connection is still active."""
        return not self.writer.is_closing()

    async def close(self) -> None:
        """Close the connection."""
        if not self.writer.is_closing():
            try:
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(f"Connection {self.client_address} closed")
            except Exception as e:
                logger.error(f"Error closing connection {self.client_address}: {e}")

    def __str__(self) -> str:
        """String representation of the connection."""
        return f"APIConnection({self.client_address}, {self.state.name}, {self.client_info})"
