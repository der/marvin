from queue import Queue
import sys
import os
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import asyncio

# Set up send connection to the rover listening on queue of commands to send
queue = Queue()

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

def handle_disconnect(_: BleakClient):
    print("Device disconnected, goodbye.")
    # cancelling all tasks effectively ends the program
    for task in asyncio.all_tasks():
        task.cancel()

async def ble_connect(task):
    print('Scanning for devices...')
    device = await BleakScanner.find_device_by_name('rover', 36000.0)
    if (device is None):
        print('Device not found')
        sys.exit(1)
        return  
    print(f'Connecting to {device.name}')

    async with BleakClient(device, disconnected_callback=handle_disconnect) as client:
        print('Connected to rover')
        rover = client.services.get_service(UART_SERVICE_UUID)
        rx = rover.get_characteristic(UART_RX_CHAR_UUID)

        print("Starting task")
        asyncio.create_task(task())

        while True:
            # Use a timeout with queue.get to avoid blocking indefinitely
            try:
                # Check if there's a command in the queue without blocking
                if not queue.empty():
                    command = queue.get_nowait()
                    if command == b'x':
                        print('Quit requested')
                        break
                    await client.write_gatt_char(rx, command, response=False)
                else:
                    # Give control back to the event loop to allow other tasks to run
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(0.1)

async def send(cmd):
    print(f"Sending {cmd.decode()}")
    queue.put(cmd)
    await asyncio.sleep(2)

async def dance():
    print("Dance called")
    await send(b'f')
    await send(b'sr')
    await send(b'b')
    await send(b'sl')
    await send(b'99f')
    await send(b'x')

async def main():
    await asyncio.gather(
        ble_connect(dance)
    )

try:
    asyncio.run(main())
except asyncio.CancelledError:
    print("Exiting")
    sys.exit()
