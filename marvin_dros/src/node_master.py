# Master for all nodes on Marvin which connect as a client to the DROS hub.
import argparse
import asyncio

from dros import Bus, ClientTransport, Node

from controllers.eyes import Eyes
from controllers.motor_control import MotorController
from controllers.neck import Neck
from messages.robot import EventMessage, EyeMessage, MotorControlMessage, NeckControlMessage
from speech.audio_player import AudioPlayer
from speech.vad_capture import VADCapture
from controllers.camera import Camera
from controllers.dist_heading_sensor import DistanceHeadingMonitor

class EyesServer(Node):
    def __init__(self, bus, topic="/marvin/eyes"):
        super().__init__(bus)
        self.eyes = Eyes()
        self.topic = topic
        self.subscribe_event(self.topic)
        self.subscribe_event("/events", self.event_reaction)

    async def start_controller(self):
        return await self.eyes.run()

    def process(self, message):
        try:
            request = EyeMessage.model_validate(message)
            print("Eye server received goal:", request)
            self.eyes.set_awake(request.open)
            self.eyes.set_wide_eyes(request.wide)
            self.eyes.set_eyes_at(request.x)
            self.publish("/events", {"type": "eyes", "message": f"set eyes: open={request.open}, wide={request.wide}, x={request.x}"})
        except Exception as e:
            print("Error processing eye message:", e)

    def event_reaction(self, message: dict):
        event = EventMessage.model_validate(message)
        if event.type == 'vad' and event.message == 'voice start':
            self.eyes.set_awake(True)
            self.eyes.set_wide_eyes(True)
        elif event.type == 'vad' and event.message == 'voice end':
            self.eyes.set_wide_eyes(False)
        elif event.message == 'sleep':
            self.eyes.set_awake(False)

class DistanceHeadingServer(Node):
    def __init__(self, bus, topic="/marvin/dist_heading", divisor=1):
        super().__init__(bus)
        self.sensor = DistanceHeadingMonitor()
        self.topic = topic
        self.divisor = divisor
        self.counter = 0
        self.sensor.add_callback(self.publish_sensor_data)

    async def start_controller(self, lock):
        print("Starting BLE connection to distance and heading sensor in background")
        asyncio.create_task(self.sensor.run(lock))

    def publish_sensor_data(self, dist, heading, pitch):
        self.counter += 1
        if self.counter % self.divisor == 0:
            self.publish(self.topic, {"dist": dist, "heading": heading, "pitch": pitch})

class MotorServer(Node):
    def __init__(self, bus, topic="/marvin/motor", interval=0.05):
        super().__init__(bus, interval=interval)
        self.motor_controller = MotorController()
        self.topic = topic
        self.subscribe_event(self.topic)
        self.subscribe_event("/events", self.event_handler)
        self.was_moving = False  # Track if the motor was moving in the last tick
        self._is_moving_cached = False  # Cached result of async is_moving(), updated by background task

    async def start_controller(self, lock):
        print("Starting BLE connection to motor base in background")
        asyncio.create_task(self.motor_controller.run(lock))
        asyncio.create_task(self._poll_is_moving())

    async def _poll_is_moving(self):
        # Bridges the async motor_controller.is_moving() into a value tick() can read synchronously.
        while True:
            self._is_moving_cached = await self.motor_controller.is_moving()
            await asyncio.sleep(0.05)

    def process(self, message):
        try:
            request = MotorControlMessage.model_validate(message)
            print("Motor server received goal:", request)
            self.motor_controller.send(speed=request.speed, dir=request.dir, dist=request.dist)
            self.publish("/events", {"type": "motor", "message": f"set motor: speed={request.speed}, dir={request.dir}, dist={request.dist}"})
        except Exception as e:
            print("Error processing motor message:", e)

    def event_handler(self, message: dict):
        try:
            event = EventMessage.model_validate(message)
            if event.message == 'stop':
                self.stop_motor()
        except Exception as e:
            print("Error processing event message:", e)

    def stop_motor(self):
        self.motor_controller.stop()

    def tick(self):
        if self._is_moving_cached:
            if not self.was_moving:
                self.publish("/events", {"type": "motor", "message": "moving start"})
                self.was_moving = True
        else:
            if self.was_moving:
                self.publish("/events", {"type": "motor", "message": "moving stop"})
                self.was_moving = False

class NeckServer(Node):
    def __init__(self, bus, topic="/marvin/neck", out_topic="/marvin/neck_position", interval=0.05):
        super().__init__(bus, interval=interval)
        self.neck_controller = Neck()
        self.topic = topic
        self.out_topic = out_topic
        self.subscribe_event(self.topic)

    def startup(self):
        self.neck_controller.set_neck(tilt=0, pan=0, speed=2000)

    def process(self, message):
        try:
            request = NeckControlMessage.model_validate(message)
            print("Neck server received goal:", request)
            self.neck_controller.set_neck(tilt=int(request.tilt), pan=int(request.pan), speed=int(request.speed))
            self.publish("/events", {"type": "neck", "message": f"set neck: pan={request.pan}, tilt={request.tilt}, speed={request.speed}"})
        except Exception as e:
            print("Error processing neck message:", e)

    def tick(self):
        tilt, pan = self.neck_controller.get_neck()
        self.publish(self.out_topic, {"tilt": tilt, "pan": pan})

class CameraServer(Node):
    def __init__(self, bus, topic="/marvin/camera", rate_divisor=1):
        super().__init__(bus)
        self.camera_controller = Camera()
        self.topic = topic
        self.rate_divisor = rate_divisor

    def startup(self):
        self.camera_controller.set_callback(self.publish_frame, divisor=self.rate_divisor)
        self.camera_controller.start_thread()
        print("Camera started, publishing frames to topic:", self.topic)

    def shutdown(self):
        self.camera_controller.stop()
        print("Camera stopped.")

    def publish_frame(self, frame: bytes):
        self.publish(self.topic, {"format": "image/jpeg", "data": frame})

async def main_loop():
    parser = argparse.ArgumentParser(description="Marvin Node Master")
#    parser.add_argument('--audio_device', type=str, default='Jabra', help='Audio output device name')
    parser.add_argument('--audio_in', type=str, default='respeaker', help='Audio input device name')
    parser.add_argument('--audio_out', type=str, default='UACDemo', help='Audio output device name')
    parser.add_argument('--audio_out_rate', type=int, default=48000, help='Audio output sample rate in Hz (device native rate)')
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    args = parser.parse_args()

    # Set default topics
    eyes_topic = "/marvin/eyes"
    motor_topic = "/marvin/motor"
    neck_topic = "/marvin/neck"

    hub_url = "http://minisforum.local:5000" if args.host == 'minimax' else "http://next.local:5000"
    bus = Bus(ClientTransport(hub_url))

    eyes_server = EyesServer(bus, topic=eyes_topic)
    motor_server = MotorServer(bus, topic=motor_topic)
    neck_server = NeckServer(bus, topic=neck_topic)
    dist_heading_server = DistanceHeadingServer(bus, topic="/marvin/dist_heading", divisor=3)
    vad_capture = VADCapture(bus, device_name=args.audio_in, topic='/audio_stream')
    audio_player = AudioPlayer(bus, topic='/speech_stream', device_name=args.audio_out, output_sample_rate=args.audio_out_rate)
    camera_server = CameraServer(bus, topic='/marvin/camera', rate_divisor=1)

    bus.start()
    try:
        async with asyncio.TaskGroup() as tg:
            lock = asyncio.Lock()  # Used to synchronize BLE connection setup when using multiple BLE connections
            task1 = tg.create_task(eyes_server.start_controller())
            task2 = tg.create_task(motor_server.start_controller(lock))
            task3 = tg.create_task(dist_heading_server.start_controller(lock))
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print("Error:", e)
    finally:
        bus.stop()

def main():
    asyncio.run(main_loop())

if __name__ == "__main__":
    main()
