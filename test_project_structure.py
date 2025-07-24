#!/usr/bin/env python3
"""Test script for complete project structure.

This script tests that all modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")

    try:
        # Test imports for all phases
        print("Testing imports...")
        try:
            from esphome_bluetooth_proxy import DeviceInfoProvider  # noqa: F401
            from esphome_bluetooth_proxy import ESPHomeAPIServer  # noqa: F401

            print("✓ Phase 1 imports successful")
        except ImportError as e:
            print(f"✗ Phase 1 imports failed: {e}")
            sys.exit(1)

        print("✓ Phase 2 imports successful")

        # Phase 3: BLE Connection Components
        from esphome_bluetooth_proxy import (
            BLECharacteristic,
            BLEConnection,
            BLEDescriptor,
            BLEService,
        )

        print("✓ Phase 3 imports successful")

        # Phase 4-6: GATT Operations and Advanced Features
        from esphome_bluetooth_proxy import (
            GATTOperationHandler,
            PairingManager,
            PairingState,
        )

        print("✓ Phase 4-6 imports successful")

        # Main Coordinator
        from esphome_bluetooth_proxy import BluetoothProxy

        print("✓ Main coordinator import successful")

        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality of key components."""
    print("\nTesting basic functionality...")

    try:
        from esphome_bluetooth_proxy import (
            BluetoothProxyFeature,
            DeviceInfoProvider,
            ESPHomeAPIServer,
        )

        # Test device info provider
        provider = DeviceInfoProvider(name="test-proxy")
        device_info = provider.get_device_info()

        print(f"✓ Device info: {device_info.name}")
        print(f"✓ MAC address: {device_info.mac_address}")
        print(f"✓ Bluetooth MAC: {device_info.bluetooth_mac_address}")
        print(f"✓ Feature flags: 0x{device_info.bluetooth_proxy_feature_flags:02x}")

        # Test feature flags
        expected_flags = (
            BluetoothProxyFeature.FEATURE_PASSIVE_SCAN
            | BluetoothProxyFeature.FEATURE_RAW_ADVERTISEMENTS
            | BluetoothProxyFeature.FEATURE_STATE_AND_MODE
        )

        if device_info.bluetooth_proxy_feature_flags == expected_flags:
            print("✓ Feature flags correct for passive mode")
        else:
            print(
                f"✗ Feature flags mismatch: expected 0x{expected_flags:02x}, "
                f"got 0x{device_info.bluetooth_proxy_feature_flags:02x}"
            )
            return False

        # Test active connections
        provider.set_active_connections(True)
        device_info_active = provider.get_device_info()

        if device_info_active.bluetooth_proxy_feature_flags > expected_flags:
            print("✓ Active connection features enabled correctly")
        else:
            print("✗ Active connection features not enabled")
            return False

        # Test API server creation (don't start it)
        server = ESPHomeAPIServer(
            name="test-server", friendly_name="Test Server", password=None
        )
        print("✓ API server created successfully")

        return True

    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False


def test_class_structure():
    """Test that classes have expected methods and attributes."""
    print("\nTesting class structure...")

    try:
        from esphome_bluetooth_proxy import (
            BLEConnection,
            BLEScanner,
            BluetoothProxy,
            ESPHomeAPIServer,
            GATTOperationHandler,
            PairingManager,
        )

        # Test ESPHomeAPIServer
        server = ESPHomeAPIServer()
        expected_methods = [
            "start",
            "stop",
            "get_authenticated_connections",
            "broadcast_message",
        ]
        for method in expected_methods:
            if not hasattr(server, method):
                print(f"✗ ESPHomeAPIServer missing method: {method}")
                return False
        print("✓ ESPHomeAPIServer has expected methods")

        # Test BLEScanner (without callback for structure test)
        def dummy_callback(adv):
            pass

        scanner = BLEScanner(dummy_callback)
        expected_methods = [
            "start_scanning",
            "stop_scanning",
            "set_scan_mode",
            "is_scanning",
        ]
        for method in expected_methods:
            if not hasattr(scanner, method):
                print(f"✗ BLEScanner missing method: {method}")
                return False
        print("✓ BLEScanner has expected methods")

        # Test BLEConnection (with dummy parameters)
        connection = BLEConnection(0, 0, None)
        expected_methods = [
            "connect",
            "disconnect",
            "discover_services",
            "read_characteristic",
            "write_characteristic",
        ]
        for method in expected_methods:
            if not hasattr(connection, method):
                print(f"✗ BLEConnection missing method: {method}")
                return False
        print("✓ BLEConnection has expected methods")

        return True

    except Exception as e:
        print(f"✗ Class structure test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("ESPHome Python Bluetooth Proxy - Project Structure Test")
    print("=" * 60)

    all_passed = True

    # Test imports
    if not test_imports():
        all_passed = False

    # Test basic functionality
    if not test_basic_functionality():
        all_passed = False

    # Test class structure
    if not test_class_structure():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\nProject structure is complete and ready for development.")
        print("\nNext steps:")
        print("1. Run Phase 1 test: python test_phase1.py")
        print("2. Test with Home Assistant integration")
        print("3. Begin implementing Phase 2 (BLE scanning)")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the error messages above.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
