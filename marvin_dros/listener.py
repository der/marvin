"""CLI tool to listen on a room and print incoming messages."""

import argparse

from dros import Bus, Node, ClientTransport

class LoggerNode(Node):
    def __init__(self, bus, topic="messages"):
        super().__init__(bus)
        self.topic = topic
        print(f"LoggerNode initialized to listen on topic: {self.topic}")
        self.subscribe_event(self.topic)

    def process(self, message):
        print("Received message:", message)

def main():
    parser = argparse.ArgumentParser(description="Listen on a topic")
    parser.add_argument("--topic", required=True, help="Topic to listen to")
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    args = parser.parse_args()

    hub_url = "http://minimax.local:5000" if args.host == 'minimax' else "http://next.local:5000"

    bus = Bus(ClientTransport(hub_url))
    logger_node = LoggerNode(bus, topic=args.topic)
    bus.run()

if __name__ == "__main__":
    main()
