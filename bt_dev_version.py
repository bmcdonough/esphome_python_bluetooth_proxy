#!/usr/bin/env python
import platform
import subprocess


def get_bluetooth_protocol_version():
    """
    Attempts to identify the Bluetooth protocol version of the local USB
    Bluetooth device. This script primarily works by parsing system command
    output, especially on Linux.
    """
    system = platform.system()

    # Define the mapping from LMP Version (hex) to Bluetooth Core Specification Version
    # This table is based on the official Bluetooth SIG assigned numbers.
    lmp_to_bluetooth_version = {
        "0x0": "1.0b",
        "0x1": "1.1",
        "0x2": "1.2",
        "0x3": "2.0 + EDR",
        "0x4": "2.1 + EDR",
        "0x5": "3.0 + HS",
        "0x6": "4.0",
        "0x7": "4.1",
        "0x8": "4.2",
        "0x9": "5.0",
        "0xa": "5.1",
        "0xb": "5.2",
        "0xc": "5.3",
        "0xd": "5.4",
        # Add more mappings as new Bluetooth versions are released
    }

    if system == "Linux":
        print("Attempting to retrieve Bluetooth adapter information on Linux...")
        try:
            # Run hciconfig -a to get detailed information about Bluetooth adapters
            # This command might require root privileges (sudo)
            process = subprocess.run(
                ["hciconfig", "-a"], capture_output=True, text=True, check=True
            )
            output = process.stdout

            # Look for "LMP Version" in the output
            lmp_version_line = next(
                (line for line in output.splitlines() if "LMP Version" in line), None
            )

            if lmp_version_line:
                # Find the start of the hex value (e.g., "0x")
                hex_start = lmp_version_line.find("0x")
                if hex_start != -1:
                    # Find the end of the hex value (the character just before
                    # the closing parenthesis)
                    hex_end = lmp_version_line.find(")", hex_start)
                    if hex_end != -1:
                        # Extract the hex value, convert to lowercase for
                        # consistent dictionary lookup
                        lmp_hex_version = (
                            lmp_version_line[hex_start:hex_end].strip().lower()
                        )

                        bluetooth_version = lmp_to_bluetooth_version.get(
                            lmp_hex_version, "Unknown"
                        )

                        print(f"\nFound LMP Version: {lmp_hex_version}")
                        print(
                            "This translates to Bluetooth Core Specification:"
                            f" {bluetooth_version}"
                        )
                        print(
                            "This is based on the Link Manager Protocol (LMP) version"
                            " reported by your adapter."
                        )
                    else:
                        print(
                            "\nCould not find closing parenthesis for LMP Version"
                            " (hex)."
                        )
                        print("Raw LMP Version line:", lmp_version_line)
                else:
                    print("\nCould not find '0x' in LMP Version line.")
                    print("Raw LMP Version line:", lmp_version_line)
            else:
                print("\n'LMP Version' not found in hciconfig output.")
                print(
                    "This might mean your Bluetooth adapter is not active, or"
                    " hciconfig output format is different."
                )
                print("Ensure your Bluetooth adapter is plugged in and enabled.")
                print(
                    "You might need to run this script with `sudo python"
                    " your_script_name.py`."
                )

        except FileNotFoundError:
            print("\nError: `hciconfig` command not found.")
            print("Please ensure `bluez` utilities are installed on your Linux system.")
            print(
                "You can usually install it with: `sudo apt-get install bluez`"
                " (Debian/Ubuntu) or `sudo yum install bluez` (Fedora/RHEL)."
            )
        except subprocess.CalledProcessError as e:
            print(f"\nError running `hciconfig`: {e}")
            print("This often means you need elevated privileges.")
            print("Try running the script with `sudo python your_script_name.py`.")
            print("Stderr:", e.stderr)
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

    elif system == "Windows":
        print(
            "Identifying Bluetooth protocol version on Windows is more complex"
            " programmatically."
        )
        print("You can usually find this information in Device Manager:")
        print("1. Open Device Manager (search for it in the Start Menu).")
        print("2. Expand 'Bluetooth' or 'Bluetooth Radios'.")
        print(
            "3. Right-click on your Bluetooth adapter (e.g., 'Generic Bluetooth"
            " Adapter') and select 'Properties'."
        )
        print(
            "4. Go to the 'Advanced' tab. The 'Firmware Version' or 'LMP' (Link"
            " Manager Protocol) entry often indicates the Bluetooth version."
        )
        print("\nHere's the LMP to Bluetooth version mapping:")
        for lmp_hex, bt_version in lmp_to_bluetooth_version.items():
            print(f"   LMP Version {lmp_hex} = Bluetooth {bt_version}")

    elif system == "Darwin":  # macOS
        print(
            "Identifying Bluetooth protocol version on macOS is more complex"
            " programmatically."
        )
        print("You can usually find this information in 'System Information':")
        print(
            "1. Hold down the Option (Alt) key and click the Apple menu () in the"
            " top-left corner."
        )
        print("2. Select 'System Information'.")
        print("3. In the left sidebar, under 'Hardware', select 'Bluetooth'.")
        print(
            "4. Look for 'LMP Version' or 'Bluetooth Low Energy Supported'. The LMP"
            " Version will indicate the core specification version."
        )
        print("\nHere's the LMP to Bluetooth version mapping:")
        for lmp_hex, bt_version in lmp_to_bluetooth_version.items():
            print(f"   LMP Version {lmp_hex} = Bluetooth {bt_version}")

    else:
        print(f"Unsupported operating system: {system}")
        print(
            "Please consult your operating system's documentation or system"
            " information tools to find your Bluetooth adapter's protocol version."
        )


if __name__ == "__main__":
    get_bluetooth_protocol_version()
