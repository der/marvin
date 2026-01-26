"""
Cortex module - Low-level rover control and state monitoring.

This module handles direct interaction with the rover hardware,
executes movement commands, and monitors for obstacles.
"""

import asyncio
import concurrent.futures
import time
from typing import Optional, Callable
from base_types import RoverState, MovementInstruction
from pydantic_ai import ModelMessage

class DummyRoverInterface:
    """
    Dummy interface to simulate rover hardware.
    Replace this with actual camera_server API calls later.
    """

    def __init__(self):
        self.heading = 0.0
        self.is_moving = False
        self.simulated_obstacle_distance = 100.0
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def get_heading(self) -> float:
        """Get current heading from compass."""
        return self.heading

    def get_distance_to_obstacle(self) -> float:
        """Get distance to nearest obstacle in cm."""
        return self.simulated_obstacle_distance

    def move_forward(self, dist: float, speed: float = 0.5):
        """Start moving forward."""
        def task():
            self.is_moving = True
            print(f"[Rover] Moving forward at speed {speed}")
            time.sleep(dist / (speed * 100))
            self.is_moving = False
        return self.executor.submit(task)

    def move_backward(self, dist: float, speed: float = 0.5):
        """Start moving backward."""
        def task():
            self.is_moving = True
            print(f"[Rover] Moving backward at speed {speed}")
            time.sleep(dist / (speed * 100))
            self.is_moving = False
        return self.executor.submit(task)

    def rotate(self, direction: str, dist: float, speed: float = 0.3):
        """Rotate on the spot."""
        def task():
            self.is_moving = True
            print(f"[Rover] Rotating {direction} at speed {speed}")
            time.sleep(dist / (speed * 100))
            if direction == "left":
                self.heading -= dist
            else:
                self.heading += dist
            self.is_moving = False
        return self.executor.submit(task)

    def strafe(self, dist: float, direction: str, speed: float = 0.5):
        """Strafe sideways using mecanum wheels."""
        def task():
            self.is_moving = True
            print(f"[Rover] Strafing {direction} at speed {speed}")
            time.sleep(dist / (speed * 100))
            self.is_moving = False
        return self.executor.submit(task)

    def stop(self):
        """Stop all movement."""
        self.is_moving = False
        print("[Rover] Stopped")


class RoverCortex:
    """
    The cortex manages low-level rover control and state monitoring.
    """
    
    def __init__(self, update_interval: float = 0.2):
        """
        Initialize the cortex.
        
        Args:
            update_interval: How often to update state in seconds (default 200ms)
        """
        self.rover = DummyRoverInterface()
        self.state = RoverState()
        self.update_interval = update_interval
        self.running = False
        self.current_instruction: Optional[MovementInstruction] = None
        self.callback = None
        self.movement_future: Optional[concurrent.futures.Future] = None
    
    def stop(self):
        """Immediately stop the rover (e.g., user says 'stop')."""
        print("[Cortex] Emergency stop triggered")
        self.rover.stop()
        self.state.is_moving = False
        self.callback = None
    
    def update_state(self):
        """Update rover state from sensors and vision."""
        self.state.heading = self.rover.get_heading()
        self.state.is_moving = self.rover.is_moving
        self.state.distance_to_obstacle = self.rover.get_distance_to_obstacle()

    def get_state(self):
        """Return the current state of the rover"""
        return self.state
    
    def move(self, instruction: MovementInstruction) -> Optional[concurrent.futures.Future]:
        """Execute a single movement instruction."""
        self.current_instruction = instruction
        direction = instruction.direction
        value = instruction.value
        
        if direction == "forward":
            return self.rover.move_forward(value)
        elif direction == "backward":
            return self.rover.move_backward(value)
        elif direction == "rotate_left":
            return self.rover.rotate("left", value)
        elif direction == "rotate_right":
            return self.rover.rotate("right", value)
        elif direction == "slide_left":
            return self.rover.strafe(value, "left")
        elif direction == "slide_right":
            return self.rover.strafe(value, "right")
        elif direction == "along_heading":
            # Move along current heading
            return self.rover.move_forward(value)
        else:
            if self.callback:
                self.callback(f"[Cortex] Unknown movement direction: {direction}")
            return None
    
    def start_movement(self, instruction: MovementInstruction, callback: Optional[Callable]):
        """Start movement without awaiting (for non-blocking calls)."""
        self.callback = callback
        self.movement_future = self.move(instruction)

    async def run(self):
        """Main control loop - updates state periodically."""
        self.running = True
        print(f"[Cortex] Starting control loop (update interval: {self.update_interval}s)")
        
        while self.running:
            self.update_state()

            if self.movement_future is not None and self.movement_future.done():
                self.movement_future = None
                instruction = self.current_instruction
                callback = self.callback
                self.callback = None
                self.current_instruction = None
                callback(instruction)
            
            await asyncio.sleep(self.update_interval)
    
    def quit(self):
        """Stop the control loop."""
        self.running = False
        self.rover.stop()
