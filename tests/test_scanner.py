"""Testy potoku generatorów."""

import inspect
import logging
from pathlib import Path

from dupfinder.scanner import group_by_size, scan, walk_directory


def names(paths):
    return {Path(p).name for p in paths}


def test_walk_directory_is_a_generator(sample_tree):
    assert inspect.isgenerator(walk_directory(sample_tree))


def test_walk_directory_finds_files_recursively(sample_tree):
    found = {entry.name for entry in walk_directory(sample_tree)}
    assert found == {
        "a.txt", "a_copy.txt", "b.txt", "big1.bin", "big2.bin",
        "big1_copy.bin", "empty.txt", "note.jpg",
    }  # katalogi nie są zwracane, tylko pliki


def test_scan_skips_empty_files_by_default(sample_tree):
    found = names(path for path, _ in scan(sample_tree))
    assert "empty.txt" not in found
    assert len(found) == 7


def test_scan_filters_by_min_size(sample_tree):
    found = names(path for path, _ in scan(sample_tree, min_size=100))
    assert found == {"big1.bin", "big2.bin", "big1_copy.bin"}


def test_scan_filters_by_extension(sample_tree):
    found = names(path for path, _ in scan(sample_tree, extensions={"txt"}))
    assert found == {"a.txt", "a_copy.txt", "b.txt"}


def test_scan_is_lazy(sample_tree):
    pipeline = scan(sample_tree)
    assert iter(pipeline) is pipeline  # generator, a nie lista


def test_group_by_size_keeps_only_groups_with_candidates(sample_tree):
    groups = group_by_size(scan(sample_tree))
    assert set(groups) == {5, 10_001}  # note.jpg (7 B) ma unikalny rozmiar
    assert names(groups[5]) == {"a.txt", "a_copy.txt", "b.txt"}
    assert len(groups[10_001]) == 3


def test_missing_directory_gives_empty_result(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert list(scan(tmp_path / "nie_istnieje")) == []
    assert "Pomijam katalog" in caplog.text