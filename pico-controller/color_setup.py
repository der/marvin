# ws_pico_res_touch.py

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2022 Peter Hinch
# With help from Tim Wermer.

import gc
from machine import Pin, SPI
from drivers.st7789.st7789_16bit import *
from drivers.st7789.sdcard import SDCard
import time
SSD = ST7789

pdc = Pin(8, Pin.OUT, value=0)
pcs = Pin(9, Pin.OUT, value=1)
prst = Pin(15, Pin.OUT, value=1)
pbl = Pin(13, Pin.OUT, value=1)
cst = Pin(16, Pin.OUT, value=1)  # Initialise all CS\ pins: XPT2046
irq = Pin(17,Pin.IN)

gc.collect()  # Precaution before instantiating framebuf
def init_spi(baudrate=60_000_000):
    return SPI(1, baudrate, sck=Pin(10), mosi=Pin(11), miso=Pin(12))

# Max baudrate produced by Pico is 31_250_000. ST7789 datasheet allows <= 62.5MHz.
spi = init_spi()

# Define the display
# For portrait mode:
# ssd = SSD(spi, height=320, width=240, dc=pdc, cs=pcs, rst=prst)
# For landscape mode:
ssd = SSD(spi, height=240, width=320, disp_mode=PORTRAIT, dc=pdc, cs=pcs, rst=prst, display=PI_PICO_28)

# SD Card support
import os
try:
    sd = SDCard(spi, Pin(22, Pin.OUT), 60_000_000)
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")
except OSError as e:
    print("SD not available: ", e)
    # SDCard driver sets baudrate to 100kHz during init and does't reset on failure
    init_spi()
    sd = None

# Touch support
class Touch:
    base_x = 4440
    base_y = 8000
    scale_x = 0.06936
    scale_y = 0.09091

    def __init__(self, spi):
        self.spi = spi
        self.irq = irq

    def touch_get(self): 
        if self.irq() == 0:
            self.spi = init_spi(baudrate=5_000_000)
            cst(0)
            x = 0
            y = 0
            for i in range(0,3):
                self.spi.write(bytearray([0XD0]))
                data = self.spi.read(2)
                time.sleep_us(10)
                x=x+(((data[0]<<8)+data[1])>>3)
                
                self.spi.write(bytearray([0X90]))
                data = self.spi.read(2)
                y=y+(((data[0]<<8)+data[1])>>3)

            x=x/3
            y=y/3
            # print("x,y=", x, y)
            
            cst(1) 
            self.spi = init_spi()
            row = int((x - self.base_x) * self.scale_x)
            row = min(max(row, 0), 239)
            col = int((self.base_y - y) * self.scale_y)
            col = min(max(col, 0), 319)
            result = [row, col]
            return(result)

touch = Touch(spi)