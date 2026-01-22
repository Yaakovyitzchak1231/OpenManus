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

        messages = [{"role": "user", "content": "Hello"}]

        # First call - should hit API
        response1 = await llm.ask(messages, stream=False)
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
    with patch("app.llm.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock streaming response
        async def mock_stream(*args, **kwargs):
            chunks = ["Streamed", " ", "Response"]
            for c in chunks:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = c
                yield chunk

        # Make the create call return the async generator (which is awaitable in the sense that it is the result of an async function)
        # But wait, OpenAI client returns an object that IS async iterable.
        # If we use side_effect = async_gen_func, calling mock() returns the async generator object.
        # If the code awaits it: await mock(), it fails because async gen is not awaitable.
        # The code in llm.py does: response = await client.create(...)
        # So we need mock() to be an async function that returns an async iterable.

        async def create_return(*args, **kwargs):
            return mock_stream()

        mock_client.chat.completions.create.side_effect = create_return

        # Reset LLM singleton and cache
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        llm = LLM()

        messages = [{"role": "user", "content": "Stream me"}]

        # First call - Stream=True
        # We need to capture stdout to verify printing
        response1 = await llm.ask(messages, stream=True)
        captured = capsys.readouterr()
        assert response1 == "Streamed Response"
        assert "Streamed Response" in captured.out
        assert mock_client.chat.completions.create.call_count == 1

        # Second call - Stream=True
        # Should hit cache and still print
        response2 = await llm.ask(messages, stream=True)
        captured = capsys.readouterr()
        assert response2 == "Streamed Response"
        assert "Streamed Response" in captured.out
        assert (
            mock_client.chat.completions.create.call_count == 1
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
