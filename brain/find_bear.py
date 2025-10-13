import time
from object_detect import detect_class
from motor_control import rotate_by, move, move_and_stop, get_heading, move_along_heading, get_sensor
from subprocess import Popen

WIDTH_THRESHOLD = 0.35  # Width of object to stop at
WIDTH_TO_LIDAR_THRESHOLD = 0.15  # Width to switch to lidar
OFFSET_THRESHOLD = 0.1
OFFSET_TO_HEADING = 30  # Degrees to turn per unit of offset
DISTANCE_THRESHOLD = 80  # Distance to obstacle to stop at

def say(text: str):
    text = text.replace("teddy ", "")
    Popen(["flite_cmu_us_rms", "-t", text])
    time.sleep(len(text) * 0.06 + 0.5)

def check_for(cls):
    detection = detect_class(cls)
    if detection is None:
        detection = detect_class(cls)
    if detection is not None:
        offset = detection['offset']
        width = detection['width']
        print(f"found {cls} with offset {offset:.3f} and width {width:.3f}")
    return detection

def find_object(cls: str) -> bool:
    say(f"Looking for {cls}")
    for iter in range(10):
        detection = check_for(cls)
        if detection is not None:
            say(f"Spotted a {cls}")
            return True
        else:
            move_and_stop("rr", 40, 15)
            # wait for image to stabilise before checking again
            time.sleep(0.5)
    return False

def centre_on(cls):
    for iter in range(10):
        detection = check_for(cls)
        if detection is not None:
            offset = detection['offset']
            if abs(offset) > OFFSET_THRESHOLD:
                rotate_by(offset)
            else:
                return True
            time.sleep(0.2)
        else:
            say(f"Lost sight of the {cls}")
    return False

def move_to_by_heading(cls):
    heading = get_heading()
    if heading < 0:
        print("Can't get heading")
        return False
    for iter in range(10):
        detection = check_for(cls)
        if detection is not None:
            offset = detection['offset']
            width = detection['width']
            print(f"found {cls} with offset {offset:.3f} and width {width:.3f}")
            sensor = get_sensor()
            print(f"sensor: {sensor}")
            if width > WIDTH_TO_LIDAR_THRESHOLD and sensor is not None and sensor.get("distance")[1] < DISTANCE_THRESHOLD:
                if iter > 0:
                    say("That's close enough")
                return True
            heading = sensor.get("heading", 0)
            target_heading = heading + int(offset * OFFSET_TO_HEADING)
            if target_heading < 0:
                target_heading += 256
            elif target_heading > 255:
                target_heading -= 256
            print(f"heading {heading} target {target_heading}")
            move_along_heading(25, target_heading, False)
            time.sleep(0.2)
        else:
            say(f"Lost sight of the {cls}")
            return False
    return False

def move_to(cls):
    for iter in range(10):
        detection = check_for(cls)
        if detection is not None:
            offset = detection['offset']
            width = detection['width']
            print(f"found {cls} with offset {offset:.3f} and width {width:.3f}")
            if abs(offset) > OFFSET_THRESHOLD:
                rotate_by(offset)
            elif width < WIDTH_THRESHOLD:
                move_and_stop("f", 40, 25)
            else:
                if iter > 0:
                    say("That's close enough")
                return True
            time.sleep(0.2)
        else:
            say(f"Lost sight of the {cls}")
            return False
    return False

def track_object(cls):
    while True:
        found = find_object(cls)
        if found:
            moved = move_to_by_heading(cls)
            if moved:
                centre_on(cls)
                say(f"Reached the {cls}")
                while check_for(cls) is not None:
                    time.sleep(2)
            else:
                say(f"Couldn't get to the {cls}")
        if not found:
            say(f"Couldn't find a {cls}")

track_object("teddy bear")
