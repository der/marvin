# Master for all nodes on Marvin which connect as a client to the DROS hub.
import argparse
import asyncio
import time

from dros import Bus, Node, ClientTransport
from messages.robot import EventMessage, EyeMessage, MotorControlMessage, NeckControlMessage
from controllers.eyes import Eyes

class EyesServer(Node):
    def __init__(self, bus):
        super().__init__(bus)
        self.eyes = Eyes()
        self.topic = "/marvin/eyes"
        self.subscribe_event(self.topic)
        self.subscribe_event("events", self.event_reaction)

    async def start_controller(self):
        return await self.eyes.run()

    def process(self, message):
        try:
            request = EyeMessage.model_validate(message)
            print("Eye server received goal:", request)
            self.eyes.set_awake(request.open)
            self.eyes.set_wide_eyes(request.wide)
            self.eyes.set_eyes_at(request.x)
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


async def main():
    parser = argparse.ArgumentParser(description="Marvin Eyes Server")
    parser.add_argument('--host', type=str, default='main', help='Choose host: minimax or main')
    args = parser.parse_args()

    hub_url = "http://minimax.local:5000" if args.host == 'minimax' else "http://next.local:5000"
    bus = Bus(ClientTransport(hub_url))
    eyes_server = EyesServer(bus)

    bus.start()
    try:
        async with asyncio.TaskGroup() as tg:
            task1 = tg.create_task(eyes_server.start_controller())
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print("Error:", e)
    finally:
        bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
