# A MicroPython driver for the Unit Joystick2
# https://docs.m5stack.com/en/unit/Unit-JoyStick2

from machine import I2C

try:
    from typing import List
except ImportError:
    pass  # Fails in MicroPython, but this is just for type checking anyway


class Joystick2Unit:
    i2c: I2C
    addr: int

    def __init__(self, i2c, addr=0x63):
        self.i2c = i2c
        self.addr = addr
        assert self.check_address(), (
            "Unit Joystick2 not found at I2C address 0x%02x" % addr
        )

    def check_address(self) -> bool:
        """Read address register, return True if the address is correct"""
        result = self.i2c.readfrom_mem(self.addr, 0xFF, 1)
        return result == bytes([self.addr])

    def _read_2_byte_int(self, reg) -> int:
        """Read a 2-byte signed integer from the specified register"""
        result = self.i2c.readfrom_mem(self.addr, reg, 2)
        return int.from_bytes(result, "little")

    def get_x_raw(self) -> int:
        """Return the x-axis position as a an integer from 0 - 65535"""
        return self._read_2_byte_int(0x00)

    def get_x(self) -> float:
        """Return the x-axis position as a float from 0.0 - 1.0"""
        return self.get_x_raw() / 65535.0

    def get_y_raw(self) -> int:
        """Return the y-axis position as an integer from 0 - 65535"""
        return self._read_2_byte_int(0x02)

    def get_y(self) -> float:
        """Return the y-axis position as a float from 0.0 - 1.0"""
        return self.get_y_raw() / 65535.0

    def is_pressed(self) -> bool:
        """Return True if the button is pressed"""
        return self.i2c.readfrom_mem(self.addr, 0x20, 1) != b"\x01"

    def get_led(self) -> List[int]:
        """Get the LED state.

        Returns a list of three integers, each from 0-255, representing the red, green,
        and blue LED values."""
        data = self.i2c.readfrom_mem(self.addr, 0x30, 3)
        return list(data)[::-1]

    def set_led(self, red: int, green: int, blue: int):
        """Set the LED state.

        red, green, and blue should be integers from 0-255."""
        if any(not 0 <= c <= 255 for c in (red, green, blue)):
            raise ValueError("LED color values must be between 0 and 255")

        self.i2c.writeto_mem(self.addr, 0x30, bytes([blue, green, red]))

    def get_bootloader_version(self) -> int:
        """Return the bootloader version as an integer"""
        return self.i2c.readfrom_mem(self.addr, 0xFC, 1)[0]

    def get_firmware_version(self) -> int:
        """Return the firmware version as an integer"""
        return self.i2c.readfrom_mem(self.addr, 0xFE, 1)[0]
