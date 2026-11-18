"""Dekoratory funkcji używane w całym projekcie."""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def measure_time[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Mierzy czas wykonania funkcji i zapisuje go w logach."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.info("[%s] wykonano w %.4f s", func.__name__, elapsed)

    return wrapper


def log_call[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Loguje (na poziomie DEBUG) argumenty wywołania i wynik funkcji."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.debug("Wywołanie %s args=%s kwargs=%s", func.__name__, args, kwargs)
        result = func(*args, **kwargs)
        logger.debug("%s zwróciła %r", func.__name__, result)
        return result

    return wrapper


def retry(
    attempts: int = 3,
    delay: float = 0.1,
    exceptions: tuple[type[BaseException], ...] = (OSError,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Fabryka dekoratorów: ponawia funkcję po wybranych wyjątkach.

    Args:
        attempts: maksymalna liczba prób (co najmniej 1).
        delay: przerwa w sekundach między próbami.
        exceptions: wyjątki, po których wolno ponowić próbę.

    Raises:
        ValueError: gdy attempts < 1.
        RuntimeError: gdy wszystkie próby się nie powiodły.
    """
    if attempts < 1:
        raise ValueError("attempts musi być >= 1")

    def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as err:
                    last_error = err
                    logger.warning(
                        "%s: próba %d/%d nieudana (%s)",
                        func.__name__, attempt, attempts, err,
                    )
                    if attempt < attempts:
                        time.sleep(delay)
            raise RuntimeError(
                f"{func.__name__}: wyczerpano limit prób ({attempts})"
            ) from last_error

        return wrapper

    return decorator