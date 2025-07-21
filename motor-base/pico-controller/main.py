from motor_controller import MotorControl
from time import sleep
import uasyncio as asyncio

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

asyncio.run(main())
