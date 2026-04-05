from machine import I2C, Pin
import ustruct

i2c = I2C(0, sda=Pin(5), scl=Pin(6), freq=40000)

i2c.writeto_mem(0x64, 0x0,  b'\x01')
i2c.writeto_mem(0x64, 0x1,  b'\x02')
i2c.writeto_mem(0x64, 0x80, ustruct.pack("<I",30000))
print(ustruct.unpack("<I",i2c.readfrom_mem(0x64, 0x90, 4)))
