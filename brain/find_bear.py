import time
from object_detect import detect_class
from motor_control import rotate_by, move, move_and_stop
from subprocess import Popen

def say(text: str):
    Popen(["flite_cmu_us_rms", "-t", text])

def find_object(cls):
    say(f"Looking for {cls}")
    for iter in range(10):
        detection = detect_class(cls)
        if detection is not None:
            say(f"Spotted a {cls}")
            offset = detection['offset']
            rotate_by(offset)
            move_to(cls)
            say(f"Hello {cls}")
            return True
        else:
            move_and_stop("rr", 40, 15)
            # wait for image to stabilise before checking again
            time.sleep(0.2)
    say(f"Couldn't find a {cls}")    

def move_to(cls):
    for iter in range(10):
        detection = detect_class(cls)
        if detection is not None:
            offset = detection['offset']
            width = detection['width']
            if abs(offset) > 0.1:
                rotate_by(offset)
            elif width < 0.15:
                if iter == 0:
                    say(f"Moving closer to the {cls}")
                move_and_stop("f", 40, 10)
            else:
                if iter > 0:
                    say(f"That's close enough")
                return True
            time.sleep(0.2)
        else:
            say(f"Lost sight of the {cls}")
            return False
    return False

find_object("teddy bear")
