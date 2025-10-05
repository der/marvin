from machine import I2C, Pin
from time import sleep

i2c = I2C(0, sda=Pin(5), scl=Pin(6))
buf = bytearray(6)
address = 96

print(i2c.readfrom_mem(address, 0x18,2))


while True:
    i2c.readfrom_mem_into(address, 0, buf)
    version = buf[0]
    heading = buf[1]
    hires = (buf[2]<<8) + buf[3]
    pitch = buf[4]
    roll = buf[5]
    callibration = i2c.readfrom_mem(address,0x1e,1)
    temp = i2c.readfrom_mem(address,0x18,2)
    print(f"version: {version} callibration: {callibration[0]:x} temp: {temp} heading: {heading:x} = {hires} pitch: {pitch:x} roll: {roll:x}")
    sleep(0.5)
