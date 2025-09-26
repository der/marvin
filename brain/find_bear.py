import time
from object_detect import detect_class
from motor_control import rotate_by, move, move_and_stop
from subprocess import Popen

WIDTH_TRESHHOLD = 0.4  # Width of object to stop at
OFFSET_THRESHOLD = 0.1

def say(text: str):
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

def find_object(cls):
    say(f"Looking for {cls}")
    for iter in range(10):
        detection = check_for(cls)
        if detection is not None:
            offset = detection['offset']
            say(f"Spotted a {cls}")
            return True
        else:
            move_and_stop("rr", 40, 15)
            # wait for image to stabilise before checking again
            time.sleep(0.5)

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

def move_to(cls):
    for iter in range(10):
        detection = check_for(cls)
        if detection is not None:
            offset = detection['offset']
            width = detection['width']
            print(f"found {cls} with offset {offset:.3f} and width {width:.3f}")
            if abs(offset) > 0.1:
                rotate_by(offset)
            elif width < WIDTH_TRESHHOLD:
                move_and_stop("f", 40, 15)
            else:
                if iter > 0:
                    say(f"That's close enough")
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
            centred = centre_on(cls)
            if centred:
                moved = move_to(cls)
                if moved:
                    say(f"Reached the {cls}")
                    while check_for(cls) is not None:
                        time.sleep(2)
                else:
                    say(f"Couldn't get to the {cls}")
            else:
                say(f"Couldn't centre on the {cls}")
        if not found:
            say(f"Couldn't find a {cls}")

track_object("teddy bear")
