import asyncio
from game import send_to_player

async def main():
    result = await send_to_player("Nick", "hello")
    print(result)

# Run the main function in the event loop
asyncio.run(main())
