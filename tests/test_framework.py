"""Tests for the prediction framework."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from framework import PredictionEngine, SchoolProgram


def test_mean_reversion_positive():
    """Score below mean → upward pressure."""
    sp = SchoolProgram(
        school="Test", major="CS", major_type="专硕",
        college="CS", exam_code="11408",
        scores={2022: 360, 2023: 355, 2024: 350, 2025: 320},
    )
    engine = PredictionEngine(global_heat=0.3)
    score = engine._mean_reversion(sp, 2026)
    assert score > 0, f"Expected positive score, got {score}"


def test_mean_reversion_negative():
    """Score above mean → downward pressure."""
    sp = SchoolProgram(
        school="Test", major="CS", major_type="专硕",
        college="CS", exam_code="11408",
        scores={2022: 320, 2023: 330, 2024: 340, 2025: 380},
    )
    engine = PredictionEngine(global_heat=0.3)
    score = engine._mean_reversion(sp, 2026)
    assert score < 0, f"Expected negative score, got {score}"


def test_quota_shrink_positive():
    """Quota reduction → upward pressure."""
    sp = SchoolProgram(
        school="Test", major="CS", major_type="专硕",
        college="CS", exam_code="11408",
        scores={2024: 340, 2025: 330},
        admitted={2024: 100, 2025: 24},
    )
    engine = PredictionEngine(global_heat=0.3)
    score = engine._quota_elasticity(sp, 2026)
    assert score > 0, f"Expected positive (quota cut), got {score}"


def test_substitute_gap_positive():
    """Peer scores higher → bargain → upward pressure."""
    sp = SchoolProgram(
        school="Test", major="CS", major_type="专硕",
        college="CS", exam_code="11408",
        scores={2025: 330},
        peers=["Peer"], peer_scores={"Peer": {2025: 360}},
    )
    engine = PredictionEngine(global_heat=0.3)
    score = engine._substitute_pricing(sp, 2026)
    assert score > 0, f"Expected positive (bargain), got {score}"


def test_r1_compound_arbitrage():
    """R1: High gap + low ratio → bonus activated."""
    sp = SchoolProgram(
        school="Test", major="CS", major_type="专硕",
        college="CS", exam_code="11408",
        scores={2022: 350, 2023: 340, 2024: 330, 2025: 300},
        ratios={2025: 1.10},
        peers=["Peer"], peer_scores={"Peer": {2025: 350}},
    )
    engine = PredictionEngine(global_heat=0.3)
    factor_scores = {
        "substitute_pricing": engine._substitute_pricing(sp, 2026),
    }
    bonus, flags = engine._apply_rules(sp, 2026, factor_scores)
    assert bonus >= 2.5, f"R1 should activate, got bonus={bonus}"
    assert any("R1" in f for f in flags)


def test_r3_absolute_floor():
    """R3: Score < 310 at 985 → bounce bonus."""
    sp = SchoolProgram(
        school="Test", major="CS", major_type="专硕",
        college="CS", exam_code="11408", is_985=True,
        scores={2025: 305},
    )
    engine = PredictionEngine(global_heat=0.3)
    _, flags = engine._apply_rules(sp, 2026, {})
    assert any("R3" in f for f in flags)


def test_direction_consistency():
    """All 13 backtest cases have correct direction."""
    from data.schools import build_school_data
    schools = build_school_data()
    engine = PredictionEngine()
    results = engine.backtest(schools, target_year=2026)

    total = len(results)
    correct = sum(1 for r in results if r["direction_correct"])
    assert correct == total, f"Direction: {correct}/{total}"
    assert total >= 8, f"Expected >=8 cases, got {total}"
