from controllers.eyes import Eyes
import asyncio
import time
import roslibpy
import roslibpy.ros1.actionlib
import argparse
    
class EyesAction:
    def __init__(self, client):
        self.client = client
        self.eyes = Eyes()
        self.server = roslibpy.ros1.actionlib.SimpleActionServer(client, 'eyes_action', 'robot_msg/Eyes')

    async def start(self):
        asyncio.create_task(self.eyes.run())
        self.server.start(self.execute)

    def execute(self, goal):
        print("Received goal:", goal)
        if goal['awake']:
            self.eyes.set_awake(True)
        else:
            self.eyes.set_awake(False)

        if goal['wide']:
            self.eyes.set_wide_eyes(True)
        else:
            self.eyes.set_wide_eyes(False)

        self.eyes.set_eyes_at(goal['x'])
        self.server.set_succeeded({'acknowledged': True})
    
async def main(args=None):
    parser = argparse.ArgumentParser(description='ROS2 Marvin Nodes')
    parser.add_argument('--ros_host', type=str, default='minimax', help='Choose ROS host: minimax or main')
    args = parser.parse_args()

    if args.ros_host == 'minimax':
        client = roslibpy.Ros(host='192.168.178.90', port=9090)
    else:
        client = roslibpy.Ros(host='192.168.178.61', port=9090)
    client.run()

    try:
        # capture = VADCapture(client, topic='audio_stream')
        # player = AudioPlayer()

        # listener = roslibpy.Topic(client, '/speech_stream', 'audio_msg/Audio')
        # listener.subscribe(lambda message: player.play_message(message))
        eye_action_server = EyesAction(client)
        asyncio.create_task(eye_action_server.start())

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down audio capture...')
    finally:
#        capture.cleanup()
#        player.cleanup()
        client.terminate()

if __name__ == "__main__":
    asyncio.run(main())
