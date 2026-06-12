"""
AgentRunner — Encapsulates the core agent turn loop.

Extracted from main.py to enable:
- Isolated testing with mocked clients
- Cleaner separation between CLI plumbing and agent logic
- Reuse in non-interactive contexts (e.g., scripted pipelines)
"""

import asyncio
import json
import random
from typing import Any

from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from .config import Theme, console, get_active_model
from .logging_config import logger
from .tools import execute_tool
from .utils import Struct, truncate_output


class AgentRunner:
    """Handles a single conversational turn: stream → parse → execute tools → loop."""

    def __init__(
        self,
        client,
        active_tools: list[dict],
        context_manager,
        token_tracker,
        mcp_manager=None,
        auto_approve: bool = False,
        is_auto_mode: bool = False,
        auto_iteration_count: int = 0,
        max_auto_iterations: int = 50,
    ):
        self.client = client
        self.active_tools = active_tools
        self.context_manager = context_manager
        self.token_tracker = token_tracker
        self.mcp_manager = mcp_manager
        self.auto_approve = auto_approve
        self.is_auto_mode = is_auto_mode
        self.auto_iteration_count = auto_iteration_count
        self.max_auto_iterations = max_auto_iterations

    async def run_turn(self, messages: list[dict]) -> None:
        """
        Execute a full agent turn: stream the model's response, handle tool calls,
        and loop until the model produces a final text response (no more tool calls).
        """
        while True:
            if self.is_auto_mode:
                self.auto_iteration_count += 1
                if self.auto_iteration_count > self.max_auto_iterations:
                    console.print(
                        f"  [{Theme.WARNING}]⚠️  Autonomous mode reached iteration limit "
                        f"({self.max_auto_iterations}). Exiting auto mode.[/{Theme.WARNING}]"
                    )
                    self.is_auto_mode = False
                    messages.append({
                        "role": "user",
                        "content": (
                            f"You have reached the maximum number of autonomous iterations "
                            f"({self.max_auto_iterations}). Please provide a brief summary "
                            f"of what you have accomplished and what remains."
                        ),
                    })
                    self.auto_iteration_count = 0

            # Stream the response
            stream_result = await self._stream_response(messages)
            if stream_result is None:
                break  # Error occurred (already printed to console)

            full_content, tool_calls_list, api_usage = stream_result

            # Track tokens
            self._track_tokens(messages, full_content, api_usage)

            # Add assistant message to history
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": full_content or "",
            }
            if tool_calls_list:
                assistant_msg["tool_calls"] = tool_calls_list
            messages.append(assistant_msg)

            # If no tool calls, we're done with this turn
            if not tool_calls_list:
                break

            # Execute tool calls
            tool_results = await self._execute_tools(tool_calls_list)
            messages.extend(tool_results)

            # Loop continues — model processes tool results

    async def _stream_response(
        self, messages: list[dict]
    ) -> tuple[str, list[dict], Any] | None:
        """
        Stream a response from the model.

        Returns (full_content, tool_calls_list, api_usage) or None on error.
        """
        full_content = ""
        accumulated_tool_calls: dict[int, dict] = {}
        api_usage = None

        spinner_label = random.choice([
            "Thinking...", "Analyzing...", "Reasoning...",
            "Processing...", "Considering...", "Exploring...", "Synthesizing...",
        ])

        if self.is_auto_mode:
            spinner_text = Text(
                f" [Step {self.auto_iteration_count}/{self.max_auto_iterations}] {spinner_label}",
                style=f"{Theme.MUTED} italic",
            )
        else:
            spinner_text = Text(f" {spinner_label}", style=f"{Theme.MUTED} italic")

        spinner_display = Spinner("dots2", text=spinner_text, style=f"{Theme.PRIMARY} bold")

        try:
            with Live(
                spinner_display, console=console, refresh_per_second=8
            ) as live:
                from openai import AsyncStream

                model = get_active_model()
                api_params: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }
                if self.active_tools:
                    api_params["tools"] = self.active_tools
                    api_params["tool_choice"] = "auto"

                stream: AsyncStream = await self.client.chat.completions.create(**api_params)

                async for chunk in stream:
                    if hasattr(chunk, "usage") and chunk.usage:
                        api_usage = chunk.usage

                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    if delta.content:
                        full_content += delta.content
                        if full_content.strip():
                            try:
                                display_content = f"**◆ AIZEN:** {full_content}"
                                rendered = Markdown(display_content)
                                live.update(rendered)
                            except Exception:
                                display_text = Text.from_markup(
                                    f"{Theme.BADGE} {full_content}"
                                )
                                live.update(display_text)

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in accumulated_tool_calls:
                                accumulated_tool_calls[idx] = {
                                    "id": "", "name": "", "arguments": "", "type": "function",
                                }
                            if tc.id:
                                accumulated_tool_calls[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    accumulated_tool_calls[idx]["name"] += tc.function.name
                                if tc.function.arguments:
                                    accumulated_tool_calls[idx]["arguments"] += tc.function.arguments

                        names = [v["name"] for v in accumulated_tool_calls.values() if v["name"]]
                        if names and not full_content.strip():
                            tool_text = Text()
                            tool_text.append("  ◆ ", style=f"bold {Theme.ACCENT}")
                            tool_text.append("Invoking ", style=f"{Theme.TEXT}")
                            tool_text.append(f"{', '.join(names)}", style=f"bold {Theme.ACCENT}")
                            tool_text.append(" ...", style=f"{Theme.MUTED}")
                            live.update(tool_text)

        except Exception as e:
            # Re-raise — let the caller (main_loop) handle specific exception types
            raise

        # Build tool calls list
        tool_calls_list: list[dict[str, Any]] = []
        for idx in sorted(accumulated_tool_calls.keys()):
            tc = accumulated_tool_calls[idx]
            tool_calls_list.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            })

        return full_content, tool_calls_list, api_usage

    async def _execute_tools(self, tool_calls_list: list[dict]) -> list[dict]:
        """Execute tool calls (in parallel where safe) and return tool result messages."""

        async def _exec_tool(tc_dict: dict) -> dict:
            func_name = tc_dict["function"]["name"]
            if func_name.startswith("mcp_") and self.mcp_manager:
                try:
                    args = json.loads(tc_dict["function"]["arguments"])
                    result = await self.mcp_manager.call_tool(func_name, args)
                except json.JSONDecodeError:
                    result = f"Error: Invalid JSON arguments for {func_name}."
            else:
                func_struct = Struct(**tc_dict["function"])
                tc_struct = Struct(
                    id=tc_dict["id"],
                    type=tc_dict["type"],
                    function=func_struct,
                )
                result = await asyncio.to_thread(execute_tool, tc_struct, self.auto_approve)

            return {
                "role": "tool",
                "tool_call_id": tc_dict["id"],
                "name": func_name,
                "content": truncate_output(result),
            }

        tool_results = await asyncio.gather(
            *[_exec_tool(tc) for tc in tool_calls_list],
            return_exceptions=True,
        )

        # Handle individual tool failures gracefully
        for i, result in enumerate(tool_results):
            if isinstance(result, Exception):
                logger.error("Tool execution failed: %s", result)
                tool_results[i] = {
                    "role": "tool",
                    "tool_call_id": tool_calls_list[i]["id"],
                    "name": tool_calls_list[i]["function"]["name"],
                    "content": f"Error: Tool execution failed — {type(result).__name__}: {result}",
                }

        return list(tool_results)

    def _track_tokens(self, messages, full_content, api_usage):
        """Update token tracking from API usage or estimation."""
        if api_usage and hasattr(api_usage, "prompt_tokens"):
            self.token_tracker.add_api_usage(
                api_usage.prompt_tokens or 0,
                api_usage.completion_tokens or 0,
            )
            self.context_manager.update(
                (api_usage.prompt_tokens or 0) + (api_usage.completion_tokens or 0)
            )
        elif full_content:
            estimated_input = self.context_manager.estimate_messages_tokens(
                messages, self.token_tracker.estimate_tokens
            )
            estimated_output = self.token_tracker.estimate_tokens(full_content)
            self.token_tracker.add_usage(estimated_input, estimated_output)
