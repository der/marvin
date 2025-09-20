import time
from object_detect import detect_class, show_detections, get_image
from motor_control import rotate_by, move
import cv2

def main():
    window = "Detections"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cvs.waitKey(10)
    while True:
        image = get_image()
        show_detections(image, window)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
