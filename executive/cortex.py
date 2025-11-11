"""
Cortex module - Low-level rover control and state monitoring.

This module handles direct interaction with the rover hardware,
executes movement commands, and monitors for obstacles.
"""

import time
import asyncio
from typing import Optional, Callable
from state import RoverState, VisibleObject
import random


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
        # Simulate small drift when moving
        if self.is_moving:
            self.heading += random.uniform(-1, 1)
            self.heading = self.heading % 360
        return self.heading
    
    def get_distance_to_obstacle(self) -> float:
        """Get distance to nearest obstacle in cm."""
        # Simulate approaching an obstacle
        if self.is_moving:
            self.simulated_obstacle_distance -= random.uniform(0, 2)
            self.simulated_obstacle_distance = max(5.0, self.simulated_obstacle_distance)
        return self.simulated_obstacle_distance
    
    def get_visible_objects(self) -> list:
        """Get list of visible objects from vision system."""
        # Dummy data - return random objects occasionally
        if random.random() < 0.3:
            objects = random.choice([
                [VisibleObject(name="teddy bear", heading=-45.0, confidence=0.9)],
                [VisibleObject(name="book", heading=10.0, confidence=0.85)],
                [VisibleObject(name="waste basket", heading=30.0, confidence=0.92)],
                []
            ])
            return objects
        return []
    
    def move_forward(self, speed: float = 0.5):
        """Start moving forward."""
        self.is_moving = True
        print(f"[Rover] Moving forward at speed {speed}")
    
    def move_backward(self, speed: float = 0.5):
        """Start moving backward."""
        self.is_moving = True
        print(f"[Rover] Moving backward at speed {speed}")
    
    def rotate(self, direction: str, speed: float = 0.3):
        """Rotate on the spot."""
        self.is_moving = True
        print(f"[Rover] Rotating {direction} at speed {speed}")
        # Simulate rotation
        if direction == "left":
            self.heading = (self.heading - 5) % 360
        else:
            self.heading = (self.heading + 5) % 360
    
    def strafe(self, direction: str, speed: float = 0.5):
        """Strafe sideways using mecanum wheels."""
        self.is_moving = True
        print(f"[Rover] Strafing {direction} at speed {speed}")
    
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
        self._obstacle_callback: Optional[Callable] = None
        self._plan_complete_callback: Optional[Callable] = None
        self.current_plan_step = 0
        self.plan_steps = []
        
    def set_obstacle_callback(self, callback: Callable):
        """Set callback to invoke when obstacle is too close."""
        self._obstacle_callback = callback
    
    def set_plan_complete_callback(self, callback: Callable):
        """Set callback to invoke when plan is complete."""
        self._plan_complete_callback = callback
    
    def emergency_stop(self):
        """Immediately stop the rover (e.g., user says 'stop')."""
        print("[Cortex] Emergency stop triggered")
        self.rover.stop()
        self.state.is_moving = False
        self.plan_steps = []
        self.current_plan_step = 0
    
    def update_state(self):
        """Update rover state from sensors and vision."""
        self.state.heading = self.rover.get_heading()
        self.state.is_moving = self.rover.is_moving
        self.state.distance_to_obstacle = self.rover.get_distance_to_obstacle()
        self.state.visible_objects = self.rover.get_visible_objects()
        
        # Check for obstacle
        if self.state.distance_to_obstacle < 10.0 and self.state.is_moving:
            print(f"[Cortex] Obstacle detected at {self.state.distance_to_obstacle:.1f}cm - stopping!")
            self.rover.stop()
            self.state.is_moving = False
            if self._obstacle_callback:
                self._obstacle_callback(self.state.distance_to_obstacle)
    
    def execute_plan(self, plan_steps: list):
        """
        Set a new plan to execute.
        
        Args:
            plan_steps: List of action dictionaries with 'action' and optional parameters
        """
        self.plan_steps = plan_steps
        self.current_plan_step = 0
        print(f"[Cortex] New plan loaded with {len(plan_steps)} steps")
    
    def step_plan(self):
        """Execute the next step in the current plan."""
        if self.current_plan_step >= len(self.plan_steps):
            if self.plan_steps:  # Only notify if there was a plan
                print("[Cortex] Plan complete")
                if self._plan_complete_callback:
                    self._plan_complete_callback()
                self.plan_steps = []
            return
        
        step = self.plan_steps[self.current_plan_step]
        action = step.get('action')
        
        print(f"[Cortex] Executing step {self.current_plan_step + 1}/{len(self.plan_steps)}: {action}")
        
        # Execute action
        if action == 'move_forward':
            distance = step.get('distance', 10)
            self.rover.move_forward()
            # In real implementation, this would be based on odometry
            time.sleep(distance / 10)  # Simulate movement time
            self.rover.stop()
        elif action == 'rotate':
            direction = step.get('direction', 'left')
            degrees = step.get('degrees', 90)
            self.rover.rotate(direction)
            time.sleep(degrees / 90)  # Simulate rotation time
            self.rover.stop()
        elif action == 'wait':
            duration = step.get('duration', 1)
            time.sleep(duration)
        
        self.current_plan_step += 1
    
    async def run(self):
        """Main control loop - updates state periodically."""
        self.running = True
        print(f"[Cortex] Starting control loop (update interval: {self.update_interval}s)")
        
        while self.running:
            self.update_state()
            
            # Execute next plan step if not moving and plan exists
            if not self.state.is_moving and self.plan_steps:
                self.step_plan()
            
            await asyncio.sleep(self.update_interval)
    
    def stop_loop(self):
        """Stop the control loop."""
        self.running = False
        self.rover.stop()
