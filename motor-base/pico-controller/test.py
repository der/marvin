from machine import Pin, PWM
from time import sleep, ticks_us, ticks_diff
import micropython

# Needed if we have hard IRQs for debugging
micropython.alloc_emergency_exception_buf(100)
MAX_DUTY = 65535
MAX_SPEED = 160

class Motor(object):
    def __init__(self, pwm_pin, dir_pin, pulse_pin, average_over=1):
        self.average_over = average_over
        self.pwm = PWM(pwm_pin, freq=5000, duty_u16=MAX_DUTY)
        self.dir_pin = dir_pin
        self.pulse_pin = pulse_pin
        self.speed = 0
        self.pulse_count=0
        self.pulse_total=0
        self.pulse_average=0
        self.pulse_last=0
        pulse_pin.irq(self.pulse, Pin.IRQ_RISING | Pin.IRQ_FALLING, hard=True)

    def pulse(self, arg):
        if self.pulse_pin.value() == 1:
            # Start of pulse
            self.pulse_last = ticks_us()
        else:
            self.pulse_total += ticks_diff(ticks_us(), self.pulse_last)
            self.pulse_count += 1
            if self.pulse_count >= self.average_over:
                self.pulse_average = self.pulse_total // self.average_over
                self.pulse_count = 0
                self.pulse_total = 0

    def set_speed(self, speed):
        """
            Set speed in %age of full speed (around 150rpm)
        """
        if speed > 100:
            speed = 100
        elif speed < -100:
            speed = -100
        self.speed = speed
        self.pwm.duty_u16(((100 - abs(speed)) * MAX_DUTY)//100)
        self.dir_pin.value(1 if speed > 0 else 0)
        self.pulse_average = 0

    def get_speed(self):
        if self.pulse_average == 0:
            return 0
        # 45:1 gear, 6 pulses per motor rev, not sure I understand the factor of 2  
        speed = 60*1000000/(45*6*2*self.pulse_average)
        return speed if speed < MAX_SPEED else MAX_SPEED

pwm = Pin(0, Pin.OUT)
dir = Pin(1, Pin.OUT)
pulse = Pin(2, Pin.IN, Pin.PULL_UP)
motor = Motor(pwm, dir, pulse, 2)

def test(speed):
    print("Speed:", speed)
    motor.set_speed(speed)
    sleep(1)
    print("Speed (rpm)", motor.get_speed())
    sleep(1)

while True:
    test(20)
    # test(0)
    # test(20)
    # test(50)
    # test(100)
    # test(-50)
