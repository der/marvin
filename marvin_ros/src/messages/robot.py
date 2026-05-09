# Messages for interacting with Marvin

from pydantic import BaseModel

class EyeMessage(BaseModel):
    """Message format for eye control commands."""
    open: bool = True
    wide: bool = False
    x: float = 0.0
