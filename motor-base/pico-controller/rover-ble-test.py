import BLEUart
import asyncio

def receive_data(data):
    print('Received: ' + data.decode())

def main():
    uart = BLEUart.BleUart("rover", receive_data)
    print("Starting BLE UART service")
    asyncio.run(uart.run())

main()
