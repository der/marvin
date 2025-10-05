from machine import I2C, Pin
from time import sleep

i2c = I2C(0, sda=Pin(5), scl=Pin(6))
buf = bytearray(6)
address = 96
calibration_register=0x1e

def get_calibration():
    calibration = i2c.readfrom_mem(address,calibration_register,8)
    return (calibration[0] >> 6) & 0x03

def calibrate():
    print("Wait, then rotate to 45 and 90 deg then random until hit calibration level of 3")
    calibration = 0
    while calibration != 3:
        print(f"Calibration level: {calibration}")
        calibration = get_calibration()
        sleep(0.5)
    print("Calibrated, saving")
    i2c.writeto_mem(address, 0, b'\0xF0')
    sleep(0.02)
    i2c.writeto_mem(address, 0, b'\0xF5')
    sleep(0.02)
    i2c.writeto_mem(address, 0, b'\0xF6')
    sleep(0.02)
    print("Saved")
    
calibrate()

