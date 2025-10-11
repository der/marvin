import requests
from time import sleep

MARVIN_BASE = "http://marvin.local:8080"
MARVIN_MOTOR = f"{MARVIN_BASE}/set-motor"
MARVIN_IS_MOVING = f"{MARVIN_BASE}/is-moving"

def move(dir="f", speed:int=50, distance: int|None=None, sync: bool = False):
    print(f"Move requested {speed} {dir} by {distance}")
    if distance is not None:
        response = requests.post(MARVIN_MOTOR, params={
            "dir": dir,
            "s": str(speed),
            "dist": str(distance),
            "sync": str(sync)
        })
    else:
        response = requests.post(MARVIN_MOTOR, params={
            "dir": dir,
            "s": str(speed)
        })
    if (response.status_code != 200):
        print(f"Request failed [{response.status_code}] {response.text}")
    return 

def is_moving() -> bool:
    response = requests.get(MARVIN_IS_MOVING)
    if (response.status_code != 200):
        print(f"Request failed [{response.status_code}] {response.text}")
        return False
    j = response.json()
    return j.get("status") == "success" and j.get("moving")

def move_and_stop(dir="f", speed:int=50, distance: int|None=None):
    move(dir, speed, distance, True)

OFFSET_SCALE=10

def rotate_by(offset: float):
    """
        rotate left/right given amount designed to re-centre image
    """
    dist = abs(int(offset * OFFSET_SCALE))
    if dist == 0:
        move("s", 0)
    else:
        move("rl" if offset < 0 else "rr", 50, dist, True)
