import time
import roslibpy
from vad_capture import VADCapture
from tts import TTSController
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
        tts = TTSController()
        tts.start()

        def tts_callback(message):
            print('Received TTS request: ' + message['data'])
            tts.queue_text(message['data'])

        listener = roslibpy.Topic(client, '/llm_response', 'std_msgs/String')
        listener.subscribe(tts_callback)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down audio capture...')
    finally:
        capture.cleanup()

if __name__ == '__main__':
    main()
