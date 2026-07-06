"""Tests for the two-agent self-play engine (selfplay.py)."""
from board_engine import generate_moves
from selfplay import board_to_text, new_game, parse_board, play_game, play_turn


def test_new_game_deals_full_bag():
    state = new_game(seed=1)
    assert len(state["racks"]["A"]) == 7
    assert len(state["racks"]["B"]) == 7
    assert len(state["bag"]) == 100 - 14  # full bag minus the two opening racks
    assert state["scores"] == {"A": 0, "B": 0}
    assert state["turn"] == "A"
    assert state["over"] is False
    assert set(state["board"]) <= {".", "\n"}


def test_board_text_round_trip_with_blank():
    empty = "\n".join("." * 15 for _ in range(15))
    letters, blanks = parse_board(empty)
    letters[7][7] = "S"
    letters[7][8] = "O"
    blanks[7][8] = True  # a blank playing O
    text = board_to_text(letters, blanks)
    lines = text.split("\n")
    assert lines[7][7] == "S"  # real tile -> uppercase
    assert lines[7][8] == "o"  # blank tile -> lowercase
    l2, b2 = parse_board(text)
    assert l2[7][7] == "S" and b2[7][7] is False
    assert l2[7][8] == "O" and b2[7][8] is True


def test_equity_turn_plays_and_scores():
    state = new_game(seed=3)
    before = state["board"]
    new_state, move = play_turn(state, "equity", seed=3)
    assert move["player"] == "A"
    if move["type"] == "play":
        assert move["score"] > 0
        assert new_state["scores"]["A"] == move["score"]
        assert new_state["board"] != before  # a tile was placed
        assert new_state["turn"] == "B"  # turn advanced
        assert len(new_state["racks"]["A"]) == 7  # rack refilled from the bag
    else:
        assert move["type"] in ("pass", "exchange")


def test_score_turn_plays_the_highest_scoring_move():
    state = new_game(seed=8)
    new_state, move = play_turn(state, "score", seed=8)
    assert move["player"] == "A"
    if move["type"] == "play":
        assert move["score"] > 0
        assert new_state["scores"]["A"] == move["score"]
        # The score agent must not be beaten on raw points by any legal play.
        from board_engine import generate_moves
        from selfplay import parse_board

        letters, blanks = parse_board(state["board"])
        best = max(generate_moves(letters, blanks, state["racks"]["A"]), key=lambda m: m.score)
        assert move["score"] == best.score


def test_simulation_turn_reports_win_pct():
    state = new_game(seed=11)
    _, move = play_turn(state, "simulation", time_budget_ms=800, max_candidates=4, seed=11)
    if move["type"] == "play":
        assert 0.0 <= move["winPct"] <= 1.0
        assert move["iterations"] >= 1


def test_game_terminates_and_scores():
    state = new_game(seed=5)
    turns = 0
    while not state["over"] and turns < 100:
        state, _ = play_turn(state, "equity", seed=100 + turns)
        turns += 1
    assert state["over"] is True
    assert state["winner"] in ("A", "B", "tie")
    assert state["scores"]["A"] + state["scores"]["B"] > 0  # a real game was played


def test_over_state_is_noop():
    state = new_game(seed=2)
    state["over"] = True
    same, move = play_turn(state, "equity", seed=2)
    assert move["type"] == "none"
    assert same["scores"] == state["scores"]


def test_score_agent_picks_max_score_move():
    state = new_game(seed=15)
    letters, blanks = parse_board(state["board"])
    moves = generate_moves(letters, blanks, state["racks"]["A"])
    assert moves, "a fresh rack should have at least one opening play"
    best_score = max(m.score for m in moves)
    _, move = play_turn(state, "score", seed=15)
    assert move["type"] == "play"
    assert move["score"] == best_score  # the score agent maximizes raw points


def test_new_game_respects_first_mover():
    assert new_game(seed=1, first="B")["turn"] == "B"
    assert new_game(seed=1, first="bogus")["turn"] == "A"


def test_play_game_finishes_with_winner():
    result = play_game("score", "equity", seed=3, first="A")
    assert result["winner"] in ("A", "B", "tie")
    assert result["turns"] > 0
    assert set(result["scores"]) == {"A", "B"}


def test_play_game_is_deterministic_with_seed():
    a = play_game("score", "equity", seed=7, first="A")
    b = play_game("score", "equity", seed=7, first="A")
    assert a["scores"] == b["scores"] and a["winner"] == b["winner"]

