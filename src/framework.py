"""Seven-factor prediction framework for CS postgraduate exam score lines."""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# ── Scoring scale ──
# Each factor returns a score from -5 to +5:
#   +5 = strong upward pressure on score line
#    0 = neutral
#   -5 = strong downward pressure

# ── Weights (refined from 13-case backtest) ──
WEIGHTS = {
    "mean_reversion": 0.23,
    "quota_elasticity": 0.20,
    "substitute_pricing": 0.17,
    "community_heat": 0.16,
    "admission_ratio": 0.10,
    "established_facts": 0.10,
    "survivorship_bias": 0.08,
}

# ── Score → Δ mapping ──
SCORE_TO_DELTA = [
    (-10.0, -2.0, (-35, -20)),
    (-2.0, -1.0, (-20, -10)),
    (-1.0, 0.0, (-10, 0)),
    (0.0, 1.0, (0, 15)),
    (1.0, 3.0, (15, 30)),
    (3.0, 5.0, (30, 45)),
    (5.0, 99.0, (40, 60)),
]


@dataclass
class SchoolProgram:
    """Data for one school + program."""

    school: str
    major: str
    major_type: str  # "学硕" or "专硕"
    college: str
    exam_code: str  # "11408" | "22408" | "842" | "855"

    # Historical score lines
    scores: dict[int, float] = field(default_factory=dict)

    # Historical admission stats
    admitted: dict[int, int] = field(default_factory=dict)
    avg_scores: dict[int, float] = field(default_factory=dict)
    min_scores: dict[int, float] = field(default_factory=dict)
    max_scores: dict[int, float] = field(default_factory=dict)
    ratios: dict[int, float] = field(default_factory=dict)

    # Peer schools for substitute pricing
    peers: list[str] = field(default_factory=list)
    peer_scores: dict[str, dict[int, float]] = field(default_factory=dict)

    # Flags
    is_985: bool = True
    exam_reform_year: Optional[int] = None  # Year exam subject changed
    first_year_data: Optional[int] = None


@dataclass
class PredictionResult:
    """Prediction output for one school + program."""

    school: str
    major: str
    exam_code: str
    current_score: float
    predicted_delta: tuple[int, int]
    predicted_score: tuple[int, int]
    total_score: float
    factor_breakdown: dict[str, float]
    rule_flags: list[str]
    confidence: str  # "high" | "medium" | "low"
    narrative: str


class PredictionEngine:
    """Multi-factor prediction engine for 408 exam score lines."""

    def __init__(self, global_heat: float = None):
        self.global_heat = global_heat

    # ── Factor 1: Mean Reversion ──
    def _mean_reversion(self, sp: SchoolProgram, target_year: int) -> float:
        years = [y for y in sp.scores if y < target_year]
        if len(years) < 3:
            return 0.0

        recent = sorted(years)[-4:]
        values = [sp.scores[y] for y in recent]
        mean = np.mean(values)
        current = sp.scores.get(target_year - 1, mean)

        deviation = current - mean

        # Non-linear amplification for extreme deviations
        multiplier = 1.0
        if abs(deviation) > 30:
            multiplier = 1.5
        elif abs(deviation) > 20:
            multiplier = 1.3

        # Score is below mean → upward pressure (positive score)
        # Score is above mean → downward pressure (negative score)
        raw = -deviation * 0.2 * multiplier
        return max(-5.0, min(5.0, raw))

    # ── Factor 2: Quota Elasticity ──
    def _quota_elasticity(self, sp: SchoolProgram, target_year: int) -> float:
        prev_year = target_year - 1
        prev2_year = target_year - 2

        q_prev = sp.admitted.get(prev_year)
        q_prev2 = sp.admitted.get(prev2_year)

        if q_prev is None:
            return 0.0

        if q_prev2 and q_prev2 > 0:
            change_pct = (q_prev - q_prev2) / q_prev2 * 100
        else:
            return 0.0

        # Fewer slots → higher score line
        if change_pct < -50:
            return 5.0
        elif change_pct < -20:
            return 3.0
        elif change_pct < -5:
            return 1.0
        elif change_pct > 50:
            return -3.0
        elif change_pct > 20:
            return -2.0
        elif change_pct > 5:
            return -1.0
        return 0.0

    # ── Factor 3: Substitute Pricing ──
    def _substitute_pricing(self, sp: SchoolProgram, target_year: int) -> float:
        prev_year = target_year - 1
        current = sp.scores.get(prev_year)
        if current is None or not sp.peer_scores:
            return 0.0

        peer_vals = []
        for peer, pscores in sp.peer_scores.items():
            pv = pscores.get(prev_year)
            if pv is not None:
                peer_vals.append(pv)

        if not peer_vals:
            return 0.0

        peer_mean = np.mean(peer_vals)
        gap = peer_mean - current  # positive = we are cheaper (bargain)

        return max(-5.0, min(5.0, gap * 0.15))

    # ── Factor 4: Community Heat ──
    def _community_heat(self, sp: SchoolProgram, target_year: int) -> float:
        prev_year = target_year - 1
        current = sp.scores.get(prev_year)
        if current is None:
            return 0.0

        score = 0.0

        # Extreme low scores generate "bargain hunting" narrative
        years = [y for y in sp.scores if y < target_year]
        if len(years) >= 3:
            recent_mean = np.mean([sp.scores[y] for y in sorted(years)[-4:]])
            if current < recent_mean - 15:
                score += 3.0
            elif current < recent_mean - 5:
                score += 1.5

        # Extreme high scores generate "avoid" narrative
        if len(years) >= 3:
            if current > recent_mean + 15:
                score -= 3.0
            elif current > recent_mean + 5:
                score -= 1.0

        # Low ratio → "easy to get in" → attracts applicants
        ratio = sp.ratios.get(prev_year)
        if ratio is not None and ratio < 1.15:
            score += 2.0
        elif ratio is not None and ratio > 2.0:
            score -= 2.0

        return max(-5.0, min(5.0, score))

    # ── Factor 5: Admission Ratio ──
    def _admission_ratio(self, sp: SchoolProgram, target_year: int) -> float:
        prev_year = target_year - 1
        ratio = sp.ratios.get(prev_year)

        if ratio is None:
            return 0.0

        if ratio < 1.10:
            return 4.0
        elif ratio < 1.20:
            return 2.0
        elif ratio < 1.50:
            return 0.0
        elif ratio < 2.00:
            return -2.0
        else:
            return -4.0

    # ── Factor 6: Established Facts ──
    def _established_facts(self, sp: SchoolProgram, target_year: int) -> float:
        score = 0.0
        prev_year = target_year - 1

        # Exam reform: self-proposition → 408
        if sp.exam_reform_year and sp.exam_reform_year == prev_year:
            score += 1.5

        # Extreme score in previous year becomes "community fact"
        current = sp.scores.get(prev_year)
        if current is not None:
            years = [y for y in sp.scores if y < target_year and y != prev_year]
            if years:
                prev_mean = np.mean([sp.scores[y] for y in years[-3:]])
                if current < prev_mean - 20:
                    score += 4.0  # "bargain" narrative
                elif current > prev_mean + 20:
                    score -= 4.0  # "overpriced" narrative

        return max(-5.0, min(5.0, score))

    # ── Factor 7: Survivorship Bias ──
    def _survivorship_bias(self, sp: SchoolProgram, target_year: int) -> float:
        prev_year = target_year - 1
        current = sp.scores.get(prev_year)
        ratio = sp.ratios.get(prev_year)

        if current is None:
            return 0.0

        score = 0.0
        # Low score + low ratio → many success stories → attracts next year
        if current < 320 and (ratio is not None and ratio < 1.3):
            score += 3.0
        elif current < 340 and (ratio is not None and ratio < 1.3):
            score += 1.5

        # High score → few success stories → deters next year
        if current > 380:
            score -= 1.0

        return max(-5.0, min(5.0, score))

    # ── Rules Engine ──
    def _apply_rules(self, sp: SchoolProgram, target_year: int,
                     factor_scores: dict) -> tuple[float, list[str]]:
        bonus = 0.0
        flags = []
        prev_year = target_year - 1
        current = sp.scores.get(prev_year)

        # R1: Compound arbitrage
        sub_gap = factor_scores.get("substitute_pricing", 0)
        ratio = sp.ratios.get(prev_year)
        if sub_gap > 3.0 and ratio is not None and ratio < 1.15:
            bonus += 2.5
            flags.append("R1: compound-arbitrage (+2.5)")

        # R2: Cross-school spillover detection
        for peer, pscores in sp.peer_scores.items():
            peer_prev = pscores.get(prev_year)
            peer_prev2 = pscores.get(prev_year - 1)
            if peer_prev and peer_prev2 and (peer_prev - peer_prev2) > 20:
                if current and peer_prev > current:
                    bonus += 1.5
                    flags.append(f"R2: spillover-from-{peer} (+1.5)")
                    break

        # R3: Absolute floor bounce
        if current is not None and current < 310 and sp.is_985:
            bonus += 1.0
            flags.append("R3: absolute-floor-bounce (+1.0)")

        # R4: Exam reform transition recovery
        if sp.exam_reform_year and sp.exam_reform_year == prev_year - 1:
            bonus += 1.0
            flags.append(f"R4: reform-recovery (+1.0)")

        # R5: Non-linear mean reversion amplifier
        if current is not None:
            years = [y for y in sp.scores if y < target_year]
            if len(years) >= 3:
                mean = np.mean([sp.scores[y] for y in sorted(years)[-4:]])
                dev = current - mean
                if abs(dev) > 30:
                    flags.append(f"R5: extreme-deviation x1.5 (dev={dev:.0f})")
                elif abs(dev) > 20:
                    flags.append(f"R5: significant-deviation x1.3 (dev={dev:.0f})")

        return bonus, flags

    # ── Predict ──
    def predict(self, sp: SchoolProgram, target_year: int) -> PredictionResult:
        prev_year = target_year - 1
        current = sp.scores.get(prev_year, 0)

        factor_scores = {
            "mean_reversion": self._mean_reversion(sp, target_year),
            "quota_elasticity": self._quota_elasticity(sp, target_year),
            "substitute_pricing": self._substitute_pricing(sp, target_year),
            "community_heat": self._community_heat(sp, target_year),
            "admission_ratio": self._admission_ratio(sp, target_year),
            "established_facts": self._established_facts(sp, target_year),
            "survivorship_bias": self._survivorship_bias(sp, target_year),
        }

        # Weighted sum
        total = sum(
            factor_scores[k] * WEIGHTS[k] for k in WEIGHTS
        )

        # Global heat
        if self.global_heat is not None:
            gh = self.global_heat
        else:
            # Auto-detect: check if many schools are below their mean
            years = [y for y in sp.scores if y < target_year]
            if len(years) >= 3:
                mean = np.mean([sp.scores[y] for y in sorted(years)[-4:]])
                gh = 0.8 if (current < mean - 5) else 0.3
            else:
                gh = 0.3
        total += gh

        # Rules
        rule_bonus, rule_flags = self._apply_rules(sp, target_year, factor_scores)
        total += rule_bonus

        # Map total score to delta range
        delta_range = (0, 0)
        for lo, hi, dr in SCORE_TO_DELTA:
            if lo <= total < hi:
                delta_range = dr
                break

        # Confidence
        if abs(total) > 3.0:
            conf = "high"
        elif abs(total) > 1.5:
            conf = "medium"
        else:
            conf = "low"

        # Narrative
        top_factors = sorted(factor_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        top_names = [k for k, v in top_factors[:2] if abs(v) > 0.5]
        direction = "上涨" if total > 0.3 else ("下跌" if total < -0.3 else "持平")
        narrative = f"{direction}（主驱动力: {', '.join(top_names) if top_names else '均衡'}）"

        return PredictionResult(
            school=sp.school,
            major=sp.major,
            exam_code=sp.exam_code,
            current_score=current,
            predicted_delta=delta_range,
            predicted_score=(int(current + delta_range[0]), int(current + delta_range[1])),
            total_score=round(total, 2),
            factor_breakdown={k: round(v, 1) for k, v in factor_scores.items()},
            rule_flags=rule_flags,
            confidence=conf,
            narrative=narrative,
        )

    def predict_all(self, schools: list[SchoolProgram],
                    target_year: int) -> list[PredictionResult]:
        results = []
        for sp in schools:
            results.append(self.predict(sp, target_year))
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results

    def backtest(self, schools: list[SchoolProgram],
                 target_year: int, force_global_heat: float = None) -> list[dict]:
        """Run backtest: predict target_year using only pre-target_year data,
        compare with actual scores."""
        results = []
        for sp in schools:
            actual = sp.scores.get(target_year)
            if actual is None:
                continue

            # Force global heat for backtest if specified
            if force_global_heat is not None:
                saved_heat = self.global_heat
                self.global_heat = force_global_heat

            # Temporarily hide target_year data
            saved = sp.scores.pop(target_year, None)
            saved_admitted = sp.admitted.pop(target_year, None)
            saved_avg = sp.avg_scores.pop(target_year, None)
            saved_min = sp.min_scores.pop(target_year, None)
            saved_max = sp.max_scores.pop(target_year, None)
            saved_ratio = sp.ratios.pop(target_year, None)

            pred = self.predict(sp, target_year)

            # Restore
            if saved is not None:
                sp.scores[target_year] = saved
            if saved_admitted is not None:
                sp.admitted[target_year] = saved_admitted
            if saved_avg is not None:
                sp.avg_scores[target_year] = saved_avg
            if saved_min is not None:
                sp.min_scores[target_year] = saved_min
            if saved_max is not None:
                sp.max_scores[target_year] = saved_max
            if saved_ratio is not None:
                sp.ratios[target_year] = saved_ratio

            # Restore global heat
            if force_global_heat is not None:
                self.global_heat = saved_heat

            pred_mid = (pred.predicted_score[0] + pred.predicted_score[1]) / 2
            error = pred_mid - actual

            # Direction correct: predicted change direction matches actual change direction
            prev_score = sp.scores.get(target_year - 1, actual)
            pred_up = pred_mid > prev_score
            actual_up = actual > prev_score
            dir_correct = (pred_up == actual_up) or (abs(pred_mid - prev_score) < 2 and abs(actual - prev_score) < 2)

            results.append({
                "school": sp.school,
                "major": sp.major,
                "predicted_range": pred.predicted_score,
                "predicted_mid": pred_mid,
                "actual": actual,
                "error": round(error, 1),
                "direction_correct": dir_correct,
                "total_score": pred.total_score,
                "confidence": pred.confidence,
            })

        return results
