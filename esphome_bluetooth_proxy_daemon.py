#!/usr/bin/env python3
"""
ESPHome Python Bluetooth Proxy Daemon

A production-ready daemon for the ESPHome Python Bluetooth Proxy with
command-line arguments, configurable logging, and network listening capabilities.

This daemon implements a complete ESPHome API server with Bluetooth proxy functionality:
- Passive BLE scanning and advertisement forwarding
- Active BLE connections with GATT operations support
- Comprehensive error handling and recovery mechanisms
- Full Home Assistant integration
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from esphome_bluetooth_proxy.api_server import ESPHomeAPIServer
from esphome_bluetooth_proxy.bluetooth_proxy import BluetoothProxy


class ESPHomeBluetoothProxyDaemon:
    """Production daemon for ESPHome Python Bluetooth Proxy."""

    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        friendly_name: str,
        password: str = None,
        log_level: str = "INFO",
        log_file: str = None,
        active_connections: bool = True,
        max_connections: int = 3,
        batch_size: int = 16,
    ):
        """Initialize the daemon with configuration parameters.

        Args:
            host: Host address to bind to (0.0.0.0 for all interfaces)
            port: Port to listen on
            name: Device name (used for ESPHome API)
            friendly_name: User-friendly device name
            password: Optional API password
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Log file path (if None, logs to stdout)
            active_connections: Enable active BLE connections
            max_connections: Maximum concurrent BLE connections
            batch_size: Advertisement batch size
        """
        self.host = host
        self.port = port
        self.name = name
        self.friendly_name = friendly_name
        self.password = password
        self.log_level = log_level
        self.log_file = log_file
        self.active_connections = active_connections
        self.max_connections = max_connections
        self.batch_size = batch_size

        self.server = None
        self.running = False
        self.logger = None

    def setup_logging(self):
        """Configure logging based on parameters."""
        # Convert string log level to numeric value
        numeric_level = getattr(logging, self.log_level.upper(), None)
        if not isinstance(numeric_level, int):
            print(f"Invalid log level: {self.log_level}")
            numeric_level = logging.INFO

        # Create logger
        self.logger = logging.getLogger("esphome_bluetooth_proxy")
        self.logger.setLevel(numeric_level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create handlers
        handlers = []

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

        # Add file handler if specified
        if self.log_file:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Create rotating file handler (10MB per file, max 5 files)
            file_handler = RotatingFileHandler(
                self.log_file, maxBytes=10 * 1024 * 1024, backupCount=5
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)

        # Add handlers to logger
        for handler in handlers:
            self.logger.addHandler(handler)

        # Log startup information
        self.logger.info("ESPHome Python Bluetooth Proxy Daemon starting")
        self.logger.info(f"Host: {self.host}, Port: {self.port}")
        self.logger.info(
            f"Device name: {self.name}, Friendly name: {self.friendly_name}"
        )
        self.logger.info(
            f"Active connections: {self.active_connections}, Max connections: {self.max_connections}"
        )
        self.logger.info(f"Log level: {self.log_level}")
        if self.log_file:
            self.logger.info(f"Logging to file: {self.log_file}")

    async def start(self):
        """Start the ESPHome API server with Bluetooth proxy."""
        try:
            # Create server
            self.server = ESPHomeAPIServer(
                host=self.host,
                port=self.port,
                name=self.name,
                friendly_name=self.friendly_name,
                password=self.password,
                active_connections=self.active_connections,
            )

            # Configure Bluetooth proxy if needed
            if hasattr(self.server, "bluetooth_proxy") and self.server.bluetooth_proxy:
                self.server.bluetooth_proxy.set_max_connections(self.max_connections)
                self.server.bluetooth_proxy.set_batch_size(self.batch_size)

            # Start server
            await self.server.start()
            self.running = True

            self.logger.info(
                f"ESPHome API server started successfully on {self.host}:{self.port}"
            )
            self.logger.info(
                f"Bluetooth proxy initialized with {self.max_connections} max connections"
            )

            # Verify GATT handler integration
            if self.server.bluetooth_proxy and hasattr(
                self.server.bluetooth_proxy, "gatt_handler"
            ):
                self.logger.info("GATT operations handler properly integrated")

                # Get GATT handler stats if available
                if hasattr(self.server.bluetooth_proxy.gatt_handler, "get_stats"):
                    stats = self.server.bluetooth_proxy.gatt_handler.get_stats()
                    self.logger.info(f"GATT handler stats: {stats}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start server: {e}", exc_info=True)
            return False

    async def run_forever(self):
        """Run the daemon indefinitely until stopped."""
        if not await self.start():
            return False

        try:
            # Run until stopped
            self.logger.info(
                "ESPHome Python Bluetooth Proxy is running. Press Ctrl+C to stop."
            )

            # Keep the daemon running
            while self.running:
                await asyncio.sleep(1)

            return True

        except Exception as e:
            self.logger.error(f"Error in daemon: {e}", exc_info=True)
            return False

    async def shutdown(self):
        """Gracefully shutdown the daemon."""
        if self.server and self.running:
            self.logger.info("Shutting down daemon...")
            self.running = False

            # Shutdown server
            if hasattr(self.server, "stop"):
                await self.server.stop()

            self.logger.info("Daemon shutdown complete")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ESPHome Python Bluetooth Proxy Daemon"
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0 for all interfaces)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=6053,
        help="Port to listen on (default: 6053)",
    )

    parser.add_argument(
        "--name",
        default="python-bluetooth-proxy",
        help="Device name used for ESPHome API (default: python-bluetooth-proxy)",
    )

    parser.add_argument(
        "--friendly-name",
        default="Python Bluetooth Proxy",
        help="User-friendly device name (default: Python Bluetooth Proxy)",
    )

    parser.add_argument(
        "--password",
        default=None,
        help="API password (default: None)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        default=None,
        help="Log file path (default: None, logs to stdout)",
    )

    parser.add_argument(
        "--no-active-connections",
        action="store_true",
        help="Disable active BLE connections (passive scanning only)",
    )

    parser.add_argument(
        "--max-connections",
        type=int,
        default=3,
        help="Maximum concurrent BLE connections (default: 3)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Advertisement batch size (default: 16)",
    )

    return parser.parse_args()


async def main():
    """Main daemon execution."""
    # Parse command line arguments
    args = parse_arguments()

    # Create daemon instance
    daemon = ESPHomeBluetoothProxyDaemon(
        host=args.host,
        port=args.port,
        name=args.name,
        friendly_name=args.friendly_name,
        password=args.password,
        log_level=args.log_level,
        log_file=args.log_file,
        active_connections=not args.no_active_connections,
        max_connections=args.max_connections,
        batch_size=args.batch_size,
    )

    # Setup logging
    daemon.setup_logging()

    # Setup signal handlers
    def signal_handler(signum, frame):
        daemon.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(daemon.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run daemon
        return await daemon.run_forever()
    except KeyboardInterrupt:
        daemon.logger.info("Daemon interrupted by user")
    except Exception as e:
        daemon.logger.error(f"Daemon failed with exception: {e}", exc_info=True)
        return False
    finally:
        await daemon.shutdown()

    return True


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
