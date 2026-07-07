"""
base.py
--------
Shared base class for every agent in the MedSaathi pipeline.

Why this exists (course concept: Multi-agent system / ADK-style design):
Each stage of the pipeline (vision, safety-check, scheduling, localization,
notification) is an independent agent with its own inputs, outputs, and
failure modes. Rather than one giant LLM call, we isolate each concern so a
failure in one stage (e.g. a blurry photo) can be retried or surfaced
without corrupting the rest of the pipeline. This matters a lot here
specifically because a silent failure could mean a missed or wrong dose.
"""

import functools
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def with_retry(max_attempts: int = 3, backoff_seconds: float = 1.5):
    """Decorator giving any agent step automatic retry with exponential backoff.

    Medical-adjacent pipelines shouldn't fail silently on a transient error
    (rate limit, flaky OCR read, network blip). This retries with backoff and
    re-raises the last error with context if all attempts fail, so the
    orchestrator can decide how to degrade gracefully.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentional broad catch here
                    last_exc = exc
                    logging.getLogger(func.__module__).warning(
                        "Attempt %s/%s failed for %s: %s",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                    )
                    if attempt < max_attempts:
                        time.sleep(backoff_seconds * attempt)
            raise RuntimeError(
                f"{func.__name__} failed after {max_attempts} attempts"
            ) from last_exc

        return wrapper

    return decorator


class Agent:
    """Common interface every pipeline agent implements."""

    name = "base_agent"

    def __init__(self, simulate: bool = False):
        self.simulate = simulate
        self.logger = logging.getLogger(self.name)

    def run(self, *args, **kwargs):
        raise NotImplementedError
