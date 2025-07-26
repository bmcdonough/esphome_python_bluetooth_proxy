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

    # Bluetooth LE messages
    BLUETOOTH_LE_ADVERTISEMENT_RESPONSE = 24
    BLUETOOTH_LE_RAW_ADVERTISEMENTS_RESPONSE = 25
    BLUETOOTH_DEVICE_REQUEST = 26
    BLUETOOTH_DEVICE_CONNECTION_RESPONSE = 27
    BLUETOOTH_GATT_GET_SERVICES_REQUEST = 28
    BLUETOOTH_GATT_GET_SERVICES_RESPONSE = 29
    BLUETOOTH_GATT_READ_REQUEST = 30
    BLUETOOTH_GATT_READ_RESPONSE = 31
    BLUETOOTH_GATT_WRITE_REQUEST = 32
    BLUETOOTH_GATT_WRITE_RESPONSE = 33
    BLUETOOTH_GATT_NOTIFY_REQUEST = 34
    BLUETOOTH_GATT_NOTIFY_RESPONSE = 35
    BLUETOOTH_GATT_NOTIFY_DATA_RESPONSE = 36


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


@dataclass
class BluetoothLEAdvertisementResponse:
    """Single BLE advertisement response message."""

    address: int  # 48-bit MAC as uint64
    rssi: int
    address_type: int  # 0=Public, 1=Random
    data: bytes  # Raw advertisement data


@dataclass
class BluetoothLERawAdvertisementsResponse:
    """Batch of BLE advertisements response message."""

    advertisements: list  # List of BluetoothLEAdvertisementResponse


@dataclass
class BluetoothDeviceRequest:
    """Bluetooth device connection request message."""

    address: int  # 48-bit MAC as uint64
    address_type: int  # 0=Public, 1=Random
    action: int  # 0=Connect, 1=Disconnect


@dataclass
class BluetoothDeviceConnectionResponse:
    """Bluetooth device connection response message."""

    address: int  # 48-bit MAC as uint64
    connected: bool
    mtu: int = 0
    error: int = 0  # Error code if connection failed


@dataclass
class BluetoothGATTService:
    """GATT service information for protocol messages."""

    uuid: bytes  # 16-byte UUID
    handle: int


@dataclass
class BluetoothGATTCharacteristic:
    """GATT characteristic information for protocol messages."""

    uuid: bytes  # 16-byte UUID
    handle: int
    properties: int  # Read/Write/Notify flags


@dataclass
class BluetoothGATTDescriptor:
    """GATT descriptor information for protocol messages."""

    uuid: bytes  # 16-byte UUID
    handle: int


@dataclass
class BluetoothGATTGetServicesRequest:
    """GATT get services request message."""

    address: int  # 48-bit MAC as uint64


@dataclass
class BluetoothGATTGetServicesResponse:
    """GATT get services response message."""

    address: int  # 48-bit MAC as uint64
    services: list  # List of BluetoothGATTService


@dataclass
class BluetoothGATTReadRequest:
    """GATT characteristic read request message."""

    address: int  # 48-bit MAC as uint64
    handle: int


@dataclass
class BluetoothGATTReadResponse:
    """GATT characteristic read response message."""

    address: int  # 48-bit MAC as uint64
    handle: int
    data: bytes
    error: int = 0  # Error code if read failed


@dataclass
class BluetoothGATTWriteRequest:
    """GATT characteristic write request message."""

    address: int  # 48-bit MAC as uint64
    handle: int
    response: bool  # Whether write response is required
    data: bytes


@dataclass
class BluetoothGATTWriteResponse:
    """GATT characteristic write response message."""

    address: int  # 48-bit MAC as uint64
    handle: int
    error: int = 0  # Error code if write failed


@dataclass
class BluetoothGATTNotifyRequest:
    """GATT notification subscription request message."""

    address: int  # 48-bit MAC as uint64
    handle: int
    enable: bool  # True to enable, False to disable


@dataclass
class BluetoothGATTNotifyResponse:
    """GATT notification subscription response message."""

    address: int  # 48-bit MAC as uint64
    handle: int
    error: int = 0  # Error code if subscription failed


@dataclass
class BluetoothGATTNotifyDataResponse:
    """GATT notification data response message."""

    address: int  # 48-bit MAC as uint64
    handle: int
    data: bytes


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

    def encode_bluetooth_le_advertisement_response(
        self, msg: BluetoothLEAdvertisementResponse
    ) -> bytes:
        """Encode BluetoothLEAdvertisementResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: rssi (int32)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_varint(msg.rssi & 0xFFFFFFFF))  # Handle negative values

        # Field 3: address_type (uint32)
        data.extend(b"\x18")  # Field 3, varint
        data.extend(encode_varint(msg.address_type))

        # Field 4: data (bytes)
        if msg.data:
            data.extend(b"\x22")  # Field 4, length-delimited
            data.extend(encode_varint(len(msg.data)))
            data.extend(msg.data)

        return bytes(data)

    def encode_bluetooth_le_raw_advertisements_response(
        self, msg: BluetoothLERawAdvertisementsResponse
    ) -> bytes:
        """Encode BluetoothLERawAdvertisementsResponse message."""
        data = bytearray()

        # Field 1: advertisements (repeated BluetoothLEAdvertisementResponse)
        for advertisement in msg.advertisements:
            data.extend(b"\x0a")  # Field 1, length-delimited
            adv_data = self.encode_bluetooth_le_advertisement_response(advertisement)
            data.extend(encode_varint(len(adv_data)))
            data.extend(adv_data)

        return bytes(data)

    def encode_bluetooth_device_connection_response(
        self, msg: BluetoothDeviceConnectionResponse
    ) -> bytes:
        """Encode BluetoothDeviceConnectionResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: connected (bool)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_bool(msg.connected))

        # Field 3: mtu (uint32)
        if msg.mtu:
            data.extend(b"\x18")  # Field 3, varint
            data.extend(encode_varint(msg.mtu))

        # Field 4: error (uint32)
        if msg.error:
            data.extend(b"\x20")  # Field 4, varint
            data.extend(encode_varint(msg.error))

        return bytes(data)

    def encode_bluetooth_gatt_get_services_response(
        self, msg: BluetoothGATTGetServicesResponse
    ) -> bytes:
        """Encode BluetoothGATTGetServicesResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: services (repeated BluetoothGATTService)
        for service in msg.services:
            data.extend(b"\x12")  # Field 2, length-delimited
            service_data = self._encode_gatt_service(service)
            data.extend(encode_varint(len(service_data)))
            data.extend(service_data)

        return bytes(data)

    def encode_bluetooth_gatt_read_response(
        self, msg: BluetoothGATTReadResponse
    ) -> bytes:
        """Encode BluetoothGATTReadResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: handle (uint32)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_varint(msg.handle))

        # Field 3: data (bytes)
        if msg.data:
            data.extend(b"\x1a")  # Field 3, length-delimited
            data.extend(encode_varint(len(msg.data)))
            data.extend(msg.data)

        # Field 4: error (uint32)
        if msg.error:
            data.extend(b"\x20")  # Field 4, varint
            data.extend(encode_varint(msg.error))

        return bytes(data)

    def encode_bluetooth_gatt_write_response(
        self, msg: BluetoothGATTWriteResponse
    ) -> bytes:
        """Encode BluetoothGATTWriteResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: handle (uint32)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_varint(msg.handle))

        # Field 3: error (uint32)
        if msg.error:
            data.extend(b"\x18")  # Field 3, varint
            data.extend(encode_varint(msg.error))

        return bytes(data)

    def encode_bluetooth_gatt_notify_response(
        self, msg: BluetoothGATTNotifyResponse
    ) -> bytes:
        """Encode BluetoothGATTNotifyResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: handle (uint32)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_varint(msg.handle))

        # Field 3: error (uint32)
        if msg.error:
            data.extend(b"\x18")  # Field 3, varint
            data.extend(encode_varint(msg.error))

        return bytes(data)

    def encode_bluetooth_gatt_notify_data_response(
        self, msg: BluetoothGATTNotifyDataResponse
    ) -> bytes:
        """Encode BluetoothGATTNotifyDataResponse message."""
        data = bytearray()

        # Field 1: address (uint64)
        data.extend(b"\x08")  # Field 1, varint
        data.extend(encode_varint(msg.address))

        # Field 2: handle (uint32)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_varint(msg.handle))

        # Field 3: data (bytes)
        if msg.data:
            data.extend(b"\x1a")  # Field 3, length-delimited
            data.extend(encode_varint(len(msg.data)))
            data.extend(msg.data)

        return bytes(data)

    def _encode_gatt_service(self, service: BluetoothGATTService) -> bytes:
        """Encode a single GATT service."""
        data = bytearray()

        # Field 1: uuid (bytes)
        data.extend(b"\x0a")  # Field 1, length-delimited
        data.extend(encode_varint(len(service.uuid)))
        data.extend(service.uuid)

        # Field 2: handle (uint32)
        data.extend(b"\x10")  # Field 2, varint
        data.extend(encode_varint(service.handle))

        return bytes(data)


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

    def decode_bluetooth_device_request(self, data: bytes) -> BluetoothDeviceRequest:
        """Decode BluetoothDeviceRequest message."""
        msg = BluetoothDeviceRequest(address=0, address_type=0, action=0)
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 0:  # address
                msg.address, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 2 and wire_type == 0:  # address_type
                msg.address_type, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 3 and wire_type == 0:  # action
                msg.action, consumed = decode_varint(data, offset)
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

    def decode_bluetooth_gatt_get_services_request(
        self, data: bytes
    ) -> BluetoothGATTGetServicesRequest:
        """Decode BluetoothGATTGetServicesRequest message."""
        msg = BluetoothGATTGetServicesRequest(address=0)
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 0:  # address
                msg.address, consumed = decode_varint(data, offset)
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

    def decode_bluetooth_gatt_read_request(
        self, data: bytes
    ) -> BluetoothGATTReadRequest:
        """Decode BluetoothGATTReadRequest message."""
        msg = BluetoothGATTReadRequest(address=0, handle=0)
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 0:  # address
                msg.address, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 2 and wire_type == 0:  # handle
                msg.handle, consumed = decode_varint(data, offset)
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

    def decode_bluetooth_gatt_write_request(
        self, data: bytes
    ) -> BluetoothGATTWriteRequest:
        """Decode BluetoothGATTWriteRequest message."""
        msg = BluetoothGATTWriteRequest(address=0, handle=0, response=True, data=b"")
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 0:  # address
                msg.address, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 2 and wire_type == 0:  # handle
                msg.handle, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 3 and wire_type == 0:  # response
                response_val, consumed = decode_varint(data, offset)
                msg.response = bool(response_val)
                offset += consumed
            elif field_num == 4 and wire_type == 2:  # data
                length, length_size = decode_varint(data, offset)
                offset += length_size
                msg.data = data[offset : offset + length]
                offset += length
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

    def decode_bluetooth_gatt_notify_request(
        self, data: bytes
    ) -> BluetoothGATTNotifyRequest:
        """Decode BluetoothGATTNotifyRequest message."""
        msg = BluetoothGATTNotifyRequest(address=0, handle=0, enable=False)
        offset = 0

        while offset < len(data):
            field_key, key_size = decode_varint(data, offset)
            offset += key_size
            field_num = field_key >> 3
            wire_type = field_key & 0x7

            if field_num == 1 and wire_type == 0:  # address
                msg.address, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 2 and wire_type == 0:  # handle
                msg.handle, consumed = decode_varint(data, offset)
                offset += consumed
            elif field_num == 3 and wire_type == 0:  # enable
                enable_val, consumed = decode_varint(data, offset)
                msg.enable = bool(enable_val)
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
