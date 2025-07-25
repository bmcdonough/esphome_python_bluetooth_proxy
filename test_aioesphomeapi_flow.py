#!/usr/bin/env python3
"""
Test script to simulate aioesphomeapi client flow: Hello → DeviceInfo (skip Connect)

This tests the dual protocol flow support we added to handle both:
1. Full Home Assistant client: Hello → Connect → DeviceInfo → ListEntities
2. aioesphomeapi client: Hello → DeviceInfo → ListEntities (skip Connect)
"""

import asyncio
import socket
import struct
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.protocol import HelloRequest, MessageEncoder, MessageType


async def test_aioesphomeapi_flow():
    """Test the aioesphomeapi client flow that skips Connect."""
    print("Testing aioesphomeapi flow: Hello → DeviceInfo (skip Connect)")

    # Connect to the server
    reader, writer = await asyncio.open_connection("localhost", 6053)

    try:
        # Send Hello request (simulating aioesphomeapi client)
        encoder = MessageEncoder()
        hello_request = HelloRequest(
            client_info="aioesphomeapi", api_version_major=1, api_version_minor=10
        )

        hello_data = encoder.encode_hello_request(hello_request)
        message = (
            struct.pack("<BI", 0, len(hello_data))
            + struct.pack("<I", MessageType.HELLO_REQUEST)
            + hello_data
        )

        writer.write(message)
        await writer.drain()
        print("✓ Sent Hello request as 'aioesphomeapi'")

        # Read Hello response
        response_data = await reader.read(1024)
        print(f"✓ Received Hello response: {len(response_data)} bytes")

        # Send DeviceInfo request (skip Connect - this is the key test)
        device_info_message = struct.pack("<BI", 0, 0) + struct.pack(
            "<I", MessageType.DEVICE_INFO_REQUEST
        )

        writer.write(device_info_message)
        await writer.drain()
        print("✓ Sent DeviceInfo request (skipping Connect)")

        # Read DeviceInfo response
        response_data = await reader.read(1024)
        if len(response_data) > 0:
            print(
                f"✓ SUCCESS: Received DeviceInfo response: {len(response_data)} bytes"
            )
            print("✓ aioesphomeapi flow is working correctly!")
        else:
            print("✗ FAILED: No DeviceInfo response received")

    except Exception as e:
        print(f"✗ ERROR: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(test_aioesphomeapi_flow())
