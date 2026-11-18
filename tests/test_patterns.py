"""Testy wyrażeń regularnych."""

import pytest

from dupfinder.patterns import parse_extensions, parse_size, split_filename


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("10MB", 10 * 1024**2),
        ("1,5 GB", int(1.5 * 1024**3)),
        ("1.5KB", 1536),
        ("500k", 512_000),
        ("2048", 2048),
        ("7 B", 7),
        ("  3 mb ", 3 * 1024**2),
    ],
)
def test_parse_size_valid(text, expected):
    assert parse_size(text) == expected


@pytest.mark.parametrize("text", ["abc", "", "MB", "10 XB", "-5", "1,2,3"])
def test_parse_size_invalid(text):
    with pytest.raises(ValueError):
        parse_size(text)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("raport.pdf", ("raport", "pdf")),
        ("archive.tar.GZ", ("archive.tar", "gz")),
        (".gitignore", (".gitignore", "")),
        ("README", ("README", "")),
    ],
)
def test_split_filename(filename, expected):
    assert split_filename(filename) == expected


def test_split_filename_rejects_empty_string():
    with pytest.raises(ValueError):
        split_filename("")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("jpg, .PNG;txt", {"jpg", "png", "txt"}),
        (".jpg", {"jpg"}),
        ("JPG jpg", {"jpg"}),
        ("", set()),
        ("   ", set()),
    ],
)
def test_parse_extensions(text, expected):
    assert parse_extensions(text) == expected