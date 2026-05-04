from controllers.eyes import Eyes
import asyncio
from messages.base import BaseNode, EventMessage
from messages.audio import AudioMessage
from speech.vad_capture import VADCapture
from speech.audio_player import AudioPlayer
import argparse

class EyesServer:
    def __init__(self, client: BaseNode):
        self.client = client
        self.eyes = Eyes()
        self.topic = "/marvin/eyes"
        client.handler(self.topic)(self.execute)

    async def run(self):
        await self.client.subscribe(self.topic)
        asyncio.create_task(self.eyes.run())

    def execute(self, goal):
        print("Eye server received goal:", goal)
        if goal['awake']:
            self.eyes.set_awake(True)
        else:
            self.eyes.set_awake(False)

        if goal['wide']:
            self.eyes.set_wide_eyes(True)
        else:
            self.eyes.set_wide_eyes(False)

        self.eyes.set_eyes_at(goal['x'])

    def event_reaction(self, event: EventMessage):
        if event.type == 'vad' and event.message == 'voice start':
            self.eyes.set_awake(True)
            self.eyes.set_wide_eyes(True)
        elif event.type == 'vad' and event.message == 'voice end':
            self.eyes.set_wide_eyes(False)
        elif event.message == 'sleep':
            self.eyes.set_awake(False)

async def main(args=None):
    parser = argparse.ArgumentParser(description='Marvin Nodes')
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    parser.add_argument('--audio-out', type=str, default='/audio_stream', help='Topic to publish audio to')
    parser.add_argument('--audio-in', type=str, default='/speech_stream', help='Topic to subscribe for audio input')
    args = parser.parse_args()

    hub_url = "http://minimax.local:5000" if args.host == 'minimax' else "http://next.local:5000"
    client = BaseNode(hub_url=hub_url, node_name="marvin")

    while not client.sio.connected:
        print(f"Connecting to hub at {hub_url}...")
        try:
            await client.sio.connect(hub_url)
            await client._connected.wait()
        except Exception as e:
            print("Failed to connect to hub, retrying")
            await asyncio.sleep(5)

    try:
        capture = VADCapture(client, topic=args.audio_out)
        player = AudioPlayer()
        eyes = EyesServer(client)

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
        client.handler("/events")(event_callback)
        await client.subscribe("/events")

        await asyncio.gather(
            capture.run(),
            eyes.run(),
            #client.run()
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Shutting down audio capture...')
    finally:
        capture.cleanup()
        await client.sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
