"""Tests for aizen.agent (AgentRunner)."""

from unittest.mock import AsyncMock

import pytest

from aizen.agent import AgentRunner
from aizen.utils import Struct


class MockTokenTracker:
    def __init__(self):
        self.usage_added = False

    def estimate_tokens(self, text):
        return len(text) // 4

    def add_usage(self, input_tokens, output_tokens):
        self.usage_added = True

    def add_api_usage(self, input_tokens, output_tokens):
        self.usage_added = True


class MockContextManager:
    def estimate_messages_tokens(self, messages, estimator):
        return 100

    def update(self, tokens):
        pass


@pytest.fixture
def mock_client():
    client = AsyncMock()

    # Mock stream response
    async def mock_stream(**kwargs):
        class MockDelta:
            def __init__(self, content, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        class MockChoice:
            def __init__(self, delta):
                self.delta = delta

        class MockChunk:
            def __init__(self, content, tool_calls=None, usage=None):
                self.choices = [MockChoice(MockDelta(content, tool_calls))]
                self.usage = usage

        async def generator():
            # Yield a couple of chunks
            yield MockChunk("Hello")
            yield MockChunk(" world", usage=Struct(prompt_tokens=10, completion_tokens=5))

        return generator()

    client.chat.completions.create = mock_stream
    return client


@pytest.mark.asyncio
async def test_agent_runner_simple_turn(mock_client):
    tracker = MockTokenTracker()
    context = MockContextManager()

    runner = AgentRunner(
        client=mock_client,
        active_tools=[],
        context_manager=context,
        token_tracker=tracker,
    )

    messages = [{"role": "user", "content": "Hi"}]

    await runner.run_turn(messages)

    # Should have appended assistant response
    assert len(messages) == 2
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == "Hello world"

    assert tracker.usage_added is True


@pytest.mark.asyncio
async def test_agent_runner_with_tools():
    # A client that yields a tool call on first iteration, then text on second iteration
    client = AsyncMock()

    call_count = 0
    async def mock_stream(**kwargs):
        nonlocal call_count
        call_count += 1

        class MockDelta:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        class MockChoice:
            def __init__(self, delta):
                self.delta = delta

        class MockChunk:
            def __init__(self, content=None, tool_calls=None, usage=None):
                self.choices = [MockChoice(MockDelta(content, tool_calls))] if (content or tool_calls) else []
                self.usage = usage

        async def generator():
            if call_count == 1:
                # Yield tool call
                tc = Struct(index=0, id="call_1", function=Struct(name="my_tool", arguments='{"arg":"val"}'))
                yield MockChunk(tool_calls=[tc])
            else:
                # Yield text
                yield MockChunk("Done")

        return generator()

    client.chat.completions.create = mock_stream

    runner = AgentRunner(
        client=client,
        active_tools=[{"type": "function", "function": {"name": "my_tool"}}],
        context_manager=MockContextManager(),
        token_tracker=MockTokenTracker(),
    )

    # Mock the execute_tools internal to avoid real execution
    async def mock_execute(tool_calls):
        return [{"role": "tool", "tool_call_id": tool_calls[0]["id"], "name": "my_tool", "content": "tool result"}]
    runner._execute_tools = mock_execute

    messages = [{"role": "user", "content": "Run tool"}]
    await runner.run_turn(messages)

    # History: user -> assistant (with tool_calls) -> tool -> assistant (text)
    assert len(messages) == 4
    assert messages[1]["role"] == "assistant"
    assert "tool_calls" in messages[1]
    assert messages[2]["role"] == "tool"
    assert messages[2]["content"] == "tool result"
    assert messages[3]["role"] == "assistant"
    assert messages[3]["content"] == "Done"


@pytest.mark.asyncio
async def test_agent_runner_auto_mode():
    runner = AgentRunner(
        client=AsyncMock(),
        active_tools=[],
        context_manager=MockContextManager(),
        token_tracker=MockTokenTracker(),
        is_auto_mode=True,
        max_auto_iterations=1,
    )

    # We'll just break the stream immediately to simulate turn completion
    async def mock_stream(msgs, **kwargs):
        return ("Done", [], None)
    runner._stream_response = mock_stream

    messages = []

    # First turn should hit iteration limit since max_auto_iterations=1 and count goes 0->1
    await runner.run_turn(messages)

    assert runner.is_auto_mode is True  # Count is 1, max is 1, not exceeded
    assert runner.auto_iteration_count == 1

    # Second turn will exceed limit
    await runner.run_turn(messages)
    assert runner.is_auto_mode is False
    assert runner.auto_iteration_count == 0
    assert "reached the maximum number of autonomous iterations" in messages[-2]["content"]
