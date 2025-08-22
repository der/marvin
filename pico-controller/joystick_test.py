import time
from machine import SoftI2C, Pin
import joystick_2_unit

SCL_1 = 1
SDA_1 = 0

SCL_2 = 3
SDA_2 = 2

i2c1 = SoftI2C(scl=Pin(SCL_1), sda=Pin(SDA_1))
i2c2 = SoftI2C(scl=Pin(SCL_2), sda=Pin(SDA_2))
joystick1 = joystick_2_unit.Joystick2Unit(i2c1)
joystick2 = joystick_2_unit.Joystick2Unit(i2c2)

joystick1.set_led(50, 50, 50)
joystick2.set_led(50, 50, 50)

def check(label, joystick):
    x = joystick.get_x()
    y = joystick.get_y()
    is_pressed = joystick.is_pressed()
    
    if is_pressed:
        joystick.set_led(0,150,0)
    else:
        joystick.set_led(50,50,50)
    print("%s x: %.02f, y: %.02f, pressed: %s" % (label, x, y, is_pressed))
    
print("Starting...")
while True:
    check("left", joystick1)
    check("right", joystick2)
    time.sleep(0.1)
