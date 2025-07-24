# ESPHome Python Bluetooth Proxy Implementation Roadmap

This document provides a detailed breakdown of the ESPHome Bluetooth proxy functionality, organized into implementable phases that closely follow the original C++ design.

## Architecture Overview

The ESPHome Bluetooth proxy consists of two main components:

### 1. BluetoothProxy (Main Coordinator)
- **Role**: Central coordinator managing all Bluetooth operations
- **Responsibilities**:
  - API connection management
  - Advertisement scanning and batching
  - Device connection lifecycle management
  - GATT operation coordination
  - Feature flag advertisement

### 2. BluetoothConnection (Device Handler)
- **Role**: Individual BLE device connection manager
- **Responsibilities**:
  - GATT service discovery
  - Characteristic read/write operations
  - Notification handling
  - Connection state management

## Feature Flags System

The proxy advertises its capabilities using feature flags:

```python
class BluetoothProxyFeature:
    FEATURE_PASSIVE_SCAN = 1 << 0        # BLE advertisement scanning
    FEATURE_ACTIVE_CONNECTIONS = 1 << 1   # Device connections
    FEATURE_REMOTE_CACHING = 1 << 2       # Service caching
    FEATURE_PAIRING = 1 << 3              # Device pairing
    FEATURE_CACHE_CLEARING = 1 << 4       # Cache management
    FEATURE_RAW_ADVERTISEMENTS = 1 << 5   # Raw advertisement data
    FEATURE_STATE_AND_MODE = 1 << 6       # Scanner state reporting
```

## Implementation Phases

### Phase 1: Foundation and Basic ESPHome API Server
**Goal**: Create the core ESPHome API server that Home Assistant can connect to

#### 1.1 Core API Server Structure
```python
# src/esphome_bluetooth_proxy/api_server.py
class ESPHomeAPIServer:
    """Main ESPHome API server implementing the 4-step handshake"""

    async def start_server(self, host: str = "0.0.0.0", port: int = 6053)
    async def handle_client(self, reader: StreamReader, writer: StreamWriter)
    async def handle_hello_request(self, msg: HelloRequest) -> HelloResponse
    async def handle_connect_request(self, msg: ConnectRequest) -> ConnectResponse
    async def handle_device_info_request(self, msg: DeviceInfoRequest) -> DeviceInfoResponse
    async def handle_list_entities_request(self, msg: ListEntitiesRequest)
```

#### 1.2 Protobuf Message Handling
```python
# src/esphome_bluetooth_proxy/protocol.py
class MessageHandler:
    """Handles ESPHome protobuf message encoding/decoding"""

    def encode_message(self, msg: ProtoMessage, msg_type: int) -> bytes
    def decode_message(self, data: bytes) -> tuple[int, ProtoMessage]
    def create_message_frame(self, msg_type: int, payload: bytes) -> bytes
```

#### 1.3 Connection State Management
```python
# src/esphome_bluetooth_proxy/connection.py
class ConnectionState(Enum):
    CONNECTING = 0
    CONNECTED = 1
    AUTHENTICATED = 2

class APIConnection:
    """Manages individual API client connections"""

    def __init__(self, reader: StreamReader, writer: StreamWriter)
    async def authenticate(self, password: str) -> bool
    async def send_message(self, msg: ProtoMessage, msg_type: int)
    async def close(self)
```

#### 1.4 Device Information Emulation
```python
# src/esphome_bluetooth_proxy/device_info.py
class DeviceInfoProvider:
    """Provides device information matching ESPHome format"""

    def get_device_info(self) -> DeviceInfoResponse:
        # Returns device info with Bluetooth proxy capabilities
        # Includes feature flags, MAC address, version info
        pass
```

**Deliverables**:
- Basic TCP server accepting connections on port 6053
- Complete 4-step handshake implementation
- Device info response with Bluetooth proxy feature flags
- Connection state management
- Basic logging and error handling

**Testing**: Home Assistant should be able to discover and connect to the proxy

---

### Phase 2: Passive BLE Scanning
**Goal**: Implement BLE advertisement scanning and forwarding to Home Assistant

#### 2.1 BLE Scanner Integration
```python
# src/esphome_bluetooth_proxy/ble_scanner.py
class BLEScanner:
    """Manages BLE advertisement scanning using bleak"""

    def __init__(self, callback: Callable[[BLEAdvertisement], None])
    async def start_scanning(self, active: bool = False)
    async def stop_scanning(self)
    def set_scan_mode(self, active: bool)
```

#### 2.2 Advertisement Data Structures
```python
# src/esphome_bluetooth_proxy/advertisement.py
@dataclass
class BLEAdvertisement:
    """Raw BLE advertisement data matching ESPHome format"""

    address: int  # 48-bit MAC as uint64
    rssi: int
    address_type: int  # Public/Random
    data: bytes  # Raw advertisement data (max 62 bytes)
    data_len: int
```

#### 2.3 Advertisement Batching System
```python
# src/esphome_bluetooth_proxy/advertisement_batcher.py
class AdvertisementBatcher:
    """Batches advertisements for efficient WiFi transmission"""

    FLUSH_BATCH_SIZE = 16  # Match ESPHome optimization

    def __init__(self, send_callback: Callable[[List[BLEAdvertisement]], None])
    def add_advertisement(self, adv: BLEAdvertisement)
    async def flush_batch(self)
    def _should_flush(self) -> bool
```

#### 2.4 Advertisement Forwarding
```python
# src/esphome_bluetooth_proxy/bluetooth_proxy.py
class BluetoothProxy:
    """Main Bluetooth proxy coordinator"""

    def __init__(self, api_server: ESPHomeAPIServer)
    async def start(self)
    async def handle_advertisement(self, adv: BLEAdvertisement)
    async def subscribe_advertisements(self, connection: APIConnection, flags: int)
    async def unsubscribe_advertisements(self, connection: APIConnection)
```

**Deliverables**:
- BLE advertisement scanning using bleak
- Advertisement batching with ESPHome-compatible optimization
- Raw advertisement forwarding to Home Assistant
- Subscription management for API connections

**Testing**: Home Assistant should receive BLE advertisements from nearby devices

---

### Phase 3: Active BLE Connections
**Goal**: Implement device connection management and basic GATT operations

#### 3.1 Connection Pool Management
```python
# src/esphome_bluetooth_proxy/connection_pool.py
class ConnectionPool:
    """Manages multiple BLE device connections"""

    def __init__(self, max_connections: int = 3)
    async def connect_device(self, address: int, address_type: int) -> BLEConnection
    async def disconnect_device(self, address: int)
    def get_connection(self, address: int) -> Optional[BLEConnection]
    def get_free_connections(self) -> int
```

#### 3.2 BLE Device Connection
```python
# src/esphome_bluetooth_proxy/ble_connection.py
class BLEConnection:
    """Individual BLE device connection handler"""

    def __init__(self, address: int, address_type: int, proxy: BluetoothProxy)
    async def connect(self) -> bool
    async def disconnect(self)
    async def discover_services(self) -> List[BLEService]
    def is_connected(self) -> bool
    async def get_mtu(self) -> int
```

#### 3.3 Device Request Handling
```python
# src/esphome_bluetooth_proxy/device_handler.py
class DeviceRequestHandler:
    """Handles device connection requests from Home Assistant"""

    async def handle_device_request(self, msg: BluetoothDeviceRequest)
    async def handle_connect_request(self, address: int, address_type: int)
    async def handle_disconnect_request(self, address: int)
    async def send_connection_response(self, address: int, connected: bool, mtu: int, error: int)
```

**Deliverables**:
- Device connection/disconnection handling
- Connection pool with configurable limits
- Connection state tracking and reporting
- Basic error handling and recovery

**Testing**: Home Assistant should be able to connect to and disconnect from BLE devices

---

### Phase 4: GATT Service Discovery
**Goal**: Implement GATT service discovery and characteristic enumeration

#### 4.1 Service Discovery
```python
# src/esphome_bluetooth_proxy/gatt_discovery.py
class GATTServiceDiscovery:
    """Handles GATT service discovery"""

    async def discover_services(self, connection: BLEConnection) -> List[BLEService]
    async def discover_characteristics(self, service: BLEService) -> List[BLECharacteristic]
    async def discover_descriptors(self, characteristic: BLECharacteristic) -> List[BLEDescriptor]
```

#### 4.2 GATT Data Structures
```python
# src/esphome_bluetooth_proxy/gatt_types.py
@dataclass
class BLEService:
    uuid: bytes  # 16-byte UUID
    handle: int
    characteristics: List[BLECharacteristic]

@dataclass
class BLECharacteristic:
    uuid: bytes
    handle: int
    properties: int  # Read/Write/Notify flags
    descriptors: List[BLEDescriptor]

@dataclass
class BLEDescriptor:
    uuid: bytes
    handle: int
```

#### 4.3 Service Response Handling
```python
# src/esphome_bluetooth_proxy/service_handler.py
class ServiceResponseHandler:
    """Handles GATT service discovery requests"""

    async def handle_get_services_request(self, msg: BluetoothGATTGetServicesRequest)
    async def send_services_response(self, address: int, services: List[BLEService])
    async def send_services_done(self, address: int)
```

**Deliverables**:
- Complete GATT service discovery
- Service/characteristic/descriptor enumeration
- Service discovery batching and optimization
- Service discovery error handling

**Testing**: Home Assistant should be able to discover services on connected devices

---

### Phase 5: GATT Read/Write Operations
**Goal**: Implement GATT characteristic and descriptor operations

#### 5.1 GATT Operations
```python
# src/esphome_bluetooth_proxy/gatt_operations.py
class GATTOperations:
    """Handles GATT read/write operations"""

    async def read_characteristic(self, connection: BLEConnection, handle: int) -> bytes
    async def write_characteristic(self, connection: BLEConnection, handle: int, data: bytes, response: bool) -> bool
    async def read_descriptor(self, connection: BLEConnection, handle: int) -> bytes
    async def write_descriptor(self, connection: BLEConnection, handle: int, data: bytes, response: bool) -> bool
```

#### 5.2 Operation Request Handling
```python
# src/esphome_bluetooth_proxy/gatt_handler.py
class GATTRequestHandler:
    """Handles GATT operation requests from Home Assistant"""

    async def handle_read_request(self, msg: BluetoothGATTReadRequest)
    async def handle_write_request(self, msg: BluetoothGATTWriteRequest)
    async def handle_read_descriptor_request(self, msg: BluetoothGATTReadDescriptorRequest)
    async def handle_write_descriptor_request(self, msg: BluetoothGATTWriteDescriptorRequest)
```

#### 5.3 Operation Response Management
```python
# src/esphome_bluetooth_proxy/gatt_responses.py
class GATTResponseManager:
    """Manages GATT operation responses"""

    async def send_read_response(self, address: int, handle: int, data: bytes)
    async def send_write_response(self, address: int, handle: int, success: bool)
    async def send_gatt_error(self, address: int, handle: int, error: int)
```

**Deliverables**:
- Characteristic read/write operations
- Descriptor read/write operations
- Operation queuing and error handling
- Response management and error reporting

**Testing**: Home Assistant should be able to read from and write to device characteristics

---

### Phase 6: GATT Notifications
**Goal**: Implement GATT notification subscription and forwarding

#### 6.1 Notification Management
```python
# src/esphome_bluetooth_proxy/notifications.py
class NotificationManager:
    """Manages GATT notifications"""

    def __init__(self, proxy: BluetoothProxy)
    async def subscribe_notifications(self, connection: BLEConnection, handle: int) -> bool
    async def unsubscribe_notifications(self, connection: BLEConnection, handle: int) -> bool
    async def handle_notification(self, address: int, handle: int, data: bytes)
```

#### 6.2 Notification Request Handling
```python
# src/esphome_bluetooth_proxy/notify_handler.py
class NotificationRequestHandler:
    """Handles notification requests from Home Assistant"""

    async def handle_notify_request(self, msg: BluetoothGATTNotifyRequest)
    async def send_notification_data(self, address: int, handle: int, data: bytes)
```

**Deliverables**:
- Notification subscription/unsubscription
- Real-time notification forwarding
- Notification state management
- Notification error handling

**Testing**: Home Assistant should receive real-time notifications from device characteristics

---

### Phase 7: Advanced Features
**Goal**: Implement pairing, cache management, and production features

#### 7.1 Device Pairing
```python
# src/esphome_bluetooth_proxy/pairing.py
class PairingManager:
    """Handles device pairing operations"""

    async def pair_device(self, address: int) -> bool
    async def unpair_device(self, address: int) -> bool
    async def clear_device_cache(self, address: int) -> bool
```

#### 7.2 Scanner Mode Management
```python
# src/esphome_bluetooth_proxy/scanner_mode.py
class ScannerModeManager:
    """Manages scanner active/passive modes"""

    def set_scanner_mode(self, active: bool)
    def get_scanner_state(self) -> ScannerState
    async def send_scanner_state_update(self)
```

#### 7.3 Production Hardening
- Comprehensive error handling and recovery
- Graceful shutdown procedures
- Configuration validation and defaults
- Performance monitoring and metrics
- Memory usage optimization
- Connection timeout handling

**Deliverables**:
- Complete feature parity with ESPHome C++ implementation
- Production-ready error handling and recovery
- Performance optimization
- Comprehensive testing and validation

## Key Implementation Notes

### 1. Advertisement Batching Optimization
The C++ implementation uses a sophisticated batching system:
- Batch size of 16 advertisements for optimal WiFi MTU utilization
- Pre-allocated response objects to minimize memory allocation
- Advertisement pooling for memory efficiency

### 2. Connection Management
- Maximum of 3 concurrent connections (configurable)
- Connection state tracking and recovery
- Proper cleanup on disconnection

### 3. Error Handling
- Comprehensive error codes matching ESP32 BLE stack
- Graceful degradation on connection failures
- Proper error reporting to Home Assistant

### 4. Memory Optimization
- Efficient data structures matching C++ layout
- Minimal memory allocation in hot paths
- Proper resource cleanup

This roadmap provides a clear path to implement a Python Bluetooth proxy that maintains full compatibility with the ESPHome C++ implementation while leveraging Python's strengths for maintainability and extensibility.
