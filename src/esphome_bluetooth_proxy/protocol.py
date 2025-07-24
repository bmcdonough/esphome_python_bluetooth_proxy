"""ESPHome API Protocol Message Handling.

This module implements the ESPHome API protocol message encoding/decoding
and provides the core message types needed for the 4-step handshake.
"""

import logging
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class MessageType(IntEnum):
    """ESPHome API message types."""

    HELLO_REQUEST = 1
    HELLO_RESPONSE = 2
    CONNECT_REQUEST = 3
    CONNECT_RESPONSE = 4
    DISCONNECT_REQUEST = 5
    DISCONNECT_RESPONSE = 6
    PING_REQUEST = 7
    PING_RESPONSE = 8
    DEVICE_INFO_REQUEST = 9
    DEVICE_INFO_RESPONSE = 10
    LIST_ENTITIES_REQUEST = 11
    LIST_ENTITIES_DONE_RESPONSE = 19


@dataclass
class HelloRequest:
    """Hello request message from client."""

    client_info: str = ""
    api_version_major: int = 1
    api_version_minor: int = 10


@dataclass
class HelloResponse:
    """Hello response message to client."""

    api_version_major: int = 1
    api_version_minor: int = 10
    server_info: str = ""
    name: str = ""


@dataclass
class ConnectRequest:
    """Connect request message from client."""

    password: str = ""


@dataclass
class ConnectResponse:
    """Connect response message to client."""

    invalid_password: bool = False


@dataclass
class DeviceInfoRequest:
    """Device info request message from client."""

    pass


@dataclass
class DeviceInfoResponse:
    """Device info response message to client."""

    uses_password: bool = False
    name: str = ""
    mac_address: str = ""
    esphome_version: str = ""
    compilation_time: str = ""
    model: str = ""
    has_deep_sleep: bool = False
    project_name: str = ""
    project_version: str = ""
    webserver_port: int = 0
    bluetooth_proxy_feature_flags: int = 0
    manufacturer: str = ""
    friendly_name: str = ""
    bluetooth_mac_address: str = ""


@dataclass
class ListEntitiesRequest:
    """List entities request message from client."""

    pass


@dataclass
class ListEntitiesDoneResponse:
    """List entities done response message to client."""

    pass


class ProtocolError(Exception):
    """Protocol-related errors."""

    pass


def encode_varint(value: int) -> bytes:
    """Encode integer as variable-length integer."""
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode variable-length integer from bytes.

    Returns:
        tuple[int, int]: (decoded_value, bytes_consumed)
    """
    result = 0
    shift = 0
    pos = offset

    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if (byte & 0x80) == 0:
            break
        shift += 7
        if shift >= 64:
            raise ProtocolError("VarInt too long")
    else:
        raise ProtocolError("Incomplete VarInt")

    return result, pos - offset


def encode_string(value: str) -> bytes:
    """Encode string with length prefix."""
    utf8_bytes = value.encode("utf-8")
    return encode_varint(len(utf8_bytes)) + utf8_bytes


def decode_string(data: bytes, offset: int = 0) -> tuple[str, int]:
    """Decode string with length prefix.

    Returns:
        tuple[str, int]: (decoded_string, bytes_consumed)
    """
    length, varint_size = decode_varint(data, offset)
    start = offset + varint_size
    end = start + length

    if end > len(data):
        raise ProtocolError("String extends beyond data")

    string_value = data[start:end].decode("utf-8")
    return string_value, varint_size + length


def encode_bool(value: bool) -> bytes:
    """Encode boolean as single byte."""
    return b"\x01" if value else b"\x00"


def decode_bool(data: bytes, offset: int = 0) -> tuple[bool, int]:
    """Decode boolean from single byte.

    Returns:
        tuple[bool, int]: (decoded_bool, bytes_consumed)
    """
    if offset >= len(data):
        raise ProtocolError("No data for boolean")
    return data[offset] != 0, 1


class MessageEncoder:
    """Encodes ESPHome API messages."""

    def encode_hello_request(self, msg: HelloRequest) -> bytes:
        """Encode HelloRequest message."""
        data = bytearray()
        if msg.client_info:
            data.extend(b"\x0a")  # Field 1, string
            data.extend(encode_string(msg.client_info))
        if msg.api_version_major != 1:
            data.extend(b"\x10")  # Field 2, varint
            data.extend(encode_varint(msg.api_version_major))
        if msg.api_version_minor != 10:
            data.extend(b"\x18")  # Field 3, varint
            data.extend(encode_varint(msg.api_version_minor))
        return bytes(data)

    def encode_hello_response(self, msg: HelloResponse) -> bytes:
        """Encode HelloResponse message."""
        data = bytearray()
        if msg.api_version_major != 1:
            data.extend(b"\x08")  # Field 1, varint
            data.extend(encode_varint(msg.api_version_major))
        if msg.api_version_minor != 10:
            data.extend(b"\x10")  # Field 2, varint
            data.extend(encode_varint(msg.api_version_minor))
        if msg.server_info:
            data.extend(b"\x1a")  # Field 3, string
            data.extend(encode_string(msg.server_info))
        if msg.name:
            data.extend(b"\x22")  # Field 4, string
            data.extend(encode_string(msg.name))
        return bytes(data)

    def encode_connect_response(self, msg: ConnectResponse) -> bytes:
        """Encode ConnectResponse message."""
        data = bytearray()
        if msg.invalid_password:
            data.extend(b"\x08")  # Field 1, bool
            data.extend(encode_bool(msg.invalid_password))
        return bytes(data)

    def encode_device_info_response(self, msg: DeviceInfoResponse) -> bytes:
        """Encode DeviceInfoResponse message."""
        data = bytearray()
        if msg.uses_password:
            data.extend(b"\x08")  # Field 1, bool
            data.extend(encode_bool(msg.uses_password))
        if msg.name:
            data.extend(b"\x12")  # Field 2, string
            data.extend(encode_string(msg.name))
        if msg.mac_address:
            data.extend(b"\x1a")  # Field 3, string
            data.extend(encode_string(msg.mac_address))
        if msg.esphome_version:
            data.extend(b"\x22")  # Field 4, string
            data.extend(encode_string(msg.esphome_version))
        if msg.compilation_time:
            data.extend(b"\x2a")  # Field 5, string
            data.extend(encode_string(msg.compilation_time))
        if msg.model:
            data.extend(b"\x32")  # Field 6, string
            data.extend(encode_string(msg.model))
        if msg.has_deep_sleep:
            data.extend(b"\x38")  # Field 7, bool
            data.extend(encode_bool(msg.has_deep_sleep))
        if msg.project_name:
            data.extend(b"\x42")  # Field 8, string
            data.extend(encode_string(msg.project_name))
        if msg.project_version:
            data.extend(b"\x4a")  # Field 9, string
            data.extend(encode_string(msg.project_version))
        if msg.webserver_port:
            data.extend(b"\x50")  # Field 10, varint
            data.extend(encode_varint(msg.webserver_port))
        if msg.bluetooth_proxy_feature_flags:
            data.extend(b"\x78")  # Field 15, varint
            data.extend(encode_varint(msg.bluetooth_proxy_feature_flags))
        if msg.manufacturer:
            data.extend(b"\x62")  # Field 12, string
            data.extend(encode_string(msg.manufacturer))
        if msg.friendly_name:
            data.extend(b"\x6a")  # Field 13, string
            data.extend(encode_string(msg.friendly_name))
        if msg.bluetooth_mac_address:
            data.extend(b"\x92\x01")  # Field 18, string
            data.extend(encode_string(msg.bluetooth_mac_address))
        return bytes(data)

    def encode_list_entities_done_response(
        self, msg: ListEntitiesDoneResponse
    ) -> bytes:
        """Encode ListEntitiesDoneResponse message."""
        return b""  # Empty message


class MessageDecoder:
    """Decodes ESPHome API messages."""

    def decode_hello_request(self, data: bytes) -> HelloRequest:
        """Decode HelloRequest message."""
        msg = HelloRequest()
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 2:  # client_info
                msg.client_info, consumed = decode_string(data, offset)
                offset += consumed
            elif field_num == 2 and wire_type == 0:  # api_version_major
                msg.api_version_major, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 3 and wire_type == 0:  # api_version_minor
                msg.api_version_minor, consumed = decode_varint(data, offset)
                offset += consumed
            else:
                # Skip unknown field
                if wire_type == 0:  # varint
                    _, consumed = decode_varint(data, offset)
                    offset += consumed
                elif wire_type == 2:  # length-delimited
                    length, length_size = decode_varint(data, offset)
                    offset += length_size + length
                else:
                    raise ProtocolError(f"Unknown wire type: {wire_type}")

        return msg

    def decode_connect_request(self, data: bytes) -> ConnectRequest:
        """Decode ConnectRequest message."""
        msg = ConnectRequest()
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 2:  # password
                msg.password, consumed = decode_string(data, offset)
                offset += consumed
            else:
                # Skip unknown field
                if wire_type == 0:  # varint
                    _, consumed = decode_varint(data, offset)
                    offset += consumed
                elif wire_type == 2:  # length-delimited
                    length, length_size = decode_varint(data, offset)
                    offset += length_size + length
                else:
                    raise ProtocolError(f"Unknown wire type: {wire_type}")

        return msg


def create_message_frame(msg_type: int, payload: bytes) -> bytes:
    """Create ESPHome message frame with header."""
    # ESPHome frame format: [0x00][VarInt: Message Size][VarInt: Message Type][Payload]
    frame = bytearray()
    frame.append(0x00)  # Frame start marker
    frame.extend(encode_varint(len(payload)))
    frame.extend(encode_varint(msg_type))
    frame.extend(payload)
    return bytes(frame)


def parse_message_frame(data: bytes) -> tuple[int, bytes, int]:
    """Parse ESPHome message frame.

    Returns:
        tuple[int, bytes, int]: (message_type, payload, total_frame_size)
    """
    if len(data) < 1 or data[0] != 0x00:
        raise ProtocolError("Invalid frame start marker")

    offset = 1
    payload_size, size_bytes = decode_varint(data, offset)
    offset += size_bytes

    msg_type, type_bytes = decode_varint(data, offset)
    offset += type_bytes

    if offset + payload_size > len(data):
        raise ProtocolError("Incomplete message frame")

    payload = data[offset : offset + payload_size]
    total_size = offset + payload_size

    return msg_type, payload, total_size
