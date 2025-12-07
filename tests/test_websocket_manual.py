import asyncio
import websockets
import json


async def test_websocket():
    uri = "ws://localhost:8000/api/receipts/ws/processing/1"
    async with websockets.connect(uri) as websocket:
        # Initial connection message
        response = await websocket.recv()
        print(f"Received: {response}")

        # Keep alive for a bit to see if we get updates (if we were running a real upload)
        # Since we are just testing connection, we just wait a bit
        try:
            await asyncio.sleep(2)
            # Send a ping/pong or just close
            await websocket.close()
            print("Connection closed cleanly")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
