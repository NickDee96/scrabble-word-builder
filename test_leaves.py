"""Sanity tests for the heuristic leave evaluator."""
from leaves import leave_value


def test_empty_leave_is_zero():
    assert leave_value("") == 0.0


def test_blank_and_s_are_valuable():
    assert leave_value("?") > 20
    assert leave_value("S") > 5
    assert leave_value("S") > leave_value("V")


def test_q_without_u_is_bad():
    assert leave_value("Q") < leave_value("QU")
    assert leave_value("Q") < -10


def test_good_bingo_leave_beats_clunky():
    assert leave_value("ERS") > leave_value("UVW")


def test_duplicates_penalised():
    assert leave_value("EE") < 2 * leave_value("E")


def test_all_vowels_penalised():
    assert leave_value("AEI") < leave_value("AEN")
