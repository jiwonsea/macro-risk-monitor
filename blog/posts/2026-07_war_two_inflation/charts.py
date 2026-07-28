#!/usr/bin/env python3
"""charts.py — 이 글 폴더의 data/*.csv → charts/S*.png (네이버 업로드용).
경로는 모두 이 파일 위치 기준(HERE). 어느 CWD에서 실행해도 동일하게 동작한다.
dataviz 원칙: one axis(혼합단위는 패널 분리), Okabe-Ito 색맹안전, 라이트배경, 큰 글자, 직접라벨.
"""
import json, warnings
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch
warnings.filterwarnings("ignore")

# --- 한글 폰트 등록 ---
# 빌드 환경 잠금 해제: 특정 경로를 하드코딩하지 않고 후보를 순회한다.
# 하나도 없으면 조용히 tofu(□□□)로 렌더링되지 않도록 검사한 후보를 모두 담아 예외를 낸다.
# NOTE: 후보 목록이 길어지거나 두 번째 활성 post가 같은 탐색을 필요로 하면 그때
#       이 함수만 blog/_lib/으로 추출한다 (2026-07-28_blog_lib_decision_handoff_feedback.md).
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf",
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
_FONT_EXTRA = ["/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"]  # 있으면 굵기용으로 함께 등록


def _resolve_korean_font():
    """존재하는 첫 한글 폰트를 등록하고 matplotlib family name을 돌려준다."""
    primary = None
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            fm.fontManager.addfont(p)
            if primary is None:
                primary = p
    if primary is None:
        raise RuntimeError(
            "한글 폰트를 찾지 못했습니다. 검사한 후보:\n  "
            + "\n  ".join(_FONT_CANDIDATES)
            + "\n설치 예: apt-get install fonts-nanum  (또는 위 경로 중 하나에 폰트 배치)"
        )
    for p in _FONT_EXTRA:
        if Path(p).exists():
            fm.fontManager.addfont(p)
    return fm.FontProperties(fname=primary).get_name()


KFONT = _resolve_korean_font()

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "charts"; OUT.mkdir(parents=True, exist_ok=True)
ann = json.loads((DATA/"annotations.json").read_text())

# --- Okabe-Ito 색맹안전 팔레트 ---
BLUE="#0072B2"; ORANGE="#E69F00"; GREEN="#009E73"; VERM="#D55E00"; PURPLE="#CC79A7"; SKY="#56B4E9"; GRAY="#7a7a7a"
INK="#1a1a1a"; SUB="#555555"; MUT="#8a8a8a"; GRID="#e8e8e8"; SURF="#ffffff"

plt.rcParams.update({
    "font.family":KFONT,"axes.unicode_minus":False,
    "figure.facecolor":SURF,"axes.facecolor":SURF,"savefig.facecolor":SURF,
    "axes.edgecolor":"#cccccc","axes.linewidth":0.8,"axes.grid":True,
    "grid.color":GRID,"grid.linewidth":1.0,"axes.axisbelow":True,
    "xtick.color":SUB,"ytick.color":SUB,"text.color":INK,
    "font.size":15,"savefig.dpi":165,"savefig.bbox":"tight","savefig.pad_inches":0.35,
})
def rd(f, parse="date"):
    d=pd.read_csv(DATA/f); d[parse]=pd.to_datetime(d[parse]); return d.set_index(parse)

def style(ax):
    ax.spines[["top","right"]].set_visible(False)
    for s in ["left","bottom"]: ax.spines[s].set_color("#cccccc")
    ax.tick_params(length=0)
def title(fig,t,sub=None):
    fig.text(0.012,0.975,t,fontsize=26,fontweight="bold",color=INK,ha="left",va="top")
    if sub: fig.text(0.012,0.905,sub,fontsize=15.5,color=SUB,ha="left",va="top")
def foot(fig,s):
    fig.text(0.012,0.014,s,fontsize=11.5,color=MUT,ha="left",va="bottom")
def dlabel(ax,x,y,txt,color,dx=8,dy=0,fs=15,weight="bold",va="center"):
    ax.annotate(txt,(x,y),xytext=(dx,dy),textcoords="offset points",color=color,
                fontsize=fs,fontweight=weight,va=va,ha="left")
def save(fig,name):
    fig.savefig(OUT/name); plt.close(fig); print("  wrote",OUT/name)

# ---------------- S1 Fed 경로 ----------------
def s1():
    d=rd("s1_fedpath.csv")
    fig,ax=plt.subplots(figsize=(12.5,6.6)); fig.subplots_adjust(top=0.80,bottom=0.12,left=0.07,right=0.83)
    ax.fill_between(d.index,d.target_lower,d.target_upper,step="post",color=BLUE,alpha=0.18,lw=0)
    ax.step(d.index,d.target_upper,where="post",color=BLUE,lw=2.4)
    ax.step(d.index,d.target_lower,where="post",color=BLUE,lw=2.4)
    sep=ann["sep_2026_yearend_median"]["value"]
    xend=d.index[-1]; up=d.target_upper.iloc[-1]; lo=d.target_lower.iloc[-1]; mid=(up+lo)/2
    ax.scatter([xend],[sep],s=90,color=ORANGE,zorder=5)
    dlabel(ax,xend,mid,f" 목표범위\n {lo:.2f}–{up:.2f}%",BLUE,dy=0,fs=13.5)
    ax.annotate(f"SEP 중앙값 {sep:.1f}%",(xend,sep),xytext=(12,30),textcoords="offset points",
                color=ORANGE,fontsize=13.5,fontweight="bold",ha="left",va="bottom",
                arrowprops=dict(arrowstyle="-",color=ORANGE,lw=1))
    style(ax); ax.set_ylabel("정책금리 목표범위 (%)",fontsize=14,color=SUB)
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(3.0,5.6)
    title(fig,"① 연준은 2026년 내내 동결",
          "목표범위 3.50–3.75% 유지 · 6월 점도표 2026년 말 중앙값은 3.8%(=소폭 인상 방향)")
    foot(fig,"출처: FRED DFEDTARU/DFEDTARL, Fed SEP(2026-06-17)  ·  점도표 중앙값은 위원 개인전망의 중앙값(투표·인상확률 아님)")
    save(fig,"S1_fedpath.png")

# ---------------- S2 인플레 ----------------
def s2():
    d=rd("s2_inflation.csv")
    fig,ax=plt.subplots(figsize=(12.5,6.6)); fig.subplots_adjust(top=0.80,bottom=0.12,left=0.07,right=0.82)
    series=[("core_pce_yoy","Core PCE",BLUE),("cpi_headline_yoy","헤드라인 CPI",ORANGE),("cpi_core_yoy","Core CPI",GREEN)]
    offs={"core_pce_yoy":-11,"cpi_headline_yoy":10,"cpi_core_yoy":0}
    for col,lab,c in series:
        s=d[col].dropna()
        ax.plot(s.index,s,color=c,lw=2.6)
        dlabel(ax,s.index[-1],s.iloc[-1],f" {lab} {s.iloc[-1]:.1f}%",c,dy=offs[col],fs=14.5)
    ax.axhline(2.0,color=MUT,lw=1.2,ls=(0,(4,4))); dlabel(ax,d.index[0],2.0,"연준 목표 2%",MUT,dx=0,dy=8,fs=12.5,weight="normal")
    style(ax); ax.set_ylabel("전년동월비 (%)",fontsize=14,color=SUB)
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title(fig,"② 인플레이션은 3% 부근에 정체",
          "Core PCE는 5월 3.4% · 유가·전쟁·AI 측정오류가 '2%로의 복귀'를 지연")
    foot(fig,"출처: FRED PCEPILFE(Core PCE, SA) / CPIAUCNS·CPILFENS(CPI, NSA)  ·  CPI 12개월 변화는 계절미조정(NSA) 기준 = BLS 공식 보도치와 일치")
    save(fig,"S2_inflation.png")

# ---------------- S3 유가 ----------------
def s3():
    d=rd("s3_oil.csv")
    fig,ax=plt.subplots(figsize=(12.5,6.8)); fig.subplots_adjust(top=0.79,bottom=0.12,left=0.07,right=0.84)
    ax.plot(d.index,d.brent,color=BLUE,lw=2.6); ax.plot(d.index,d.wti,color=ORANGE,lw=2.6)
    dlabel(ax,d.index[-1],d.brent.iloc[-1],f" Brent {d.brent.iloc[-1]:.0f}",BLUE)
    dlabel(ax,d.index[-1],d.wti.iloc[-1],f" WTI {d.wti.iloc[-1]:.0f}",ORANGE)
    for ev in ann["oil_events"]:
        x=pd.to_datetime(ev["date"]); ax.axvline(x,color=MUT,lw=1.1,ls=(0,(3,3)))
        ax.annotate(ev["label"],(x,ax.get_ylim()[1]),xytext=(3,-4),textcoords="offset points",
                    fontsize=11.5,color=SUB,rotation=0,va="top")
    pk=ann["oil_peak_derived"]; px=pd.to_datetime(pk["brent_peak_date"])
    ax.scatter([px],[pk["brent_peak_value"]],s=70,color=VERM,zorder=6)
    ax.annotate(f"피크 Brent {pk['brent_peak_value']:.0f} (4/7)",(px,pk["brent_peak_value"]),
                xytext=(46,-30),textcoords="offset points",color=VERM,fontsize=13,fontweight="bold",
                ha="left",va="top",arrowprops=dict(arrowstyle="-",color=VERM,lw=1))
    style(ax); ax.set_ylabel("$/배럴",fontsize=14,color=SUB)
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m월"))
    title(fig,"③ 유가: 4월 피크 후 되돌림",
          "채널 1 — 전쟁발 유가 급등은 SPR 방출·휴전·중재로 제한적. 피크 대비 크게 하락")
    foot(fig,"출처: FRED DCOILWTICO/DCOILBRENTEU(일간)  ·  피크는 데이터 idxmax로 산출  ·  이벤트: CENTCOM·UN·White House")
    save(fig,"S3_oil.png")

# ---------------- S4 SPR ----------------
def s4():
    d=rd("s4_spr.csv")
    fig,ax=plt.subplots(figsize=(12.5,6.6)); fig.subplots_adjust(top=0.80,bottom=0.12,left=0.08,right=0.83)
    ax.fill_between(d.index,d.spr_mbbl,color=BLUE,alpha=0.15,lw=0); ax.plot(d.index,d.spr_mbbl,color=BLUE,lw=2.4)
    last=d.spr_mbbl.iloc[-1]
    dlabel(ax,d.index[-1],last,f" 현재 {last:.0f}M",BLUE,dy=0)
    sr=ann["spr_release"]
    _p=d.spr_mbbl.loc["2026-01-01":].max(); _pd=d.spr_mbbl.loc["2026-01-01":].idxmax()
    box=("완충 소진 진행\n"
         f"· 계획 방출 {sr['planned_mbbl']}M\n"
         f"· 실제 방출 {sr['released_through_2026_04_24_mbbl']}M (4/24까지)\n"
         f"· 재고 감소 {_pd:%-m/%-d} {_p:.0f}M → {d.index[-1]:%-m/%-d} {last:.0f}M ({_p-last:.0f}M)")
    ax.text(0.035,0.30,box,transform=ax.transAxes,fontsize=13,color=INK,va="top",ha="left",
            bbox=dict(boxstyle="round,pad=0.6",fc="#fff6ec",ec=ORANGE,lw=1.3))
    style(ax); ax.set_ylabel("SPR 원유재고 (백만 배럴)",fontsize=14,color=SUB)
    ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title(fig,"④ 유가를 누른 대가: SPR은 1983년 이후 최저",
          "전략비축유가 1980년대 이후 최저 부근 — 향후 호르무즈 재쇼크에 쓸 완충은 얇아졌다")
    foot(fig,"출처: EIA WCSSTUS1(주간)  ·  방출량 주석은 EIA(id=67625). 계획량≠실제 방출량")
    save(fig,"S4_spr.png")

# ---------------- S5 기대인플레 (핵심) ----------------
def s5():
    d=rd("s5_sce.csv"); t=rd("s5_t5yifr.csv"); g=rd("s5b_gas.csv")
    fig,(a1,a2)=plt.subplots(2,1,figsize=(12.5,8.6),height_ratios=[2.5,1],sharex=True)
    fig.subplots_adjust(top=0.83,bottom=0.10,left=0.07,right=0.83,hspace=0.13)
    for col,lab,c in [("sce_1y","SCE 1년",ORANGE),("sce_3y","SCE 3년",PURPLE),("sce_5y","SCE 5년",BLUE)]:
        s=d[col].dropna(); a1.plot(s.index,s,color=c,lw=2.6)
        dlabel(a1,s.index[-1],s.iloc[-1],f" {lab} {s.iloc[-1]:.1f}",c,fs=13.5)
    ts=t["t5yifr_monthend"].dropna(); a1.plot(ts.index,ts,color=GREEN,lw=2.2,ls=(0,(5,2)))
    dlabel(a1,ts.index[-1],ts.iloc[-1],f" 시장 5y5y {ts.iloc[-1]:.2f}",GREEN,fs=13.5)
    style(a1); a1.set_ylabel("기대 인플레이션 (%)",fontsize=13.5,color=SUB)
    gs=g["gas_exp"].dropna(); a2.plot(gs.index,gs,color=VERM,lw=2.6)
    dlabel(a2,gs.index[-1],gs.iloc[-1],f" gas {gs.iloc[-1]:.1f}",VERM,fs=13.5)
    style(a2); a2.set_ylabel("휘발유 기대(%)",fontsize=12.5,color=SUB)
    a2.xaxis.set_major_locator(mdates.YearLocator()); a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title(fig,"⑤ 핵심: 기대인플레는 '유가만'으로 설명 안 된다",
          "휘발유 기대는 1.5%로 급락했는데 단기(1년)·중기(3년) 기대는 오히려 상승 · 장기(5년)·시장 5y5y는 안정")
    foot(fig,"출처: NY Fed SCE(중앙값, 월간) · FRED T5YIFR(월말)  ·  위=기대인플레, 아래=휘발유 가격 기대(별도 스케일)")
    save(fig,"S5_inflexp.png")

# ---------------- S6 소비자 연체 ----------------
def s6():
    d=rd("s6_consumer.csv")
    fig,ax=plt.subplots(figsize=(12.5,6.6)); fig.subplots_adjust(top=0.80,bottom=0.12,left=0.07,right=0.82)
    ax.plot(d.index,d.cc_delinq,color=BLUE,lw=2.6)
    dlabel(ax,d.index[-1],d.cc_delinq.iloc[-1],f" {d.cc_delinq.iloc[-1]:.2f}%",BLUE)
    ax.text(0.035,0.93,"주: 'Equifax 13.12%(subprime/severe)'는 정의가 다른 지표 — 여기(전 상업은행 연체율)와 혼동 금지",
            transform=ax.transAxes,fontsize=11.5,color=MUT,va="top")
    style(ax); ax.set_ylabel("카드 연체율 (%, 전 상업은행)",fontsize=14,color=SUB)
    ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title(fig,"⑥ 소비자: 취약하지만 '아직' 발작은 아니다",
          "은행 카드 연체율은 완만 — domino의 불쏘시개이나 base가 아닌 tail")
    foot(fig,"출처: FRED DRCCLACBS(분기, 계절조정)")
    save(fig,"S6_consumer.png")

# ---------------- S7 노동 (패널 분리, dual-axis 금지) ----------------
def s7():
    d=rd("s7_labor.csv")
    fig,(a1,a2)=plt.subplots(2,1,figsize=(12.5,8.4),height_ratios=[1,1],sharex=True)
    fig.subplots_adjust(top=0.83,bottom=0.10,left=0.07,right=0.85,hspace=0.13)
    a1.plot(d.index,d.unrate,color=BLUE,lw=2.6)
    dlabel(a1,d.index[-1],d.unrate.iloc[-1],f" {d.unrate.iloc[-1]:.1f}%",BLUE)
    style(a1); a1.set_ylabel("실업률 (%)",fontsize=13.5,color=SUB); a1.set_ylim(3.2,4.7)
    cols=[GREEN if v>=0 else VERM for v in d.payems_mom_k]
    a2.bar(d.index,d.payems_mom_k,width=22,color=cols,alpha=0.85)
    dlabel(a2,d.index[-1],d.payems_mom_k.iloc[-1],f" +{d.payems_mom_k.iloc[-1]:.0f}k",GREEN,fs=13.5,va="bottom")
    style(a2); a2.set_ylabel("월간 고용증감 (천명)",fontsize=13.5,color=SUB); a2.axhline(0,color="#cccccc",lw=1)
    a2.xaxis.set_major_locator(mdates.YearLocator()); a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title(fig,"⑦ 완충: 노동은 아직 견조",
          "실업률 4.2%, 6월 고용 +57k — 이 완충이 '아직 base가 아니다'의 근거이자 domino의 트리거(꺾이면 activate)")
    foot(fig,"출처: FRED UNRATE, PAYEMS(월간 차분=고용증감)")
    save(fig,"S7_labor.png")

# ---------------- S8 EPU ----------------
def s8():
    d=rd("s8_epu.csv")["epu"].dropna()
    fig,ax=plt.subplots(figsize=(12.5,6.6)); fig.subplots_adjust(top=0.80,bottom=0.12,left=0.07,right=0.82)
    q1,med,q3=d.quantile(.25),d.median(),d.quantile(.75)
    ax.axhspan(q1,q3,color=GRAY,alpha=0.12); ax.axhline(med,color=MUT,lw=1.1,ls=(0,(4,4)))
    dlabel(ax,d.index[0],med,f"2015~ 중앙값 {med:.0f}",MUT,dx=0,dy=8,fs=12,weight="normal")
    ax.plot(d.index,d,color=BLUE,lw=2.3)
    dlabel(ax,d.index[-1],d.iloc[-1],f" {d.iloc[-1]:.0f}",BLUE)
    style(ax); ax.set_ylabel("경제정책 불확실성 지수",fontsize=14,color=SUB)
    ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    title(fig,"⑧ 불확실성은 구조적으로 높아졌다",
          "관세·다전선 갈등으로 정책 불확실성이 2015~ 정상범위(음영=IQR) 상단에 지속")
    foot(fig,"출처: FRED USEPUINDXM(월간)  ·  음영=2015년 이후 25–75퍼센타일, 점선=중앙값(임계 아님)")
    save(fig,"S8_epu.png")

# ---------------- S9 대시보드 (PNG 전용 요약) ----------------
def s9():
    fedU=rd("s1_fedpath.csv").target_upper.iloc[-1]; fedL=rd("s1_fedpath.csv").target_lower.iloc[-1]
    inf=rd("s2_inflation.csv"); sce=rd("s5_sce.csv"); gas=rd("s5b_gas.csv")["gas_exp"].iloc[-1]
    t5=rd("s5_t5yifr.csv")["t5yifr_monthend"].iloc[-1]; oil=rd("s3_oil.csv")
    spr=rd("s4_spr.csv").spr_mbbl.iloc[-1]; cc=rd("s6_consumer.csv").cc_delinq.iloc[-1]
    lab=rd("s7_labor.csv"); epu=rd("s8_epu.csv").epu.iloc[-1]
    tiles=[
        ("정책금리",f"{fedL:.2f}–{fedU:.2f}%","동결 · SEP 3.8%",BLUE),
        ("Core PCE",f"{inf.core_pce_yoy.dropna().iloc[-1]:.1f}%","3% 부근 정체",ORANGE),
        ("SCE 1년 / 5년",f"{sce.sce_1y.iloc[-1]:.1f} / {sce.sce_5y.iloc[-1]:.1f}%","단기↑·장기 안정",PURPLE),
        ("휘발유 기대",f"{gas:.1f}%","급락(유가발 아님)",VERM),
        ("시장 5y5y",f"{t5:.2f}%","앵커 안정",GREEN),
        ("WTI / Brent",f"{oil.wti.iloc[-1]:.0f} / {oil.brent.iloc[-1]:.0f}","피크 대비 하락",BLUE),
        ("SPR 재고",f"{spr:.0f}M","1983년래 최저",ORANGE),
        ("카드 연체율",f"{cc:.2f}%","완만(tail)",GREEN),
        ("실업률 / 고용",f"{lab.unrate.iloc[-1]:.1f}% / +{lab.payems_mom_k.iloc[-1]:.0f}k","완충 견조",BLUE),
        ("정책 불확실성",f"{epu:.0f}","정상범위 상단",PURPLE),
    ]
    fig=plt.figure(figsize=(12.5,8.2)); fig.subplots_adjust(top=0.82,bottom=0.08,left=0.04,right=0.96)
    title(fig,"⑨ 한눈에: 견조 · 의문 · 연결",
          "지금은 base가 아닌 tail. 그러나 지표들이 서로 연결돼 노동이 꺾이면 stagflation 도미노로 번질 수 있다")
    ncol=2; nrow=5
    for i,(k,v,note,c) in enumerate(tiles):
        r,cc_=divmod(i,ncol); x=0.045+cc_*0.475; y=0.74-r*0.145
        fig.patches.append(FancyBboxPatch((x,y-0.115),0.44,0.115,boxstyle="round,pad=0.006",
            transform=fig.transFigure,fc="#fafafa",ec="#e2e2e2",lw=1.2,mutation_aspect=0.9))
        fig.text(x+0.018,y-0.028,k,fontsize=14,color=SUB,va="top")
        fig.text(x+0.018,y-0.058,v,fontsize=23,fontweight="bold",color=c,va="top")
        fig.text(x+0.30,y-0.052,note,fontsize=12.5,color=MUT,va="top")
    foot(fig,"출처: FRED·EIA·NY Fed·Fed SEP  ·  종합: 사용자 2-channel × Claude·Codex 검증(2026-07)")
    save(fig,"S9_dashboard.png")

for f in [s1,s2,s3,s4,s5,s6,s7,s8,s9]:
    f()
print("charts done")
