"""CLI entry point for the prediction system."""

import argparse
import sys

from framework import PredictionEngine
from data.schools import build_school_data


def cmd_predict(args):
    schools = build_school_data()
    engine = PredictionEngine()

    if args.schools:
        schools = [s for s in schools if any(
            kw in s.school + s.major for kw in args.schools.split(",")
        )]
        if not schools:
            print(f"No schools matched filter: {args.schools}")
            return

    results = engine.predict_all(schools, target_year=args.year)

    print(f"\n{'='*100}")
    print(f"  2027 年 408 考研复试线预测 (基于七维因子框架)")
    print(f"{'='*100}\n")
    print(f"{'排名':<4} {'学校':<8} {'专业':<28} {'科目':<8} {'2026线':<8} {'2027预测':<14} {'变化':<10} {'置信度':<6}")
    print("-" * 100)

    for i, r in enumerate(results, 1):
        delta_str = f"+{r.predicted_delta[0]}~+{r.predicted_delta[1]}" if r.predicted_delta[0] >= 0 else f"{r.predicted_delta[0]}~{r.predicted_delta[1]}"
        pred_str = f"{r.predicted_score[0]}-{r.predicted_score[1]}"
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(r.confidence, "⚪")
        print(f"{i:<4} {r.school:<8} {r.major:<28} {r.exam_code:<8} {r.current_score:<8.0f} {pred_str:<14} {delta_str:<10} {conf_icon} {r.confidence}")

    print("-" * 100)
    print()

    # Detailed breakdown for each
    for r in results:
        print(f"\n{'─'*80}")
        print(f"  {r.school} · {r.major} ({r.exam_code})")
        print(f"  2026 复试线: {r.current_score:.0f} → 2027 预测: {r.predicted_score[0]}-{r.predicted_score[1]}")
        print(f"  框架得分: {r.total_score:.1f} | 置信度: {r.confidence}")
        print(f"  逻辑: {r.narrative}")
        if r.rule_flags:
            print(f"  触发规则: {', '.join(r.rule_flags)}")
        print(f"  因子分解:")
        for k, v in r.factor_breakdown.items():
            bar = "█" * max(0, int(abs(v))) * ("+" if v > 0 else "-") if v != 0 else "·"
            print(f"    {k:<22s} {v:>+5.1f}  {bar}")


def cmd_backtest(args):
    schools = build_school_data()
    engine = PredictionEngine()
    results = engine.backtest(schools, target_year=args.year, force_global_heat=0.8)

    print(f"\n{'='*90}")
    print(f"  回测 {args.year} 年预测 (使用 {args.year} 年之前的数据)")
    print(f"{'='*90}\n")
    print(f"{'学校':<8} {'专业':<26} {'预测中点':<8} {'实际':<8} {'误差':<8} {'方向':<6}")
    print("-" * 90)

    errors = []
    correct_dir = 0
    for r in results:
        errors.append(abs(r["error"]))
        if r["direction_correct"]:
            correct_dir += 1
        dir_icon = "✅" if r["direction_correct"] else "❌"
        err_str = f"{r['error']:+.1f}"
        print(f"{r['school']:<8} {r['major']:<26} {r['predicted_mid']:<8.0f} {r['actual']:<8.0f} {err_str:<8} {dir_icon}")

    print("-" * 90)
    print(f"\n  方向准确率: {correct_dir}/{len(results)} ({correct_dir/len(results)*100:.0f}%)")
    print(f"  中位数误差: {sorted(errors)[len(errors)//2]:.0f} 分")
    print(f"  平均误差: {sum(errors)/len(errors):.1f} 分")


def cmd_export(args):
    import pandas as pd
    schools = build_school_data()
    engine = PredictionEngine()
    results = engine.predict_all(schools, target_year=args.year)

    rows = []
    for r in results:
        rows.append({
            "学校": r.school, "专业": r.major, "考试科目": r.exam_code,
            "2026复试线": r.current_score,
            "2027预测复试线_低": r.predicted_score[0],
            "2027预测复试线_高": r.predicted_score[1],
            "框架得分": r.total_score,
            "驱动因子": r.narrative,
            "置信度": r.confidence,
        })

    df = pd.DataFrame(rows)
    df.to_excel(args.output, index=False, sheet_name="2027预测")
    print(f"Exported to: {args.output}")


def main():
    parser = argparse.ArgumentParser(
        description="CS Kaoyan 408 Score Line Predictor (七维因子框架)"
    )
    sub = parser.add_subparsers(dest="command")

    # predict
    p = sub.add_parser("predict", help="Predict score lines for a target year")
    p.add_argument("year", type=int, default=2027, nargs="?")
    p.add_argument("--schools", "-s", help="Filter schools (comma-separated keywords)")
    p.set_defaults(func=cmd_predict)

    # backtest
    b = sub.add_parser("backtest", help="Backtest framework against historical data")
    b.add_argument("--year", "-y", type=int, default=2026)
    b.set_defaults(func=cmd_backtest)

    # export
    e = sub.add_parser("export", help="Export predictions to Excel")
    e.add_argument("--year", "-y", type=int, default=2027)
    e.add_argument("--output", "-o", default="predictions.xlsx")
    e.set_defaults(func=cmd_export)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
