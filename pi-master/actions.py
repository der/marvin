# Collection of action tasks that we might expose to the brain
from controllers import HEADING_PID as PID
from dist_heading_sensor import DistanceHeadingMonitor
from motor_control import MotorController
import asyncio

ROTATION_SCALING = 2.66

async def rotate_to_heading(target: int, sensor: DistanceHeadingMonitor, motor: MotorController):
    pid = PID(kp=1.0, ki=0.05, kd=0.1)
    pid.set_target(target)
    heading = sensor.heading
    pid.set_current(heading)

    finished = False

    def sensor_callback(dist, heading, pitch):
        nonlocal finished

        change = pid.update(heading)
        movement = round(change / ROTATION_SCALING)
        speed = 50 if abs(movement) < 20 else 90
        dir = "rr" if movement > 0 else "rl"
        print(f"Heading {heading} change {change} moving {abs(movement)}{dir}{speed}")
        if movement == 0 or abs(pid.last_error) < 3:
            motor.send(0, "f")
            finished = True
        else:
            motor.send(speed, dir, abs(movement))

    sensor.add_callback(sensor_callback)
    while not finished:
        await asyncio.sleep(0.1)
    sensor.remove_callback(sensor_callback)
