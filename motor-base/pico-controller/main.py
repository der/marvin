from motor_controller import MotorControl
import uasyncio as asyncio
from battery_monitor import BatteryLed, BatteryMonitor
import BLEUart
import ure

from resettable_timer import ResettableTimer

motor_control = MotorControl()

def fail_safe():
    print("Fail safe stop")
    motor_control.set_all_speeds(0)

def emergency():
    print("Battery dead!!")
    fail_safe()

fail_safe_timer = ResettableTimer(3000, fail_safe)

led = BatteryLed()
monitor = BatteryMonitor(led, emergency)

command_pattern = ure.compile(r"^(\d*)([A-Za-z]+)")

def command(cmdin):
    cmd = cmdin.decode()
    print("Received command ", cmd)
    match = command_pattern.match(cmd)
    if match:
        speed = match.group(1)
        command = match.group(2)

        speed_setting = int(speed) if speed else 50
        motor_control.set_motion(speed_setting, command)
        fail_safe_timer.start()

async def main():
    uart = BLEUart.BleUart("rover", command)
    print("Starting BLE UART service")

    tasks = [
        asyncio.create_task(motor_control.pid_update_loop()),
        asyncio.create_task(monitor.run_monitor()),
        asyncio.create_task(uart.run())
    ]
    # Wait for everything to finish
    await asyncio.gather(*tasks)

asyncio.run(main())
