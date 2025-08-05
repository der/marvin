import bluetooth
from micropython import const
import asyncio
import aioble
from machine import Pin

_UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
_UART_TX_UUID = bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')
_UART_RX_UUID = bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)

# How frequently to send advertising beacons.
_ADV_INTERVAL_MS = 250_000

class BleUart:
    """
        A simple UART-over-BLE service.

        Doesn't provide buffering or flow control, limited to 20 byte read/write packets.
    """
    def __init__(self, name="ble-uart", callback=None):
        self._name = name
        self._callback = callback
        self.connected = False
        self._service = aioble.Service(_UART_UUID)
        self._write = aioble.Characteristic(self._service, _UART_RX_UUID, read=True, notify=True)
        self._read = aioble.Characteristic(self._service, _UART_TX_UUID, write=True, write_no_response=True, capture=True)
        aioble.register_services(self._service)
    
    async def send(self, data):
        self._write.write(data, send_update=True)

    async def watch_for_data(self):
        while self.connected:
            try:
                connection, data = await self._read.written()
                if data and self._callback:
                    self._callback(data)
            except asyncio.TimeoutError:
                print('no data yet ...')
            
    async def run(self):
        while True:
            async with await aioble.advertise(
                _ADV_INTERVAL_MS,
                name=self._name,
                services=[_UART_UUID],
                appearance=_ADV_APPEARANCE_GENERIC_COMPUTER
            ) as connection:
                # print("Connection from", connection.device)               
                led = Pin("LED", Pin.OUT)
                led.on()
                self._connection = connection
                self.connected = True
                asyncio.create_task(self.watch_for_data())
                await connection.disconnected(timeout_ms=None)
                led.off()
