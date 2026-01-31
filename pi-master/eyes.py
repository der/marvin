import asyncio
import os
import random
import sys 
import time
import logging

import spidev as SPI
import LCD_1inch28
from PIL import Image,ImageDraw,ImageFont

class Eyes:
    # Raspberry Pi pin configuration 0:
    RST0 = 4
    DC0 = 2
    BL0 = 3
    bus0 = 0
    device0 = 0

    # Raspberry Pi pin configuration 1:
    RST1 = 27
    DC1 = 17
    BL1 = 22
    bus1 = 0
    device1 = 1

    width = 240
    height = 240

    def __init__(self, backlight=80):
        self.disp0 = LCD_1inch28.LCD_1inch28(spi=SPI.SpiDev(self.bus0, self.device0),spi_freq=10000000,rst=self.RST0,dc=self.DC0,bl=self.BL0)
        self.disp1 = LCD_1inch28.LCD_1inch28(spi=SPI.SpiDev(self.bus1, self.device1),spi_freq=10000000,rst=self.RST1,dc=self.DC1,bl=self.BL1)
        self.eyes_closed = self.make_eyes_closed_image()
        self.blink_image = self.make_blink_image()
        self.awake = False
        self.blinkState = -1
        self.wide_eyes = False
        self.blink_delay = 80  # 40 cycles average = 2s
        self.eyes_at = 0
        self.draw_pending = True
        for disp in [self.disp0, self.disp1]:
            disp.Init()
            disp.clear()
            disp.bl_DutyCycle(backlight)

    def make_eyes_closed_image(self):
        image = Image.new("RGB", (self.width, self.height), "BLACK")
        draw = ImageDraw.Draw(image)
        draw.arc([(10,100),(230,160)],0,180,fill=(255,255,255))
        return image

    def make_blink_image(self):
        image = Image.new("RGB", (self.width, self.height), "BLACK")
        draw = ImageDraw.Draw(image)
        draw.chord([(10,115),(230,125)],0,359,fill=(255,255,255))
        return image
 
    def show_closed(self):
        self.show_image(self.eyes_closed)

    def show_blink(self):
        self.show_image(self.blink_image)

    def show_eyes_at(self, x):
        """
            x offset of eyes is between -100 and 100

        """
        image = Image.new("RGB", (self.width, self.height), "BLACK")
        draw = ImageDraw.Draw(image)
        offset = int(x/2) + 120
        if self.wide_eyes:
            draw.chord([(10,30),(230,210)],0,359,fill=(255,255,255))
        else:
            draw.chord([(10,60),(230,180)],0,359,fill=(255,255,255))
        draw.circle((offset,120), 48, fill = (50,50,250))
        draw.circle((offset,120), 20, fill = (0,0,0))
        self.show_image(image)

    def show_image(self, image: Image):
        for d in [self.disp0, self.disp1]:
            d.ShowImage(image)

    def set_awake(self, awake: bool):
        self.awake = awake
        self.draw_pending = True
    
    def set_wide_eyes(self, wide: bool):
        self.wide_eyes = wide
        self.draw_pending = True

    def set_eyes_at(self, x: float):
        self.eyes_at = x
        self.draw_pending = True

    async def run(self):
        while True:
            if self.draw_pending:
                if self.awake:
                    if self.blinkState <= 0:
                        self.show_blink()
                        self.blinkState = random.randint(5,2*self.blink_delay)
                    else:
                        self.show_eyes_at(self.eyes_at)
                        self.draw_pending = False
                else:
                    self.show_closed()
                    self.draw_pending = False
            else:
                if self.awake:
                    self.blinkState -= 1
                    if self.blinkState <= 0:
                        self.draw_pending = True
            await asyncio.sleep(0.05)
