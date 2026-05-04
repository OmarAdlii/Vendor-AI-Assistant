from typing import Dict, Any, Optional, AsyncGenerator
import openai
import json
from app.config import get_settings
from utils.json_utils import make_serializable
from agent.memory import conversation_memory
from agent.prompts import SYSTEM_PROMPT, get_error_message
from mcp_server.server import mcp_server
from utils.logger import get_logger
from utils.token_utils import count_tokens, count_messages_tokens

logger = get_logger(__name__)

settings = get_settings()
openai.api_key = settings.openai_api_key

class AIAgent:
    """Main AI Agent with tool calling capabilities"""
    
    def __init__(self):
        self.model = settings.openai_model
        self.max_tool_calls = 5  # Prevent infinite loops
        self._initialized = False
    
    async def initialize(self):
        """Initialize AI Agent and MCP Server"""
        if not self._initialized:
            await mcp_server.initialize()
            self._initialized = True
            print(" AI Agent initialized")
    
    async def process_message(
        self,
        message: str,
        vendor_id: str,
        session_id: str,
        stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator:
        """Process user message and generate response"""
        
        logger.info("process_message called; session_id=%s vendor_id=%s", session_id, vendor_id)
        logger.debug("incoming message: %s", message)
        # Initialize if needed
        await self.initialize()
        
        # Get conversation history
        history = await conversation_memory.get_history(session_id)
        
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Current Vendor ID: {vendor_id}"}
        ]
        
        # Add conversation history
        for msg in history[-10:]:  # Last 10 messages
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Save user message to memory (include vendor_id)
        await conversation_memory.add_message(session_id, "user", message, vendor_id=vendor_id)

        # Log token usage estimate
        try:
            toks = count_tokens(message, model=self.model)
            logger.info("message token estimate: %d", toks)
        except Exception:
            logger.exception("Failed to count tokens for message")
        
        # Get available tools
        tools = self._format_tools_for_openai()
        logger.info("formatted %d tools for OpenAI", len(tools))
        
        if stream:
            return self._stream_response(messages, tools, session_id, vendor_id)
        else:
            return await self._generate_response(messages, tools, session_id, vendor_id)
    
    async def _generate_response(
        self,
        messages: list,
        tools: list,
        session_id: str,
        vendor_id: str
    ) -> Dict[str, Any]:
        """Generate non-streaming response"""
        
        tool_calls_made = []
        current_messages = messages.copy()
        steps = []  # detailed steps with token accounting
        iteration = 0
        
        while iteration < self.max_tool_calls:
            iteration += 1
            
            # Call OpenAI
            # Estimate input tokens for this model call
            try:
                input_tokens = count_messages_tokens(current_messages, model=self.model)
            except Exception:
                input_tokens = None

            response = openai.chat.completions.create(
                model=self.model,
                messages=current_messages,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message

            # Estimate output tokens for the model's assistant message
            try:
                output_tokens = count_tokens(message.content or "", model=self.model)
            except Exception:
                output_tokens = None

            # Record the model call as a step
            steps.append({
                "step_type": "model_call",
                "iteration": iteration,
                "model": self.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "prompt_summary": (current_messages[-1]["content"] if current_messages else "")
            })
            
            # Check if tool calls are needed
            if not message.tool_calls:
                # No more tool calls - we have final response
                final_content = message.content
                
                # Save assistant response to memory
                await conversation_memory.add_message(
                    session_id,
                    "assistant",
                    final_content,
                    {"tool_calls": tool_calls_made},
                    vendor_id=vendor_id
                )
                # Token accounting already recorded for this iteration; attach steps
                # Compute aggregated token breakdown across steps
                total_input = 0
                total_output = 0
                total_args = 0
                total_results = 0
                for s in steps:
                    if s.get("step_type") == "model_call":
                        if isinstance(s.get("input_tokens"), (int, float)):
                            total_input += int(s.get("input_tokens") or 0)
                        if isinstance(s.get("output_tokens"), (int, float)):
                            total_output += int(s.get("output_tokens") or 0)
                    elif s.get("step_type") == "tool_call":
                        if isinstance(s.get("args_tokens"), (int, float)):
                            total_args += int(s.get("args_tokens") or 0)
                        if isinstance(s.get("result_tokens"), (int, float)):
                            total_results += int(s.get("result_tokens") or 0)

                hidden_tokens = total_args + total_results
                total_tokens = total_input + hidden_tokens + total_output

                tokens_payload = {
                    "input": total_input if total_input > 0 else None,
                    "hidden": hidden_tokens if hidden_tokens > 0 else None,
                    "output": total_output if total_output > 0 else None,
                    "total": total_tokens if total_tokens > 0 else None,
                    "breakdown": {
                        "model_input": total_input,
                        "model_output": total_output,
                        "tool_args": total_args,
                        "tool_results": total_results
                    }
                }

                return {
                    "response": final_content,
                    "tool_calls": tool_calls_made,
                    "steps": steps,
                    "tokens": tokens_payload,
                    "session_id": session_id
                }
            
            # Execute tool calls
            current_messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                
                try:
                    # Parse arguments
                    args = json.loads(tool_call.function.arguments)
                    
                    # Add vendor_id if tool needs it
                    if "vendor_id" in args and not args.get("vendor_id"):
                        args["vendor_id"] = vendor_id
                    
                    # Execute tool
                    result = await mcp_server.execute_tool(tool_name, args)
                    
                    # Estimate tokens for tool args and result
                    try:
                        args_tokens = count_tokens(json.dumps(make_serializable(args)), model=self.model)
                    except Exception:
                        args_tokens = None
                    try:
                        res_tokens = count_tokens(json.dumps(make_serializable(result)), model=self.model)
                    except Exception:
                        res_tokens = None

                    tool_entry = {
                        "tool": tool_name,
                        "parameters": args,
                        "result": result,
                        "args_tokens": args_tokens,
                        "result_tokens": res_tokens
                    }
                    tool_calls_made.append(tool_entry)

                    # Add tool-call step
                    steps.append({
                        "step_type": "tool_call",
                        "tool": tool_name,
                        "parameters": args,
                        "result_summary": result if isinstance(result, dict) else str(result),
                        "args_tokens": args_tokens,
                        "result_tokens": res_tokens
                    })
                    
                    # Add tool result to messages
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(make_serializable(result))
                    })
                
                except Exception as e:
                    error_msg = f"Error executing tool {tool_name}: {str(e)}"
                    current_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(make_serializable({"error": error_msg}))
                    })
        
        # Max iterations reached
        return {
            "response": "عذراً، واجهت صعوبة في معالجة طلبك. يرجى المحاولة مرة أخرى بطريقة مختلفة.",
            "tool_calls": tool_calls_made,
            "session_id": session_id
        }
    
    async def _stream_response(
        self,
        messages: list,
        tools: list,
        session_id: str,
        vendor_id: str
    ) -> AsyncGenerator:
        """Generate streaming response"""
        # Note: Streaming with tool calls is complex
        # For now, we'll do non-streaming when tools are needed
        
        # Check if we need tools
        response = openai.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        if response.choices[0].message.tool_calls:
            # Need tools - use non-streaming
            result = await self._generate_response(messages, tools, session_id, vendor_id)
            yield result
        else:
            # No tools needed - can stream
            stream = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            full_content = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield {"type": "chunk", "content": content}
            
            # Save complete response (include vendor_id)
            await conversation_memory.add_message(session_id, "assistant", full_content, vendor_id=vendor_id)
            yield {"type": "done", "session_id": session_id}
    
    def _format_tools_for_openai(self) -> list:
        """Format MCP tools for OpenAI function calling"""
        tools_list = mcp_server.list_tools()
        
        formatted_tools = []
        for tool in tools_list:
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            param: {
                                "type": self._infer_param_type(param),
                                "description": f"The {param} parameter"
                            }
                            for param in tool["parameters"]
                        }
                    }
                }
            })
        
        return formatted_tools
    
    def _infer_param_type(self, param_name: str) -> str:
        """Infer parameter type from name"""
        if "id" in param_name.lower():
            return "integer"
        elif "status" in param_name.lower():
            return "boolean"
        elif param_name in ["discount", "threshold", "top_k"]:
            return "number"
        else:
            return "string"

# Singleton instance
ai_agent = AIAgent()