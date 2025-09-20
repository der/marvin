import time
from object_detect import detect_class, show_detections, get_image
from motor_control import rotate_by, move

def main():
    while True:
        image = get_image()
        show_detections(image)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
