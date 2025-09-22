import time
from object_detect import detect_class
from motor_control import rotate_by, move, move_and_stop
from subprocess import Popen

WIDTH_TRESHHOLD = 0.08  # Width of object to stop at

def say(text: str):
    Popen(["flite_cmu_us_rms", "-t", text])
    time.sleep(len(text) * 0.06 + 0.5)

def check_for(cls):
    detection = detect_class(cls)
    if detection is None:
        detection = detect_class(cls)
    return detection

def find_object(cls):
    say(f"Looking for {cls}")
    while True:
        for iter in range(10):
            detection = check_for(cls)
            if detection is not None:
                say(f"Spotted a {cls}")
                offset = detection['offset']
                rotate_by(offset)
                detection = check_for(cls)
                if detection is not None and detection["width"] < WIDTH_TRESHHOLD:
                    say(f"Moving closer to the {cls}")
                    move_to(cls)
                return True
            else:
                move_and_stop("rr", 40, 15)
                # wait for image to stabilise before checking again
                time.sleep(0.3)
        say(f"Couldn't find a {cls}")    

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

find_object("teddy bear")
