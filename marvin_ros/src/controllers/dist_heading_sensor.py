# Support for monitoring heading and three proximity monitors over BLE
import sys
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import asyncio
import contextlib

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
        self.callbacks = []

    def add_callback(self, callback):
        """Add a callback function to be called when new data arrives.
        
        Args:
            callback: A callable that accepts (dist, heading, pitch) parameters
                     where dist is a list of 3 distance values, heading is an int,
                     and pitch is an int.
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback):
        """Remove a previously registered callback.
        
        Args:
            callback: The callback function to remove
            
        Returns:
            bool: True if callback was found and removed, False otherwise
        """
        try:
            self.callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def clear_callbacks(self):
        """Remove all registered callbacks."""
        self.callbacks.clear()

    async def run(self, lock):
        # Possible future reconnect loop
        await self.connect(lock)

    def uart_data_handler(self, sender, data):
        unpacked = list(data)
        self.dist = unpacked[0:3]
        self.heading = unpacked[3]
        self.pitch = unpacked[4]
        #print(f"Heading: {self.heading}, pitch: {self.pitch}, dist: {self.dist}")
        
        # Call all registered callbacks with the new data
        for callback in self.callbacks:
            try:
                callback(self.dist, self.heading, self.pitch)
            except Exception as e:
                print(f"Error calling callback {callback}: {e}")

    def handle_disconnect(self, _: BleakClient):
        print(f"Device {self.device} disconnected, retrying")
        self.client = None
        self.is_connected = False

    async def connect(self, lock):
        async with contextlib.AsyncExitStack() as stack:
            async with lock:
                print('Scanning for devices...')
                self.device = await BleakScanner.find_device_by_name(DEVICE_NAME, 36000.0)
                if (self.device is None):
                    print('Device not found')
                    return  

                print(f'Connecting to {self.device.name}')
                client = await stack.enter_async_context(BleakClient(self.device, disconnected_callback=self.handle_disconnect))
                print(f'Connected to {DEVICE_NAME}')
                self.is_connected = True
                self.client = client
                sensor = client.services.get_service(UART_SERVICE_UUID)
                self.rx = sensor.get_characteristic(UART_RX_CHAR_UUID)
                self.tx = sensor.get_characteristic(UART_TX_CHAR_UUID)
                await client.start_notify(self.tx.uuid, self.uart_data_handler)

            # Release lock
            try:
                while self.is_connected:
                        # Give control back to the event loop to allow other tasks to run
                        await asyncio.sleep(0.5)
            except Exception as e:
                print(e)

async def main():
    sensor = DistanceHeadingMonitor()
    lock = asyncio.Lock()
    
    # Example callback function
    def data_callback(dist, heading, pitch):
        print(f"Callback received - Heading: {heading}, Pitch: {pitch}, Distances: {dist}")
    
    # Add the callback
    sensor.add_callback(data_callback)

    tasks = [
        asyncio.create_task(sensor.run(lock))
    ]
    # Wait for everything to finish
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
