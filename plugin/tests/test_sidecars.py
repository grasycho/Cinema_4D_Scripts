import os

import pytest

from core.sidecars import find_icon, read_description, tooltip


@pytest.fixture()
def script(tmp_path):
    path = tmp_path / "Fix_Mixamo_Names.py"
    path.write_text("# script", encoding="utf-8")
    return str(path)


def test_no_sidecars_at_all(script):
    assert find_icon(script) is None
    assert read_description(script) == ""
    assert tooltip(script) == ""


def test_png_icon_is_found(script, tmp_path):
    (tmp_path / "Fix_Mixamo_Names.png").write_bytes(b"x")
    assert find_icon(script) == str(tmp_path / "Fix_Mixamo_Names.png")


def test_png_wins_over_bmp(script, tmp_path):
    (tmp_path / "Fix_Mixamo_Names.bmp").write_bytes(b"x")
    (tmp_path / "Fix_Mixamo_Names.png").write_bytes(b"x")
    assert find_icon(script).endswith(".png")


def test_an_icon_for_a_different_script_is_ignored(script, tmp_path):
    (tmp_path / "Something_Else.png").write_bytes(b"x")
    assert find_icon(script) is None


def test_description_is_read_and_stripped(script, tmp_path):
    (tmp_path / "Fix_Mixamo_Names.txt").write_text("  Renames joints.\nMore.  ", encoding="utf-8")
    assert read_description(script) == "Renames joints.\nMore."


def test_tooltip_is_the_first_line(script, tmp_path):
    (tmp_path / "Fix_Mixamo_Names.txt").write_text("Renames joints.\nLong detail.", encoding="utf-8")
    assert tooltip(script) == "Renames joints."


def test_undecodable_description_does_not_raise(script, tmp_path):
    (tmp_path / "Fix_Mixamo_Names.txt").write_bytes(b"\xff\xfe\x00bad")
    assert isinstance(read_description(script), str)


def test_empty_path_is_handled(script):
    assert find_icon("") is None
    assert read_description("") == ""


def test_a_directory_is_not_mistaken_for_a_sidecar(script, tmp_path):
    os.mkdir(tmp_path / "Fix_Mixamo_Names.txt")
    assert read_description(script) == ""
