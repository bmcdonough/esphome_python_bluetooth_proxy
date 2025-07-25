"""ESPHome Device Information Provider.

This module provides device information that matches the ESPHome format,
including Bluetooth proxy capabilities and feature flags.
"""

import logging
import subprocess
from datetime import datetime
from typing import Optional

from bleak import BleakScanner

from .protocol import DeviceInfoResponse


class BluetoothProxyFeature:
    """Bluetooth proxy feature flags matching ESPHome implementation."""

    FEATURE_PASSIVE_SCAN = 1 << 0  # BLE advertisement scanning
    FEATURE_ACTIVE_CONNECTIONS = 1 << 1  # Device connections
    FEATURE_REMOTE_CACHING = 1 << 2  # Service caching
    FEATURE_PAIRING = 1 << 3  # Device pairing
    FEATURE_CACHE_CLEARING = 1 << 4  # Cache management
    FEATURE_RAW_ADVERTISEMENTS = 1 << 5  # Raw advertisement data
    FEATURE_STATE_AND_MODE = 1 << 6  # Scanner state reporting


class DeviceInfoProvider:
    """Provides device information matching ESPHome format."""

    def __init__(
        self,
        name: str = "python-bluetooth-proxy",
        friendly_name: str = "Python Bluetooth Proxy",
        password: Optional[str] = None,
        active_connections: bool = False,
    ):
        """Initialize device info provider.

        Args:
            name: Device name
            friendly_name: Human-readable device name
            password: API password (if any)
            active_connections: Whether to support active BLE connections
        """
        self.name = name
        self.friendly_name = friendly_name
        self.password = password
        self.active_connections = active_connections

        # Hardware Bluetooth MAC address - must be detected from actual hardware
        self.bluetooth_mac_address = None  # Will be set asynchronously
        self._bluetooth_mac_cached = None

        # Version and build info
        self.esphome_version = "2024.12.0"  # Match recent ESPHome version
        self.compilation_time = datetime.now().strftime("%b %d %Y, %H:%M:%S")

    async def _get_bluetooth_mac_address(self) -> str:
        """Get the actual Bluetooth hardware MAC address.

        This method only returns hardware MAC addresses. If no hardware
        Bluetooth adapter is found, the program will exit with suggestions.
        """
        if self._bluetooth_mac_cached:
            return self._bluetooth_mac_cached

        logger = logging.getLogger(__name__)
        errors = []

        # Method 1: Try to get the Bluetooth adapter address using bleak
        try:
            logger.debug("Attempting to detect Bluetooth MAC via bleak/pybluez...")
            scanner = BleakScanner()
            # Get the adapter info - this will give us the local adapter details
            adapter = scanner._adapter if hasattr(scanner, "_adapter") else None

            if adapter and hasattr(adapter, "address"):
                mac_address = adapter.address
                logger.info(f"Found Bluetooth adapter MAC via bleak: {mac_address}")
                self._bluetooth_mac_cached = mac_address
                return mac_address
            else:
                errors.append(
                    "bleak: No adapter found or adapter has no address attribute"
                )
        except Exception as e:
            errors.append(f"bleak: {str(e)}")
            logger.debug(f"bleak method failed: {e}")

        # Method 2: Try to read from hciconfig (Linux)
        try:
            logger.debug("Attempting to detect Bluetooth MAC via hciconfig...")
            result = subprocess.run(
                ["hciconfig", "hci0"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "BD Address:" in line:
                        mac_address = line.split("BD Address:")[1].strip().split()[0]
                        logger.info(f"Found Bluetooth MAC via hciconfig: {mac_address}")
                        self._bluetooth_mac_cached = mac_address
                        return mac_address
                errors.append(
                    "hciconfig: Command succeeded but no BD Address found in output"
                )
            else:
                errors.append(
                    f"hciconfig: Command failed with return code {result.returncode}"
                )
                if result.stderr:
                    errors.append(f"hciconfig stderr: {result.stderr.strip()}")
        except FileNotFoundError:
            errors.append("hciconfig: Command not found (install bluez-utils package)")
        except subprocess.TimeoutExpired:
            errors.append("hciconfig: Command timed out after 5 seconds")
        except Exception as e:
            errors.append(f"hciconfig: {str(e)}")

        # If we reach here, no hardware MAC address could be detected
        logger.error("CRITICAL: Could not detect hardware Bluetooth MAC address")
        logger.error("Attempted methods and their errors:")
        for error in errors:
            logger.error(f"  - {error}")

        logger.error("\nTroubleshooting suggestions:")
        logger.error("1. Ensure Bluetooth hardware is present and enabled")
        logger.error(
            "2. Check if Bluetooth service is running: systemctl status bluetooth"
        )
        logger.error("3. Install required packages: sudo apt install bluez bluez-utils")
        logger.error(
            "4. Verify Bluetooth adapter is detected: lsusb | grep -i bluetooth"
        )
        logger.error("5. Check kernel modules: lsmod | grep bluetooth")
        logger.error("6. Try manual hciconfig: hciconfig -a")
        logger.error("7. Install Python Bluetooth libraries: pip install pybluez")

        # Exit the program - we cannot continue without hardware MAC
        import sys

        logger.error(
            "\nExiting: Hardware Bluetooth MAC address is required for operation"
        )
        sys.exit(1)

    def get_feature_flags(self) -> int:
        """Get Bluetooth proxy feature flags."""
        flags = 0

        # Always supported features
        flags |= BluetoothProxyFeature.FEATURE_PASSIVE_SCAN
        flags |= BluetoothProxyFeature.FEATURE_RAW_ADVERTISEMENTS
        flags |= BluetoothProxyFeature.FEATURE_STATE_AND_MODE

        # Conditional features based on configuration
        if self.active_connections:
            flags |= BluetoothProxyFeature.FEATURE_ACTIVE_CONNECTIONS
            flags |= BluetoothProxyFeature.FEATURE_REMOTE_CACHING
            flags |= BluetoothProxyFeature.FEATURE_PAIRING
            flags |= BluetoothProxyFeature.FEATURE_CACHE_CLEARING

        return flags

    async def get_device_info(self) -> DeviceInfoResponse:
        """Get complete device information response."""
        # Ensure we have the Bluetooth MAC address
        if not self.bluetooth_mac_address:
            self.bluetooth_mac_address = await self._get_bluetooth_mac_address()

        return DeviceInfoResponse(
            uses_password=self.password is not None,
            name=self.name,
            mac_address=self.bluetooth_mac_address,  # Use hardware Bluetooth MAC
            esphome_version=self.esphome_version,
            compilation_time=self.compilation_time,
            model="Python Bluetooth Proxy",
            has_deep_sleep=False,
            project_name="esphome.python-bluetooth-proxy",
            project_version="0.1.0",
            webserver_port=0,  # No web server for now
            bluetooth_proxy_feature_flags=self.get_feature_flags(),
            manufacturer="ESPHome Community",
            friendly_name=self.friendly_name,
            bluetooth_mac_address=self.bluetooth_mac_address,
        )

    def set_active_connections(self, active: bool) -> None:
        """Enable or disable active connection support."""
        self.active_connections = active

    def has_active_connections(self) -> bool:
        """Check if active connections are supported."""
        return self.active_connections
