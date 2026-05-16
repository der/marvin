# Messages for interacting with Marvin

from pydantic import BaseModel

class EyeMessage(BaseModel):
    """Message format for eye control commands."""
    open: bool = True
    wide: bool = False
    x: float = 0.0

class NeckControlMessage(BaseModel):
    """Message format for neck control commands."""
    pan: float = 0.0
    tilt: float = 0.0
    speed: int = 2000

class MotorControlMessage(BaseModel):
    """Message format for motor control commands."""
    speed: int = 50  # Speed percentage (0-100)
    dir: str = 's'  # 'f' for forward, 'b' for backward, 'sl'/'sr' for slide left/right, 'rl'/'rr' for rotate left/right, 'tr'/'tl' for turn right/left while moving forward, 's' for stop
    dist: int | None = 50  # Optional distance to move in cm
