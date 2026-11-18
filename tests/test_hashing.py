"""Testy liczenia skrótów: poprawność, tryby, synchronizacja."""

import hashlib
import threading
from pathlib import Path

import pytest

from dupfinder import hashing
from dupfinder.hashing import (
    PARTIAL_SIZE,
    ProgressCounter,
    hash_file,
    hash_multiprocess,
    hash_sequential,
    hash_threaded,
    safe_hash,
)

RUNNERS = [
    pytest.param(lambda p, limit=None: hash_sequential(p, limit), id="sequential"),
    pytest.param(lambda p, limit=None: hash_threaded(p, limit, workers=4), id="threads"),
    pytest.param(lambda p, limit=None: hash_multiprocess(p, limit, workers=2), id="processes"),
]


def expected_hashes(paths, limit=None):
    """Niezależnie liczy oczekiwane skróty (wprost przez hashlib)."""
    return {
        path: hashlib.sha256(Path(path).read_bytes()[:limit]).hexdigest()
        for path in paths
    }


@pytest.fixture
def files(tmp_path):
    paths = []
    for i in range(6):
        path = tmp_path / f"f{i}.bin"
        path.write_bytes(bytes([i % 3]) * 50_000)
        paths.append(str(path))
    return paths


def test_hash_file_matches_hashlib(tmp_path):
    path = tmp_path / "dane.bin"
    path.write_bytes(b"abc" * 100_000)
    assert hash_file(str(path)) == hashlib.sha256(b"abc" * 100_000).hexdigest()


def test_hash_file_with_limit_hashes_only_the_beginning(tmp_path):
    data = bytes(range(256)) * 100
    path = tmp_path / "dane.bin"
    path.write_bytes(data)
    assert hash_file(str(path), PARTIAL_SIZE) == hashlib.sha256(data[:PARTIAL_SIZE]).hexdigest()


def test_safe_hash_returns_none_for_missing_file(tmp_path):
    path = str(tmp_path / "brak.bin")
    assert safe_hash(path) == (path, None)


def test_safe_hash_gives_up_after_repeated_permission_errors(monkeypatch):
    class LockedReader:
        def __init__(self, *args, **kwargs):
            raise PermissionError("plik zablokowany")

    monkeypatch.setattr(hashing, "ChunkReader", LockedReader)
    assert safe_hash("cokolwiek.bin") == ("cokolwiek.bin", None)


def test_progress_counter_is_thread_safe():
    counter = ProgressCounter(total=40_000)

    def work():
        for _ in range(10_000):
            counter.increment()

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert counter.done == 40_000  # bez Lock aktualizacje by się gubiły


@pytest.mark.parametrize("runner", RUNNERS)
def test_all_modes_give_correct_hashes(runner, files):
    assert runner(files) == expected_hashes(files)


@pytest.mark.parametrize("runner", RUNNERS)
def test_all_modes_support_partial_hash(runner, files):
    assert runner(files, PARTIAL_SIZE) == expected_hashes(files, PARTIAL_SIZE)


@pytest.mark.parametrize("runner", RUNNERS)
def test_all_modes_skip_missing_files(runner, files):
    missing = str(Path(files[0]).with_name("brak.bin"))
    assert runner(files + [missing]) == expected_hashes(files)


def test_threaded_reports_progress_without_gaps(files):
    seen = []
    hash_threaded(files, workers=4, on_progress=lambda done, total: seen.append(done))
    assert sorted(seen) == list(range(1, len(files) + 1))


def test_multiprocess_handles_empty_input():
    assert hash_multiprocess([]) == {}