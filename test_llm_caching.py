from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import LLM


@pytest.mark.asyncio
async def test_llm_ask_caching(capsys):
    """Test caching for LLM.ask method"""
    with patch("app.llm.AsyncOpenAI") as mock_openai:
        # Setup mock
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock non-streaming response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Cached Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_client.chat.completions.create.return_value = mock_response

        # Reset LLM singleton and cache
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        llm = LLM()

        # DEBUG
        print(f"DEBUG: Enable cache: {llm.enable_response_cache}")

        messages = [{"role": "user", "content": "Hello"}]

        # First call - should hit API
        response1 = await llm.ask(messages, stream=False)
        print(f"DEBUG: Cache size after 1st call: {len(LLM._response_cache)}")
        assert response1 == "Cached Response"
        assert mock_client.chat.completions.create.call_count == 1

        # Second call - should hit cache
        response2 = await llm.ask(messages, stream=False)
        assert response2 == "Cached Response"
        # Call count should still be 1 if caching works
        # If implementation is missing, this will fail (call_count will be 2)
        assert (
            mock_client.chat.completions.create.call_count == 1
        ), "Cache miss! API called twice."


@pytest.mark.asyncio
async def test_llm_ask_caching_streaming(capsys):
    """Test caching for LLM.ask method with streaming"""

    # Create a dummy class to handle async streaming instead of complex AsyncMock
    class DummyStream:
        def __init__(self):
            self.chunks = ["Streamed", " ", "Response"]

        def __aiter__(self):
            self.idx = 0
            return self

        async def __anext__(self):
            if self.idx >= len(self.chunks):
                raise StopAsyncIteration

            c = self.chunks[self.idx]
            self.idx += 1

            # Create a simple object structure to mimic the response chunk
            # chunk.choices[0].delta.content
            class Delta:
                def __init__(self, content):
                    self.content = content

            class Choice:
                def __init__(self, content):
                    self.delta = Delta(content)

            class Chunk:
                def __init__(self, content):
                    self.choices = [Choice(content)]

            return Chunk(c)

    class DummyClient:
        def __init__(self):
            # Mock the structure: client.chat.completions.create
            self.chat = MagicMock()
            # We can't easily mock the method call without AsyncMock or a custom class for 'completions'
            # Let's use a custom class structure for client

        async def create(self, **kwargs):
            self.call_count += 1
            return DummyStream()

    # We need a proper client structure that LLM expects: self.client.chat.completions.create
    class Completions:
        def __init__(self):
            self.create_obj = (
                DummyClient()
            )  # reusing class name for the create method holder
            self.create_obj.call_count = (
                0  # Initialize call_count here on the object instance!
            )
            self.create = self.create_obj.create

    class Chat:
        def __init__(self):
            self.completions = Completions()

    class FullClient:
        def __init__(self):
            self.chat = Chat()

    dummy_client = FullClient()
    # We need to access the call counter. It's inside dummy_client.chat.completions.create_obj.call_count

    with patch("app.llm.AsyncOpenAI", return_value=dummy_client):
        # Reset LLM singleton and cache
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        llm = LLM()
        print(f"DEBUG: Enable cache (stream): {llm.enable_response_cache}")

        messages = [{"role": "user", "content": "Stream me"}]

        # First call - Stream=True
        # We need to capture stdout to verify printing
        response1 = await llm.ask(messages, stream=True)
        print(f"DEBUG: Cache size after 1st call (stream): {len(LLM._response_cache)}")
        captured = capsys.readouterr()
        assert response1 == "Streamed Response"
        assert "Streamed Response" in captured.out
        assert dummy_client.chat.completions.create_obj.call_count == 1

        # Second call - Stream=True
        # Should hit cache and still print
        response2 = await llm.ask(messages, stream=True)
        captured = capsys.readouterr()
        assert response2 == "Streamed Response"
        assert "Streamed Response" in captured.out
        assert (
            dummy_client.chat.completions.create_obj.call_count == 1
        ), "Cache miss! API called twice."


@pytest.mark.asyncio
async def test_llm_ask_with_images_caching():
    """Test caching for LLM.ask_with_images method"""
    with patch("app.llm.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Image Response"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 5

        mock_client.chat.completions.create.return_value = mock_response

        # Reset LLM singleton and cache
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        # Mock MULTIMODAL_MODELS check by setting model directly
        llm = LLM()
        llm.model = "gpt-4o"

        messages = [{"role": "user", "content": "Look at this"}]
        images = ["http://example.com/image.jpg"]

        # First call
        response1 = await llm.ask_with_images(messages, images=images, stream=False)
        assert response1 == "Image Response"
        assert mock_client.chat.completions.create.call_count == 1

        # Second call
        response2 = await llm.ask_with_images(messages, images=images, stream=False)
        assert response2 == "Image Response"
        assert (
            mock_client.chat.completions.create.call_count == 1
        ), "Cache miss! API called twice."
