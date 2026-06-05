"""
Retry logic with exponential backoff + jitter for transient API errors.
"""

import time
import random
import functools
from rich.text import Text

from .config import console


def retry_with_backoff(
    max_retries: int = 3,
    backoff_base: float = 2.0,
    retryable_exceptions: tuple | None = None,
    jitter: bool = True,
):
    """
    Decorator that retries a function on transient failures with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_base: Base for exponential backoff (delay = base ** attempt).
        retryable_exceptions: Tuple of exception types to retry on.
        jitter: If True, adds random jitter (±25%) to prevent thundering herd.
    """
    if retryable_exceptions is None:
        # Import here to avoid circular imports — these are the standard transient errors
        from openai import (
            RateLimitError as OpenAIRateLimitError,
            APITimeoutError,
            APIConnectionError as OpenAIConnectionError,
            APIStatusError,
        )
        retryable_exceptions = (
            OpenAIRateLimitError,
            APITimeoutError,
            OpenAIConnectionError,
        )

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: BaseException = RuntimeError("Retry exhausted")
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = backoff_base ** attempt
                        if jitter:
                            # Add ±25% jitter to avoid thundering herd
                            delay *= 1.0 + random.uniform(-0.25, 0.25)
                        retry_msg = Text()
                        retry_msg.append("  ⏳ ", style="yellow")
                        retry_msg.append(
                            f"{type(e).__name__}. ",
                            style="dim",
                        )
                        retry_msg.append(
                            f"Retrying in {delay:.1f}s... ({attempt + 1}/{max_retries})",
                            style="dim italic",
                        )
                        console.print(retry_msg)
                        time.sleep(delay)
                except Exception as e:
                    # Check for retryable HTTP status codes (503 Service Unavailable)
                    if hasattr(e, "status_code") and e.status_code == 503:
                        last_exception = e
                        if attempt < max_retries:
                            delay = backoff_base ** attempt
                            if jitter:
                                delay *= 1.0 + random.uniform(-0.25, 0.25)
                            retry_msg = Text()
                            retry_msg.append("  ⏳ ", style="yellow")
                            retry_msg.append("Service Unavailable (503). ", style="dim")
                            retry_msg.append(
                                f"Retrying in {delay:.1f}s... ({attempt + 1}/{max_retries})",
                                style="dim italic",
                            )
                            console.print(retry_msg)
                            time.sleep(delay)
                            continue
                    raise  # Non-retryable error, propagate immediately
            raise last_exception

        return wrapper

    return decorator
