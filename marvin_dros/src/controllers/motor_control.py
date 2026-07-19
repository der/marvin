# Support for controlling the motor base over BLE
import sys
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import asyncio
from collections import deque
import contextlib

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class MotorController:
    """
        Drive motor base over BLE.
        Send command strings in form "[s]op[d]" where s, if present is speed between 0 and 100,
        d, if present, is a distance to travel in (approx) cm
        The commands are:
            - x           - exit controller and close bluetooth
            - f b sr sl   - forward/back/slide right/slide left
            - dr dl Dr Dl - diagonal right/left forward/back
            - tr tl Tr Tl - turn right/left turn back right/left
            - rr rl       - rotate right or left
            - s           - stop
            - ?           - status request, returns 1 if moving, 0 if stopped
    """
    def __init__(self):
        # Short length queue of commands to send
        self.queue = deque([], 4)
        self.is_connected = False
        
    async def run(self, lock):
        # possible future auto-reconnect loop here
        await self.connect(lock)

    def handle_disconnect(self, _: BleakClient):
        print(f"Device {self.device} disconnected")
        self.client = None
        self.is_connected = False

    async def connect(self, lock):
        async with contextlib.AsyncExitStack() as stack:
            async with lock:
                print('Scanning for devices...')
                self.device = await BleakScanner.find_device_by_name('rover', 36000.0)
                if (self.device is None):
                    print('Device not found')
                    return  

                print(f'Connecting to {self.device.name}')
                client = await stack.enter_async_context(BleakClient(self.device, disconnected_callback=self.handle_disconnect))
                print('Connected to rover')
                self.is_connected = True
                self.client = client
                rover = client.services.get_service(UART_SERVICE_UUID)
                self.rx = rover.get_characteristic(UART_RX_CHAR_UUID)
                self.tx = rover.get_characteristic(UART_TX_CHAR_UUID)
            try:
                while self.is_connected:
                    # Check if there's a command in the queue without blocking
                    try:
                        command = self.queue.pop()
                        if command == 'x':
                            print('Quit requested')
                            self.client = None
                            self.is_connected = False
                            await client.disconnect()
                            return
                        print(f"Sending {command}")
                        await client.write_gatt_char(self.rx, command.encode(), response=False)
                    except IndexError:
                        # Give control back to the event loop to allow other tasks to run
                        await asyncio.sleep(0.01)
            except Exception as e:
                print(e)

    async def is_moving(self):
        if self.is_connected and self.client is not None:
            await self.client.write_gatt_char(self.rx, b'?', response=True)
            response = await self.client.read_gatt_char(self.tx)
            return bool(response is not None and response.decode().strip() == '1')

    def send(self, speed: int, dir: str, dist: int | None = None):
        if dist is not None:
            self.queue.append(f"{speed}{dir}{dist}")
        else:
            self.queue.append(f"{speed}{dir}")

    def stop(self):
        self.queue.append("0s")

    def shutdown(self):
        self.queue.append("s")
        self.queue.append("x")
