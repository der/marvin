from picamera2 import Picamera2
from libcamera import Transform, controls
import time
import threading
from copy import copy
import cv2

class Camera:
    JPEG_QUALITY = 70 

    def __init__(self):
        self.frame_lock = threading.Lock()
        self.latest_lores = None
        self.latest_frame = None
        self.stream_active = True

        try:
            self.camera = Picamera2()
            self.config = self.camera.create_still_configuration(
                buffer_count=2, transform=Transform(vflip=True, hflip=True)
            )
            self.config["main"] = {"format": "RGB888", "size": (1024, 768), "preserve_ar": True}
            self.config["lores"] = {"format": "RGB888", "size": (320, 240), "preserve_ar": True}
            self.camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})
            self.camera.configure(self.config)
            self.camera.start()
            time.sleep(0.5)
            print("Camera initialized")
        except Exception as e:
            print("Error initializing camera:", e)
            raise

    
    def capture_frames(self):
        """Continuously capture frames from the camera."""
        while self.stream_active:
            (main, lores), metadata = self.camera.capture_arrays(["main", "lores"])
            if lores is not None:
                # print(f"Captured frame: {lores.shape}")
                with self.frame_lock:
                    self.latest_frame = copy(main)
                    self.latest_lores = copy(lores)

    def _encode(self, frame):
        """Encode a frame as JPEG."""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.JPEG_QUALITY]
        result, encimg = cv2.imencode('.jpg', frame, encode_param)
        if result:
            return encimg.tobytes()
        else:
            print("Error encoding frame")
            return None

    def get_latest_lores(self):
        """Get the latest low-resolution frame."""
        with self.frame_lock:
            return self._encode(self.latest_lores)
    
    def get_latest_frame(self):
        """Get the latest high-resolution frame."""
        with self.frame_lock:
            return self._encode(self.latest_frame)
    
    def start_thread(self):
        """Start the camera capture thread."""
        self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.capture_thread.start()

    def stop(self):
        """Stop the camera stream."""
        self.stream_active = False
        self.capture_thread.join()
        self.camera.stop()
