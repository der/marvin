"""
Executive Agent - High-level planning and decision making.

This module uses an LLM to interpret user commands, create plans,
and respond to queries about the rover's state and environment.
"""

import asyncio
from typing import Any, Optional
from pydantic_ai import Agent, RunContext, CallDeferred, DeferredToolRequests, DeferredToolResults
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from base_types import HighLevelState, MovementInstruction, Prompt, UIOutput, ExecutiveBase, CortexBase
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


class Executive(ExecutiveBase):

    def __init__(self, cortex: CortexBase):
        self.cortex = cortex
        self.prompt_queue: list[Prompt] = []
        self.deferred_tool_requests = {}
        self.running = True
        self.message_history = []
    
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

    def set_output(self, out: UIOutput):
        """Set UI to use for reporting agent"""
        self.out = out

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
            self.record_deferred_tool_request(ctx)
            callback = lambda response: self.movement_completed(ctx.tool_call_id, response)
            print(f"[ExecutiveAgent] Scheduling movement: {instruction}")
            ctx.deps.cortex.start_movement(instruction, callback)
            raise CallDeferred

    def record_deferred_tool_request(self, ctx: RunContext[ExecutiveDeps]):
        self.deferred_tool_requests[ctx.tool_call_id] = ctx.messages

    def stop(self):
        self.deferred_tool_requests.clear()
        self.prompt_queue.clear()

    def enqueue_prompt(self, prompt: str):
        """Add a user prompt to the processing queue."""
        self.prompt_queue.append(Prompt(prompt=prompt))
    
    def movement_completed(self, call_id: str, results: Any):
        """Notify the executive that a movement instruction has completed."""
        self.prompt_queue.append(Prompt(prompt=results, deferred_call_id=call_id))

    async def run_next_prompt(self) -> Optional[str]:
        """Process the next prompt in the queue, if any."""
        if not self.prompt_queue:
            return None

        deps = ExecutiveDeps(
            high_level_state=self.high_level_state,
            cortex=self.cortex
        )

        next_prompt = self.prompt_queue.pop(0)

        if next_prompt.deferred_call_id:
            id = next_prompt.deferred_call_id
            if id in self.deferred_tool_requests:
                print(f"[ExecutiveAgent] Resuming deferred call ID: {id}")
                messages = self.deferred_tool_requests.pop(id)
                def_results = DeferredToolResults()
                def_results.calls[id] = next_prompt.prompt
                result = await self.exec_agent.run(message_history=messages, deferred_tool_results=def_results, deps=deps)
                # TODO trap poor results
                self.message_history.extend(result.new_messages())
                return "done"
            else:
                return f"Internal error: No deferred request found for call ID: {id}"
        else:
            try:
                print(f"[ExecutiveAgent] Processing prompt: {next_prompt.prompt}")
                result = await self.exec_agent.run(user_prompt=next_prompt.prompt, message_history=self.message_history, deps=deps)
                if isinstance(result.output, DeferredToolRequests):
                    return "moving"
                else:
                    print(f"[ExecutiveAgent] LLM response: {result}")
                    self.message_history.extend(result.new_messages())
                    return result.output
            except Exception as e:
                return f"Error processing prompt: {str(e)}"

    async def run(self):
        """Main control loop."""
        self.running = True
        print("[Executive] start executive loop")
        while self.running:
            if len(self.prompt_queue) > 0:
                response = await self.run_next_prompt()
                if response is not None:
                    self.out.respond_to_user(response)
            else:
                await asyncio.sleep(0.1)

    def quit(self):
        """Stop the control loop."""
        self.running = False
        self.cortex.quit()
