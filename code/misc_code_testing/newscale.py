"""New scale"""
from sartorius import Scale
from sartorius.mock import Scale as MockScale
import asyncio

scale = Scale(address='COM6')
mock_scale = MockScale()

async def get_weight():
    async with scale:
        reading = await scale.get()
        while not reading['stable']:      # Get mass, units, stability
            await asyncio.sleep(0.1)
            reading = await scale.get()
        return reading['mass']

print(scale.read_scale())