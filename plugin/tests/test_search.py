import pytest

from core.search import Result, filter_matching, match, search

LIBRARY = [
    "Fix_Mixamo_Names",
    "Batch_Current_State_to_Object",
    "List_Hiearchy",
    "OpenPose Sequence Generator From Selected Joints",
    "Mixamo_Helper_06",
]


def test_initials_match_underscore_name():
    assert match("fmn", "Fix_Mixamo_Names") is not None


def test_initials_rank_the_intended_script_first():
    assert search("fmn", LIBRARY)[0].item == "Fix_Mixamo_Names"


def test_non_subsequence_does_not_match():
    assert match("zzz", "Fix_Mixamo_Names") is None


def test_query_longer_than_text_does_not_match():
    assert match("abcdef", "abc") is None


def test_empty_query_matches_with_zero_score():
    found = match("", "anything")
    assert found is not None and found.score == 0 and found.positions == ()


def test_empty_query_returns_every_item_in_input_order():
    assert [result.item for result in search("", LIBRARY)] == LIBRARY


def test_positions_point_at_the_matched_characters():
    found = match("fmn", "Fix_Mixamo_Names")
    assert "".join("Fix_Mixamo_Names"[i] for i in found.positions).lower() == "fmn"


def test_word_boundary_beats_a_mid_word_match():
    boundary = match("mn", "Mixamo_Names")
    mid_word = match("mn", "ximamoxnames")
    assert boundary.score > mid_word.score


def test_consecutive_beats_scattered():
    consecutive = match("mix", "mixamo")
    scattered = match("mix", "mxxxixxx")
    assert consecutive.score > scattered.score


def test_matching_is_case_insensitive():
    assert match("MIXAMO", "mixamo") is not None
    assert match("mixamo", "MIXAMO") is not None


def test_exact_case_scores_higher_than_folded_case():
    assert match("Mix", "Mixamo").score > match("mix", "Mixamo").score


def test_ranking_is_deterministic_for_equal_scores():
    items = ["abc", "abc", "abc"]
    assert [result.score for result in search("abc", items)] == [result.score for result in search("abc", items)]


def test_shorter_text_wins_a_score_tie():
    results = search("op", ["op", "op_much_longer_name"])
    assert results[0].item == "op"


def test_search_accepts_a_key_function():
    items = [{"name": "Fix_Mixamo_Names"}, {"name": "List_Hiearchy"}]
    results = search("fmn", items, key=lambda item: item["name"])
    assert results[0].item["name"] == "Fix_Mixamo_Names"


def test_filter_matching_drops_scores():
    matched = filter_matching("fmn", LIBRARY)
    assert matched[0] == "Fix_Mixamo_Names"
    assert all(isinstance(item, str) for item in matched)


def test_filter_matching_excludes_non_matches():
    assert "List_Hiearchy" not in filter_matching("fmn", LIBRARY)


def test_camel_case_counts_as_a_boundary():
    camel = match("pose", "OpenPose")
    flat = match("pose", "Openpose")
    assert camel.score > flat.score


def test_result_is_hashable_and_frozen():
    result = Result("x", 1, (0,))
    with pytest.raises(Exception):
        result.score = 2
