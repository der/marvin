import time
from object_detect import detect_class
from motor_control import rotate_by, move

def turn_to(cls):
    while True:
        detection = detect_class(cls)
        if detection is None:
            # Want to be able to move, then return when move done
            # After move camera still shaky so perhaps try a few detects during a settle time.
            move("rr", 30, 10)
            time.sleep(0.4)
            move("s", 0)
            time.sleep(0.2)
        else:
            offset = detection['offset']
            print(f"Found bear at offset {offset}")
            if abs(offset) < 0.1:
                print("Found the bear")
                return
            else:
                rotate_by(offset)
                time.sleep(0.5)

turn_to("teddy bear")
