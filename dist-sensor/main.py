import uasyncio as asyncio
import BLEUart
from opt3101 import OPT3101, BRIGHTNESS_ADAPTIVE
from machine import I2C, Pin

i2c = I2C(0, sda=Pin(5), scl=Pin(6))
compass = 96

lidar = OPT3101( i2c )
lidar.set_frame_timing(128)  # will take about 33ms per channel at timing
lidar.set_brightness( BRIGHTNESS_ADAPTIVE )

async def get_distance(channel:int):
    """Distance in cm packed to a byte, so max is 256"""
    lidar.set_channel(channel)
    lidar.start_sample()
    while True:
        if lidar.is_sample_done():
            lidar.read_output_regs() # Read data from board
            dist = min(int(lidar.distance / 10), 255)
            return dist & 0xFF
        await asyncio.sleep(0.01)

async def get_sensor_readings():
    results = bytearray(5)
    for i in range(0,3):
        results[i] = await get_distance(i)
    buf = bytearray(6)
    i2c.readfrom_mem_into(compass, 0, buf)
    results[3] = buf[1]  # heading
    results[4] = buf[4]  # pitch
    return bytes(results)

async def monitor_sensors(uart: BLEUart):
    while True:
        result_bytes = await get_sensor_readings()
        print(f"Send sensor update: {list(result_bytes)}")
        await uart.send(result_bytes)

def command(cmdin):
    cmd = cmdin.decode()
    print("Received command ", cmd)
    if (cmd == "c"):
        print("TODO implement calibration")
    return None
    
async def main():
    uart = BLEUart.BleUart("dist-sensor", command)
    print("Starting BLE UART service")

    tasks = [
        asyncio.create_task(uart.run()),
        asyncio.create_task(monitor_sensors(uart))
    ]
    # Wait for everything to finish
    await asyncio.gather(*tasks)

asyncio.run(main())
