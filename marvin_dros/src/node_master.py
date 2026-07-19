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

class MotorServer(Node):
    def __init__(self, bus, topic="/marvin/motor"):
        super().__init__(bus)
        self.motor_controller = MotorController()
        self.topic = topic
        self.subscribe_event(self.topic)
        self.subscribe_event("/events", self.event_handler)

    async def start_controller(self, lock):
        print("Starting BLE connection to motor base in background")
        asyncio.create_task(self.motor_controller.run(lock))

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

class NeckServer(Node):
    def __init__(self, bus, topic="/marvin/neck"):
        super().__init__(bus)
        self.neck_controller = Neck()
        self.topic = topic
        self.subscribe_event(self.topic)

    def process(self, message):
        try:
            request = NeckControlMessage.model_validate(message)
            print("Neck server received goal:", request)
            self.neck_controller.set_neck(tilt=request.tilt, pan=request.pan, speed=request.speed)
            self.publish("/events", {"type": "neck", "message": f"set neck: pan={request.pan}, tilt={request.tilt}, speed={request.speed}"})
        except Exception as e:
            print("Error processing neck message:", e)

async def main():
    parser = argparse.ArgumentParser(description="Marvin Node Master")
    parser.add_argument('--audio_device', type=str, default='Jabra', help='Audio output device name')
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    args = parser.parse_args()

    # Set default topics
    eyes_topic = "/marvin/eyes"
    motor_topic = "/marvin/motor"
    neck_topic = "/marvin/neck"

    hub_url = "http://minimax.local:5000" if args.host == 'minimax' else "http://next.local:5000"
    bus = Bus(ClientTransport(hub_url))

    eyes_server = EyesServer(bus, topic=eyes_topic)
    motor_server = MotorServer(bus, topic=motor_topic)
    neck_server = NeckServer(bus, topic=neck_topic)
    vad_capture = VADCapture(bus)
    audio_player = AudioPlayer(bus, topic='/speech_stream', device_name=args.audio_device)

    bus.start()
    try:
        async with asyncio.TaskGroup() as tg:
            lock = asyncio.Lock()  # Used to synchronize BLE connection setup when using multiple BLE connections
            task1 = tg.create_task(eyes_server.start_controller())
            task2 = tg.create_task(motor_server.start_controller(lock))
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print("Error:", e)
    finally:
        bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
