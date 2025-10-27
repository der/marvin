from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pprint import pprint
from robot_tools import robot_move, robot_turn, robot_get_camera_image, describe_scene
from langchain.agents.middleware import after_model, AgentState
from langgraph.runtime import Runtime
from typing import Any, Callable
import sys

#model_id = "geoffmunn/Qwen3-Coder-30B-A3B-Instruct"
#model_id = "ggml-org/gemma-3-4b-it-GGUF"
model_id = "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"

llm = ChatOpenAI(
    model=model_id,
    # stream_usage=True,
    max_retries=2,
    api_key="",
    base_url="http://localhost:8080/v1",
    use_responses_api= False,
)

@after_model(can_jump_to=["end"])
def log_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    last_message = state["messages"][-1]
    print(f"Agent: {last_message.content}")
    return None

agent = create_agent(
    model=llm,
    tools=[robot_move, robot_turn, describe_scene],
    middleware=[log_messages],
    system_prompt="You are Marvin, a helpful domestic robot droid. You can move and see what's in front of you. When asked to move plan out the sequence first carefully and then issue the more calls in the right sequence",
#    system_prompt="You are Marvin, a helpful domestic robot droid. You can move and see what's in front of you.",
).with_config({
    "recursion_limit": 50,
    "parallel_tool_calls": False
    })

def main():
    if len(sys.argv) != 2:
        print("Usage: python llm-test.py '<prompt>'")
        sys.exit(1)
    
    prompt = sys.argv[1]
    response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    pprint(response)

if __name__ == "__main__":
    response = main()
