# Collection of LangChain-compatible tools for driving Marvin
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from motor_control import move, is_moving, get_heading
import requests
import base64

@tool
def robot_move(direction: str, distance: int) -> str:
    """
    Move the robot in the specified direction for the given distance.
    If the robot reaches an obstacle, it will stop moving.
    If there is some problem executing the command, returns an explanation prefixed by 'failed'

    Args:
        direction: Direction to move ('forward', 'backward', 'left', 'right')
        distance: Distance to move in centimeters

    Returns:
        str: Confirmation message one of 'ok', 'failed ...' or 'blocked'
    """

    match direction:
        case "forward":
            dir_code = "f"
        case "backward":
            dir_code = "b"
        case "left":
            dir_code = "sl"
        case "right":
            dir_code = "sr"
        case _:
            return f"failed: unknown direction '{direction}'"
    move(dir=dir_code, speed=60, distance=distance, sync=True)
    return "ok"

@tool
def robot_turn(angle: int) -> str:
    """
    Turn the robot by the specified angle in degrees.
    Positive angles turn right, negative angles turn left.
    If there is some problem executing the command, returns an explanation prefixed by 'failed'

    Args:
        angle: Angle to turn in degrees

    Returns:
        str: Confirmation message one of 'ok' or 'failed ...'
    """

    if angle > 0:
        dir_code = "rr"
    else:
        dir_code = "rl"
    move(dir=dir_code, speed=60, distance=abs(angle)//4, sync=True)
    return "ok"

@tool
def robot_get_camera_image() -> str:
    """
    Capture an image from the robot's camera.
    
    Returns:
        str: Base64-encoded data URL of the captured image, or error message starting with 'failed'
    """
    
    try:
        response = requests.get("http://marvin.local:8080/still", timeout=10)
        response.raise_for_status()
        
        # Encode image as base64
        image_b64 = base64.b64encode(response.content).decode('utf-8')
        
        # Return as data URL
        return f"data:image/png;base64,{image_b64}"  
    except requests.exceptions.RequestException as e:
        return f"failed: could not capture image - {str(e)}"
    except Exception as e:
        return f"failed: unexpected error - {str(e)}"


vllm = ChatOpenAI(
    model="ggml-org/gemma-3-4b-it-GGUF",
    # stream_usage=True,
    max_retries=2,
    api_key="",
    base_url="http://localhost:8090/v1",
    use_responses_api= False,
)


@tool
def describe_scene() -> str:
    """
    Capture an image from the robot's camera and describe the scene using an external vision API.
    
    Returns:
        str: Description of the scene, or error message starting with 'failed'
    """
    
#    image_data_url = robot_get_camera_image()
#    if image_data_url.startswith("failed"):
#        return image_data_url  # Propagate failure message   

    try:
        # Call external vision API to describe the image
        conversation = [
            SystemMessage("You are the vision expert of a small mobile droid called marvin. Please make your responses short and suitable for reading out loud."),
            HumanMessage(content=[
                {"type": "text", "text": "What do you see in this image from the front camera?"},
                {"type": "image_url", "image_url": {"url": "http://marvin.local:8080/still"}}
            ])
        ]
        response = vllm.invoke(conversation)
        return response.content
    except Exception as e:
        return f"failed: unexpected error - {str(e)}"
