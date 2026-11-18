"""Testy iteratora ChunkReader."""

import pytest

from dupfinder.reader import ChunkReader


@pytest.fixture
def digits_file(tmp_path):
    path = tmp_path / "dane.bin"
    path.write_bytes(b"0123456789")
    return path


def test_reads_file_in_chunks(digits_file):
    assert list(ChunkReader(digits_file, chunk_size=4)) == [b"0123", b"4567", b"89"]


def test_limit_stops_reading_early(digits_file):
    assert list(ChunkReader(digits_file, chunk_size=4, limit=6)) == [b"0123", b"45"]


def test_zero_limit_gives_no_chunks(digits_file):
    assert list(ChunkReader(digits_file, limit=0)) == []


def test_empty_file_gives_no_chunks(tmp_path):
    path = tmp_path / "pusty.bin"
    path.write_bytes(b"")
    assert list(ChunkReader(path)) == []


def test_chunks_join_to_original_content(tmp_path):
    data = b"ab" * 100_000
    path = tmp_path / "duzy.bin"
    path.write_bytes(data)
    assert b"".join(ChunkReader(path, chunk_size=1000)) == data


def test_iter_returns_itself(digits_file):
    reader = ChunkReader(digits_file)
    assert iter(reader) is reader  # to jest iterator, a nie tylko iterable


def test_iterator_is_single_use(digits_file):
    reader = ChunkReader(digits_file, chunk_size=4)
    assert len(list(reader)) == 3
    assert list(reader) == []  # wyczerpany, nie da się go przewinąć


def test_next_raises_stop_iteration_at_the_end(digits_file):
    reader = ChunkReader(digits_file, chunk_size=100)
    next(reader)
    with pytest.raises(StopIteration):
        next(reader)


def test_context_manager_closes_reader(digits_file):
    with ChunkReader(digits_file, chunk_size=3) as reader:
        assert next(reader) == b"012"
    assert list(reader) == []  # po wyjściu z with iteracja jest zakończona


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(ChunkReader(tmp_path / "brak.bin"))


def test_invalid_arguments_raise_value_error(digits_file):
    with pytest.raises(ValueError):
        ChunkReader(digits_file, chunk_size=0)
    with pytest.raises(ValueError):
        ChunkReader(digits_file, limit=-1)