import asyncio
from unittest.mock import AsyncMock


async def main():
    mock = AsyncMock()

    async def my_gen():
        yield 1
        yield 2

    mock.side_effect = my_gen

    try:
        # This simulates response = await create(...)
        result = await mock()
        print(f"Result type: {type(result)}")

        async for item in result:
            print(f"Item: {item}")

    except Exception as e:
        print(f"Caught error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
