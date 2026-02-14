#!/usr/bin/env python3
from picamera2 import Picamera2
from libcamera import Transform, controls
from copy import copy
import cv2
import asyncio
import time
import sys
import threading
from typing import Iterator
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from contextlib import asynccontextmanager
import zlib
from motor_control import MotorController
from dist_heading_sensor import DistanceHeadingMonitor
from actions import rotate_to_heading, move_along_heading
from eyes import Eyes
from st3215 import ST3215
import os

# Configuration
HOST = "0.0.0.0"  # Allow access from any device on the network
PORT = 80
JPEG_QUALITY = 70  # 0-100, higher is better quality but larger size

# Global variable for camera and frame handling
camera = None
frame_lock = threading.Lock()
latest_lores = None
latest_frame = None
stream_active = True


def initialize_camera():
    """Initialize the camera."""
    global camera
    try:
        camera = Picamera2()
        config = camera.create_still_configuration(
            buffer_count=2, transform=Transform(vflip=True, hflip=True)
        )
        config["main"] = {"format": "RGB888", "size": (1024, 768), "preserve_ar": True}
        config["lores"] = {"format": "RGB888", "size": (320, 240), "preserve_ar": True}
        camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        camera.configure(config)

        # To do, set up sizes and lores
        camera.start()
        time.sleep(1)
        print("Camera initialized successfully.")
        return True
    except Exception as e:
        print(f"Error initializing camera: {e}")
        return False


def capture_frames():
    """Continuously capture frames from the camera."""
    global latest_lores, latest_frame, stream_active

    while stream_active:
        (main, lores), metadata = camera.capture_arrays(["main", "lores"])
        if lores is not None:
            # print(f"Captured frame: {lores.shape}")
            with frame_lock:
                latest_frame = copy(main)
                latest_lores = copy(lores)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    # Clean up the ML models and release the resources
    await shutdown()


app = FastAPI(title="Pi Rover Camera Server", lifespan=lifespan)

# Camera block

def generate_frames() -> Iterator[bytes]:
    """Generate frames for the multipart response."""
    while True:
        # Wait until a frame is available
        if latest_lores is None:
            time.sleep(0.01)
            continue

        # Get the current frame
        with frame_lock:
            ret, jpeg = cv2.imencode(
                ".jpg", latest_lores, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            )
            if ret:
                # Convert the frame to bytes
                frame_data = jpeg.tobytes()

        # Yield the frame in the format expected by multipart responses
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n")


@app.get("/stream")
async def stream():
    """Stream the camera feed as multipart/x-mixed-replace content."""
    return StreamingResponse(
        generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/still")
async def still():
    """Single high-res image."""
    return await response_for(latest_frame)


@app.get("/still-lores")
async def still_lores():
    """Single log-res image."""
    return await response_for(latest_lores)


@app.get("/still-565")
async def still_565():
    frame = latest_lores
    if frame is None:
        return Response(content="No image available", media_type="text/plain")

    with frame_lock:
        # Convert the frame to RGB565 format
        rgb565_frame = frame.astype("uint16")
        # Implicit RGB to BGR via swapping suffixes instead of using cvtColor
        rgb565_frame = (
            ((rgb565_frame[:, :, 2] >> 3) << 11)
            | ((rgb565_frame[:, :, 1] >> 2) << 5)
            | (rgb565_frame[:, :, 0] >> 3)
        )
        # Swap the bytes to big-endian format
        rgb565_bytes = rgb565_frame.byteswap().tobytes()
        # Compress the RGB565 data using zlib
        compressed_data = zlib.compress(rgb565_bytes)
    return Response(content=compressed_data, media_type="application/octet-stream")


async def response_for(frame):
    if frame is None:
        return Response(content="No image available", media_type="text/plain")

    with frame_lock:
        ret, jpeg = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
        )
        if ret:
            return Response(content=jpeg.tobytes(), media_type="image/jpeg")
        else:
            return Response(content="Failed to encode image", media_type="text/plain")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a simple HTML page with the stream embedded."""
    html_content = """
    <html>
    <head>
        <title>Pi Rover Camera Stream</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            h1 {
                color: #333;
            }
            .stream-container {
                margin-top: 20px;
                overflow: hidden;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            img {
                max-width: 100%;
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Pi Rover Camera Stream</h1>
            <div class="stream-container">
                <img src="/stream" alt="Pi Rover Camera Stream" />
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Motor controller block

motor = MotorController()

@app.post("/set-motor")
async def set_motor(s: int, dir: str, dist: int = None, sync: bool = False):
    """
    Set the speed, direction and optional distance of the motor
    Example: POST /set-motor?s=50&dir=f&dist=5
    """
    try:
        if motor.is_connected:
            command = "s" if dir == "s" else f"{s}{dir}"
            if dist is not None:
                command += f"{dist}"
            else:
                command += 99
            motor.queue.append(command)
            if sync:
                await asyncio.sleep(0.05)
                while await motor.is_moving():
                    await asyncio.sleep(0.1)
            return {
                "status": "success",
                "message": f"Motor set to dir={dir}, speed={s}, dist={dist}",
            }
        else:
            return {"status": "error", "message": "Motor base BLE connection not ready"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/is-moving")
async def is_moving():
    """Check if the motor is currently moving."""
    try:
        if motor.is_connected:
            moving = await motor.is_moving()
            return {"status": "success", "moving": moving}
        else:
            return {"status": "error", "message": "Motor base BLE connection not ready"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Sensor block

sensor = DistanceHeadingMonitor()

@app.get("/sensor-status")
async def sensor_status():
    """Get the current sensor status."""
    try:
        if sensor.is_connected:
            status = {
                "heading": sensor.heading,
                "pitch": sensor.pitch,
                "distance" : sensor.dist,
            }
            return {"status": "success", "sensor_status": status}
        else:
            return {"status": "error", "message": "Sensor connection not ready"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/turn-to-heading")
async def turn_to_heading(heading: int, sync: bool = False):
    if heading < 0 or heading > 255:
        return {"status": "error", "message": "Heading must be between 0 and 255"}
    if not sensor.is_connected:
        return {"status": "error", "message": "Sensor connection not ready"}
    if not motor.is_connected:
        return {"status": "error", "message": "Motor base BLE connection not ready"}
    task = asyncio.create_task(rotate_to_heading(heading, sensor, motor))
    if sync:
        await task
        return {"status": "success", "message": f"Turning to heading {heading}"}
    return {"status": "turning"}

@app.post("/move-along-heading")
async def move_heading(dist: int, heading: int, sync: bool = False):
    if not sensor.is_connected:
        return {"status": "error", "message": "Sensor connection not ready"}
    if not motor.is_connected:
        return {"status": "error", "message": "Motor base BLE connection not ready"}
    task = asyncio.create_task(move_along_heading(dist, heading, sensor, motor))
    if sync:
        await task
        return {"status": "success", "message": f"Moving along heading {heading} for {dist} units"}
    return {"status": "moving"}

# Eyes controller block

eyes = Eyes()

@app.post("/set-eyes")
async def set_eyes(awake: bool = True, wide: bool = False, x: int = 0):
    """
    Set the eyes state and position.
    awake: true/false default true
    wide: true/false default false
    x: offset of eyes between -100 and 100
    """
    try:
        eyes.set_awake(awake)
        if (awake):
            eyes.set_wide_eyes(wide)
            eyes.set_eyes_at(x)
        return {"status": "success", "message": f"Eyes set to awake={awake}, wide={wide}, x={x}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Neck block

servo = ST3215('/dev/ttyACM0')

TILT_RANGE = 250
PAN_RANGE = 750

@app.post("/set-neck")
async def set_neck(tilt: int, pan: int, speed: int =2000):
    """
    Set the neck tilt and pan angles.
    tilt: range -100 to 100
    pan: range -100 to 100
    speed: movement speed (default 2000)
    """
    try:
        if tilt < -100 or tilt > 100 or pan < -100 or pan > 100:
            return {"status": "error", "message": "Tilt and pan must be between -100 and 100"}
        tilt = int(tilt * TILT_RANGE / 100) + 2048
        pan = int(pan * PAN_RANGE / 100) + 2048
        servo.MoveTo(0, tilt, speed=speed, acc=50, wait=False)
        servo.MoveTo(1, pan, speed=speed, acc=50, wait=False)
        return {"status": "success", "message": f"Neck set to tilt={tilt}, pan={pan}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/get-neck")
async def get_neck():
    """
    Get the current neck tilt and pan angles.
    """
    try:
        tilt_pos = servo.ReadPosition(0)
        pan_pos = servo.ReadPosition(1)
        tilt = int((tilt_pos - 2048) * 100 / TILT_RANGE)
        pan = int((pan_pos - 2048) * 100 / PAN_RANGE)
        return {"status": "success", "tilt": tilt, "pan": pan}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/shutdown")
async def shutdown_endpoint():
    """Shutdown the robot server."""
    await shutdown()
    # Stop the server
    os.system("sudo shutdown now")

async def startup():
    """Initialize camera and start frame capture thread on startup."""
    if not initialize_camera():
        print("Failed to initialize camera. The stream will not work.")
        return
    
    # Start the frame capture thread
    capture_thread = threading.Thread(target=capture_frames)
    capture_thread.daemon = True
    capture_thread.start()
    print("Camera capture thread started.")
    # Start BLE connection listener
    lock = asyncio.Lock()
    print("Starting BLE connection to motor base in background")
    asyncio.create_task(motor.run(lock))
    # Start sensor listener
    print("Starting sensor listener")
    asyncio.create_task(sensor.run(lock))
    # Eyes controller
    asyncio.create_task(eyes.run())
    eyes.set_awake(True)


async def shutdown():
    """Release camera resources on shutdown."""
    global stream_active
    stream_active = False
    if camera is not None:
        camera.stop()
        print("Camera stopped.")
    if motor.is_connected:
        motor.shutdown()


def main():
    """Main function to start the FastAPI server with Uvicorn."""
    try:
        print(f"Starting server at http://{HOST}:{PORT}")
        print("Press Ctrl+C to stop the server")
        uvicorn.run(app, host=HOST, port=PORT)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
