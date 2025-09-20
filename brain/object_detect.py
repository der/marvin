from ultralytics import YOLOE
import requests
from io import BytesIO
from PIL import Image
import threading
import cv2

MODEL = "yoloe-v8s-seg"

classes = [
    "person",
    "teddy bear",
    "balcony",
    "book",
    "bookshelf",
    "chair",
    "coffee table",
    "door",
    "doorframe",
    "windowed door",
    "stool",
    "pc",
    "sofa",
    "table",
    "tv",
    "cupboard",
    "stairs"
    "piano",
    "mouse",
    "keyboard"]

MARVIN_CAMERA = "http://marvin.local:8080/still"
image_width = 1024

_model = None
_model_lock = threading.Lock()

def get_object_model():
    global _model, _model_lock
    with _model_lock:
        if _model is None:
            _model = YOLOE(MODEL)
            _model.set_classes(classes, _model.get_text_pe(classes))
    return _model

def get_image() -> Image:
    try:
        response = requests.get(MARVIN_CAMERA, stream=True)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        return image
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
    except IOError as e:
        print(f"Error processing image: {e}")


def detect_class(cls:str, image:Image = None) -> None|int:
    """
        Check the image for occurrences of the given class.
        Return None if none found, otherwise return dict with:
           offset - offset from centre line of image as +/- fraction
           width - factional width of the image taken up
    """
    try:
        class_id = classes.index(cls)
    except ValueError:
        print(f"Class not known: {cls}")
        return None
    model = get_object_model()
    if image is None:
        image = get_image()
    result = model.predict(image, classes=[class_id])[0]
    boxes = result.boxes
    if len(boxes.cls) > 0:
        x1,y1,x2,y2=[t.item() for t in boxes.xyxy[0]]
        offset = ((x2+x1)-image_width)/image_width
        width = (x2-x1)/image_width
        return {"offset": offset, "width": width}
    else:
        return None

def show_detections(image:Image = None, window="Detections") -> None:
    """
       Debugging aid - shows all detected classes as an overlay image
    """
    model = get_object_model()
    if image is None:
        image = get_image()
    result = model.predict(image)[0]
    annotated_frame = result.plot()
    cv2.imshow(window, annotated_frame)
    cv2.waitKey(10)    
