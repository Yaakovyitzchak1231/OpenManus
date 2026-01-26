import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.llm import LLM
from app.config import LLMSettings


# Mock dependencies
@pytest.fixture
def mock_openai():
    with patch("app.llm.AsyncOpenAI") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def llm(mock_openai):
    # Reset singleton instance
    LLM._instances = {}
    LLM._response_cache.clear()

    settings = LLMSettings(
        model="gpt-4",
        base_url="http://test",
        api_key="test-key",
        api_type="openai",
        api_version="v1",
    )

    # Mock tiktoken to avoid downloading models
    with patch("tiktoken.encoding_for_model") as mock_tiktoken:
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = [1, 2, 3]  # Dummy tokens
        mock_tiktoken.return_value = mock_encoding

        llm_instance = LLM(llm_config={"default": settings})
        return llm_instance


@pytest.mark.asyncio
async def test_ask_caching(llm, mock_openai):
    messages = [{"role": "user", "content": "Hello"}]

    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello there!"))]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    mock_openai.chat.completions.create.return_value = mock_response

    # First call
    response1 = await llm.ask(messages, stream=False)
    assert response1 == "Hello there!"
    assert mock_openai.chat.completions.create.call_count == 1

    # Second call (should be cached but currently isn't)
    response2 = await llm.ask(messages, stream=False)
    assert response2 == "Hello there!"

    # This assertion will FAIL if caching is not implemented
    assert mock_openai.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_ask_with_images_caching(llm, mock_openai):
    messages = [{"role": "user", "content": "Describe this image"}]
    images = ["http://example.com/image.jpg"]

    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="It is a cat."))]
    mock_response.usage.prompt_tokens = 20
    mock_response.usage.completion_tokens = 5

    mock_openai.chat.completions.create.return_value = mock_response

    # Use a multimodal model
    llm.model = "gpt-4o"

    # First call
    response1 = await llm.ask_with_images(messages, images, stream=False)
    assert response1 == "It is a cat."
    assert mock_openai.chat.completions.create.call_count == 1

    # Second call
    response2 = await llm.ask_with_images(messages, images, stream=False)
    assert response2 == "It is a cat."

    # Should be 1 if cached, currently will be 2
    assert mock_openai.chat.completions.create.call_count == 1
