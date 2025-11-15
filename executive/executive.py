"""
Executive Agent - High-level planning and decision making.

This module uses an LLM to interpret user commands, create plans,
and respond to queries about the rover's state and environment.
"""

from typing import Optional
from pydantic_ai import Agent, RunContext, CallDeferred, DeferredToolRequests
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from state import HighLevelState, RoverState, MovementInstruction
from dataclasses import dataclass
from cortex import RoverCortex

EXEC_MODEL="Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M"

EXEC_PROMPT="""
You are the executive controller for a small mobile rover droid robot called Marvin.

You can move, answer questions about the environment, as well as answer general knowledge questions. 

When responding to user questions keep answers concise and simple so they can be 
presented as audio.

Use the tools available to you to perform actions and gather information.
"""

@dataclass
class ExecutiveDeps:
    """Dependencies injected into the agent context."""
    high_level_state: HighLevelState
    cortex: RoverCortex

class Executive:

    def __init__(self, cortex: RoverCortex):
        self.cortex = cortex
    
        self.exec_model = OpenAIModel(EXEC_MODEL, provider = OpenAIProvider(
            base_url="http://localhost:8080/v1",
            api_key="dummy-key"
        ))

        self.high_level_state = HighLevelState()

        self.exec_agent = Agent(
            self.exec_model,
            deps_type=ExecutiveDeps,
            instructions=EXEC_PROMPT,
            output_type=[str, DeferredToolRequests]
        )

        self._register_tools()

    def _register_tools(self):

        @self.exec_agent.tool
        def rover_status(ctx: RunContext[ExecutiveDeps]) -> str:
            """Get a summary of the current rover state."""
            return f"Rover is {ctx.deps.high_level_state.mode.value}: {ctx.deps.cortex.state.get_summary()}"

        @self.exec_agent.tool
        def move(ctx: RunContext[ExecutiveDeps], instruction: MovementInstruction):
            """Move in the direction and distanace given by the instruction.

               Args:
                    instruction: The direction and distance to move.
            """
            messages = ctx.messages
            def callback(i: MovementInstruction):
                print(f"[Executive] Completed movement: {i.direction} {i.value}, returning to exec agent")
                self.exec_agent.run(message_history=messages, deps=ctx.deps, deferred_tool_results=f"Completed movement: {i.direction} {i.value}")
            ctx.deps.cortex.start_movement(instruction, callback=callback)
            raise CallDeferred

    async def process_prompt(
        self, 
        prompt: str, 
    ) -> str:
        """
        Process a user prompt and return a response.
        
        Args:
            prompt: User's input text
        
        Returns:
            Agent's response text
        """
        # Create context with current state
        deps = ExecutiveDeps(
            high_level_state=self.high_level_state,
            cortex=self.cortex
        )
        
        try:
            result = await self.exec_agent.run(prompt, deps=deps)

            if isinstance(result.output, DeferredToolRequests):
                return "moving"
            else:
                print(f"[ExecutiveAgent] LLM response: {result}")
                return result.output
        except Exception as e:
            return f"Error processing prompt: {str(e)}"
