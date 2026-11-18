"""Testy klasy DuplicateFinder."""

from pathlib import Path

import pytest

from dupfinder.finder import DuplicateFinder, DuplicateGroup


def names(groups):
    return [sorted(Path(p).name for p in group.paths) for group in groups]


@pytest.mark.parametrize("mode", ["sequential", "threads", "processes"])
def test_find_returns_same_groups_in_every_mode(sample_tree, mode):
    groups = DuplicateFinder(sample_tree, mode=mode).find()
    # posortowane od największej straty miejsca
    assert names(groups) == [["big1.bin", "big1_copy.bin"], ["a.txt", "a_copy.txt"]]


def test_find_reports_wasted_space(sample_tree):
    groups = DuplicateFinder(sample_tree, mode="sequential").find()
    assert sum(group.wasted_bytes for group in groups) == 10_001 + 5


def test_files_with_same_beginning_but_different_end_are_not_duplicates(sample_tree):
    groups = DuplicateFinder(sample_tree, mode="sequential").find()
    assert all("big2.bin" not in names([g])[0] for g in groups)


def test_find_respects_min_size(sample_tree):
    groups = DuplicateFinder(sample_tree, min_size=100, mode="sequential").find()
    assert names(groups) == [["big1.bin", "big1_copy.bin"]]


def test_find_respects_extensions(sample_tree):
    groups = DuplicateFinder(sample_tree, extensions={"txt"}, mode="sequential").find()
    assert names(groups) == [["a.txt", "a_copy.txt"]]


def test_find_returns_empty_list_when_no_duplicates(tmp_path):
    (tmp_path / "a.txt").write_text("jeden")
    (tmp_path / "b.txt").write_text("dwa!!")
    assert DuplicateFinder(tmp_path, mode="sequential").find() == []


def test_find_rejects_missing_directory(tmp_path):
    with pytest.raises(NotADirectoryError):
        DuplicateFinder(tmp_path / "nie_istnieje").find()


def test_find_keeps_its_name_despite_decorators():
    assert DuplicateFinder.find.__name__ == "find"


def test_min_size_property_validates_value(tmp_path):
    finder = DuplicateFinder(tmp_path)
    finder.min_size = 5
    assert finder.min_size == 5
    with pytest.raises(ValueError):
        finder.min_size = -1


def test_constructor_validates_min_size_through_setter(tmp_path):
    with pytest.raises(ValueError):
        DuplicateFinder(tmp_path, min_size=-1)


def test_constructor_rejects_unknown_mode(tmp_path):
    with pytest.raises(ValueError):
        DuplicateFinder(tmp_path, mode="turbo")


def test_from_strings_parses_size_and_extensions(tmp_path):
    finder = DuplicateFinder.from_strings(
        str(tmp_path), min_size="10KB", extensions="JPG, .png", mode="sequential"
    )
    assert finder.min_size == 10 * 1024
    assert finder.extensions == {"jpg", "png"}
    assert finder.mode == "sequential"


def test_from_strings_without_extensions_means_all_files(tmp_path):
    assert DuplicateFinder.from_strings(str(tmp_path)).extensions is None


def test_from_strings_works_for_subclasses(tmp_path):
    class Sub(DuplicateFinder):
        pass

    assert isinstance(Sub.from_strings(str(tmp_path)), Sub)  # classmethod dostaje cls


@pytest.mark.parametrize(
    ("size", "expected"),
    [(0, "0 B"), (500, "500 B"), (1024, "1.0 KB"), (1536, "1.5 KB"), (1024**2, "1.0 MB")],
)
def test_format_size(size, expected):
    assert DuplicateFinder.format_size(size) == expected


def test_duplicate_group_wasted_bytes():
    group = DuplicateGroup(size=100, digest="x", paths=("a", "b", "c"))
    assert group.wasted_bytes == 200  # dwie nadmiarowe kopie