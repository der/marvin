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
    current_image: Optional[str] = Field(
        default=None,
        description="Path or reference to current camera image"
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
    current_goal: Optional[str] = Field(
        default=None,
        description="Current goal as set by user prompts"
    )
    plan: Optional[str] = Field(
        default=None,
        description="High-level plan to achieve the current goal"
    )
    
    def get_summary(self) -> str:
        """Get a human-readable summary of high-level state."""
        goal_str = self.current_goal if self.current_goal else "none"
        plan_str = self.plan if self.plan else "none"
        return f"Mode: {self.mode.value}, Goal: {goal_str}, Plan: {plan_str}"
