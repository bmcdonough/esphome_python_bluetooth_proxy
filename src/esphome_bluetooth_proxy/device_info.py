"""ESPHome Device Information Provider.

This module provides device information that matches the ESPHome format,
including Bluetooth proxy capabilities and feature flags.
"""

import logging
import subprocess
import uuid
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

        # Generate a consistent MAC address based on device name
        self.mac_address = self._generate_mac_address()
        # Read actual Bluetooth hardware address
        self.bluetooth_mac_address = None  # Will be set asynchronously
        self._bluetooth_mac_cached = None

        # Version and build info
        self.esphome_version = "2024.12.0"  # Match recent ESPHome version
        self.compilation_time = datetime.now().strftime("%b %d %Y, %H:%M:%S")

    def _generate_mac_address(self) -> str:
        """Generate a consistent MAC address based on device name."""
        # Use UUID5 to generate consistent MAC from device name
        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
        device_uuid = uuid.uuid5(namespace, self.name)

        # Extract 6 bytes from UUID for MAC address
        mac_bytes = device_uuid.bytes[:6]
        # Set locally administered bit and ensure unicast
        mac_bytes = bytes([mac_bytes[0] | 0x02 & 0xFE]) + mac_bytes[1:]

        return ":".join(f"{b:02X}" for b in mac_bytes)

    async def _get_bluetooth_mac_address(self) -> str:
        """Get the actual Bluetooth hardware MAC address."""
        if self._bluetooth_mac_cached:
            return self._bluetooth_mac_cached

        logger = logging.getLogger(__name__)

        try:
            # Try to get the Bluetooth adapter address using bleak
            scanner = BleakScanner()
            # Get the adapter info - this will give us the local adapter details
            adapter = scanner._adapter if hasattr(scanner, "_adapter") else None

            if adapter and hasattr(adapter, "address"):
                mac_address = adapter.address
                logger.info(f"Found Bluetooth adapter MAC: {mac_address}")
                self._bluetooth_mac_cached = mac_address
                return mac_address

            # Fallback: try to read from system files (Linux)
            try:
                result = subprocess.run(
                    ["hciconfig", "hci0"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "BD Address:" in line:
                            mac_address = (
                                line.split("BD Address:")[1].strip().split()[0]
                            )
                            logger.info(
                                f"Found Bluetooth MAC via hciconfig: {mac_address}"
                            )
                            self._bluetooth_mac_cached = mac_address
                            return mac_address
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

            # Final fallback: generate a consistent address
            logger.warning(
                "Could not read hardware Bluetooth MAC, generating consistent fallback"
            )
            namespace = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
            device_uuid = uuid.uuid5(namespace, self.name + "_bt")
            mac_bytes = device_uuid.bytes[:6]
            mac_bytes = bytes([mac_bytes[0] | 0x02 & 0xFE]) + mac_bytes[1:]
            mac_address = ":".join(f"{b:02X}" for b in mac_bytes)

            self._bluetooth_mac_cached = mac_address
            return mac_address

        except Exception as e:
            logger.error(f"Error reading Bluetooth MAC address: {e}")
            # Generate fallback address
            namespace = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
            device_uuid = uuid.uuid5(namespace, self.name + "_bt_fallback")
            mac_bytes = device_uuid.bytes[:6]
            mac_bytes = bytes([mac_bytes[0] | 0x02 & 0xFE]) + mac_bytes[1:]
            mac_address = ":".join(f"{b:02X}" for b in mac_bytes)

            self._bluetooth_mac_cached = mac_address
            return mac_address

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
            mac_address=self.mac_address,
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
