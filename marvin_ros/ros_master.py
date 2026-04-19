from controllers.eyes import Eyes
import asyncio
import time
from src.speech.audio_player import AudioPlayer
from src.speech.vad_capture import VADCapture
import roslibpy
import roslibpy.ros1.actionlib
import argparse
    
class EyesServer:
    def __init__(self, client):
        self.client = client
        self.eyes = Eyes()
        self.server = roslibpy.Topic(client, '/marvin/eyes', 'robot_msg/Eyes')

    async def start(self):
        asyncio.create_task(self.eyes.run())
        self.server.subscribe(self.execute)

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

    def event_reaction(self, event: str):
        if event == 'vad/start':
            self.eyes.set_awake(True)
            self.eyes.set_wide_eyes(True)
        elif event == 'vad/end':
            self.eyes.set_wide_eyes(False)
        elif event == 'sleep':
            self.eyes.set_awake(False)
    
async def main(args=None):
    parser = argparse.ArgumentParser(description='ROS2 Marvin Nodes')
    parser.add_argument('--ros_host', type=str, default='minimax', help='Choose ROS host: minimax or main')
    args = parser.parse_args()

    while True:
        try:
            if args.ros_host == 'minimax':
                print("Connecting to minimax ROS host...")
                client = roslibpy.Ros(host='192.168.178.90', port=9090)
            else:
                print("Connecting to main ROS host...")
                client = roslibpy.Ros(host='192.168.178.62', port=9090)
            client.run()
            break
        except Exception as e:
            print(f"Error connecting to ROS host: {e}, retry in 5 seconds...")
            await asyncio.sleep(5)

    try:
        # Audio capture and playback setup
        capture = VADCapture(client, topic='audio_stream')
        player = AudioPlayer()
        listener = roslibpy.Topic(client, '/speech_stream', 'audio_msg/Audio')
        listener.subscribe(lambda message: player.play_message(message))

        # Eye controller
        eye_server = EyesServer(client)
        asyncio.create_task(eye_server.start())

        # Event handling
        events_listener = roslibpy.Topic(client, '/events', 'std_msgs/String')
        def event_callback(message):
            msg = message['data'] if 'data' in message else str(message)
            print(f"Received event: {msg}")
            eye_server.event_reaction(msg)
            if msg == 'vad/start':
                print("Stopping player")
                player.stop()
            
        events_listener.subscribe(event_callback)

        while True:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Shutting down audio capture...')
    finally:
        capture.cleanup()
        player.cleanup()
        client.terminate()

if __name__ == "__main__":
    asyncio.run(main())
