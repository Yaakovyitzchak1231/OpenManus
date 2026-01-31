import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock dependencies
sys.modules["app.utils.cost_tracker"] = MagicMock()

from app.llm import LLM

@pytest.mark.asyncio
async def test_llm_caching():
    # Patch AsyncOpenAI
    with patch("app.llm.AsyncOpenAI") as MockClientClass:
        # Setup the mock client
        mock_client = AsyncMock()
        MockClientClass.return_value = mock_client

        # Setup the mock response
        mock_response_message = MagicMock()
        mock_response_message.message.content = "Mock Response"

        mock_choice = MagicMock()
        mock_choice.message = mock_response_message.message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_client.chat.completions.create.return_value = mock_response

        # Initialize LLM
        LLM._instances = {}
        llm = LLM()

        messages = [{"role": "user", "content": "Hello"}]

        # Call 1
        response1 = await llm.ask(messages, stream=False)
        assert response1 == "Mock Response"

        # Call 2
        response2 = await llm.ask(messages, stream=False)
        assert response2 == "Mock Response"

        # Verify
        assert mock_client.chat.completions.create.call_count == 1
