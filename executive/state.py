"""
State models for the rover system.

This module defines the data structures for coordinating between
the executive agent and the cortex controller.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class RoverMode(str, Enum):
    """Operating mode of the rover."""
    STANDBY = "standby"
    ACTING = "acting"


class VisibleObject(BaseModel):
    """An object detected in the camera view."""
    name: str = Field(description="Type/name of the object")
    heading: float = Field(description="Relative heading to the object in degrees (-180 to 180)")
    confidence: float = Field(default=1.0, description="Detection confidence (0-1)")


class RoverState(BaseModel):
    """Low-level state information about the rover."""
    heading: float = Field(default=0.0, description="Absolute heading in degrees (0-360)")
    is_moving: bool = Field(default=False, description="Whether the rover is currently moving")
    distance_to_obstacle: float = Field(
        default=999.0, 
        description="Distance to nearest obstacle in cm"
    )
    visible_objects: List[VisibleObject] = Field(
        default_factory=list,
        description="List of objects currently visible"
    )
    
    def get_summary(self) -> str:
        """Get a human-readable summary of rover state."""
        objects_str = ", ".join([obj.name for obj in self.visible_objects]) if self.visible_objects else "none"
        return (
            f"Heading: {self.heading}°, "
            f"Moving: {self.is_moving}, "
            f"Obstacle distance: {self.distance_to_obstacle}cm, "
            f"Visible objects: {objects_str}"
        )


class HighLevelState(BaseModel):
    """High-level state managed by the executive."""
    mode: RoverMode = Field(default=RoverMode.STANDBY)

    def get_summary(self) -> str:
        """Get a human-readable summary of high-level state."""
        return f"Mode: {self.mode.value}"

class MovementDirections(str, Enum):
    """Possible movement directions for the rover."""
    FORWARD = "forward"
    BACKWARD = "backward"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ALONG_HEADING = "along_heading"

class MovementInstruction(BaseModel):
    """A single movement instruction for the rover."""
    direction: MovementDirections = Field(description="Direction of movement")
    value: float = Field(
        description="Distance in cm for linear movements or degrees for rotations or headings"
    )
