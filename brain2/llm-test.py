from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pprint import pprint
from robot_tools import robot_move, robot_turn, robot_get_camera_image
from langchain.agents.middleware import after_model, AgentState
from langgraph.runtime import Runtime
from typing import Any, Callable

llm = ChatOpenAI(
    model="geoffmunn/Qwen3-Coder-30B-A3B-Instruct",
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
    tools=[robot_move, robot_turn, robot_get_camera_image],
    middleware=[log_messages],
#    system_prompt="You are Marvin, a helpful domestic robot droid. You can move and see what's in front of you. When asked to move plan out the sequence first carefully and then issue the more calls in the right sequence",
    system_prompt="You are Marvin, a helpful domestic robot droid. You can move and see what's in front of you.",
).with_config({
    "recursion_limit": 50,
    "parallel_tool_calls": False
    })

# Run the agent
response = agent.invoke(
#    {"messages": [{"role": "user", "content": "Move forward 100 centimeters, then turn right 90 degrees and move forward another 50 centimeters."}]}
#    {"messages": [{"role": "user", "content": "Move around a 20 cm square"}]}
#    {"messages": [{"role": "user", "content": "Move around a 20 cm square without turning by using left and right moves only."}]}
    {"messages": [{"role": "user", "content": "take a picture and describe what you see."}]}
)
pprint(response)
