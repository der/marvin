from machine import SoftI2C, Pin
import joystick_2_unit
import asyncio
from urllib.urequest import urlopen
from math import atan2, pi, floor

pi_by_8 = pi/8
two_pi = 2*pi

SCL_1 = 1
SDA_1 = 0

SCL_2 = 3
SDA_2 = 2

# Convert joystick x,y to an angular sector between 0 (=East) and 15, anti-clockwise
def to_sector(x,y):
    a = atan2(y,x)
    if a < 0:
        a = two_pi+a
    return floor(a/pi_by_8)

def median(a, b, c):
    # Sort the three values
    if a > b:
        a, b = b, a
    if b > c:
        b, c = c, b
    if a > b:
        a, b = b, a
    return b

# Convert raw coord value to range -100 to 100 and apply a median denoise filter
class AxisTracker:
    def __init__(self):
        self.p2 = 0
        self.p1 = 0
        self.p0 = 0
        self.value = 0

    def normalize(self, x: float) -> int:
        v = round(x * 200) - 100
        if v > 100:
            v = 100
        elif v < -100:
            v= -100
        elif abs(v) < 10:
            v = 0
        return v
        
    def update(self, v: float) -> int:
        n = self.normalize(v)
        self.p2 = self.p1
        self.p1 = self.p0
        self.p0 = n
        self.value = median(self.p2, self.p1, self.p0)
        return self.value
    
# Track a single joystick.
# When axes changes enough and stably convert position to sector and magnitude % and fire callback
class JoystickTracker:
    THRESHOLD = 5
    
    def __init__(self, name, scl_pin, sda_pin, callback):
        i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.name = name
        self.stick =  joystick_2_unit.Joystick2Unit(i2c)
        self.stick.set_led(0, 80, 0)
        self.x_track = AxisTracker()
        self.y_track = AxisTracker()
        self.prior_x = 0
        self.prior_y = 0
        self.callback = callback

    def value_changed(self, x, y):
        if abs(x-self.prior_x) + abs(y-self.prior_y) > self.THRESHOLD:
            self.prior_x = x
            self.prior_y = y
            return True
        return False
    
    async def check_stick(self):
        x = self.x_track.update( self.stick.get_x())
        y = self.y_track.update( self.stick.get_y())
        if self.value_changed(x, y):
            print(f"check_stick({self.name}) found x={x} y={y}")
            mag = ((abs(x) + abs(y)) // 60) * 30
            sector = to_sector(x, y)
            print(f"callback on {sector}:{mag}%")
            await self.callback(mag, sector)
            return True
        return False
    
class JoystickController:
    def __init__(self, rover_url, console):
        self.rover = rover_url
        self.console = console
        self.left_stick = JoystickTracker("left", SCL_1, SDA_1, self.left_action)
        self.right_stick = JoystickTracker("right", SCL_2, SDA_2, self.right_action)
        self.left_map = ["rl", "rl", "f", "f", "f", "f", "rl", "rl", "rl", "rl", "b", "b", "b", "b", "rl", "rl"]
        self.right_map = ["sl", "dl", "dl", "f", "f", "dr", "dr", "sr", "sr", "Dr", "Dr", "b", "b", "Dl", "Dl", "sl"]

    async def left_action(self, mag, sector):
        await self.notify(mag, self.left_map[sector])

    async def right_action(self, mag, sector):
        await self.notify(mag, self.right_map[sector])

    async def notify(self, mag, code):
        print(f"notify called on {code}:{mag}%")
        await self.console.message(f"Joystick {code}:{mag}%")
        try:
            urlopen(self.rover + f"set-motor?s={mag}&dir={code}", data="", method ="POST").close()
        except OSError:
            await self.console.message("could not connect")

    async def watch_controls(self):
        while True:
            await self.left_stick.check_stick()
            await self.right_stick.check_stick()
            await asyncio.sleep(0.03)
