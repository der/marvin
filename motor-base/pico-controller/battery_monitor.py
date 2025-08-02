from machine import ADC, Pin, PWM
import time
import uasyncio as asyncio

# Maximum duty cycle value (65535 for 16-bit PWM)
MAX_DUTY = 65535

class BatteryLed:
    
    def __init__(self, RED_PIN=4, GREEN_PIN = 1, BLUE_PIN = 2):
        self.red_pwm = PWM(Pin(RED_PIN))
        self.green_pwm = PWM(Pin(GREEN_PIN))
        self.blue_pwm = PWM(Pin(BLUE_PIN))
        self.red_pwm.freq(1000)
        self.green_pwm.freq(1000)
        self.blue_pwm.freq(1000)

    def set_colour(self, r, g, b):
        """
        Set RGB LED color using values from 0-255 for each component
        """
        self.red_pwm.duty_u16(int(r * MAX_DUTY / 255))
        self.green_pwm.duty_u16(int(g * MAX_DUTY / 255))
        self.blue_pwm.duty_u16(int(b * MAX_DUTY / 255))    
    
    def set_green(self):
        self.set_colour(0, 150, 0)
        
    def set_orange(self):
        self.set_colour(150, 50, 0)
    
    def set_red(self):
        self.set_colour(150, 0, 0)
        
class BatteryMonitor:
    def __init__(self, led, emergency_callback=None, ADC_PIN=28):
        self.adc = ADC(Pin(ADC_PIN))
        self.voltage = 0
        self.led = led
        self.emergency_callback = emergency_callback

    def check_voltage(self):
        raw_value = self.adc.read_u16()
    
        # Convert to 3.3v reference then account for 10:1 divider chain
        self.voltage = (raw_value / 65535) * 3.3 * 11
    
        if self.voltage > 11.6:
            self.led.set_green()
        elif self.voltage > 10.6:
            self.led.set_orange()
        else:
            self.led.set_red()
            
        if self.voltage < 9.6 and self.emergency_callback != None:
            self.emergency_callback()
        return self.voltage

    async def run_monitor(self):
        while True:
            self.check_voltage()
            await asyncio.sleep(0.5)

def emergency():
    print("Battery dead!!")

def main():
    led = BatteryLed()
    monitor = BatteryMonitor(led, emergency)
    asyncio.create_task(monitor.run_monitor())
    while True:
        await asyncio.sleep(10)

asyncio.run(main())