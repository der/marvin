"""
Executive Agent - High-level planning and decision making.

This module uses an LLM to interpret user commands, create plans,
and respond to queries about the rover's state and environment.
"""

from typing import Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from state import HighLevelState, RoverState, RoverMode
from dataclasses import dataclass


@dataclass
class ExecutiveDeps:
    """Dependencies injected into the agent context."""
    high_level_state: HighLevelState
    rover_state: RoverState
    cortex: 'RoverCortex'  # Forward reference


class ExecutiveAgent:
    """
    The executive agent uses an LLM to make high-level decisions.
    """
    
    def __init__(
        self, 
        model_url: str = "http://localhost:8080/v1",
        model_name: str = "local-model"
    ):
        """
        Initialize the executive agent.
        
        Args:
            model_url: Base URL for the LLM API (OpenAI compatible)
            model_name: Model name/identifier
        """
        self.high_level_state = HighLevelState()
        
        # Initialize the pydantic-ai agent with custom OpenAI provider
        # Create provider with custom base URL and dummy API key for local LLM
        provider = OpenAIProvider(
            base_url=model_url,
            api_key='dummy-key'
        )
        
        # Create the model using the provider
        model = OpenAIModel(model_name, provider=provider)
        
        # Create the agent with the model
        self.agent = Agent(
            model,
            deps_type=ExecutiveDeps,
            system_prompt=(
                "You are the executive controller for a small mobile rover robot. "
                "You help plan actions, answer questions about the environment, and "
                "coordinate the rover's activities. You can see through the rover's camera "
                "and control its movement. Be concise and practical in your responses. "
                "When given a goal, break it down into actionable steps."
            )
        )
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all tools available to the agent."""
        
        @self.agent.tool
        async def check_object_visible(ctx: RunContext[ExecutiveDeps], object_name: str) -> str:
            """
            Check if an object of the named type is currently visible.
            
            Args:
                object_name: The type of object to look for (e.g., 'teddy bear', 'book')
            
            Returns:
                Description of whether the object is visible and its heading if found
            """
            for obj in ctx.deps.rover_state.visible_objects:
                if object_name.lower() in obj.name.lower():
                    return f"Yes, {obj.name} is visible at heading {obj.heading:.1f}° (confidence: {obj.confidence:.2f})"
            return f"No, {object_name} is not currently visible"
        
        @self.agent.tool
        async def turn_to_object(ctx: RunContext[ExecutiveDeps], object_name: str) -> str:
            """
            Turn the rover to face a visible object.
            
            Args:
                object_name: The object to turn towards
            
            Returns:
                Status message
            """
            for obj in ctx.deps.rover_state.visible_objects:
                if object_name.lower() in obj.name.lower():
                    # Calculate rotation needed
                    target_heading = (ctx.deps.rover_state.heading + obj.heading) % 360
                    direction = "left" if obj.heading < 0 else "right"
                    degrees = abs(obj.heading)
                    
                    # Send command to cortex
                    ctx.deps.cortex.execute_plan([
                        {'action': 'rotate', 'direction': direction, 'degrees': degrees}
                    ])
                    
                    return f"Turning {direction} {degrees:.1f}° to face {obj.name}"
            
            return f"{object_name} is not visible, cannot turn to it"
        
        @self.agent.tool
        async def move_direction(
            ctx: RunContext[ExecutiveDeps], 
            direction: str, 
            distance: float
        ) -> str:
            """
            Move the rover in a direction for a specified distance.
            
            Args:
                direction: 'forward', 'backward', 'left', or 'right'
                distance: Distance to move in cm
            
            Returns:
                Status message
            """
            action = None
            if direction == 'forward':
                action = {'action': 'move_forward', 'distance': distance}
            elif direction == 'backward':
                action = {'action': 'move_backward', 'distance': distance}
            else:
                return f"Direction '{direction}' not yet implemented"
            
            if action:
                ctx.deps.cortex.execute_plan([action])
                return f"Moving {direction} for {distance}cm"
            
            return "Invalid direction"
        
        @self.agent.tool
        async def execute_movement_sequence(
            ctx: RunContext[ExecutiveDeps],
            plan_description: str
        ) -> str:
            """
            Execute a sequence of movement actions. Use this when you need to
            perform multiple movements as part of a plan.
            
            Args:
                plan_description: Description of the movement sequence (for logging)
            
            Returns:
                Status message
            """
            # For now, this is a placeholder
            # In a real implementation, the LLM would provide structured plan data
            ctx.deps.high_level_state.plan = plan_description
            ctx.deps.high_level_state.mode = RoverMode.ACTING
            
            return f"Plan set: {plan_description}. Awaiting detailed movement commands."
        
        @self.agent.tool
        async def get_current_heading(ctx: RunContext[ExecutiveDeps]) -> str:
            """
            Get the rover's current heading.
            
            Returns:
                Current heading in degrees
            """
            return f"Current heading is {ctx.deps.rover_state.heading:.1f}°"
        
        @self.agent.tool
        async def get_obstacle_distance(ctx: RunContext[ExecutiveDeps]) -> str:
            """
            Get the distance to the nearest obstacle in front of the rover.
            
            Returns:
                Distance in cm
            """
            dist = ctx.deps.rover_state.distance_to_obstacle
            return f"Distance to nearest obstacle: {dist:.1f}cm"
        
        @self.agent.tool
        async def update_goal(ctx: RunContext[ExecutiveDeps], goal: str) -> str:
            """
            Update the current goal that the rover is working towards.
            
            Args:
                goal: Description of the new goal
            
            Returns:
                Confirmation message
            """
            ctx.deps.high_level_state.current_goal = goal
            ctx.deps.high_level_state.mode = RoverMode.ACTING
            return f"Goal updated: {goal}"
    
    async def process_prompt(
        self, 
        prompt: str, 
        rover_state: RoverState,
        cortex: 'RoverCortex'
    ) -> str:
        """
        Process a user prompt and return a response.
        
        Args:
            prompt: User's input text
            rover_state: Current state of the rover
            cortex: Reference to the cortex for executing commands
        
        Returns:
            Agent's response text
        """
        # Create context with current state
        context_prompt = f"""
Current State:
- {self.high_level_state.get_summary()}
- {rover_state.get_summary()}

User prompt: {prompt}
"""
        
        # Run the agent
        deps = ExecutiveDeps(
            high_level_state=self.high_level_state,
            rover_state=rover_state,
            cortex=cortex
        )
        
        try:
            result = await self.agent.run(context_prompt, deps=deps)
            print(f"[ExecutiveAgent] LLM response: {result}")
            return result.data
        except Exception as e:
            return f"Error processing prompt: {str(e)}"
    
    def handle_obstacle_event(self, distance: float) -> str:
        """
        Handle an obstacle detection event from the cortex.
        
        Args:
            distance: Distance to the obstacle
        
        Returns:
            Response message
        """
        response = f"Obstacle detected at {distance:.1f}cm. Stopped to avoid collision."
        self.high_level_state.mode = RoverMode.STANDBY
        return response
    
    def handle_plan_complete(self) -> str:
        """
        Handle plan completion event from the cortex.
        
        Returns:
            Response message
        """
        response = "Plan completed successfully."
        self.high_level_state.mode = RoverMode.STANDBY
        return response
