import importlib
import sys

import pytest

import c4d_stub


@pytest.fixture()
def tree(monkeypatch):
    """The shape probe 3 measured: nested folders, plus an unsaved buffer."""
    roots = [
        c4d_stub.folder(
            "scripts",
            [
                c4d_stub.script("Fix_Mixamo_Names", "/lib/Fix_Mixamo_Names.py", "a" * 10, 600000013),
                c4d_stub.folder(
                    "Batch Image To Plane MS",
                    [c4d_stub.script("Batch Image To Plane MS", "/lib/batch/Batch.py", "b" * 20, 600000015)],
                ),
            ],
        ),
        c4d_stub.script("untitled", "", "c" * 30, 600000053),
    ]
    module = c4d_stub.install(monkeypatch, roots)
    sys.modules.pop("registry", None)
    registry = importlib.import_module("registry")
    yield registry, module
    sys.modules.pop("registry", None)


def test_unsaved_buffers_are_filtered_out(tree):
    registry, _ = tree
    assert [entry.name for entry in registry.load()] == ["Fix_Mixamo_Names", "Batch Image To Plane MS"]


def test_nested_folders_are_recorded_as_a_path(tree):
    registry, _ = tree
    entries = {entry.name: entry for entry in registry.load()}
    assert entries["Fix_Mixamo_Names"].folder == "scripts"
    assert entries["Batch Image To Plane MS"].folder == "scripts/Batch Image To Plane MS"


def test_dynamic_ids_are_carried_through(tree):
    registry, _ = tree
    assert registry.load()[0].dynamic_id == 600000013


def test_char_count_comes_from_the_node_text(tree):
    registry, _ = tree
    assert registry.load()[0].char_count == 10


def test_find_matches_on_a_normalised_path(tree):
    registry, _ = tree
    assert registry.find("/lib/Fix_Mixamo_Names.py").name == "Fix_Mixamo_Names"
    assert registry.find("/lib/missing.py") is None


def test_run_prefers_call_command(tree):
    registry, module = tree
    entry = registry.load()[0]
    assert registry.run(entry) is True
    assert module.calls == [600000013]


def test_run_falls_back_when_there_is_no_dynamic_id(tree, tmp_path):
    registry, module = tree
    marker = tmp_path / "ran.txt"
    script = tmp_path / "Demo.py"
    script.write_text("open(%r, 'w').write('ok')" % str(marker), encoding="utf-8")

    entry = registry.ScriptEntry("Demo", str(script), dynamic_id=-1)
    assert registry.run(entry) is True
    assert marker.read_text(encoding="utf-8") == "ok"
    assert module.calls == []


def test_a_failing_script_is_reported_not_raised(tree, tmp_path):
    registry, _ = tree
    script = tmp_path / "Bad.py"
    script.write_text("raise RuntimeError('boom')", encoding="utf-8")
    assert registry.run(registry.ScriptEntry("Bad", str(script), dynamic_id=-1)) is False


def test_the_fallback_runner_does_not_call_main(tree, tmp_path):
    """V3 measured that Script Manager does not call ``main()``."""
    registry, _ = tree
    marker = tmp_path / "called.txt"
    script = tmp_path / "Guarded.py"
    script.write_text(
        "def main():\n"
        "    open(%r, 'a').write('x')\n" % str(marker),
        encoding="utf-8",
    )
    assert registry.run(registry.ScriptEntry("Guarded", str(script), dynamic_id=-1)) is True
    assert not marker.exists()


def test_the_fallback_runner_sets_name_and_file(tree, tmp_path):
    registry, _ = tree
    out = tmp_path / "out.txt"
    script = tmp_path / "Reports.py"
    script.write_text(
        "open(%r, 'w').write(__name__ + '|' + __file__)" % str(out), encoding="utf-8"
    )
    registry.run(registry.ScriptEntry("Reports", str(script), dynamic_id=-1))
    assert out.read_text(encoding="utf-8") == "__main__|" + str(script)


def test_library_json_is_resolved_through_gegetc4dpath(tree):
    registry, _ = tree
    assert registry.library_json_path().startswith("/library/user")
    assert registry.library_json_path().endswith("library.json")


def test_as_info_feeds_duplicate_detection(tree):
    registry, _ = tree
    from core.dupes import find_duplicates

    entries = [
        registry.ScriptEntry("OpenPose Sequence Generator", "/a/OpenPose Sequence Generator.py", -1),
        registry.ScriptEntry("OpenPose_Sequence_Generator", "/b/OpenPose_Sequence_Generator.py", -1),
    ]
    groups = find_duplicates(entry.as_info() for entry in entries)
    assert len(groups) == 1 and len(groups[0].scripts) == 2
