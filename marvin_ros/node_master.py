from controllers.eyes import Eyes
import asyncio
from src.messages.base import BaseNode
from src.speech.audio_player import AudioPlayer
from src.speech.vad_capture import VADCapture
import argparse

async def main(args=None):
    parser = argparse.ArgumentParser(description='Marvin Nodes')
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    parser.add_argument('--topic', type=str, default='/audio_stream', help='Topic to publish audio to')
    args = parser.parse_args()

    hub_url = "http://minimax.local:5000" if args.host == 'minimax' else "http://next.local:5000"
    client = BaseNode(hub_url=hub_url, node_name="marvin")

    await client.sio.connect(hub_url)
    await client._connected.wait()

    try:
        capture = VADCapture(client, topic=args.topic)
        while True:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Shutting down audio capture...')
    finally:
        capture.cleanup()
        client.sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
