from core.dupes import ScriptInfo, find_duplicates, normalise_stem

OPENPOSE_SPACED = ScriptInfo(
    path="/lib/OpenPose Sequence Generator From Selected Joints.py",
    name="OpenPose Sequence Generator From Selected Joints",
    size=17981,
    mtime=100.0,
)
OPENPOSE_UNDERSCORED = ScriptInfo(
    path="/user/OpenPose_Sequence_Generator_From_Selected_Joints.py",
    name="OpenPose_Sequence_Generator_From_Selected_Joints",
    size=21495,
    mtime=200.0,
)


def test_spaces_and_underscores_normalise_to_the_same_stem():
    assert normalise_stem("Fix Mixamo Names") == normalise_stem("Fix_Mixamo_Names")


def test_py_suffix_is_dropped():
    assert normalise_stem("Fix_Mixamo_Names.py") == "fix_mixamo_names"


def test_directories_are_ignored():
    assert normalise_stem("/a/b/Fix_Mixamo_Names.py") == "fix_mixamo_names"


def test_trailing_version_markers_are_stripped():
    assert normalise_stem("Universal_Rig_Normalizer_v3") == "universal_rig_normalizer"
    assert normalise_stem("Mixamo_Helper_06") == "mixamo_helper"
    assert normalise_stem("OpenPose v4.5") == "openpose"


def test_only_a_trailing_version_is_stripped():
    assert normalise_stem("v3_Rig_Tool") == "v3_rig_tool"


def test_the_two_openpose_versions_group_together():
    groups = find_duplicates([OPENPOSE_SPACED, OPENPOSE_UNDERSCORED])
    assert len(groups) == 1
    assert len(groups[0].scripts) == 2


def test_the_newest_version_comes_first():
    groups = find_duplicates([OPENPOSE_SPACED, OPENPOSE_UNDERSCORED])
    assert groups[0].scripts[0] is OPENPOSE_UNDERSCORED


def test_the_larger_file_wins_an_mtime_tie():
    older = ScriptInfo(path="/a/Rig.py", name="Rig", size=10, mtime=1.0)
    bigger = ScriptInfo(path="/b/Rig.py", name="Rig", size=99, mtime=1.0)
    groups = find_duplicates([older, bigger])
    assert groups[0].scripts[0] is bigger


def test_a_unique_script_produces_no_group():
    assert find_duplicates([OPENPOSE_SPACED]) == []


def test_versioned_siblings_are_reported_as_duplicates():
    v3 = ScriptInfo(path="/a/Universal_Rig_Normalizer_v3.py", name="Universal_Rig_Normalizer_v3", mtime=2.0)
    plain = ScriptInfo(path="/a/Universal_Rig_Normalizer.py", name="Universal_Rig_Normalizer", mtime=1.0)
    groups = find_duplicates([plain, v3])
    assert [group.stem for group in groups] == ["universal_rig_normalizer"]


def test_groups_are_ordered_by_stem():
    pairs = []
    for stem in ("zeta", "alpha"):
        pairs.append(ScriptInfo(path=f"/a/{stem}.py", name=stem))
        pairs.append(ScriptInfo(path=f"/b/{stem}.py", name=stem))
    assert [group.stem for group in find_duplicates(pairs)] == ["alpha", "zeta"]


def test_nameless_entries_fall_back_to_the_path():
    a = ScriptInfo(path="/a/Rig.py", name="")
    b = ScriptInfo(path="/b/Rig.py", name="")
    assert len(find_duplicates([a, b])) == 1
