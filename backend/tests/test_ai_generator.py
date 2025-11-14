"""
Unit tests for AIGenerator

Tests the AI generation and tool calling orchestration to ensure:
- Correct Claude API interactions
- Proper tool execution flow
- Error handling for API failures
- Conversation history integration
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from ai_generator import AIGenerator


@pytest.mark.unit
class TestAIGeneratorDirectResponse:
    """Tests for direct AI responses without tool usage"""

    def test_generate_response_without_tools_success(self, mock_anthropic_client_direct):
        """Test 1: Direct response without tools works correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            response = generator.generate_response(
                query="What is 2+2?",
                conversation_history=None,
                tools=None,
                tool_manager=None
            )

            # Verify API was called
            mock_anthropic_client_direct.messages.create.assert_called_once()

            # Verify response
            assert isinstance(response, str)
            assert len(response) > 0
            assert response == "This is a direct answer without using tools."

    def test_generate_response_with_conversation_history(self, mock_anthropic_client_direct):
        """Test 8: Conversation history is properly integrated"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            history = "User: What is RAG?\nAssistant: RAG stands for Retrieval-Augmented Generation."

            response = generator.generate_response(
                query="Can you elaborate?",
                conversation_history=history,
                tools=None,
                tool_manager=None
            )

            # Verify history was included in system prompt
            call_args = mock_anthropic_client_direct.messages.create.call_args
            system_content = call_args.kwargs['system']
            assert history in system_content
            assert "Previous conversation:" in system_content


@pytest.mark.unit
class TestAIGeneratorToolUsage:
    """Tests for AI responses that use tools"""

    def test_generate_response_with_tools_success(self, mock_anthropic_client_tool_use, mock_tool_manager_success):
        """Test 2: Tool usage flow works correctly (two API calls)"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "search_course_content", "description": "Search courses"}]

            response = generator.generate_response(
                query="What is RAG?",
                conversation_history=None,
                tools=tools,
                tool_manager=mock_tool_manager_success
            )

            # Verify two API calls were made
            assert mock_anthropic_client_tool_use.messages.create.call_count == 2

            # Verify tool was executed
            mock_tool_manager_success.execute_tool.assert_called_once()

            # Verify final response
            assert isinstance(response, str)
            assert "RAG stands for Retrieval-Augmented Generation" in response

    def test_handle_tool_execution_success(self, mock_anthropic_client_tool_use, mock_tool_manager_success):
        """Test 3: _handle_tool_execution method works correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "search_course_content", "description": "Search courses"}]

            response = generator.generate_response(
                query="What is RAG?",
                tools=tools,
                tool_manager=mock_tool_manager_success
            )

            # Verify tool execution happened
            tool_call_args = mock_tool_manager_success.execute_tool.call_args
            assert tool_call_args.args[0] == "search_course_content"
            assert "query" in tool_call_args.kwargs

            # Verify second API call included tool results
            second_call_args = mock_anthropic_client_tool_use.messages.create.call_args_list[1]
            messages = second_call_args.kwargs['messages']

            # Should have original user message, assistant tool_use, and tool results
            assert len(messages) >= 2
            assert any(msg['role'] == 'assistant' for msg in messages)


@pytest.mark.unit
class TestAIGeneratorErrorHandling:
    """Tests for error handling in AI generation"""

    def test_first_api_call_failure(self, mock_anthropic_client_api_error):
        """Test 4: First API call failure raises exception"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_api_error):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            # This should raise an exception (no try-catch in current implementation)
            with pytest.raises(Exception) as exc_info:
                generator.generate_response(
                    query="What is RAG?",
                    tools=None,
                    tool_manager=None
                )

            assert "API connection timeout" in str(exc_info.value)

    def test_second_api_call_failure(self, mock_anthropic_client_second_call_fails, mock_tool_manager_success):
        """Test 5: Second API call failure (after tool execution) raises exception"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_second_call_fails):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "search_course_content", "description": "Search courses"}]

            # First call succeeds, tool executes, second call fails
            with pytest.raises(Exception) as exc_info:
                generator.generate_response(
                    query="What is RAG?",
                    tools=tools,
                    tool_manager=mock_tool_manager_success
                )

            # Verify tool was executed before failure
            mock_tool_manager_success.execute_tool.assert_called_once()

            # Verify second call failed
            assert "Second API call failed" in str(exc_info.value)

    def test_tool_execution_exception(self, mock_anthropic_client_tool_use, mock_tool_manager_exception):
        """Test 6: Tool execution exception propagates correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "search_course_content", "description": "Search courses"}]

            # Tool execution raises exception
            with pytest.raises(Exception) as exc_info:
                generator.generate_response(
                    query="What is RAG?",
                    tools=tools,
                    tool_manager=mock_tool_manager_exception
                )

            assert "Tool execution failed" in str(exc_info.value)

    def test_malformed_tool_use_response(self, mock_tool_manager_success):
        """Test 7: Malformed tool_use block is handled"""
        # Create a mock client with malformed tool_use response
        mock_client = Mock()
        malformed_response = Mock()

        # Tool use block missing required attributes
        malformed_tool_block = Mock()
        malformed_tool_block.type = "tool_use"
        # Missing 'id', 'name', or 'input' could cause AttributeError
        del malformed_tool_block.id  # Simulate missing attribute

        malformed_response.content = [malformed_tool_block]
        malformed_response.stop_reason = "tool_use"
        mock_client.messages.create.return_value = malformed_response

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "search_course_content", "description": "Search courses"}]

            # Should raise AttributeError due to missing 'id'
            with pytest.raises(AttributeError):
                generator.generate_response(
                    query="What is RAG?",
                    tools=tools,
                    tool_manager=mock_tool_manager_success
                )


@pytest.mark.unit
class TestAIGeneratorConfiguration:
    """Tests for AIGenerator configuration and setup"""

    def test_initialization(self):
        """Test AIGenerator initializes correctly"""
        with patch('ai_generator.anthropic.Anthropic') as MockClient:
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            # Verify client was created
            MockClient.assert_called_once_with(api_key="test-key")

            # Verify configuration
            assert generator.model == "claude-sonnet-4"
            assert generator.base_params["model"] == "claude-sonnet-4"
            assert generator.base_params["temperature"] == 0
            assert generator.base_params["max_tokens"] == 800

    def test_system_prompt_exists(self):
        """Test system prompt is defined"""
        assert hasattr(AIGenerator, 'SYSTEM_PROMPT')
        assert len(AIGenerator.SYSTEM_PROMPT) > 0
        assert "search tool" in AIGenerator.SYSTEM_PROMPT.lower()
        assert "one search per query maximum" in AIGenerator.SYSTEM_PROMPT.lower()


@pytest.mark.unit
class TestAIGeneratorMessageConstruction:
    """Tests for message and parameter construction"""

    def test_api_params_construction_without_tools(self, mock_anthropic_client_direct):
        """Test API parameters are constructed correctly without tools"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            generator.generate_response(query="Test query")

            # Check the call arguments
            call_kwargs = mock_anthropic_client_direct.messages.create.call_args.kwargs

            assert "messages" in call_kwargs
            assert "system" in call_kwargs
            assert "model" in call_kwargs
            assert call_kwargs["model"] == "claude-sonnet-4"
            assert "tools" not in call_kwargs

    def test_api_params_construction_with_tools(self, mock_anthropic_client_direct):
        """Test API parameters include tools when provided"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "test_tool", "description": "A test tool"}]

            generator.generate_response(
                query="Test query",
                tools=tools,
                tool_manager=Mock()
            )

            # Check tools were included
            call_kwargs = mock_anthropic_client_direct.messages.create.call_args.kwargs

            assert "tools" in call_kwargs
            assert call_kwargs["tools"] == tools
            assert "tool_choice" in call_kwargs
            assert call_kwargs["tool_choice"]["type"] == "auto"

    def test_messages_array_structure(self, mock_anthropic_client_direct):
        """Test messages array is structured correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            query = "What is RAG?"
            generator.generate_response(query=query)

            # Check messages structure
            call_kwargs = mock_anthropic_client_direct.messages.create.call_args.kwargs
            messages = call_kwargs["messages"]

            assert isinstance(messages, list)
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == query


@pytest.mark.unit
class TestAIGeneratorEdgeCases:
    """Edge case tests for AIGenerator"""

    def test_empty_query(self, mock_anthropic_client_direct):
        """Test with empty query string"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            response = generator.generate_response(query="")

            # Should still make API call
            mock_anthropic_client_direct.messages.create.assert_called_once()
            assert isinstance(response, str)

    def test_very_long_conversation_history(self, mock_anthropic_client_direct):
        """Test with very long conversation history"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_direct):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            # Create long history
            long_history = ("User: Question?\nAssistant: Answer.\n" * 100)

            response = generator.generate_response(
                query="New question",
                conversation_history=long_history
            )

            # Should handle long history
            assert isinstance(response, str)
            call_kwargs = mock_anthropic_client_direct.messages.create.call_args.kwargs
            assert long_history in call_kwargs["system"]

    def test_none_tool_manager_with_tools(self, mock_anthropic_client_tool_use):
        """Test tool_use response with None tool_manager"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_tool_use):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

            tools = [{"name": "test_tool"}]

            # Tool use requires tool_manager, but it's None
            # This should cause an error when trying to execute
            with pytest.raises(AttributeError):
                generator.generate_response(
                    query="Test",
                    tools=tools,
                    tool_manager=None
                )
