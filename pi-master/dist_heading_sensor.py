# Support for monitoring heading and three proximity monitors over BLE
import sys
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import asyncio

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

DEVICE_NAME = "dist-sensor"

class DistanceHeadingMonitor:
    def __init__(self):
        self.is_connected = False
        self.dist= [255, 255, 255]
        self.heading = 0
        self.pitch = 0

    async def run(self):
        print('Scanning for devices...')
        self.device = await BleakScanner.find_device_by_name(DEVICE_NAME, 36000.0)
        if (self.device is None):
            print('Device not found')
            sys.exit(1)
            return
        await self.connect()

    def uart_data_handler(self, sender, data):
        print(f'Received {list(data)}')

    def handle_disconnect(self, _: BleakClient):
        print(f"Device {self.device} disconnected, retrying")
        self.client = None
        self.is_connected = False

    async def connect(self):
        while True:
            print(f'Connecting to {self.device.name}')
            async with BleakClient(self.device, disconnected_callback=self.handle_disconnect) as client:
                try:
                    # client.connect()
                    print(f'Connected to {DEVICE_NAME}')
                    self.is_connected = True
                    self.client = client
                    sensor = client.services.get_service(UART_SERVICE_UUID)
                    self.rx = sensor.get_characteristic(UART_RX_CHAR_UUID)
                    self.tx = sensor.get_characteristic(UART_TX_CHAR_UUID)
                    await client.start_notify(self.tx.uuid, self.uart_data_handler)
                    while self.is_connected:
                            # Give control back to the event loop to allow other tasks to run
                            await asyncio.sleep(0.01)
                except Exception as e:
                    print(e)

async def main():
    sensor = DistanceHeadingMonitor()

    tasks = [
        asyncio.create_task(sensor.run())
    ]
    # Wait for everything to finish
    await asyncio.gather(*tasks)

asyncio.run(main())
