from machine import Pin, PWM
from time import sleep, ticks_us, ticks_diff
import micropython
import uasyncio as asyncio

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
        speed = 100 * speed / MAX_SPEED  # Convert to percentage of max speed
        return speed if speed < 100 else 100

def limit_speed(speed: float) -> int:
    """
    Limit the speed to the range 0 to 100.
    """
    if speed > 100:
        return 100
    elif speed < 0:
        return 0
    return int(speed)

class MotorPID:
    def __init__(self, motor: Motor, kp:float = 1.0, ki:float = 0.1, kd:float = 0.05):
        self.motor = motor
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = 0
        self.reverse = False
        self.last_setting = 0
        self.last_value = 0
        self.integral = 0

    def set_speed(self, speed: int):
        self.setpoint = abs(speed)
        self.reverse = speed < 0
        
    def update(self):
        if self.setpoint == 0:
            self.motor.set_speed(0)
            return
        current_value = self.motor.get_speed()
        error = self.setpoint - current_value
        self.integral = limit_speed(self.integral + error)
        # Use derivative kick trick: http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-derivative-kick/
        derivative = -(current_value - self.last_value)
        delta = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        output = limit_speed(self.last_setting + delta)
        self.last_setting = output
        self.last_value = current_value
        speed = -output if self.reverse else output
        print(f"Current: {current_value}, Error: {error}, Delta: {delta}, Output: {output}, Speed: {speed}")
        self.motor.set_speed(speed)

async def pid_update_loop(motor_pid: MotorPID):
    while True:
        motor_pid.update()
        await asyncio.sleep(0.05)

async def test(motor_pid: MotorPID):
    motor_pid.set_speed(20)
    await asyncio.sleep(3)
    motor_pid.set_speed(50)
    await asyncio.sleep(3)
    motor_pid.set_speed(100)
    await asyncio.sleep(3)
    motor_pid.set_speed(-50)
    await asyncio.sleep(3)
    motor_pid.set_speed(0)
    await asyncio.sleep(3)

def init_motor():
    pwm = Pin(0, Pin.OUT)
    dir = Pin(1, Pin.OUT)
    pulse = Pin(2, Pin.IN, Pin.PULL_UP)
    motor = Motor(pwm, dir, pulse, 2)
    return MotorPID(motor)

async def main():
    motor_pid = init_motor()
    motor_pid.motor.set_speed(0)  # Ensure motor is stopped initially
    asyncio.create_task(pid_update_loop(motor_pid))
    asyncio.create_task(test(motor_pid))
    await asyncio.sleep(30)  # Yield control to the event loop

asyncio.run(main())
