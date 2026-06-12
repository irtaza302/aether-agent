"""Tests for aizen.retry module."""

import asyncio
from unittest.mock import patch

import pytest
from openai import APITimeoutError

from aizen.retry import _compute_delay, _is_retryable_503, retry_with_backoff


class TestRetryDelay:
    def test_compute_delay_no_jitter(self):
        # base=2.0
        assert _compute_delay(2.0, 0, jitter=False) == 1.0  # 2^0
        assert _compute_delay(2.0, 1, jitter=False) == 2.0  # 2^1
        assert _compute_delay(2.0, 2, jitter=False) == 4.0  # 2^2

    def test_compute_delay_with_jitter(self):
        delay = _compute_delay(2.0, 1, jitter=True)
        # Should be between 2.0 * 0.75 and 2.0 * 1.25
        assert 1.5 <= delay <= 2.5


class TestIsRetryable503:
    class FakeException(Exception):
        def __init__(self, status_code=None):
            if status_code:
                self.status_code = status_code
            super().__init__("error")

    def test_is_503(self):
        assert _is_retryable_503(self.FakeException(503)) is True
        assert _is_retryable_503(self.FakeException(404)) is False
        assert _is_retryable_503(self.FakeException()) is False
        assert _is_retryable_503(ValueError("test")) is False


class TestRetrySync:
    @patch("time.sleep")
    def test_sync_success_first_try(self, mock_sleep):
        @retry_with_backoff(max_retries=2, jitter=False)
        def func():
            return "success"

        assert func() == "success"
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_sync_retry_then_success(self, mock_sleep):
        attempts = 0

        @retry_with_backoff(max_retries=2, jitter=False, retryable_exceptions=(ValueError,))
        def func():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("transient error")
            return "success"

        assert func() == "success"
        assert attempts == 2
        mock_sleep.assert_called_once_with(1.0)  # 2^0 = 1.0

    @patch("time.sleep")
    def test_sync_retry_exhausted(self, mock_sleep):
        attempts = 0

        @retry_with_backoff(max_retries=2, jitter=False, retryable_exceptions=(ValueError,))
        def func():
            nonlocal attempts
            attempts += 1
            raise ValueError("always fail")

        with pytest.raises(ValueError, match="always fail"):
            func()
        
        assert attempts == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    def test_sync_non_retryable_exception(self):
        @retry_with_backoff(max_retries=2, retryable_exceptions=(ValueError,))
        def func():
            raise TypeError("not retryable")

        with pytest.raises(TypeError, match="not retryable"):
            func()


class TestRetryAsync:
    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_async_success_first_try(self, mock_sleep):
        @retry_with_backoff(max_retries=2, jitter=False)
        async def func():
            return "success"

        assert await func() == "success"
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_async_retry_then_success(self, mock_sleep):
        attempts = 0

        @retry_with_backoff(max_retries=2, jitter=False, retryable_exceptions=(ValueError,))
        async def func():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("transient error")
            return "success"

        assert await func() == "success"
        assert attempts == 2
        mock_sleep.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_async_retry_exhausted(self, mock_sleep):
        attempts = 0

        @retry_with_backoff(max_retries=2, jitter=False, retryable_exceptions=(ValueError,))
        async def func():
            nonlocal attempts
            attempts += 1
            raise ValueError("always fail")

        with pytest.raises(ValueError, match="always fail"):
            await func()
        
        assert attempts == 3
        assert mock_sleep.call_count == 2
        
    @pytest.mark.asyncio
    async def test_async_openai_default_exceptions(self):
        @retry_with_backoff(max_retries=1, jitter=False)
        async def func():
            # APITimeoutError requires a request object, but we can mock it
            from httpx import Request
            req = Request("GET", "http://example.com")
            raise APITimeoutError(request=req)

        with pytest.raises(APITimeoutError):
            with patch("asyncio.sleep") as mock_sleep:
                await func()
                assert mock_sleep.call_count == 1
