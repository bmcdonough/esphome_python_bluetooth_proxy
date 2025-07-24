# ESPHome-Home Assistant Connection Protocol Analysis

This document provides a comprehensive analysis of the ESPHome-Home Assistant connection protocol, based on examination of the ESPHome codebase. This analysis serves as the foundation for implementing a Python-based Bluetooth proxy that can seamlessly integrate with Home Assistant's ESPHome integration.

## Overview

ESPHome uses a **TCP-based Protocol Buffers (protobuf) protocol** for communication with Home Assistant. The connection operates on **port 6053** by default and supports both plaintext and encrypted (Noise protocol) communication.

## Connection Protocol Architecture

### Transport Layer
- **Protocol**: TCP
- **Default Port**: 6053
- **Encryption**: Optional Noise protocol with pre-shared keys
- **Message Format**: `[0x00][VarInt: Message Size][VarInt: Message Type][Protobuf Data]`

### Security Options
1. **Plaintext**: Direct TCP communication (less secure, simpler implementation)
2. **Noise Protocol**: Encrypted communication providing:
   - Forward secrecy
   - Mutual authentication
   - Protection against man-in-the-middle attacks

## Initial Connection Handshake

The connection establishment follows a precise **4-step process**:

### Step 1: Hello Request/Response
**Purpose**: Version negotiation and client identification

```protobuf
// Client (Home Assistant) → Server (ESPHome)
HelloRequest {
  client_info: "Home Assistant"
  api_version_major: 1
  api_version_minor: 10
}

// Server (ESPHome) → Client (Home Assistant)
HelloResponse {
  api_version_major: 1
  api_version_minor: 10
  server_info: "device_name (esphome v2024.x.x)"
  name: "device_name"
}
```

**What happens:**
- Home Assistant identifies itself and declares its API version
- ESPHome responds with its capabilities and version information
- Both sides negotiate the protocol version to use
- No authentication required for this step

### Step 2: Connect Request/Response (Authentication)
**Purpose**: Password-based authentication

```protobuf
// Client → Server
ConnectRequest {
  password: "your_api_password"  // if configured, empty string if no password
}

// Server → Client
ConnectResponse {
  invalid_password: false  // true if authentication failed
}
```

**What happens:**
- Home Assistant sends the API password (if configured)
- ESPHome validates the password and responds with success/failure
- If successful, the connection moves to authenticated state
- Connection is terminated immediately if authentication fails

### Step 3: Device Information Exchange
**Purpose**: Device metadata and capability discovery

```protobuf
// Client → Server
DeviceInfoRequest {}

// Server → Client
DeviceInfoResponse {
  uses_password: true
  name: "device_name"
  mac_address: "AA:BB:CC:DD:EE:FF"
  esphome_version: "2024.x.x"
  compilation_time: "Jan 1 2024, 12:00:00"
  model: "ESP32"
  has_deep_sleep: false
  project_name: "esphome.bluetooth-proxy"
  project_version: "1.0.0"
  webserver_port: 80
  bluetooth_proxy_feature_flags: 123  // if Bluetooth proxy enabled
  manufacturer: "Espressif"
  friendly_name: "Living Room Bluetooth Proxy"
  bluetooth_mac_address: "AA:BB:CC:DD:EE:AA"  // if Bluetooth available
  // Additional device metadata...
}
```

**What happens:**
- Home Assistant requests comprehensive device information
- ESPHome provides device metadata including Bluetooth capabilities
- This information is used by HA to configure the integration and determine available features

### Step 4: Entity Discovery
**Purpose**: Discover all available entities and their capabilities

```protobuf
// Client → Server
ListEntitiesRequest {}

// Server → Client (multiple responses for different entity types)
ListEntitiesSensorResponse {
  object_id: "temperature"
  key: 1234567890
  name: "Temperature"
  unique_id: "esp32_temp_sensor"
  device_class: "temperature"
  unit_of_measurement: "°C"
  accuracy_decimals: 1
  // ... other sensor properties
}

ListEntitiesBinarySensorResponse {
  object_id: "motion"
  key: 1234567891
  name: "Motion Sensor"
  unique_id: "esp32_motion"
  device_class: "motion"
  // ... other binary sensor properties
}

// ... other entity types (lights, switches, etc.)

ListEntitiesDoneResponse {}  // Signals end of entity list
```

**What happens:**
- Home Assistant requests all available entities
- ESPHome sends detailed information about each entity (sensors, switches, lights, etc.)
- Each entity includes metadata like device class, unit of measurement, capabilities
- The process ends with a `ListEntitiesDoneResponse` message

## Bluetooth Proxy Integration

When Bluetooth proxy functionality is enabled, ESPHome advertises specific capabilities and handles Bluetooth-related messages.

### Bluetooth Capability Advertisement

In the `DeviceInfoResponse`, Bluetooth proxy capabilities are indicated by:
- `bluetooth_proxy_feature_flags`: Bitfield indicating supported features
- `bluetooth_mac_address`: The Bluetooth MAC address of the device

### Bluetooth-Specific Message Types

#### BLE Advertisement Subscription
```protobuf
// Client subscribes to BLE advertisements
SubscribeBluetoothLEAdvertisementsRequest {
  flags: 1  // Subscription flags
}

// Server streams BLE advertisement data
BluetoothLERawAdvertisementsResponse {
  advertisements: [
    {
      address: 0x112233445566
      rssi: -45
      address_type: 1  // Public/Random address type
      data: [0x02, 0x01, 0x06, ...]  // Raw BLE advertisement data (max 62 bytes)
    }
  ]
}
```

#### Device Connection Management
```protobuf
BluetoothDeviceRequest {
  address: 0x112233445566
  request_type: BLUETOOTH_DEVICE_REQUEST_TYPE_CONNECT  // or DISCONNECT, PAIR, etc.
  has_address_type: true
  address_type: 1
}

BluetoothDeviceConnectionResponse {
  address: 0x112233445566
  connected: true
  mtu: 247
  error: 0
}
```

#### GATT Operations
```protobuf
// Service discovery
BluetoothGATTGetServicesRequest {
  address: 0x112233445566
}

BluetoothGATTGetServicesResponse {
  address: 0x112233445566
  services: [
    {
      uuid: [0x12, 0x34, ...]  // 16-byte UUID
      handle: 1
      characteristics: [
        {
          uuid: [0x56, 0x78, ...]
          handle: 2
          properties: 0x12  // Read/Write/Notify flags
          descriptors: [...]
        }
      ]
    }
  ]
}

// Read/Write operations
BluetoothGATTReadRequest {
  address: 0x112233445566
  handle: 2
}

BluetoothGATTWriteRequest {
  address: 0x112233445566
  handle: 2
  response: true
  data: [0x01, 0x02, 0x03]
}

// Notifications
BluetoothGATTNotifyRequest {
  address: 0x112233445566
  handle: 2
  enable: true
}
```

## Ongoing Communication

After the initial handshake, the connection maintains several types of ongoing communication:

### State Updates
- Real-time entity state changes are pushed to Home Assistant
- Each state update includes the entity key and new value

### Command Handling
- Home Assistant sends control commands for entities
- ESPHome processes commands and updates entity states accordingly

### Keepalive Mechanism
- Periodic ping/pong messages maintain connection health
- Configurable timeout for connection failure detection

### Bluetooth Data Streaming
- Continuous BLE advertisement data forwarding (if proxy enabled)
- Real-time GATT operation responses
- Connection status updates for paired devices

## Implementation Requirements for Python Bluetooth Proxy

Based on this protocol analysis, a Python implementation must:

### Core Protocol Implementation
1. **TCP Server**: Listen on port 6053 for incoming connections
2. **Protobuf Handling**: Implement ESPHome's protobuf message definitions
3. **Message Framing**: Handle the ESPHome message format with VarInt encoding
4. **State Management**: Track connection phases (connecting → connected → authenticated)

### Authentication & Security
1. **Password Validation**: Support optional API password authentication
2. **Noise Protocol**: Optional encrypted communication support
3. **Connection Management**: Handle multiple simultaneous client connections

### Device Emulation
1. **Device Information**: Provide realistic device metadata
2. **Entity Discovery**: Implement entity listing mechanism
3. **Bluetooth Capabilities**: Advertise Bluetooth proxy feature flags

### Bluetooth Integration
1. **BLE Scanning**: Use `bleak` library for Bluetooth Low Energy device discovery
2. **Advertisement Forwarding**: Stream BLE advertisement data to Home Assistant
3. **GATT Operations**: Handle device connection, service discovery, read/write/notify operations
4. **Device Management**: Track connected devices and their states

### Async Architecture
1. **Async I/O**: The protocol is designed for asynchronous operation
2. **Concurrent Handling**: Support multiple simultaneous Bluetooth operations
3. **Event-Driven**: React to BLE events and forward them appropriately

## Key Protocol Files in ESPHome

For reference, the key files in the ESPHome codebase that define this protocol:

- `esphome/components/api/api.proto` - Protocol buffer definitions
- `esphome/components/api/api_connection.cpp` - Connection handling logic
- `esphome/components/api/api_server.cpp` - Server implementation
- `esphome/components/api/api_pb2.cpp` - Generated protobuf code

## Message Flow Diagram

```
Home Assistant                    ESPHome Device
     |                                 |
     |-------- HelloRequest --------->|
     |<------- HelloResponse ---------|
     |                                |
     |------- ConnectRequest -------->|
     |<------ ConnectResponse --------|
     |                                |
     |------ DeviceInfoRequest ------>|
     |<----- DeviceInfoResponse ------|
     |                                |
     |----- ListEntitiesRequest ----->|
     |<-- ListEntities*Response ------|
     |<-- ListEntitiesDoneResponse ---|
     |                                |
     |-- SubscribeBluetoothLE... ---->|
     |<-- BluetoothLERawAdvert... ----|
     |<-- BluetoothLERawAdvert... ----|
     |         (continuous)           |
```

This protocol analysis provides the complete foundation needed to implement a Python-based ESPHome Bluetooth proxy that will seamlessly integrate with Home Assistant's existing ESPHome integration.
