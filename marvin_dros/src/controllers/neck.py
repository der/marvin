# Support for neck movement and sensing
import logging

from st3215 import ST3215

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("NeckController")

class Neck:
    TILT_RANGE = 250
    PAN_RANGE = 750
    UART_PORT = "/dev/ttyACM0"

    def __init__(self):
        self.servo = ST3215(self.UART_PORT)

    def set_neck(self, tilt: int, pan: int, speed: int = 2000) -> None:
        """
        Set the neck tilt and pan angles.
        tilt: range -100 to 100
        pan: range -100 to 100
        speed: movement speed (default 2000)
        """
        try:
            tilt = -100 if tilt < -100 else 100 if tilt > 100 else tilt
            pan = -100 if pan < -100 else 100 if pan > 100 else pan
            tilt = int(tilt * self.TILT_RANGE / 100) + 2048
            pan = int(pan * self.PAN_RANGE / 100) + 2048
            self.servo.MoveTo(0, tilt, speed=speed, acc=50, wait=False)
            self.servo.MoveTo(1, pan, speed=speed, acc=50, wait=False)
            logger.info(f"Neck set to tilt={tilt}, pan={pan}")
            return
        except Exception as e:
            logger.error(f"Error setting neck: {e}")

    def get_neck(self) -> tuple[int, int]:
        """
        Get the current neck tilt and pan angles.
        Returns a tuple (tilt, pan) with values in range -100 to 100.
        """
        try:
            tilt = self.servo.ReadPosition(0)
            pan = self.servo.ReadPosition(1)
            tilt = int((tilt - 2048) * 100 / self.TILT_RANGE)
            pan = int((pan - 2048) * 100 / self.PAN_RANGE)
            logger.debug(f"Neck position read as tilt={tilt}, pan={pan}")
            return tilt, pan
        except Exception as e:
            logger.debug(f"Error reading neck position: {e}")
            return 0, 0
