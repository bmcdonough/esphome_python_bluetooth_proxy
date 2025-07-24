"""ESPHome Python Bluetooth Proxy.

A Python implementation of the ESPHome Bluetooth proxy functionality.
"""

__version__ = "0.1.0"

from .advertisement_batcher import AdvertisementBatcher

# Phase 1: Core API Server Components
from .api_server import ESPHomeAPIServer

# Phase 3: BLE Connection Components
from .ble_connection import BLECharacteristic, BLEConnection, BLEDescriptor, BLEService

# Phase 2: BLE Scanning Components
from .ble_scanner import BLEAdvertisement, BLEScanner

# Main Coordinator
from .bluetooth_proxy import BluetoothProxy
from .connection import APIConnection, ConnectionState
from .device_info import BluetoothProxyFeature, DeviceInfoProvider

# Phase 4-6: GATT Operations and Advanced Features
from .gatt_operations import GATTOperationHandler
from .pairing_manager import PairingManager, PairingState
from .protocol import MessageDecoder, MessageEncoder, MessageType

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
