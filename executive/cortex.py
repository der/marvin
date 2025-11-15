"""
Cortex module - Low-level rover control and state monitoring.

This module handles direct interaction with the rover hardware,
executes movement commands, and monitors for obstacles.
"""

import asyncio
from typing import Optional, Callable
from state import RoverState, MovementInstruction
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
        
    def get_heading(self) -> float:
        """Get current heading from compass."""
        return self.heading
    
    def get_distance_to_obstacle(self) -> float:
        """Get distance to nearest obstacle in cm."""
        return self.simulated_obstacle_distance
    
    async def move_forward(self, dist: float, speed: float = 0.5):
        """Start moving forward."""
        self.is_moving = True
        print(f"[Rover] Moving forward at speed {speed}")
        await asyncio.sleep(dist / (speed * 100))
        self.is_moving = False
    
    async def move_backward(self, dist: float, speed: float = 0.5):
        """Start moving backward."""
        self.is_moving = True
        print(f"[Rover] Moving backward at speed {speed}")
        await asyncio.sleep(dist / (speed * 100))
    
    async def rotate(self, direction: str, dist:float, speed: float = 0.3):
        """Rotate on the spot."""
        self.is_moving = True
        print(f"[Rover] Rotating {direction} at speed {speed}")
        # Simulate rotation
        await asyncio.sleep(dist / (speed * 100))
        if direction == "left":
            self.heading = self.heading - dist
        else:
            self.heading = self.heading + dist
        self.is_moving = False
    
    async def strafe(self, dist: float, direction: str, speed: float = 0.5):
        """Strafe sideways using mecanum wheels."""
        self.is_moving = True
        print(f"[Rover] Strafing {direction} at speed {speed}")
        await asyncio.sleep(dist / (speed * 100))
        self.is_moving = False  
    
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
        self.callback = None
        self.current_instruction: Optional[MovementInstruction] = None
    
    def emergency_stop(self):
        """Immediately stop the rover (e.g., user says 'stop')."""
        print("[Cortex] Emergency stop triggered")
        self.rover.stop()
        self.state.is_moving = False
    
    def update_state(self):
        """Update rover state from sensors and vision."""
        self.state.heading = self.rover.get_heading()
        self.state.is_moving = self.rover.is_moving
        self.state.distance_to_obstacle = self.rover.get_distance_to_obstacle()

    async def move(self, instruction: MovementInstruction):
        """Execute a single movement instruction."""
        direction = instruction.direction
        value = instruction.value
        
        if direction == "forward":
            await self.rover.move_forward(value)
        elif direction == "backward":
            await self.rover.move_backward(value)
        elif direction == "rotate_left":
            await self.rover.rotate("left", value)
        elif direction == "rotate_right":
            await self.rover.rotate("right", value)
        elif direction == "slide_left":
            await self.rover.strafe(value, "left")
        elif direction == "slide_right":
            await self.rover.strafe(value, "right")
        elif direction == "along_heading":
            # Move along current heading
            await self.rover.move_forward(value)
        else:
            print(f"[Cortex] Unknown movement direction: {direction}")
    
    def start_movement(self, instruction: MovementInstruction, callback):
        """Start movement without awaiting (for non-blocking calls)."""
        self.callback = callback
        self.current_instruction = instruction
        asyncio.create_task(self.move(instruction))

    async def run(self):
        """Main control loop - updates state periodically."""
        self.running = True
        print(f"[Cortex] Starting control loop (update interval: {self.update_interval}s)")
        
        while self.running:
            self.update_state()
            
            if not self.state.is_moving and self.callback is not None:
                instruction = self.current_instruction
                callback = self.callback
                self.callback = None
                self.current_instruction = None
                callback(instruction)
            
            await asyncio.sleep(self.update_interval)
    
    def stop_loop(self):
        """Stop the control loop."""
        self.running = False
        self.rover.stop()
