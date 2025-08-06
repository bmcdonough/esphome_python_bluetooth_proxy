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

Clone the repository and install dependencies:

```bash
git clone https://github.com/bmcdonough/esphome_python_bluetooth_proxy.git
cd esphome_python_bluetooth_proxy
pip install -e .
```

## Production Daemon

The project includes a production-ready daemon script that provides a comprehensive implementation of the ESPHome Bluetooth Proxy API. This daemon supports command-line arguments, proper logging, and listening on all network interfaces.

### Running the Daemon

You can run the daemon directly:

```bash
python3 esphome_bluetooth_proxy_daemon.py --log-level INFO
```

### Command Line Arguments

The daemon supports the following command-line arguments:

| Argument | Description | Default |
|----------|-------------|----------|
| `--host` | Hostname/IP to listen on | `0.0.0.0` (all interfaces) |
| `--port` | Port to listen on | `6053` |
| `--name` | Device name | `python-bluetooth-proxy` |
| `--friendly-name` | Friendly device name | `Python Bluetooth Proxy` |
| `--password` | API password (optional) | `None` (no password) |
| `--active-connections` | Enable active BLE connections | `True` |
| `--no-active-connections` | Disable active BLE connections | |
| `--max-connections` | Maximum concurrent BLE connections | `3` |
| `--advertisement-batch-size` | Number of advertisements to batch | `20` |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `--log-file` | Path to log file (optional) | `None` (console only) |
| `--log-max-size` | Maximum log file size in MB | `10` |
| `--log-backup-count` | Number of log backups to keep | `3` |

### Integration with Home Assistant

To add the Python Bluetooth Proxy to Home Assistant:

1. Start the daemon on your server
2. In Home Assistant, go to **Settings** > **Devices & Services**
3. Click **+ Add Integration**
4. Search for and select **ESPHome**
5. Enter the IP address of your server and port 6053
6. If you set a password, enter it when prompted
7. The device will be added as a Bluetooth proxy

## Systemd Service

For production use, you can set up the daemon to run as a systemd service:

1. Copy the provided service file to the systemd directory:

```bash
sudo cp esphome-bluetooth-proxy.service /etc/systemd/system/
```

2. Edit the service file to match your installation path:

```bash
sudo nano /etc/systemd/system/esphome-bluetooth-proxy.service
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable esphome-bluetooth-proxy
sudo systemctl start esphome-bluetooth-proxy
```

4. Check the service status:

```bash
sudo systemctl status esphome-bluetooth-proxy
```

5. View the logs:

```bash
sudo journalctl -u esphome-bluetooth-proxy -f
```

### Customizing the Service

The default service configuration runs the daemon as root (required for BLE access) and logs to `/var/log/esphome-bluetooth-proxy.log`. You can modify the service file to change these settings before installing.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development setup instructions.

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
