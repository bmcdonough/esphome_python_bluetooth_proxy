"""BLE Scanner Module.

This module manages BLE advertisement scanning using bleak,
corresponding to the ESP32 BLE tracker functionality in ESPHome.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

logger = logging.getLogger(__name__)


@dataclass
class BLEAdvertisement:
    """Raw BLE advertisement data matching ESPHome format."""

    address: int  # 48-bit MAC as uint64
    rssi: int
    address_type: int  # Public/Random (0=Public, 1=Random)
    data: bytes  # Raw advertisement data (max 62 bytes)
    data_len: int


class BLEScanner:
    """Manages BLE advertisement scanning using bleak.

    This class corresponds to the ESP32 BLE tracker functionality
    in the ESPHome C++ implementation.
    """

    def __init__(self, callback: Callable[[BLEAdvertisement], None]):
        """Initialize BLE scanner.

        Args:
            callback: Function to call when advertisement is received
        """
        self.callback = callback
        self.scanner: Optional[BleakScanner] = None
        self.scanning = False
        self.active_scan = False

    async def start_scanning(self, active: bool = False) -> None:
        """Start BLE scanning.

        Args:
            active: Whether to use active scanning (scan requests)
        """
        if self.scanning:
            logger.warning("Scanner is already running")
            return

        self.active_scan = active
        logger.info(f"Starting BLE scanning (active={active})")

        try:
            self.scanner = BleakScanner(
                detection_callback=self._on_advertisement,
                scanning_mode="active" if active else "passive",
            )

            await self.scanner.start()
            self.scanning = True
            logger.info("BLE scanning started successfully")

        except Exception as e:
            logger.error(f"Failed to start BLE scanning: {e}")
            raise

    async def stop_scanning(self) -> None:
        """Stop BLE scanning."""
        if not self.scanning:
            return

        logger.info("Stopping BLE scanning")

        try:
            if self.scanner:
                await self.scanner.stop()
            self.scanning = False
            logger.info("BLE scanning stopped")

        except Exception as e:
            logger.error(f"Error stopping BLE scanning: {e}")

    def set_scan_mode(self, active: bool) -> None:
        """Set scanning mode (active/passive).

        Args:
            active: Whether to use active scanning
        """
        if self.active_scan != active:
            logger.info(f"Changing scan mode to {'active' if active else 'passive'}")
            self.active_scan = active

            # Restart scanning with new mode if currently scanning
            if self.scanning:
                asyncio.create_task(self._restart_scanning())

    async def _restart_scanning(self) -> None:
        """Restart scanning with current mode."""
        await self.stop_scanning()
        await self.start_scanning(self.active_scan)

    def _on_advertisement(
        self, device: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Handle received BLE advertisement.

        Args:
            device: BLE device information
            advertisement_data: Advertisement data
        """
        try:
            # Convert MAC address string to uint64
            mac_parts = device.address.split(":")
            address = 0
            for part in mac_parts:
                address = (address << 8) + int(part, 16)

            # Determine address type (simplified - bleak doesn't always provide this)
            address_type = (
                1
                if device.address.startswith(("4", "5", "6", "7", "C", "D", "E", "F"))
                else 0
            )

            # Combine advertisement and scan response data
            adv_data = bytearray()

            # Add manufacturer data
            if advertisement_data.manufacturer_data:
                for company_id, data in advertisement_data.manufacturer_data.items():
                    # Add manufacturer data TLV
                    adv_data.extend([0xFF])  # Manufacturer data type
                    adv_data.extend(company_id.to_bytes(2, "little"))
                    adv_data.extend(data)

            # Add service data
            if advertisement_data.service_data:
                for service_uuid, data in advertisement_data.service_data.items():
                    adv_data.extend([0x16])  # Service data type
                    # Add UUID (simplified - assumes 16-bit UUID)
                    if len(service_uuid) == 36:  # Full UUID string
                        uuid_bytes = bytes.fromhex(service_uuid.replace("-", ""))[:2]
                    else:
                        uuid_bytes = bytes.fromhex(service_uuid)[:2]
                    adv_data.extend(uuid_bytes)
                    adv_data.extend(data)

            # Add local name if present
            if advertisement_data.local_name:
                name_bytes = advertisement_data.local_name.encode("utf-8")
                adv_data.extend([0x09, len(name_bytes)])  # Complete local name
                adv_data.extend(name_bytes)

            # Ensure data doesn't exceed 62 bytes (31 adv + 31 scan response)
            if len(adv_data) > 62:
                adv_data = adv_data[:62]

            # Create advertisement object
            advertisement = BLEAdvertisement(
                address=address,
                rssi=advertisement_data.rssi or -127,
                address_type=address_type,
                data=bytes(adv_data),
                data_len=len(adv_data),
            )

            # Call the callback
            self.callback(advertisement)

        except Exception as e:
            logger.error(f"Error processing advertisement from {device.address}: {e}")

    def is_scanning(self) -> bool:
        """Check if scanner is currently active."""
        return self.scanning

    def get_scan_mode(self) -> str:
        """Get current scan mode."""
        return "active" if self.active_scan else "passive"
