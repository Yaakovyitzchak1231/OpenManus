from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

from app.llm import LLM


# --- Dummy Classes for Mocking OpenAI Client ---


class DummyResponse:
    def __init__(self, content):
        self.choices = [MagicMock()]
        self.choices[0].message.content = content
        self.usage = MagicMock()
        self.usage.prompt_tokens = 10
        self.usage.completion_tokens = 5


class DummyStream:
    def __init__(self, content_chunks):
        self.chunks = content_chunks

    def __aiter__(self):
        self.idx = 0
        return self

    async def __anext__(self):
        if self.idx >= len(self.chunks):
            raise StopAsyncIteration

        c = self.chunks[self.idx]
        self.idx += 1

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
    def __init__(self, stream_content=None, static_content=None):
        self.chat = MagicMock()
        self.call_count = 0
        self.stream_content = stream_content
        self.static_content = static_content

    async def create(self, **kwargs):
        self.call_count += 1
        if kwargs.get("stream"):
            if self.stream_content is None:
                raise ValueError("Stream content not provided for streaming request")
            return DummyStream(self.stream_content)
        else:
            if self.static_content is None:
                return DummyResponse("Default Response")
            return DummyResponse(self.static_content)


class Completions:
    def __init__(self, client):
        self.create_obj = client
        self.create = client.create


class Chat:
    def __init__(self, client):
        self.completions = Completions(client)


class FullClient:
    def __init__(self, stream_content=None, static_content=None):
        self.dummy_client = DummyClient(stream_content, static_content)
        self.chat = Chat(self.dummy_client)


# --- Tests ---


@pytest.mark.asyncio
async def test_llm_ask_caching():
    """Test caching for LLM.ask method (non-streaming)"""
    client = FullClient(static_content="Cached Response")

    with patch("app.llm.AsyncOpenAI", return_value=client):
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        llm = LLM()

        messages = [{"role": "user", "content": "Hello"}]

        # First call
        response1 = await llm.ask(messages, stream=False)
        assert response1 == "Cached Response"
        assert client.dummy_client.call_count == 1

        # Second call
        response2 = await llm.ask(messages, stream=False)
        assert response2 == "Cached Response"
        assert client.dummy_client.call_count == 1


@pytest.mark.asyncio
async def test_llm_ask_caching_streaming(capsys):
    """Test caching for LLM.ask method with streaming"""
    client = FullClient(stream_content=["Streamed", " ", "Response"])

    with patch("app.llm.AsyncOpenAI", return_value=client):
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        llm = LLM()

        messages = [{"role": "user", "content": "Stream me"}]

        # First call
        response1 = await llm.ask(messages, stream=True)
        captured = capsys.readouterr()
        assert response1 == "Streamed Response"
        assert "Streamed Response" in captured.out
        assert client.dummy_client.call_count == 1

        # Second call
        response2 = await llm.ask(messages, stream=True)
        captured = capsys.readouterr()
        assert response2 == "Streamed Response"
        assert "Streamed Response" in captured.out
        assert client.dummy_client.call_count == 1


@pytest.mark.asyncio
async def test_llm_ask_with_images_caching():
    """Test caching for LLM.ask_with_images method"""
    client = FullClient(static_content="Image Response")

    with patch("app.llm.AsyncOpenAI", return_value=client):
        LLM._instances = {}
        LLM._response_cache = OrderedDict()
        llm = LLM()
        llm.model = "gpt-4o"

        messages = [{"role": "user", "content": "Look at this"}]
        images = ["http://example.com/image.jpg"]

        # First call
        response1 = await llm.ask_with_images(messages, images=images, stream=False)
        assert response1 == "Image Response"
        assert client.dummy_client.call_count == 1

        # Second call
        response2 = await llm.ask_with_images(messages, images=images, stream=False)
        assert response2 == "Image Response"
        assert client.dummy_client.call_count == 1
