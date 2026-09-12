import json
import os

import pytest

from core.tags import SCHEMA, Entry, Library, migrate, normalise_key, normalise_tags

SCRIPT = "/lib/Fix_Mixamo_Names.py"
OTHER = "/lib/List_Hierarchy.py"


@pytest.fixture()
def library_path(tmp_path):
    return str(tmp_path / "library.json")


def test_missing_file_loads_as_an_empty_library(library_path):
    assert Library.load(library_path).entries == {}


def test_corrupt_file_loads_as_an_empty_library(library_path):
    with open(library_path, "w", encoding="utf-8") as handle:
        handle.write("{not json")
    assert Library.load(library_path).entries == {}


def test_round_trip_preserves_every_field(library_path):
    library = Library()
    library.set_tags(SCRIPT, ["Rigging", "mixamo"])
    library.set_description(SCRIPT, "  Renames Mixamo joints.  ")
    library.set_favourite(SCRIPT, True)
    library.record_run(SCRIPT, 1234.5)
    library.save(library_path)

    entry = Library.load(library_path).get(SCRIPT)
    assert entry == Entry(("mixamo", "rigging"), "Renames Mixamo joints.", True, 1, 1234.5)


def test_saved_file_declares_the_schema(library_path):
    Library().set_tags(SCRIPT, ["x"])
    library = Library()
    library.set_tags(SCRIPT, ["x"])
    library.save(library_path)
    with open(library_path, encoding="utf-8") as handle:
        assert json.load(handle)["schema"] == SCHEMA


def test_save_is_atomic_and_leaves_no_temp_files(tmp_path):
    path = str(tmp_path / "library.json")
    library = Library()
    library.set_tags(SCRIPT, ["x"])
    library.save(path)
    library.save(path)
    assert sorted(os.listdir(tmp_path)) == ["library.json"]


def test_save_creates_the_containing_directory(tmp_path):
    path = str(tmp_path / "nested" / "deeper" / "library.json")
    library = Library()
    library.set_tags(SCRIPT, ["x"])
    library.save(path)
    assert os.path.isfile(path)


def test_unknown_script_returns_a_blank_entry():
    assert Library().get("/nowhere.py") == Entry()


def test_tags_are_lowercased_deduplicated_and_sorted():
    assert normalise_tags([" Rig ", "rig", "Anim"]) == ("anim", "rig")


def test_blank_tags_are_dropped():
    assert normalise_tags(["", "   ", "rig"]) == ("rig",)


def test_add_and_remove_tag():
    library = Library()
    library.add_tag(SCRIPT, "rig")
    library.add_tag(SCRIPT, "Anim")
    assert library.get(SCRIPT).tags == ("anim", "rig")
    library.remove_tag(SCRIPT, "RIG")
    assert library.get(SCRIPT).tags == ("anim",)


def test_removing_the_last_tag_drops_the_entry():
    library = Library()
    library.add_tag(SCRIPT, "rig")
    library.remove_tag(SCRIPT, "rig")
    assert library.entries == {}


def test_empty_entries_are_not_written(library_path):
    library = Library()
    library.set_favourite(SCRIPT, True)
    library.set_favourite(SCRIPT, False)
    library.save(library_path)
    with open(library_path, encoding="utf-8") as handle:
        assert json.load(handle)["entries"] == {}


def test_toggle_favourite():
    library = Library()
    assert library.toggle_favourite(SCRIPT).favourite is True
    assert library.toggle_favourite(SCRIPT).favourite is False


def test_record_run_increments_the_count_and_stamps_the_time():
    library = Library()
    library.record_run(SCRIPT, 10.0)
    entry = library.record_run(SCRIPT, 20.0)
    assert (entry.run_count, entry.last_run) == (2, 20.0)


def test_recent_is_newest_first_and_limited():
    library = Library()
    library.record_run(SCRIPT, 10.0)
    library.record_run(OTHER, 20.0)
    assert library.recent() == (normalise_key(OTHER), normalise_key(SCRIPT))
    assert library.recent(limit=1) == (normalise_key(OTHER),)


def test_never_run_scripts_are_absent_from_recent():
    library = Library()
    library.set_tags(SCRIPT, ["rig"])
    assert library.recent() == ()


def test_favourites_and_with_tag():
    library = Library()
    library.set_favourite(SCRIPT, True)
    library.set_tags(OTHER, ["rig"])
    assert library.favourites() == (normalise_key(SCRIPT),)
    assert library.with_tag(" RIG ") == (normalise_key(OTHER),)


def test_all_tags_is_the_sorted_union():
    library = Library()
    library.set_tags(SCRIPT, ["rig", "mixamo"])
    library.set_tags(OTHER, ["rig", "debug"])
    assert library.all_tags() == ("debug", "mixamo", "rig")


def test_rekey_moves_an_entry_on_rename():
    library = Library()
    library.set_tags(SCRIPT, ["rig"])
    moved = library.rekey(SCRIPT, OTHER)
    assert moved.tags == ("rig",)
    assert library.get(SCRIPT) == Entry()
    assert library.get(OTHER).tags == ("rig",)


def test_rekey_of_an_unknown_path_is_a_no_op():
    library = Library()
    assert library.rekey(SCRIPT, OTHER) is None
    assert library.entries == {}


def test_relative_and_absolute_paths_share_one_key():
    library = Library()
    library.set_tags(os.path.abspath("script.py"), ["rig"])
    assert library.get("script.py").tags == ("rig",)


def test_migrate_adds_a_missing_schema():
    assert migrate({"entries": {}})["schema"] == SCHEMA


def test_migrate_rejects_a_future_schema():
    with pytest.raises(ValueError):
        migrate({"schema": SCHEMA + 1, "entries": {}})


def test_loading_a_future_schema_raises(library_path):
    with open(library_path, "w", encoding="utf-8") as handle:
        json.dump({"schema": SCHEMA + 1, "entries": {}}, handle)
    with pytest.raises(ValueError):
        Library.load(library_path)


def test_a_schemaless_document_still_loads_its_entries(library_path):
    with open(library_path, "w", encoding="utf-8") as handle:
        json.dump({"entries": {SCRIPT: {"tags": ["rig"]}}}, handle)
    assert Library.load(library_path).get(SCRIPT).tags == ("rig",)


def test_partial_entries_fill_in_defaults(library_path):
    with open(library_path, "w", encoding="utf-8") as handle:
        json.dump({"schema": SCHEMA, "entries": {SCRIPT: {"tags": ["rig"]}}}, handle)
    assert Library.load(library_path).get(SCRIPT) == Entry(("rig",))
