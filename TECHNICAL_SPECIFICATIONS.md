# Technical Specifications for Missing Features

This document provides detailed technical specifications for implementing the remaining features needed for full parity between the ESPHome C++ Bluetooth Proxy and the Python Bluetooth Proxy implementation.

## 1. Device Pairing Support

### 1.1 Overview

Device pairing support enables secure connections to BLE devices that require authentication. The implementation must match ESPHome's pairing functionality, including handling pairing requests, PIN code input, and bonding information storage.

### 1.2 Architectural Components

#### 1.2.1 PairingManager Class

Create a dedicated `PairingManager` class to handle all pairing-related operations:

```python
class PairingManager:
    def __init__(self, proxy: BluetoothProxy):
        self.proxy = proxy
        self.pending_pairing_requests = {}  # address -> PairingRequest
        self.bonded_devices = {}  # address -> BondInfo
        self.load_bonding_data()
    
    async def handle_pairing_request(self, address: int, io_capability: int, pairing_data: Dict) -> None:
        """Handle incoming pairing request from BLE device."""
        pass
        
    async def confirm_pairing(self, address: int, confirm: bool, passkey: Optional[str] = None) -> None:
        """Confirm or reject a pairing request, optionally with passkey."""
        pass
        
    async def remove_bond(self, address: int) -> bool:
        """Remove bonding information for a device."""
        pass
        
    def load_bonding_data(self) -> None:
        """Load bonding data from persistent storage."""
        pass
        
    def save_bonding_data(self) -> None:
        """Save bonding data to persistent storage."""
        pass
```

#### 1.2.2 Integration with BluetoothProxy

Extend the `BluetoothProxy` class to include pairing capabilities:

```python
class BluetoothProxy:
    # Existing code...
    
    def __init__(self, api_server, max_connections=3):
        # Existing initialization...
        self.pairing_manager = PairingManager(self)
        
    # Add pairing-related methods
    async def handle_pairing_request(self, address: int, io_capability: int, pairing_data: Dict) -> None:
        """Forward pairing request to pairing manager."""
        await self.pairing_manager.handle_pairing_request(address, io_capability, pairing_data)
        
    async def confirm_pairing(self, address: int, confirm: bool, passkey: Optional[str] = None) -> None:
        """Confirm or reject a pairing request."""
        await self.pairing_manager.confirm_pairing(address, confirm, passkey)
        
    async def remove_bond(self, address: int) -> bool:
        """Remove bonding information for a device."""
        return await self.pairing_manager.remove_bond(address)
```

#### 1.2.3 BLE Connection Enhancements

Extend the `BLEConnection` class to handle pairing events:

```python
class BLEConnection:
    # Existing code...
    
    async def handle_pairing_request(self, io_capability: int, pairing_data: Dict) -> None:
        """Handle pairing request from the device."""
        if self.proxy:
            await self.proxy.handle_pairing_request(self.address, io_capability, pairing_data)
            
    async def confirm_pairing(self, confirm: bool, passkey: Optional[str] = None) -> None:
        """Process pairing confirmation."""
        # Implementation using bleak
        pass
```

### 1.3 Protobuf Message Integration

Implement handlers for pairing-related protobuf messages:

1. `BluetoothDevicePairingRequest` - Incoming pairing request from device
2. `BluetoothDevicePairingResponse` - Response to pairing request
3. `BluetoothDeviceUnpairingRequest` - Request to remove pairing
4. `BluetoothDeviceClearCacheRequest` - Clear device cache

```python
# In api_server.py or appropriate handler file
async def handle_bluetooth_device_pairing_response(self, msg) -> None:
    """Handle pairing response from Home Assistant."""
    address = msg.address
    confirm = msg.confirm
    passkey = msg.passkey if msg.has_passkey else None
    
    await self.bluetooth_proxy.confirm_pairing(address, confirm, passkey)
    
async def handle_bluetooth_device_unpairing_request(self, msg) -> None:
    """Handle unpairing request from Home Assistant."""
    address = msg.address
    success = await self.bluetooth_proxy.remove_bond(address)
    
    # Send response
    await self.send_bluetooth_device_unpairing_response(address, success)
```

### 1.4 Persistent Storage

Implement persistent storage for bonding information:

```python
class BondStorage:
    """Persistent storage for bond information."""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.ensure_storage_dir()
        
    def ensure_storage_dir(self) -> None:
        """Ensure the storage directory exists."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
    def load(self) -> Dict:
        """Load bonding data from storage."""
        try:
            with open(self.storage_path, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
            
    def save(self, data: Dict) -> None:
        """Save bonding data to storage."""
        with open(self.storage_path, 'w') as file:
            json.dump(data, file)
```

### 1.5 Bleak Integration

Use bleak's pairing capabilities to implement the low-level pairing operations:

```python
async def pair_device(self, address: int, passkey: Optional[str] = None) -> bool:
    """Pair with a device using bleak."""
    try:
        client = self._get_or_create_client(address)
        if passkey:
            # Set passkey handler if available
            # This is platform dependent and may require different approaches
            pass
        
        await client.pair()
        return True
    except Exception as e:
        logger.error(f"Failed to pair with device {address:012X}: {e}")
        return False
```

### 1.6 Security Considerations

1. Store bonding information securely with appropriate permissions
2. Implement proper error handling for failed pairing attempts
3. Consider platform-specific pairing requirements

## 2. Cache Management

### 2.1 Overview

Cache management enables storing and retrieving service and characteristic information for devices, improving connection speed and reliability for frequently used devices.

### 2.2 Architectural Components

#### 2.2.1 CacheManager Class

Create a dedicated `CacheManager` class to handle device information caching:

```python
class CacheManager:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.device_caches = {}  # address -> DeviceCache
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_device_cache(self, address: int) -> Optional[DeviceCache]:
        """Get cache for a specific device."""
        if address in self.device_caches:
            return self.device_caches[address]
            
        # Try to load from disk
        cache = self.load_device_cache(address)
        if cache:
            self.device_caches[address] = cache
            return cache
            
        return None
        
    def store_device_cache(self, address: int, services: Dict) -> None:
        """Store device services in cache."""
        cache = DeviceCache(address, services)
        self.device_caches[address] = cache
        self.save_device_cache(cache)
        
    def clear_device_cache(self, address: int) -> bool:
        """Clear cached data for a device."""
        if address in self.device_caches:
            del self.device_caches[address]
            
        # Remove from disk if exists
        cache_path = self._get_cache_path(address)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            return True
            
        return False
        
    def load_device_cache(self, address: int) -> Optional[DeviceCache]:
        """Load device cache from disk."""
        cache_path = self._get_cache_path(address)
        try:
            with open(cache_path, 'r') as file:
                data = json.load(file)
                return DeviceCache.from_json(data)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
            
    def save_device_cache(self, cache: DeviceCache) -> None:
        """Save device cache to disk."""
        cache_path = self._get_cache_path(cache.address)
        with open(cache_path, 'w') as file:
            json.dump(cache.to_json(), file)
            
    def _get_cache_path(self, address: int) -> str:
        """Get file path for device cache."""
        return os.path.join(self.cache_dir, f"{address:012X}.json")
```

#### 2.2.2 DeviceCache Class

```python
class DeviceCache:
    def __init__(self, address: int, services: Dict = None):
        self.address = address
        self.services = services or {}
        self.timestamp = time.time()
        
    def to_json(self) -> Dict:
        """Convert cache to JSON serializable dict."""
        return {
            "address": self.address,
            "services": self.services,
            "timestamp": self.timestamp
        }
        
    @classmethod
    def from_json(cls, data: Dict) -> 'DeviceCache':
        """Create DeviceCache from JSON data."""
        return cls(
            address=data["address"],
            services=data["services"]
        )
```

#### 2.2.3 Integration with BLEConnection

Modify the `BLEConnection` class to use the cache:

```python
class BLEConnection:
    # Existing code...
    
    async def connect(self) -> bool:
        """Connect to the device, using cached service info if available."""
        try:
            # Normal connection logic
            await self.client.connect()
            
            # Try to use cached services if available
            cache = self.proxy.get_device_cache(self.address)
            if cache and cache.services:
                # Apply cached services if possible
                try:
                    self.services = await self._parse_cached_services(cache.services)
                    return True
                except Exception as e:
                    logger.warning(f"Failed to use cached services: {e}, falling back to discovery")
            
            # Normal service discovery if cache not available or failed
            await self.discover_services()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to device {self.address_str}: {e}")
            return False
            
    async def discover_services(self) -> Dict:
        """Discover device services and cache them."""
        services = await self.client.get_services()
        
        # Convert to serializable format and cache
        services_dict = self._services_to_dict(services)
        if self.proxy:
            self.proxy.store_device_cache(self.address, services_dict)
            
        return services
        
    def _services_to_dict(self, services) -> Dict:
        """Convert bleak services to serializable dict."""
        # Implementation to convert bleak.BleakGATTService objects to dict
        pass
        
    async def _parse_cached_services(self, services_dict: Dict):
        """Parse cached services dict back to usable format."""
        # Implementation to convert dict back to usable service objects
        pass
```

#### 2.2.4 Integration with BluetoothProxy

Extend the `BluetoothProxy` class to include cache management:

```python
class BluetoothProxy:
    # Existing code...
    
    def __init__(self, api_server, max_connections=3):
        # Existing initialization...
        cache_dir = os.path.join(os.path.expanduser("~"), ".esphome_bluetooth_proxy", "cache")
        self.cache_manager = CacheManager(cache_dir)
        
    def get_device_cache(self, address: int) -> Optional[DeviceCache]:
        """Get cache for a device."""
        return self.cache_manager.get_device_cache(address)
        
    def store_device_cache(self, address: int, services: Dict) -> None:
        """Store device services in cache."""
        self.cache_manager.store_device_cache(address, services)
        
    async def clear_device_cache(self, address: int) -> bool:
        """Clear device cache."""
        return self.cache_manager.clear_device_cache(address)
```

### 2.3 Protobuf Message Integration

Implement handler for cache clearing requests:

```python
async def handle_bluetooth_device_clear_cache_request(self, msg) -> None:
    """Handle request to clear device cache."""
    address = msg.address
    success = await self.bluetooth_proxy.clear_device_cache(address)
    
    # Send response
    await self.send_bluetooth_device_clear_cache_response(address, success)
```

### 2.4 Cache Validation

Implement cache validation to ensure cached data is still valid:

```python
def is_cache_valid(self, cache: DeviceCache) -> bool:
    """Check if cached data is still valid."""
    # Check age of cache
    max_age = 30 * 24 * 60 * 60  # 30 days in seconds
    if time.time() - cache.timestamp > max_age:
        return False
        
    # Additional validation logic as needed
    return True
```

## 3. Implementation Timeline

### 3.1 Phase 1: Foundation (Week 1)

1. Create basic class structures for PairingManager and CacheManager
2. Implement persistent storage mechanisms
3. Add integration points with BluetoothProxy and BLEConnection

### 3.2 Phase 2: Pairing Implementation (Week 2)

1. Implement platform-specific pairing with bleak
2. Add protobuf message handlers for pairing operations
3. Develop unit tests for pairing functionality

### 3.3 Phase 3: Cache Management Implementation (Week 3)

1. Implement service caching and restoration
2. Add cache validation and expiration
3. Develop unit tests for cache functionality

### 3.4 Phase 4: Integration and Testing (Week 4)

1. Integrate both features with main codebase
2. Perform end-to-end testing with Home Assistant
3. Optimize and refine implementation

## 4. Platform-Specific Considerations

### 4.1 Linux

- Use DBus for system-level pairing operations
- Consider BlueZ backend-specific pairing requirements

### 4.2 Windows

- Use Windows Bluetooth API for pairing operations
- Handle Windows-specific pairing prompts and security dialogs

### 4.3 macOS

- Use Core Bluetooth for pairing operations
- Handle macOS-specific pairing prompts

## 5. Testing Requirements

### 5.1 Unit Tests

1. Create tests for PairingManager functionality
2. Create tests for CacheManager operations
3. Test cache serialization and deserialization

### 5.2 Integration Tests

1. Test pairing with various BLE devices (requiring different security levels)
2. Test cache persistence across application restarts
3. Test cache invalidation scenarios

### 5.3 End-to-End Tests

1. Test complete Home Assistant integration
2. Verify protobuf message handling with actual devices
3. Measure performance improvements from caching

## 6. Conclusion

This technical specification provides a detailed roadmap for implementing device pairing and cache management in the Python Bluetooth Proxy. Following these specifications will ensure full feature parity with the ESPHome C++ implementation while maintaining the modular and platform-independent architecture of the Python version.

The implementation should focus first on core functionality, then address platform-specific differences to ensure consistent behavior across all supported operating systems.
