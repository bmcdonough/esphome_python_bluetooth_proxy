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
- Asynchronous operation for better performance
- Comprehensive logging and error handling
- Configurable via YAML files

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

## Quick Start

```python
from esphome_bluetooth_proxy import BluetoothProxy

# Initialize the proxy
proxy = BluetoothProxy()

# Start the proxy
await proxy.start()
```

## Configuration

Create a `config.yaml` file:

```yaml
esphome:
  host: "192.168.1.100"
  port: 6053
  password: "your_api_password"

bluetooth:
  scan_interval: 30
  devices:
    - name: "Temperature Sensor"
      mac: "AA:BB:CC:DD:EE:FF"
```

## Development Status

🚧 **This project is currently in early development** 🚧

- [x] Project structure and tooling setup
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
