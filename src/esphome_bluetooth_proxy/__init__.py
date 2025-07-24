"""ESPHome Python Bluetooth Proxy.

A Python implementation of the ESPHome Bluetooth proxy functionality.
"""

__version__ = "0.1.0"

# Phase 1: Core API Server Components
from .api_server import ESPHomeAPIServer
from .connection import APIConnection, ConnectionState
from .device_info import DeviceInfoProvider, BluetoothProxyFeature
from .protocol import MessageType, MessageEncoder, MessageDecoder

# Phase 2: BLE Scanning Components
from .ble_scanner import BLEScanner, BLEAdvertisement
from .advertisement_batcher import AdvertisementBatcher

# Phase 3: BLE Connection Components
from .ble_connection import BLEConnection, BLEService, BLECharacteristic, BLEDescriptor

# Phase 4-6: GATT Operations and Advanced Features
from .gatt_operations import GATTOperationHandler
from .pairing_manager import PairingManager, PairingState

# Main Coordinator
from .bluetooth_proxy import BluetoothProxy

__all__ = [
    # Phase 1: Core API Server
    "ESPHomeAPIServer",
    "APIConnection",
    "ConnectionState",
    "DeviceInfoProvider",
    "BluetoothProxyFeature",
    "MessageType",
    "MessageEncoder",
    "MessageDecoder",
    
    # Phase 2: BLE Scanning
    "BLEScanner",
    "BLEAdvertisement",
    "AdvertisementBatcher",
    
    # Phase 3: BLE Connections
    "BLEConnection",
    "BLEService",
    "BLECharacteristic",
    "BLEDescriptor",
    
    # Phase 4-6: GATT and Advanced Features
    "GATTOperationHandler",
    "PairingManager",
    "PairingState",
    
    # Main Coordinator
    "BluetoothProxy",
]
__author__ = "bmcdonough"
