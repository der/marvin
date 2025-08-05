from motor_controller import MotorControl, Motor
from time import sleep
import uasyncio as asyncio
from machine import Pin

async def test(motor_control: MotorControl):
    motor_control.set_all_speeds(20)
    await asyncio.sleep(3)
    motor_control.set_all_speeds(50)
    await asyncio.sleep(3)
    motor_control.set_all_speeds(100)
    await asyncio.sleep(3)
    motor_control.set_all_speeds(-50)
    await asyncio.sleep(3)
    motor_control.set_all_speeds(0)
    await asyncio.sleep(3)

async def main():
    motor_control = MotorControl()
    asyncio.create_task(motor_control.pid_update_loop())
    asyncio.create_task(test(motor_control))
    while True:
        await asyncio.sleep(10)  # Yield control to the event loop

# asyncio.run(main())


def test():
    pwm = Pin(10, Pin.OUT)
    dir = Pin(11, Pin.OUT)
    pulse = Pin(12, Pin.IN, Pin.PULL_UP)
    motor = Motor(pwm, dir, pulse)

    print("Setting motor to 50%")
    motor.set_speed(50)
    sleep(5)
    
test()
