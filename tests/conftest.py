"""Wspólne fixture'y testów."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """Katalog testowy z duplikatami i plikami odpadającymi na różnych etapach.

    Duplikaty: a.txt = sub/a_copy.txt oraz big1.bin = sub/big1_copy.bin.
    b.txt ma ten sam rozmiar co a.txt, ale inną zawartość (odpada w etapie 2).
    big2.bin ma ten sam rozmiar i początek co big1.bin, ale inny ostatni bajt
    (odpada dopiero w etapie 3, po pełnym skrócie).
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "sub" / "a_copy.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    (tmp_path / "big1.bin").write_bytes(b"x" * 10_000 + b"A")
    (tmp_path / "big2.bin").write_bytes(b"x" * 10_000 + b"B")
    (tmp_path / "sub" / "big1_copy.bin").write_bytes(b"x" * 10_000 + b"A")
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "sub" / "note.jpg").write_text("hello!!")
    return tmp_path