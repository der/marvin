# Support for controlling the motor base over BLE
import sys
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import asyncio
from collections import deque

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class MotorController:
    """
        Drive motor base over BLE.
        Send command strings in form "[n]c" where n, if present is speed between 0 and 100.
        The commands are:
            - x           - exit controller and close bluetooth
            - f b sr sl   - forward/back/slide right/slide left
            - dr dl Dr Dl - diagonal right/left forward/back
            - tr tl Tr Tl - turn right/left turn back right/left
            - rr rl       - rotate right or left
            - s           - stop
    """
    def __init__(self):
        # Short length queue of commands to send
        self.queue = deque([], 2)
        self.is_connected = False
        
    async def run(self):
        print('Scanning for devices...')
        device = await BleakScanner.find_device_by_name('rover', 36000.0)
        if (device is None):
            print('Device not found')
            sys.exit(1)
            return  
        print(f'Connecting to {device.name}')

        async with BleakClient(device, disconnected_callback=self.handle_disconnect) as client:
            print('Connected to rover')
            self.is_connected = True
            rover = client.services.get_service(UART_SERVICE_UUID)
            rx = rover.get_characteristic(UART_RX_CHAR_UUID)

            while True:
                try:
                    # Check if there's a command in the queue without blocking
                    if not self.queue.empty():
                        command = self.queue.get_nowait()
                        if command == 'x':
                            print('Quit requested')
                            self.is_connected = False
                            break
                        print(f"Sending {command}")
                        await client.write_gatt_char(rx, command.encode(), response=False)
                    else:
                        # Give control back to the event loop to allow other tasks to run
                        await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"Error: {e}")
                    await asyncio.sleep(0.01)

    def handle_disconnect(self, _: BleakClient):
        print("Device disconnected, goodbye.")
        self.is_connected = False
        self.queue.append("x")
