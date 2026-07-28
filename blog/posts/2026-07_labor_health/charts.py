"""charts.py — 이 글 폴더의 data/*.csv → charts/c2-*.png
경로는 모두 이 파일 위치 기준(HERE). 어느 CWD에서 실행해도 동일하게 동작한다.
NOTE(legacy): 이 글은 발행 완료본이며 재렌더링 계획이 없다. 네이버 발행본 이미지와의
대응을 유지하기 위해 폰트·팔레트·스타일은 글 B(Okabe-Ito)와 통일하지 않는다.
"""
import csv, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "charts"; OUT.mkdir(parents=True, exist_ok=True)

# Korean font
FP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
fm.fontManager.addfont(FP)
prop = fm.FontProperties(fname=FP)
plt.rcParams["font.family"] = prop.get_name()
plt.rcParams["axes.unicode_minus"] = False

# unified palette
RED="#C0392B"; YELLOW="#E1A100"; GREEN="#1E8449"; GREY="#7F8C8D"; DARK="#2C3E50"
DPI=112; W=12  # 12in*100dpi = 1200px

def load(p):
    with open(DATA / Path(p).name, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def footer(fig, src):
    fig.text(0.01, 0.01, src, fontsize=8, color=GREY, ha="left")

def save(fig, name):
    fig.savefig(OUT / name, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)

# ---- C2-1: low vs high wage ----
d = load("data/c2-1_wage_split.csv")
labels = ["평균임금 이하 산업", "평균임금 이상 산업"]
vals = [int(d[0]["jobs_change"]), int(d[1]["jobs_change"])]
fig, ax = plt.subplots(figsize=(W,6.2))
bars = ax.bar(labels, vals, color=[GREEN, RED], width=0.55)
for b,v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v + (18000 if v>0 else -18000),
            f"{v:+,}", ha="center", va="bottom" if v>0 else "top",
            fontsize=15, fontweight="bold", color=GREEN if v>0 else RED)
ax.axhline(0, color=DARK, lw=1)
ax.set_title("일자리 증가는 저임금 산업에 편중  (2025.6~2026.6 누적, 민간)",
             fontsize=16, fontweight="bold", pad=14)
ax.set_ylabel("고용 순증감 (명)")
ax.set_ylim(-160000, 900000)
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
ax.spines[["top","right"]].set_visible(False)
footer(fig, "출처: Center for American Progress (June Jobs Numbers, 2026)")
save(fig, "c2-1_low_vs_high_wage.png")

# ---- C2-2: industry breakdown ----
d = load("data/c2-2_industry.csv")
names = [r["industry"].split(" (")[0] for r in d]
vals = [int(r["jobs_change"]) for r in d]
colors = [GREEN if v>0 else RED for v in vals]
fig, ax = plt.subplots(figsize=(W,6.4))
order = sorted(range(len(vals)), key=lambda i: vals[i])
names=[names[i] for i in order]; vals=[vals[i] for i in order]; colors=[colors[i] for i in order]
bars = ax.barh(names, vals, color=colors, height=0.6)
for b,v in zip(bars, vals):
    ax.text(v + (10000 if v>0 else -10000), b.get_y()+b.get_height()/2,
            f"{v:+,}", va="center", ha="left" if v>0 else "right",
            fontsize=13, fontweight="bold", color=GREEN if v>0 else RED)
ax.axvline(0, color=DARK, lw=1)
ax.set_title("업종별 고용 순증감  (2025.6~2026.6 누적)", fontsize=16, fontweight="bold", pad=14)
ax.set_xlabel("고용 순증감 (명)")
ax.set_xlim(-140000, 780000)
ax.get_xaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,_: f"{int(x):,}"))
ax.spines[["top","right"]].set_visible(False)
footer(fig, "출처: Center for American Progress (June Jobs Numbers, 2026)")
save(fig, "c2-2_industry_change.png")

# ---- C2-3: U-3 vs U-6 ----
d = load("data/c2-3_u3_u6.csv")
labels = ["U-3\n(공식 실업률)", "U-6\n(광의: 불완전취업 포함)"]
vals = [float(d[0]["rate_pct"]), float(d[1]["rate_pct"])]
fig, ax = plt.subplots(figsize=(W,6.2))
bars = ax.bar(labels, vals, color=[GREY, YELLOW], width=0.5)
for b,v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+0.12, f"{v:.1f}%",
            ha="center", fontsize=16, fontweight="bold", color=DARK)
ax.set_title("공식 실업률이 놓치는 것  (2026년 6월)", fontsize=16, fontweight="bold", pad=14)
ax.set_ylabel("실업률 (%)")
ax.set_ylim(0, 9.5)
ax.spines[["top","right"]].set_visible(False)
ax.text(0.5, 0.92, "U-6는 U-3의 약 1.9배 — 불완전취업·구직단념자 포함 시 체감은 더 나쁘다",
        transform=ax.transAxes, ha="center", fontsize=11, color=GREY)
footer(fig, "출처: CNBC / BLS Table A-15 / Trading Economics (2026-06)")
save(fig, "c2-3_u3_vs_u6.png")

# ---- C2-4: hardship withdrawals ----
d = load("data/c2-4_hardship.csv")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W,5.8), gridspec_kw={"width_ratios":[1,1.05]})
# left: 5%->6% trend
yrs=["2024","2025"]; share=[5,6]
ax1.plot(yrs, share, marker="o", color=RED, lw=3, markersize=11)
for x,y in zip(yrs, share):
    ax1.text(x, y+0.12, f"{y}%", ha="center", fontsize=15, fontweight="bold", color=RED)
ax1.set_title("401k 하드십 인출 참가자 비율\n(사상 최대)", fontsize=13.5, fontweight="bold")
ax1.set_ylim(0, 8); ax1.set_ylabel("참가자 중 비율 (%)")
ax1.spines[["top","right"]].set_visible(False)
ax1.text(0.5, -0.16, "팬데믹 이전 평균 ≈ 2%", transform=ax1.transAxes, ha="center", fontsize=10, color=GREY)
# right: reasons
reasons=["압류·퇴거\n방지", "의료비", "기타\n(주택수리 등)"]
rvals=[34, 30, 36]
rc=[RED, YELLOW, GREY]
ax2.bar(reasons, rvals, color=rc, width=0.6)
for i,(r,v) in enumerate(zip(reasons, rvals)):
    ax2.text(i, v+0.8, f"{'>1/3' if i==0 else ('3 in 10' if i==1 else '')}", ha="center", fontsize=11, color=DARK)
ax2.set_title("인출 사유 구성 (2025)\n최대 사유는 '대학'이 아니라 주거·의료", fontsize=13.5, fontweight="bold")
ax2.set_ylabel("비중 (%)"); ax2.set_ylim(0, 45)
ax2.spines[["top","right"]].set_visible(False)
footer(fig, "출처: Vanguard How America Saves 2026 / CBS News (2025년 데이터, 중위 인출액 $1,900)")
save(fig, "c2-4_hardship_withdrawals.png")

# ---- C2-5: AI fear ----
d = load("data/c2-5_ai_fear.csv")
yrs=[r["year"] for r in d]; vals=[int(r["fear_pct"]) for r in d]
fig, ax = plt.subplots(figsize=(W,6.0))
bars = ax.bar(yrs, vals, color=[GREY, RED], width=0.45)
for b,v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+0.8, f"{v}%", ha="center", fontsize=17, fontweight="bold", color=DARK)
ax.annotate("", xy=(1, 40), xytext=(0, 28),
            arrowprops=dict(arrowstyle="->", color=RED, lw=2))
ax.text(0.5, 35, "+12%p\n(2년)", ha="center", fontsize=12, color=RED, fontweight="bold")
ax.set_title("\"AI가 내 일자리를 없앨 것\" 우려 비율", fontsize=16, fontweight="bold", pad=14)
ax.set_ylabel("응답 비율 (%)"); ax.set_ylim(0, 50)
ax.spines[["top","right"]].set_visible(False)
footer(fig, "출처: Mercer Global Talent Trends 2026")
save(fig, "c2-5_ai_fear.png")

print("DONE")
