# Marvin Executive System

An intelligent rover control system that uses LLM-based agents for high-level planning and decision-making.

## Overview

This system controls a mobile rover with mecanum wheels, camera, and sensors through a two-layer architecture:

- **Executive Agent**: High-level planning and decision-making using an LLM (via pydantic-ai)
- **Cortex**: Low-level control, state monitoring, and obstacle detection

## Components

### State Models (`state.py`)
Defines shared state structures:
- `RoverState`: Low-level rover status (heading, movement, obstacles, visible objects)
- `HighLevelState`: Executive-level state (mode, goals, plans)

### Cortex (`cortex.py`)
Low-level rover control:
- Monitors sensors every 200ms
- Executes movement plans
- Stops automatically when obstacles are < 10cm away
- Uses dummy interface (replace with actual camera_server API later)

### Executive Agent (`executive.py`)
LLM-powered decision-making with tools:
- `check_object_visible`: Check if named object is in view
- `turn_to_object`: Rotate to face a visible object
- `move_direction`: Move forward/backward for a distance
- `get_current_heading`: Query current compass heading
- `get_obstacle_distance`: Check distance to nearest obstacle
- `update_goal`: Set new high-level goal

### Dialog Handler (`dialog.py`)
User interaction interface:
- Processes text commands from terminal
- Special commands: `stop`, `status`, `quit`/`exit`
- Coordinates between executive and cortex

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have an LLM running with OpenAI-compatible API (e.g., llama.cpp server):
```bash
# Example: llama.cpp server on port 8080
./server -m model.gguf --port 8080
```

## Usage

Run the system:
```bash
python main.py
```

With custom LLM settings:
```bash
python main.py --model-url http://localhost:8080/v1 --model-name my-model
```

### Commands

- Type natural language instructions (e.g., "turn left", "find the teddy bear")
- `stop` - Emergency stop the rover
- `status` - Show current system state
- `quit` or `exit` - Shutdown

### Example Tasks

From the design outline:
- "there's a teddy bear to your left, go up to it"
- "turn around and tell me what objects you see"
- "go up to the waste basket"
- "can you see a book? what is it called?"
- "explore this room and find a book and a bear"

## Current Implementation Status

✅ Core framework with state management
✅ Executive agent with pydantic-ai and tool definitions
✅ Cortex with dummy rover interface
✅ Dialog handler for user interaction
✅ Asynchronous control loops

🔄 Using dummy data for:
- Rover movement (simulated)
- Object detection (random dummy objects)
- Obstacle distance (simulated)

## Future Enhancements

1. **Replace dummy interface**: Connect to actual `../pi-master/camera_server.py`
2. **Vision integration**: Add real object detection using VLM
3. **Better planning**: More sophisticated movement sequences
4. **Odometry**: Track actual distance traveled
5. **Vision-language model**: Integrate VLM for visual understanding
6. **Persistent memory**: Save and recall previous interactions

## Architecture

```
┌─────────────┐
│   User      │
│   Input     │
└──────┬──────┘
       │
┌──────▼──────────┐
│  Dialog Handler │
└──────┬──────────┘
       │
┌──────▼────────────┐      ┌─────────────┐
│ Executive Agent   │◄─────┤  LLM API    │
│  (High Level)     │      │  (OpenAI)   │
└──────┬────────────┘      └─────────────┘
       │
       │ Plans/Commands
       │
┌──────▼──────────┐       ┌──────────────┐
│     Cortex      │◄──────┤  Rover API   │
│  (Low Level)    │       │ camera_server│
└─────────────────┘       └──────────────┘
       │
       │ Motor Control
       │
┌──────▼──────────┐
│  Physical Rover │
│  Sensors/Camera │
└─────────────────┘
```

## Notes

- The system runs two async loops: cortex control and dialog handling
- State updates happen every 200ms by default (configurable)
- Obstacle detection triggers automatic stops
- The framework is designed to be extended with real hardware interfaces
