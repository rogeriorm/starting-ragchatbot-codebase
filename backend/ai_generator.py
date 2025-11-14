import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **One search per query maximum**
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string

        Raises:
            Exception: With descriptive message if API call or tool execution fails
        """

        try:
            # Build system content efficiently - avoid string ops when possible
            system_content = (
                f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
                if conversation_history
                else self.SYSTEM_PROMPT
            )

            # Prepare API call parameters efficiently
            api_params = {
                **self.base_params,
                "messages": [{"role": "user", "content": query}],
                "system": system_content
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude with error handling
            try:
                response = self.client.messages.create(**api_params)
            except anthropic.APIConnectionError as e:
                raise Exception(f"Failed to connect to Anthropic API. Please check your internet connection. Details: {str(e)}")
            except anthropic.APITimeoutError as e:
                raise Exception(f"Anthropic API request timed out. Please try again. Details: {str(e)}")
            except anthropic.RateLimitError as e:
                raise Exception(f"Anthropic API rate limit exceeded. Please wait a moment before trying again. Details: {str(e)}")
            except anthropic.APIStatusError as e:
                raise Exception(f"Anthropic API error (status {e.status_code}). Details: {str(e)}")
            except anthropic.AuthenticationError as e:
                raise Exception(f"Anthropic API authentication failed. Please check your API key. Details: {str(e)}")
            except Exception as e:
                raise Exception(f"Unexpected error calling Anthropic API: {str(e)}")

            # Handle tool execution if needed
            if response.stop_reason == "tool_use" and tool_manager:
                return self._handle_tool_execution(response, api_params, tool_manager)

            # Return direct response
            return response.content[0].text

        except Exception as e:
            # Log the error (in production, use proper logging)
            print(f"[AI_GENERATOR ERROR] generate_response failed: {str(e)}")
            raise
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution

        Raises:
            Exception: If tool execution or synthesis API call fails
        """
        try:
            # Start with existing messages
            messages = base_params["messages"].copy()

            # Add AI's tool use response
            messages.append({"role": "assistant", "content": initial_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in initial_response.content:
                if content_block.type == "tool_use":
                    try:
                        # Execute the tool with error handling
                        tool_result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result
                        })
                    except Exception as e:
                        # Log tool execution error and return error as tool result
                        # This allows Claude to see the error and respond appropriately
                        print(f"[AI_GENERATOR ERROR] Tool '{content_block.name}' execution failed: {str(e)}")
                        error_message = f"Tool execution failed: {str(e)}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": error_message,
                            "is_error": True
                        })

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Prepare final API call without tools
            final_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }

            # Get final response with error handling
            try:
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text
            except anthropic.APIConnectionError as e:
                raise Exception(f"Failed to connect to Anthropic API during synthesis. Details: {str(e)}")
            except anthropic.APITimeoutError as e:
                raise Exception(f"Anthropic API timed out during response synthesis. Details: {str(e)}")
            except anthropic.RateLimitError as e:
                raise Exception(f"Rate limit exceeded during response synthesis. Details: {str(e)}")
            except anthropic.APIStatusError as e:
                raise Exception(f"API error during synthesis (status {e.status_code}). Details: {str(e)}")
            except Exception as e:
                raise Exception(f"Unexpected error during response synthesis: {str(e)}")

        except Exception as e:
            print(f"[AI_GENERATOR ERROR] _handle_tool_execution failed: {str(e)}")
            raise Exception(f"Tool execution and synthesis failed: {str(e)}")