# ESPHome Python Bluetooth Proxy

A Python-based Bluetooth proxy for ESPHome devices, converting the existing C++ implementation to a more flexible and maintainable Python solution.

## Overview

This project aims to provide a Python alternative to the existing C++ ESPHome Bluetooth proxy, offering:

- **Better maintainability**: Python's readability and extensive ecosystem
- **Enhanced flexibility**: Easier customization and extension
- **Modern development practices**: Comprehensive testing, linting, and CI/CD
- **Cross-platform compatibility**: Runs on various platforms with Python support

## Features

- Bluetooth Low Energy (BLE) device discovery and communication
- Integration with ESPHome API
- Passive BLE scanning with advertisement forwarding
- Active BLE connections with GATT operations support
- Asynchronous operation for better performance
- Comprehensive logging and error handling
- Configurable via command-line arguments

## Requirements

### System Requirements

- Python 3.12 or higher
- Bluetooth adapter (built-in or USB)
- ESPHome device with API enabled

### System Dependencies (Ubuntu/Debian)

Install the required system packages:

```bash
sudo apt update
sudo apt install bluez bluez-utils
```

**Package descriptions:**
- `bluez`: Core Bluetooth protocol stack for Linux
- `bluez-utils`: Bluetooth utilities including `hciconfig` for hardware detection

**Verify installation:**
```bash
# Check if Bluetooth service is running
sudo systemctl status bluetooth

# Verify Bluetooth adapter is detected
hciconfig -a

# Check for Bluetooth hardware
lsusb | grep -i bluetooth
```

## Installation

### For Users

```bash
pip install esphome-python-bluetooth-proxy
```

### For Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development setup instructions.

## Production Daemon

The project includes a production-ready daemon script that can be used for real-world testing and deployment:

### Running the Daemon

```bash
# Basic usage (listens on all interfaces, port 6053)
python3 esphome_bluetooth_proxy_daemon.py

# With custom host and port
python3 esphome_bluetooth_proxy_daemon.py --host 192.168.1.10 --port 6054

# With API password
python3 esphome_bluetooth_proxy_daemon.py --password your_secret_password

# With logging to file
python3 esphome_bluetooth_proxy_daemon.py --log-file /var/log/bluetooth_proxy.log

# Passive scanning only (no active connections)
python3 esphome_bluetooth_proxy_daemon.py --no-active-connections
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|--------|
| `--host` | Host address to bind to | `0.0.0.0` (all interfaces) |
| `--port` | Port to listen on | `6053` |
| `--name` | Device name used for ESPHome API | `python-bluetooth-proxy` |
| `--friendly-name` | User-friendly device name | `Python Bluetooth Proxy` |
| `--password` | API password | `None` (no password) |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `--log-file` | Log file path | `None` (logs to stdout) |
| `--no-active-connections` | Disable active BLE connections (passive scanning only) | `False` |
| `--max-connections` | Maximum concurrent BLE connections | `3` |
| `--batch-size` | Advertisement batch size | `16` |

### Home Assistant Integration

1. Run the daemon on a machine with Bluetooth capabilities
2. In Home Assistant, add a new ESPHome device:
   - Go to Settings → Devices & Services → Add Integration
   - Select ESPHome
   - Enter the IP address of the machine running the daemon
   - Enter the port (default: 6053)
   - Enter the API password if configured

## Quick Start (Library Usage)

```python
from esphome_bluetooth_proxy import BluetoothProxy

# Initialize the proxy
proxy = BluetoothProxy()

# Start the proxy
await proxy.start()
```

## Development Status

🚧 **This project is in active development** 🚧

- [x] Project structure and tooling setup
- [x] Phase 1: ESPHome API server foundation
- [x] Phase 2: Complete Home Assistant integration
- [x] Phase 3: Passive BLE scanning
- [x] Phase 4: Active BLE connections
- [x] Phase 5: GATT operations
- [ ] Phase 6: Advanced features (pairing, cache management)
- [ ] Phase 7: Optimization and production readiness
- [ ] Core Bluetooth functionality
- [ ] ESPHome API integration
- [ ] Configuration management
- [ ] Testing suite
- [ ] Documentation

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up the development environment
- Code quality standards (isort, black, flake8)
- Testing requirements
- Pull request process

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## References

- [ESPHome Source Code](https://github.com/esphome/esphome/) - The original ESPHome project
- [ESPHome Bluetooth Proxy Implementation](https://github.com/esphome/esphome/tree/dev/esphome/components/bluetooth_proxy) - Original C++ Bluetooth proxy component
- [ESPHome Protocol Analysis](ESPHOME_PROTOCOL_ANALYSIS.md) - Detailed analysis of the ESPHome-Home Assistant connection protocol

## Acknowledgments

- Original ESPHome Bluetooth proxy implementation
- ESPHome community for inspiration and support
