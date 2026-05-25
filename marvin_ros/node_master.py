import argparse
import asyncio
import time

from controllers.camera import Camera
from controllers.eyes import Eyes
from controllers.motor_control import MotorController
from controllers.neck import Neck
from messages.audio import AudioMessage
from messages.base import BaseNode, EventMessage
from messages.robot import EyeMessage, MotorControlMessage, NeckControlMessage
from speech.audio_player import AudioPlayer
from speech.vad_capture import VADCapture


class EyesServer:
    def __init__(self, client: BaseNode):
        self.client = client
        self.eyes = Eyes()
        self.topic = "/marvin/eyes"
        client.handler(self.topic)(self.execute)

    async def run(self):
        await self.client.subscribe(self.topic)
        asyncio.create_task(self.eyes.run())

    async def execute(self, msg: dict):
        try:
            request = EyeMessage(**msg)
            print("Eye server received goal:", request)
            self.eyes.set_awake(request.open)
            self.eyes.set_wide_eyes(request.wide)
            self.eyes.set_eyes_at(request.x)
        except Exception as e:
            print("Error processing eye message:", e)

    def event_reaction(self, event: EventMessage):
        if event.type == 'vad' and event.message == 'voice start':
            self.eyes.set_awake(True)
            self.eyes.set_wide_eyes(True)
        elif event.type == 'vad' and event.message == 'voice end':
            self.eyes.set_wide_eyes(False)
        elif event.message == 'sleep':
            self.eyes.set_awake(False)

class MotorServer:
    def __init__(self, client: BaseNode):
        self.client = client
        self.motor_controller = MotorController()
        self.topic = "/marvin/motor"
        client.handler(self.topic)(self.execute)

    async def run(self, lock):
        print("Starting BLE connection to motor base in background")
        asyncio.create_task(self.motor_controller.run(lock))
        await self.client.subscribe(self.topic)

    async def execute(self, msg: dict):
        try:
            motor_msg = MotorControlMessage(**msg)
            print("Motor server received goal:", motor_msg)
            self.motor_controller.send(speed=motor_msg.speed, dir=motor_msg.dir, dist=motor_msg.dist)
        except Exception as e:
            print("Error processing motor message:", e)

    def stop(self):
        self.motor_controller.send(speed=0, dir='s')
        

async def main(args=None):
    parser = argparse.ArgumentParser(description='Marvin Nodes')
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    parser.add_argument('--audio-out', type=str, default='/audio_stream', help='Topic to publish audio to')
    parser.add_argument('--audio-in', type=str, default='/speech_stream', help='Topic to subscribe for audio input')
    args = parser.parse_args()

    hub_url = "http://minimax.local:5000" if args.host == 'minimax' else "http://next.local:5000"
    client = BaseNode(hub_url=hub_url, node_name="marvin")

    # Test camera
    camera = Camera()
    camera.start_thread()

    while not client.sio.connected:
        print(f"Connecting to hub at {hub_url}...")
        try:
            await client.sio.connect(hub_url)
            await client._connected.wait()
        except Exception as e:
            print("Failed to connect to hub, retrying")
            await asyncio.sleep(5)

    capture = VADCapture(client, topic=args.audio_out)
    try:
        player = AudioPlayer()
        eyes = EyesServer(client)
        neck = Neck()
        motor = MotorServer(client)

        # Set up handler for incoming audio messages
        async def audio_callback(msg: dict):
            audio_message = AudioMessage(**msg)
            player.play_message(audio_message)
        client.handler(args.audio_in)(audio_callback)
        await client.subscribe(args.audio_in)

        # Events capture
        async def event_callback(message: dict):
            event = EventMessage(**message)
            eyes.event_reaction(event)
            if (event.message == 'stop'):
                player.stop()
                motor.stop()            
        client.handler("/events")(event_callback)
        await client.subscribe("/events")

        # Neck control handler
        async def neck_callback(msg: dict):
            neck_msg = NeckControlMessage(**msg)
            neck.set_neck(tilt=neck_msg.tilt, pan=neck_msg.pan, speed=neck_msg.speed)
        client.handler("/marvin/neck")(neck_callback)
        await client.subscribe("/marvin/neck")

        # Camera RPC
        # TODO

        lock = asyncio.Lock()  # Used to synchronize BLE connection setup when using multiple BLE connections
        await asyncio.gather(
            capture.run(),
            eyes.run(),
            motor.run(lock),
            #client.run()
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Shutting down audio capture...')
    finally:
        if capture is not None:
            capture.cleanup()
        await client.sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
