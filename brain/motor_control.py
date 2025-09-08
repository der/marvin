import requests

MARVIN_MOTOR = "http://marvin.local:8080/set-motor"

def move(dir="f", speed:int=50, distance: int|None=None):
    print(f"Move requested {speed} {dir} by {distance}")
    if distance is not None:
        response = requests.post(MARVIN_MOTOR, params={
            "dir": dir,
            "s": str(speed),
            "dist": str(distance)
        })
    else:
        response = requests.post(MARVIN_MOTOR, params={
            "dir": dir,
            "s": str(speed)
        })
    if (response.status_code != 200):
        print(f"Request failed [{response.status_code}] {response.text}")
    return 

OFFSET_SCALE=10

def rotate_by(offset: float):
    """
        rotate left/right given amount designed to re-centre image
    """
    dist = abs(int(offset * OFFSET_SCALE))
    if dist == 0:
        move("s", 0)
    else:
        move("rl" if offset < 0 else "rr", 50, dist)
