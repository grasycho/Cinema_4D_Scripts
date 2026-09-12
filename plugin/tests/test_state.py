import importlib
import sys

import pytest

import c4d_stub


@pytest.fixture()
def browser(monkeypatch, tmp_path):
    roots = [
        c4d_stub.folder(
            "scripts",
            [
                c4d_stub.script("Fix_Mixamo_Names", "/lib/Fix_Mixamo_Names.py", "a", 600000013),
                c4d_stub.script("List_Hiearchy", "/lib/List_Hiearchy.py", "b", 600000014),
                c4d_stub.script("Mixamo_Helper_06", "/lib/Mixamo_Helper_06.py", "c", 600000015),
                c4d_stub.script("Mixamo_Helper", "/lib/Mixamo_Helper.py", "d", 600000016),
            ],
        )
    ]
    c4d_stub.install(monkeypatch, roots)
    for name in ("registry", "ui", "ui.state"):
        sys.modules.pop(name, None)
    registry = importlib.import_module("registry")
    monkeypatch.setattr(registry, "library_json_path", lambda: str(tmp_path / "library.json"))
    state = importlib.import_module("ui.state")
    yield state, state.Browser()
    for name in ("registry", "ui", "ui.state"):
        sys.modules.pop(name, None)


def test_every_saved_script_is_listed(browser):
    state, view = browser
    assert len(view.results("", state.SCOPE_ALL)) == 4


def test_empty_query_sorts_alphabetically(browser):
    state, view = browser
    names = [item.name for item in view.results("", state.SCOPE_ALL)]
    assert names == sorted(names, key=str.lower)


def test_initials_rank_the_intended_script_first(browser):
    state, view = browser
    assert view.results("fmn", state.SCOPE_ALL)[0].name == "Fix_Mixamo_Names"


def test_tags_are_searchable(browser):
    state, view = browser
    target = view.results("", state.SCOPE_ALL)[0]
    view.set_tags(target, ["cleanup"])
    assert view.results("cleanup", state.SCOPE_ALL)[0] is target


def test_favourites_scope(browser):
    state, view = browser
    target = view.results("fmn", state.SCOPE_ALL)[0]
    assert view.results("", state.SCOPE_FAVOURITES) == []
    view.toggle_favourite(target)
    assert [item.name for item in view.results("", state.SCOPE_FAVOURITES)] == ["Fix_Mixamo_Names"]


def test_recent_scope_is_newest_first(browser):
    state, view = browser
    by_name = {item.name: item for item in view.results("", state.SCOPE_ALL)}
    view.run(by_name["List_Hiearchy"])
    view.run(by_name["Fix_Mixamo_Names"])
    assert [item.name for item in view.results("", state.SCOPE_RECENT)] == [
        "Fix_Mixamo_Names",
        "List_Hiearchy",
    ]


def test_duplicates_scope_flags_the_version_pair(browser):
    state, view = browser
    names = sorted(item.name for item in view.results("", state.SCOPE_DUPLICATES))
    assert names == ["Mixamo_Helper", "Mixamo_Helper_06"]


def test_metadata_survives_a_reload(browser, tmp_path):
    state, view = browser
    target = view.results("fmn", state.SCOPE_ALL)[0]
    view.set_description(target, "Renames Mixamo joints.")
    view.refresh()
    assert view.description(view.results("fmn", state.SCOPE_ALL)[0]) == "Renames Mixamo joints."


def test_description_falls_back_to_the_sidecar(monkeypatch, browser, tmp_path):
    state, view = browser
    script_path = tmp_path / "Demo.py"
    script_path.write_text("pass", encoding="utf-8")
    (tmp_path / "Demo.txt").write_text("From the sidecar.", encoding="utf-8")
    import registry

    assert view.description(registry.ScriptEntry("Demo", str(script_path), -1)) == "From the sidecar."


def test_running_records_the_run(browser):
    state, view = browser
    target = view.results("fmn", state.SCOPE_ALL)[0]
    assert view.run(target) is True
    assert view.entry_meta(target).run_count == 1
