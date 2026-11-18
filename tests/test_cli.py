"""Testy interfejsu wiersza poleceń."""

import pytest

import main as cli


def test_cli_prints_report(sample_tree, capsys):
    code = cli.main([str(sample_tree), "--mode", "sequential"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Grupa 1" in out
    assert "Znaleziono 2 grup duplikatów" in out


def test_cli_reports_no_duplicates(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("jeden")
    assert cli.main([str(tmp_path), "--mode", "sequential"]) == 0
    assert "Nie znaleziono duplikatów." in capsys.readouterr().out


def test_cli_returns_1_for_missing_directory(tmp_path, capsys):
    assert cli.main([str(tmp_path / "nie_istnieje")]) == 1
    assert "Błąd" in capsys.readouterr().err


def test_cli_exits_with_2_for_invalid_size(tmp_path):
    with pytest.raises(SystemExit) as info:
        cli.main([str(tmp_path), "--min-size", "abc"])
    assert info.value.code == 2


def test_cli_default_mode_is_threads():
    assert cli.build_parser().parse_args(["."]).mode == "threads"