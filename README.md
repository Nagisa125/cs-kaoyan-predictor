# CS Kaoyan Predictor (cs-kaoyan-predictor)

A multi-factor prediction system for forecasting Chinese CS postgraduate
entrance exam (408 track) admission score lines.

## Overview

This project implements a **7-factor scoring framework** combined with
**5 heuristic rules** to predict year-over-year changes in the minimum
admission score line (复试线) for 408-based CS graduate programs at
top Chinese universities.

Unlike simple linear regression or neural network approaches that only
look at historical score sequences, our framework incorporates market-style
factors such as substitution effects, community sentiment, quota elasticity,
and cross-school spillover.

## Framework

### Seven Core Factors

| # | Factor | Weight | Description |
|---|--------|--------|-------------|
| 1 | Mean Reversion | 0.23 | How far the current score line deviates from the 4-year mean |
| 2 | Quota Elasticity | 0.20 | Change in available exam admission slots |
| 3 | Substitute Pricing | 0.17 | Score gap vs same-tier peer schools |
| 4 | Community Heat | 0.16 | Discussion frequency on social platforms |
| 5 | Admission Ratio | 0.10 | Previous year's interview-to-offer ratio |
| 6 | Established Facts | 0.10 | Structural changes (exam reform, department merge) |
| 7 | Survivorship Bias | 0.08 | Distortion from success-story amplification |

### Five Heuristic Rules (R1-R5)

| Rule | Trigger | Adjustment |
|------|---------|------------|
| R1 | Substitute gap > 30 AND admission ratio < 1.15 | +2.5 boost |
| R2 | Same-tier school surges > 20 pts | +1.5 spillover to bargain schools |
| R3 | Score line < 310 at 985-level school | +1.0 absolute-floor bounce |
| R4 | First-year exam reform transition | +1.0 partial recovery |
| R5 | Score deviation > 20 pts | ×1.3 mean-reversion amplifier |

### Global Heat Coefficient

| Scope | Condition | Value |
|------|-----------|-------|
| Standard | < 50% tracked schools below 4-year mean | +0.3 |
| Elevated | ≥ 50% tracked schools below 4-year mean | +0.8 |

### Exam Code Reference

| Code | Subjects |
|------|----------|
| `11408` | Politics + English-I + Math-I + 408 |
| `22408` | Politics + English-II + Math-II + 408 |

## Usage

### CLI

```bash
# Predict all tracked schools for 2027
kaoyan-predict 2027

# Predict specific school
kaoyan-predict 2027 --schools hust,nju,zju

# Backtest framework against historical data
kaoyan-predict backtest --year 2026

# Export predictions to Excel
kaoyan-predict 2027 --export predictions.xlsx
```

### Python API

```python
from src.data.loader import load_school_data
from src.framework import PredictionEngine

engine = PredictionEngine()
schools = load_school_data()
predictions = engine.predict_all(schools, target_year=2027)

for p in predictions:
    print(f"{p.school} {p.major}: {p.predicted_score} (±{p.confidence_interval})")
```

## Backtest Performance

Validated against 13 school-program pairs (2022-2025 → 2026):

| Metric | Value |
|--------|-------|
| Direction accuracy | 100% (13/13) |
| Median absolute error | 3 pts |
| Mean absolute error | 5.5 pts |
| Within 10 pts | 92% (12/13) |

## Tracked Schools (2022-2026 data)

| School | Programs |
|--------|----------|
| 同济大学 | CS, SE, CS Tech |
| 武汉大学 | CS, SE, CS Tech, Cybersec |
| 华中科技大学 | CS, CS Tech, SE, Cybersec, AI |
| 南京大学 | CS, CS Tech, SE |
| 中山大学 | CS, CS Tech, SE, AI, Cybersec |
| 上海交通大学 | CS, CS Tech |
| 浙江大学 | CS, CS Tech, SE |
| 电子科技大学 | CS, CS Tech, SE |

## License

MIT
