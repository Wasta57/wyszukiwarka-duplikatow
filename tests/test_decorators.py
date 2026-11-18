"""Testy dekoratorów funkcji i metod."""

import logging
from pathlib import Path

import pytest

from dupfinder.decorators import log_call, measure_time, requires_root, retry


def test_measure_time_keeps_result_and_metadata(caplog):
    @measure_time
    def add(a, b):
        """Dodaje dwie liczby."""
        return a + b

    with caplog.at_level(logging.INFO, logger="dupfinder.decorators"):
        assert add(2, 3) == 5

    assert add.__name__ == "add"  # działa dzięki functools.wraps
    assert add.__doc__ == "Dodaje dwie liczby."
    assert "wykonano" in caplog.text


def test_measure_time_logs_even_when_function_raises(caplog):
    @measure_time
    def broken():
        raise ValueError("błąd")

    with caplog.at_level(logging.INFO, logger="dupfinder.decorators"):
        with pytest.raises(ValueError):
            broken()

    assert "wykonano" in caplog.text  # blok finally


def test_log_call_keeps_result_and_logs_arguments(caplog):
    @log_call
    def multiply(a, b=1):
        return a * b

    with caplog.at_level(logging.DEBUG, logger="dupfinder.decorators"):
        assert multiply(3, b=4) == 12

    assert "multiply" in caplog.text
    assert multiply.__name__ == "multiply"


def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    @retry(attempts=3, delay=0, exceptions=(ConnectionError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("brak połączenia")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_raises_runtime_error_after_all_attempts():
    @retry(attempts=2, delay=0, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("zawsze")

    with pytest.raises(RuntimeError, match="wyczerpano limit prób") as info:
        always_fails()
    assert isinstance(info.value.__cause__, ValueError)


def test_retry_does_not_catch_other_exceptions():
    calls = {"n": 0}

    @retry(attempts=3, delay=0, exceptions=(ValueError,))
    def wrong_error():
        calls["n"] += 1
        raise KeyError("inny wyjątek")

    with pytest.raises(KeyError):
        wrong_error()
    assert calls["n"] == 1  # bez ponawiania


def test_retry_keeps_metadata():
    @retry(attempts=2)
    def documented():
        """Dokumentacja."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Dokumentacja."


def test_retry_rejects_invalid_attempts():
    with pytest.raises(ValueError):
        retry(attempts=0)


class Dummy:
    """Klasa pomocnicza do testowania dekoratora metody."""

    def __init__(self, root):
        self.root = Path(root)

    @requires_root
    def work(self, value):
        """Zwraca wartość."""
        return value


def test_requires_root_allows_existing_directory(tmp_path):
    assert Dummy(tmp_path).work(42) == 42


def test_requires_root_rejects_missing_directory(tmp_path):
    with pytest.raises(NotADirectoryError):
        Dummy(tmp_path / "nie_istnieje").work(1)


def test_requires_root_keeps_metadata():
    assert Dummy.work.__name__ == "work"
    assert Dummy.work.__doc__ == "Zwraca wartość."