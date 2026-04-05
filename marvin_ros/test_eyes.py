from controllers.eyes import Eyes
import asyncio

eyes = Eyes()

async def test_eyes():
    asyncio.create_task(eyes.run())
    eyes.set_awake(True)
    await asyncio.sleep(1)
    eyes.set_wide_eyes(True)
    await asyncio.sleep(1)
    eyes.set_wide_eyes(False)
    for x in range(-100, 100, 10):
        eyes.set_eyes_at(x)
        await asyncio.sleep(0.5)

def main():
    asyncio.run(test_eyes())

if __name__ == "__main__":
    main()
