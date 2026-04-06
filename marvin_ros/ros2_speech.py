import time
import roslibpy
from speech.vad_capture import VADCapture
from speech.audio_player import AudioPlayer
import argparse
    
def main(args=None):
    parser = argparse.ArgumentParser(description='ROS2 Speech Node')
    parser.add_argument('--ros_host', type=str, default='minimax', help='Choose ROS host: minimax or main')
    args = parser.parse_args()

    if args.ros_host == 'minimax':
        client = roslibpy.Ros(host='192.168.178.90', port=9090)
    else:
        client = roslibpy.Ros(host='192.168.178.61', port=9090)
    client.run()

    try:
        capture = VADCapture(client, topic='audio_stream')
        player = AudioPlayer()

        listener = roslibpy.Topic(client, '/speech_stream', 'audio_msg/Audio')
        listener.subscribe(lambda message: player.play_message(message))

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down audio capture...')
    finally:
        capture.cleanup()
        player.cleanup()
        client.terminate()

if __name__ == '__main__':
    main()
