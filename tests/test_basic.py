"""Basic tests for ESPHome Bluetooth Proxy."""

from esphome_bluetooth_proxy import __version__


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_import():
    """Test that the package can be imported."""
    import esphome_bluetooth_proxy  # noqa: F401

    assert True
