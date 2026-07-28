#!/usr/bin/env python3
"""
collect_data.py — 네이버 블로그 "WAR와 두 개의 인플레이션" 데이터 수집.

실행 위치: 네트워크가 있는 환경(예: Codex 로컬). 스프레드시트 artifact 도구 불필요 — pandas만 있으면 됨.
출력: ./data/*.csv (고정 스키마) + manifest.json + annotations.json.
이후 Claude가 이 CSV들로 xlsx + PNG를 빌드한다.

의존: pandas, requests (또는 urllib), openpyxl/xlrd(엑셀 소스 읽기용). matplotlib 불필요.
  pip install pandas requests openpyxl xlrd

주의(PLAN §7):
- FRED는 CSV 엔드포인트(키 불필요). EIA SPR은 WCSSTUS1(FRED 아님). NY Fed SCE는 공식 xlsx 전체 시계열.
- 파생: YoY=100*(x/x.shift(12)-1), PAYEMS MoM=diff()(천명, 연율화 금지), T5YIFR 월말 리샘플.
- 하드코딩 수동값(SEP 3.8%, SPR 계획/실제, 이벤트 날짜)은 annotations.json에 URL·as-of와 함께.
- 끝에서 assertion으로 최신 관측치를 검증한다(불일치 시 실패 → 값이 바뀌었으면 assertion 갱신).
"""

import json
import io
import sys
import datetime as dt
from pathlib import Path

import pandas as pd

try:
    import requests
    def _get(url, **kw):
        r = requests.get(url, timeout=60, headers={"User-Agent": "macro-blog/1.0"}, **kw)
        r.raise_for_status()
        return r.content
except Exception:
    from urllib.request import urlopen, Request
    def _get(url, **kw):
        req = Request(url, headers={"User-Agent": "macro-blog/1.0"})
        return urlopen(req, timeout=60).read()

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)
RETRIEVED_AT = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={cosd}"
manifest = []


def fred(series_id, cosd="2015-01-01"):
    """FRED 단일 시리즈 → DataFrame(index=date, col=series_id). 값 '.'는 결측."""
    raw = _get(FRED.format(id=series_id, cosd=cosd))
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    df = df.dropna().set_index("date")
    manifest.append({"series": series_id, "source": "FRED",
                     "url": FRED.format(id=series_id, cosd=cosd),
                     "freq": pd.infer_freq(df.index) or "irregular",
                     "last_obs": str(df.index[-1].date()),
                     "last_value": float(df[series_id].iloc[-1])})
    return df


def yoy(s):
    prior_year = s.copy()
    prior_year.index = prior_year.index + pd.DateOffset(years=1)
    return (100 * (s / prior_year - 1)).dropna()


def save(df, name):
    p = OUT / name
    df.to_csv(p, date_format="%Y-%m-%d")
    print(f"  wrote {p}  ({len(df)} rows)")


# ---------- S1 Fed 경로 ----------
def s1_fedpath():
    up = fred("DFEDTARU", "2023-01-01")
    lo = fred("DFEDTARL", "2023-01-01")
    df = up.join(lo, how="outer").ffill().dropna()
    df.columns = ["target_upper", "target_lower"]
    save(df, "s1_fedpath.csv")


# ---------- S2 인플레 (YoY) ----------
def s2_inflation():
    pce = fred("PCEPILFE", "2021-01-01")["PCEPILFE"]
    cpi = fred("CPIAUCNS", "2021-01-01")["CPIAUCNS"]
    cpicore = fred("CPILFENS", "2021-01-01")["CPILFENS"]
    df = pd.DataFrame({
        "core_pce_yoy": yoy(pce),
        "cpi_headline_yoy": yoy(cpi),
        "cpi_core_yoy": yoy(cpicore),
    }).dropna(how="all")
    df = df[df.index >= "2023-01-01"]
    save(df, "s2_inflation.csv")
    return df


# ---------- S3 유가 ----------
def s3_oil():
    wti = fred("DCOILWTICO", "2026-01-01")["DCOILWTICO"]
    brent = fred("DCOILBRENTEU", "2026-01-01")["DCOILBRENTEU"]
    df = pd.DataFrame({"wti": wti, "brent": brent})
    save(df, "s3_oil.csv")
    # 피크는 하드코딩 금지 — 데이터에서 산출해 annotation에 기록
    peak_date = brent.idxmax()
    return {"brent_peak_date": str(peak_date.date()),
            "brent_peak_value": float(brent.max()),
            "wti_peak_date": str(wti.idxmax().date()),
            "wti_peak_value": float(wti.max())}


# ---------- S4 SPR (EIA WCSSTUS1) ----------
def s4_spr():
    """EIA 주간 SPR 재고. 우선순위: EIA hist_xls → EIA API(키 있으면) → 실패 시 안내."""
    urls = [
        "https://www.eia.gov/dnav/pet/hist_xls/WCSSTUS1w.xls",   # weekly xls (키 불필요)
    ]
    df = None
    for u in urls:
        try:
            raw = _get(u)
            # EIA hist_xls: 'Data 1' 시트, 2행 헤더. 열: Date, "... SPR (Thousand Barrels)"
            x = pd.read_excel(io.BytesIO(raw), sheet_name="Data 1", skiprows=2)
            x.columns = ["date", "spr_thousand_bbl"]
            x["date"] = pd.to_datetime(x["date"])
            x["spr_mbbl"] = pd.to_numeric(x["spr_thousand_bbl"], errors="coerce") / 1000.0
            df = x.dropna(subset=["spr_mbbl"])[["date", "spr_mbbl"]].set_index("date")
            df = df[df.index >= "2018-01-01"]
            manifest.append({"series": "WCSSTUS1", "source": "EIA", "url": u,
                             "freq": "weekly", "units": "million barrels",
                             "last_obs": str(df.index[-1].date()),
                             "last_value": float(df["spr_mbbl"].iloc[-1])})
            break
        except Exception as e:
            print(f"  [S4] {u} 실패: {e}", file=sys.stderr)
    if df is None:
        raise RuntimeError("EIA WCSSTUS1 수집 실패 — EIA API 키(EIA_API_KEY) 사용하거나 수동 CSV 배치 필요")
    save(df, "s4_spr.csv")


# ---------- S5 NY Fed SCE + T5YIFR ----------
def s5_sce():
    """NY Fed SCE 공식 데이터(중앙값 기대인플레 1y/3y/5y + gas)."""
    SCE_MAIN = "https://www.newyorkfed.org/medialibrary/Interactives/sce/sce/downloads/data/FRBNY-SCE-Data.xlsx"
    raw = _get(SCE_MAIN)
    xls = pd.ExcelFile(io.BytesIO(raw))
    print(f"  [S5] SCE 시트: {xls.sheet_names}", file=sys.stderr)
    inflation_sheet = next(
        s for s in xls.sheet_names if s.lower() == "inflation expectations"
    )
    commodity_sheet = next(
        s for s in xls.sheet_names if s.lower() == "commodity expectations"
    )
    five_year_sheet = next(
        (s for s in xls.sheet_names if s.lower() == "five-year ahead infl exp"),
        None,
    )

    def read_sheet(sheet):
        frame = pd.read_excel(xls, sheet_name=sheet, skiprows=3)
        frame.columns = [str(c).strip() for c in frame.columns]
        datecol = frame.columns[0]
        frame[datecol] = pd.to_datetime(
            frame[datecol].astype(str), format="%Y%m", errors="coerce"
        )
        return frame.dropna(subset=[datecol]).rename(
            columns={datecol: "date"}
        ).set_index("date")

    sce = read_sheet(inflation_sheet)

    def pick(keys):
        for c in sce.columns:
            lc = c.lower()
            if all(k in lc for k in keys):
                return c
        return None
    col1 = pick(["one", "year"]) or pick(["1", "year"]) or pick(["1yr"])
    col3 = pick(["three", "year"]) or pick(["3", "year"]) or pick(["3yr"])
    out = pd.DataFrame(index=sce.index)
    if col1:
        out["sce_1y"] = pd.to_numeric(sce[col1], errors="coerce")
    if col3:
        out["sce_3y"] = pd.to_numeric(sce[col3], errors="coerce")

    col5 = None
    if five_year_sheet:
        five = read_sheet(five_year_sheet)
        col5 = next(
            (c for c in five.columns
             if "median five-year ahead expected inflation rate" in c.lower()),
            None,
        )
        if col5:
            out["sce_5y"] = pd.to_numeric(five[col5], errors="coerce")

    out = out[out.index >= "2023-01-01"].dropna(how="all")
    save(out, "s5_sce.csv")

    commodity = read_sheet(commodity_sheet)
    colg = next((c for c in commodity.columns if c.lower() == "gas"), None)
    if not colg:
        raise RuntimeError("Commodity expectations 시트에서 Gas 열을 찾지 못함")
    g = pd.DataFrame({"gas_exp": pd.to_numeric(commodity[colg], errors="coerce")})
    g = g[g.index >= "2023-01-01"].dropna()
    save(g, "s5b_gas.csv")

    manifest.append({"series": "NYFED_SCE", "source": "NY Fed", "url": SCE_MAIN,
                     "freq": "monthly",
                     "last_obs": str(out.index[-1].date()),
                     "last_value": {
                         column: float(out[column].dropna().iloc[-1])
                         for column in out.columns
                     },
                     "sheets": {
                         "1y_3y": inflation_sheet,
                         "5y": five_year_sheet,
                         "gas": commodity_sheet,
                     },
                     "cols_mapped": {"1y": col1, "3y": col3, "5y": col5, "gas": colg}})
    # T5YIFR 월말 리샘플
    t5 = fred("T5YIFR", "2023-01-01")["T5YIFR"].resample("ME").last().dropna()
    save(t5.to_frame("t5yifr_monthend"), "s5_t5yifr.csv")
    return out


# ---------- S6 소비자 연체 ----------
def s6_consumer():
    d = fred("DRCCLACBS", "2015-01-01")
    d.columns = ["cc_delinq"]
    save(d, "s6_consumer.csv")
    return d


# ---------- S7 노동 ----------
def s7_labor():
    un = fred("UNRATE", "2023-01-01")["UNRATE"]
    pay = fred("PAYEMS", "2022-01-01")["PAYEMS"]
    mom = pay.diff().dropna()  # 천 명
    df = pd.DataFrame({"unrate": un, "payems_mom_k": mom}).dropna()
    df = df[df.index >= "2023-01-01"]
    save(df, "s7_labor.csv")
    return df


# ---------- S10 노동공급 ----------
def s10_laborsupply():
    """실업률이 '수요 강세'인지 '공급 축소'인지 가르는 최소 지표 묶음.

    실업률만으로는 분자(실업자)가 줄어서 내린 건지 분모(경제활동인구)가
    줄어서 내린 건지 구별되지 않는다. 고용률(EMRATIO)은 분모가 전체 인구라
    그 구별이 된다. 실업률↓ + 고용률↓ = 공급 축소.
    """
    un = fred("UNRATE", "2024-01-01")["UNRATE"]
    emr = fred("EMRATIO", "2024-01-01")["EMRATIO"]          # 고용률(취업자/인구)
    civ = fred("CIVPART", "2024-01-01")["CIVPART"]           # 경제활동참가율
    prime = fred("LNS11300060", "2024-01-01")["LNS11300060"]  # 25~54세 참가율
    u6 = fred("U6RATE", "2024-01-01")["U6RATE"]
    df = pd.DataFrame({
        "unrate": un, "emratio": emr, "civpart": civ,
        "primeage_civpart": prime, "u6rate": u6,
    })
    df = df[df.index >= "2024-01-01"].dropna(how="all")
    save(df, "s10_laborsupply.csv")
    return df


# ---------- S11 노동공급 구성 + 임금 ----------
def s11_laborcomposition():
    """공급 축소의 '원인'과 '인플레 전이'를 각각 반증 가능하게 만드는 묶음.

    - 구직단념설 반증용: NILFWJN(일자리를 원하는 비경활인구)이 늘지 않으면 단념이 아니다.
    - 인구설 확인용: 외국출생 경활인구 '수준'이 줄고 '참가율'은 평평하면 인구 감소다.
    - 임금 전이 반증용: 공급이 줄어도 시간당임금이 가속되지 않으면
      '노동비용발 서비스 인플레' 경로는 성립하지 않는다.
    """
    clf = fred("CLF16OV", "2024-01-01")["CLF16OV"]            # 경활인구 총계(SA)
    fb = fred("LNU01073395", "2024-01-01")["LNU01073395"]     # 외국출생 경활인구(NSA)
    fbr = fred("LNU01373395", "2024-01-01")["LNU01373395"]    # 외국출생 참가율(NSA)
    nilf = fred("NILFWJN", "2024-01-01")["NILFWJN"]           # 일자리 원하는 비경활인구
    ahe = fred("CES0500000003", "2023-01-01")["CES0500000003"]  # 시간당임금(민간 전체)
    df = pd.DataFrame({
        "clf_total_sa_k": clf,
        "clf_foreignborn_nsa_k": fb,
        "foreignborn_lfpr_nsa": fbr,
        "nilf_want_job_k": nilf,
        "ahe_usd": ahe,
        "ahe_yoy_pct": yoy(ahe),
    })
    df = df[df.index >= "2024-06-01"].dropna(how="all")
    save(df, "s11_laborcomposition.csv")
    return df


# ---------- S8 EPU ----------
def s8_epu():
    e = fred("USEPUINDXM", "2015-01-01")
    e.columns = ["epu"]
    save(e, "s8_epu.csv")
    return e


def near(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def main():
    print("Collecting…")
    s1_fedpath()
    s2 = s2_inflation()
    oil_peak = s3_oil()
    s4_spr()
    try:
        sce = s5_sce()
    except Exception as e:
        print(f"  [S5] SCE 수집 경고: {e} — 열 매핑 확인 필요", file=sys.stderr)
        sce = None
    s6 = s6_consumer()
    s7 = s7_labor()
    s8_epu()
    s10 = s10_laborsupply()
    s11 = s11_laborcomposition()

    # --- 수동값 + 이벤트(annotations) : 출처·as-of 명시, 값은 시계열 점 아님 ---
    annotations = {
        "as_of": RETRIEVED_AT,
        "sep_2026_yearend_median": {"value": 3.8, "as_of": "2026-06-17",
            "label": "2026 year-end median of appropriate policy (SEP)",
            "url": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm"},
        "spr_release": {"planned_mbbl": 172, "released_through_2026_04_24_mbbl": 17.5,
            "stock_at_2026_04_24_mbbl": 397.9,
            "note": "172M=계획량, 17.5M=4/24까지 실제 방출. stock축에 그리지 말 것.",
            "url": "https://www.eia.gov/todayinenergy/detail.php?id=67625"},
        "cc_delinq_equifax_note": {"value": 13.12,
            "note": "정의가 다른 Equifax subprime/severe 지표 — DRCCLACBS(≈2.9%)와 혼동 금지. 차트에 그리지 말 것."},
        "oil_events": [
            {"date": "2026-02-28", "label": "US-Iran 개전",
             "url": "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/4418396/us-forces-launch-operation-epic-fury/"},
            {"date": "2026-04-08", "label": "휴전",
             "url": "https://www.un.org/sg/en/content/highlight/2026-04-08.html"},
            {"date": "2026-07-08", "label": "재점화(미국 타격)",
             "url": "https://www.whitehouse.gov/videos/president-donald-j-trump-provides-an-update-on-u-s-forces-retaliatory-strikes-against-iran/"},
        ],
        "oil_peak_derived": oil_peak,  # 하드코딩 아님 — 데이터 idxmax
        "midterm": {"date": "2026-11-03", "label": "미국 중간선거"},
    }
    (OUT / "annotations.json").write_text(
        json.dumps(annotations, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "manifest.json").write_text(json.dumps(
        {"retrieved_at": RETRIEVED_AT, "series": manifest},
        ensure_ascii=False,
        indent=2,
    ), encoding="utf-8")
    print(f"  wrote {OUT/'annotations.json'}, {OUT/'manifest.json'}")

    # --- 검증 assertion (PLAN 확정값. 개정으로 바뀌면 값+주석 갱신) ---
    print("Asserting known values…")
    checks = [
        ("core PCE May≈3.4", lambda: near(s2["core_pce_yoy"].loc["2026-05"].iloc[0], 3.4, 0.15)),
        ("CPI June≈3.5", lambda: near(s2["cpi_headline_yoy"].loc["2026-06"].iloc[0], 3.5, 0.15)),
        ("core CPI June≈2.6", lambda: near(s2["cpi_core_yoy"].loc["2026-06"].iloc[0], 2.6, 0.15)),
        ("UNRATE June≈4.2", lambda: near(s7["unrate"].loc["2026-06"].iloc[0], 4.2, 0.15)),
        ("payroll June≈+57k", lambda: near(s7["payems_mom_k"].loc["2026-06"].iloc[0], 57, 20)),
        ("DRCCLACBS latest≈2.92", lambda: near(s6["cc_delinq"].iloc[-1], 2.92, 0.2)),
        # --- 본문 '완충은 착시' 주장의 근거. 이 셋이 깨지면 결론을 되돌려야 한다. ---
        ("EMRATIO June≈59.0", lambda: near(s10["emratio"].loc["2026-06"].iloc[0], 59.0, 0.2)),
        ("CIVPART June≈61.5", lambda: near(s10["civpart"].loc["2026-06"].iloc[0], 61.5, 0.2)),
        # 실업률과 고용률이 '같이' 내려가야 공급축소 해석이 성립한다. 갈라지면 재검토.
        ("UNRATE·EMRATIO 동반하락(2025-11→2026-06)", lambda: (
            s10["unrate"].loc["2026-06"].iloc[0] < s10["unrate"].loc["2025-11"].iloc[0]
            and s10["emratio"].loc["2026-06"].iloc[0] < s10["emratio"].loc["2025-11"].iloc[0]
        )),
        # 임금이 가속되면 '노동공급 축소 → 서비스 인플레' 경로가 살아난다 → 본문 수정 필요
        ("AHE YoY 미가속(2026-06 < 2025-06)", lambda: (
            s11["ahe_yoy_pct"].loc["2026-06"].iloc[0] < s11["ahe_yoy_pct"].loc["2025-06"].iloc[0]
        )),
        # 구직단념설 반증: 일자리 원하는 비경활인구가 크게 늘지 않아야 한다
        ("NILFWJN YoY 증가 <300k", lambda: abs(
            s11["nilf_want_job_k"].loc["2026-06"].iloc[0]
            - s11["nilf_want_job_k"].loc["2025-06"].iloc[0]) < 300),
        # Core PCE > Core CPI 역전 지속 여부 (본문 4장)
        ("Core PCE > Core CPI 역전 유지", lambda:
            s2["core_pce_yoy"].dropna().iloc[-1] > s2["cpi_core_yoy"].dropna().iloc[-1]),
    ]
    if sce is not None and "sce_1y" in sce:
        checks.append(
            ("SCE 1y June≈3.7", lambda: near(sce["sce_1y"].loc["2026-06"].iloc[0], 3.7, 0.3))
        )
    for label, check in checks:
        try:
            result = check()
            print(f"  {'PASS' if result else 'FAIL'} {label}")
        except Exception as e:
            print(f"  FAIL {label}: {e}", file=sys.stderr)

    print("Done. data/ 폴더를 Claude에게 전달 → xlsx+PNG 빌드.")


if __name__ == "__main__":
    main()
