"""한·미 10년물 동조화 점검 — 월별 변화의 상관·민감도(β)와 국면별 비교.

Input: data/snapshots/*_ecos_monthly.csv (KTB3Y, KTB10Y, CORP_AA3Y, BOK_BASE — ECOS 721Y001/722Y001)
       data/snapshots/*_fred_monthly.csv (DGS10 avg, DGS2 avg, DFEDTARU eop, DEXKOUS avg, VIXCLS avg, T10YIE avg)
Output: reports/comovement/{stats.json, fig_levels.png, fig_rolling.png, fig_scatter.png}

β = Cov(ΔKTB10, ΔUST10) / Var(ΔUST10) — 미 10년물이 1%p 움직일 때 국고채 10년물의 평균 동반 변화.
상관·β는 동조화의 '정도'이지 인과의 방향을 말하지 않는다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

KR, US = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e4e3dc"
REGIMES = [("2016-11", "2020-12", "2016-11 ~ 2020-12"),
           ("2021-01", "2023-12", "2021-01 ~ 2023-12 (글로벌 인플레이션)"),
           ("2024-01", "2026-09", "2024-01 ~ 2026-09"),
           ("2025-10", "2026-09", "최근 12개월")]


def _font():
    for name in ("Noto Sans CJK KR", "Noto Sans CJK JP", "Malgun Gothic", "NanumGothic"):
        if any(name in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams.update({"axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
                         "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.unicode_minus": False, "font.size": 9})


def beta(x: pd.DataFrame) -> float:
    return float(np.cov(x.du, x.dk)[0, 1] / np.var(x.du, ddof=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecos", type=Path, default=Path("data/snapshots/2026-10-05_ecos_monthly.csv"))
    ap.add_argument("--fred", type=Path, default=Path("data/snapshots/2026-10-05_fred_monthly.csv"))
    ap.add_argument("--out", type=Path, default=Path("reports/comovement"))
    ap.add_argument("--window", type=int, default=36)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    _font()

    e = pd.read_csv(a.ecos, dtype={"month": str})
    f = pd.read_csv(a.fred, dtype={"month": str})
    d = e.merge(f, on="month", validate="one_to_one")
    d.index = pd.to_datetime(d.month, format="%Y%m")
    X = pd.DataFrame({"dk": d.KTB10Y.diff(), "du": d.DGS10.diff()}).dropna()

    stats = {"sample": [str(d.index[0].date())[:7], str(d.index[-1].date())[:7]], "n_changes": len(X),
             "full": {"corr": round(X.dk.corr(X.du), 3), "beta": round(beta(X), 3)}, "regimes": []}
    for lo, hi, label in REGIMES:
        x = X.loc[lo:hi]
        stats["regimes"].append({"label": label, "n": len(x), "corr": round(x.dk.corr(x.du), 3),
                                 "beta": round(beta(x), 3)})
    roll_c = X.dk.rolling(a.window).corr(X.du)
    roll_b = X.dk.rolling(a.window).cov(X.du) / X.du.rolling(a.window).var()
    stats["rolling"] = {"window": a.window, "corr_last": round(float(roll_c.iloc[-1]), 3),
                        "corr_peak": round(float(roll_c.max()), 3), "corr_peak_at": str(roll_c.idxmax().date())[:7],
                        "beta_last": round(float(roll_b.iloc[-1]), 3),
                        "beta_peak": round(float(roll_b.max()), 3), "beta_peak_at": str(roll_b.idxmax().date())[:7]}
    last12 = d.loc["2025-09":"2026-09"]
    stats["last12_level_change_bp"] = {
        "KTB10Y": round((last12.KTB10Y.iloc[-1] - last12.KTB10Y.iloc[0]) * 100),
        "UST10Y": round((last12.DGS10.iloc[-1] - last12.DGS10.iloc[0]) * 100),
        "BOK_BASE": round((last12.BOK_BASE.iloc[-1] - last12.BOK_BASE.iloc[0]) * 100),
        "FED_UPPER": round((last12.DFEDTARU.iloc[-1] - last12.DFEDTARU.iloc[0]) * 100)}
    gap = d.KTB10Y - d.DGS10
    stats["gap_10y"] = {"last": round(float(gap.iloc[-1]), 3), "p10": round(float(gap.quantile(.1)), 3),
                        "p50": round(float(gap.quantile(.5)), 3), "min": round(float(gap.min()), 3),
                        "min_at": str(gap.idxmin().date())[:7]}
    (a.out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # Fig 1 — levels (one axis: both in % p.a.)
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    ax.plot(d.index, d.KTB10Y, color=KR, lw=2, label="국고채 10년 (ECOS)")
    ax.plot(d.index, d.DGS10, color=US, lw=2, label="미 국채 10년 (FRED)")
    ax.text(d.index[-1], d.KTB10Y.iloc[-1], f"  {d.KTB10Y.iloc[-1]:.2f}", color=INK, va="center", fontsize=8)
    ax.text(d.index[-1], d.DGS10.iloc[-1], f"  {d.DGS10.iloc[-1]:.2f}", color=INK, va="center", fontsize=8)
    ax.set_ylabel("연 %, 월평균"); ax.legend(frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(a.out / "fig_levels.png", dpi=200); plt.close(fig)

    # Fig 2 — rolling corr and beta as two small multiples (no dual axis)
    fig, axs = plt.subplots(2, 1, figsize=(7.2, 3.6), sharex=True)
    for ax, s, lab in ((axs[0], roll_c, f"{a.window}개월 이동 상관계수"), (axs[1], roll_b, f"{a.window}개월 이동 β")):
        ax.axvspan(pd.Timestamp("2021-01"), pd.Timestamp("2023-12"), color=GRID, alpha=0.6, lw=0)
        ax.plot(s.index, s, color=KR, lw=2)
        ax.set_ylabel(lab); ax.set_ylim(0, 1.05)
        ax.text(s.index[-1], s.iloc[-1], f"  {s.iloc[-1]:.2f}", color=INK, va="center", fontsize=8)
    axs[0].text(pd.Timestamp("2021-02"), 0.08, "2021~2023 글로벌 인플레이션 국면", color=MUTED, fontsize=8)
    fig.tight_layout(); fig.savefig(a.out / "fig_rolling.png", dpi=200); plt.close(fig)

    # Fig 3 — regime bars (beta), direct-labelled
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    labs = [r["label"] for r in stats["regimes"]]; vals = [r["beta"] for r in stats["regimes"]]
    bars = ax.barh(labs[::-1], vals[::-1], color=KR, height=0.5)
    for b, r in zip(bars, stats["regimes"][::-1]):
        ax.text(b.get_width() + 0.02, b.get_y() + b.get_height() / 2,
                f"β {r['beta']:.2f} · 상관 {r['corr']:.2f} · n={r['n']}", va="center", color=INK, fontsize=8)
    ax.set_xlim(0, 1.25); ax.set_xlabel("β (미 10년물 1%p 변화당 국고채 10년물 변화, %p)")
    ax.grid(axis="y", visible=False)
    fig.tight_layout(); fig.savefig(a.out / "fig_regimes.png", dpi=200); plt.close(fig)
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
