
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import time
from app.llm import LLM
from app.config import LLMSettings

# Mock settings
mock_llm_config = {
    "default": LLMSettings(
        provider="openai",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        api_type="openai",
        api_version="v1",
        temperature=0.7,
        max_tokens=100
    )
}

class TestLLMCaching(unittest.TestCase):
    def setUp(self):
        # Reset singleton instance before each test to ensure clean state
        LLM._instances = {}
        self.llm = LLM(llm_config=mock_llm_config)
        self.llm._response_cache.clear()

    @patch("app.llm.AsyncOpenAI")
    def test_ask_caching(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Cached Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        # Override client on the existing instance
        self.llm.client = mock_instance

        async def run_test():
            prompt = [{"role": "user", "content": "Hello Cache"}]

            # First call
            response1 = await self.llm.ask(prompt, stream=False)
            self.assertEqual(response1, "Cached Response")

            # Second call
            response2 = await self.llm.ask(prompt, stream=False)
            self.assertEqual(response2, "Cached Response")

            # Verify API called only once
            self.assertEqual(mock_instance.chat.completions.create.call_count, 1)

        asyncio.run(run_test())

    @patch("app.llm.AsyncOpenAI")
    def test_ask_caching_miss(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        self.llm.client = mock_instance

        async def run_test():
            prompt1 = [{"role": "user", "content": "Prompt 1"}]
            prompt2 = [{"role": "user", "content": "Prompt 2"}]

            await self.llm.ask(prompt1, stream=False)
            await self.llm.ask(prompt2, stream=False)

            # Verify API called twice
            self.assertEqual(mock_instance.chat.completions.create.call_count, 2)

        asyncio.run(run_test())

    @patch("app.llm.AsyncOpenAI")
    def test_ask_with_images_caching(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Image Response"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 5
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        self.llm.client = mock_instance

        async def run_test():
            prompt = [{"role": "user", "content": "Describe this image"}]
            images = ["http://example.com/image.jpg"]

            # First call
            response1 = await self.llm.ask_with_images(prompt, images, stream=False)
            self.assertEqual(response1, "Image Response")

            # Second call
            response2 = await self.llm.ask_with_images(prompt, images, stream=False)
            self.assertEqual(response2, "Image Response")

            # Verify API called only once
            self.assertEqual(mock_instance.chat.completions.create.call_count, 1)

        asyncio.run(run_test())

    @patch("app.llm.AsyncOpenAI")
    def test_disable_caching(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        self.llm.client = mock_instance
        self.llm.enable_response_cache = False

        async def run_test():
            prompt = [{"role": "user", "content": "Hello No Cache"}]

            await self.llm.ask(prompt, stream=False)
            await self.llm.ask(prompt, stream=False)

            # Verify API called twice
            self.assertEqual(mock_instance.chat.completions.create.call_count, 2)

        asyncio.run(run_test())

    @patch("app.llm.AsyncOpenAI")
    def test_streaming_cache(self, MockClient):
        # Setup mock
        mock_instance = MockClient.return_value

        # Streaming response
        async def mock_stream_response():
            chunks = ["Res", "pon", "se"]
            for chunk in chunks:
                mock_chunk = MagicMock()
                mock_chunk.choices = [MagicMock()]
                mock_chunk.choices[0].delta.content = chunk
                yield mock_chunk

        mock_instance.chat.completions.create = AsyncMock(side_effect=lambda **kwargs: mock_stream_response())
        self.llm.client = mock_instance

        async def run_test():
            prompt = [{"role": "user", "content": "Stream me"}]

            # First call (Stream)
            response1 = await self.llm.ask(prompt, stream=True)
            self.assertEqual(response1, "Response")

            # Second call (Stream) - should hit cache
            response2 = await self.llm.ask(prompt, stream=True)
            self.assertEqual(response2, "Response")

            # Verify API called once
            self.assertEqual(mock_instance.chat.completions.create.call_count, 1)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
