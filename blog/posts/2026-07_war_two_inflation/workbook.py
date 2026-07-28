#!/usr/bin/env python3
"""workbook.py — 이 글 폴더의 data/*.csv → out/war_two_inflation_data.xlsx
경로는 모두 이 파일 위치 기준(HERE). 어느 CWD에서 실행해도 동일하게 동작한다.
README + S1~S11 시트(각 다른 데이터 + 네이티브 차트). dual-axis 금지 → 혼합단위는 시트 내 2차트.
"""
import json
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, BarChart, AreaChart, Reference, Series
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out" / "war_two_inflation_data.xlsx"; OUT.parent.mkdir(parents=True, exist_ok=True)
ann = json.loads((DATA/"annotations.json").read_text())
man = json.loads((DATA/"manifest.json").read_text())

BLUE="0072B2"; INKFILL="1A1A1A"; HEADFILL="20303A"
thin=Side(style="thin",color="DDDDDD"); border=Border(left=thin,right=thin,top=thin,bottom=thin)

wb=Workbook(); wb.remove(wb.active)

def add_df(ws, df, start=3):
    df=df.reset_index()
    df.iloc[:,0]=pd.to_datetime(df.iloc[:,0]).dt.strftime("%Y-%m-%d")
    for j,col in enumerate(df.columns,1):
        c=ws.cell(start,j,col); c.font=Font(bold=True,color="FFFFFF"); c.fill=PatternFill("solid",fgColor=HEADFILL)
        c.alignment=Alignment(horizontal="center")
    for i,row in enumerate(dataframe_to_rows(df,index=False,header=False),start+1):
        for j,v in enumerate(row,1): ws.cell(i,j,v)
    ws.column_dimensions["A"].width=13
    for col in "BCDEFGH": ws.column_dimensions[col].width=15
    return len(df)+start  # last row

def head(ws,title,sub,src):
    ws["A1"]=title; ws["A1"].font=Font(size=15,bold=True,color="1A1A1A")
    ws["A2"]=sub; ws["A2"].font=Font(size=10,italic=True,color="666666")
    ws.sheet_view.showGridLines=False

def lchart(ws,title,minr,maxr,mincol,maxcol,anchor,y="%"):
    ch=LineChart(); ch.title=title; ch.height=9; ch.width=20; ch.style=2
    ch.y_axis.title=y; ch.x_axis.number_format="yyyy-mm"; ch.x_axis.majorTimeUnit="months"
    data=Reference(ws,min_col=mincol,max_col=maxcol,min_row=minr,max_row=maxr)
    cats=Reference(ws,min_col=1,min_row=minr+1,max_row=maxr)
    ch.add_data(data,titles_from_data=True); ch.set_categories(cats)
    for s in ch.series: s.smooth=False
    ws.add_chart(ch,anchor)

# README
rm=wb.create_sheet("README")
rm.sheet_view.showGridLines=False
rm["A1"]="WAR와 두 개의 인플레이션 — 데이터"; rm["A1"].font=Font(size=16,bold=True)
rm["A2"]=f"수집 시각(UTC): {man.get('retrieved_at','')}  ·  YoY=100*(x/x.shift(12)-1), PAYEMS MoM=diff(천명), T5YIFR 월말 리샘플"
rm["A2"].font=Font(italic=True,color="666666")
hdr=["시트","내용","소스","시리즈/ID","freq","비고"]
rows=[
 ["S1_FedPath","정책금리 목표범위 + SEP dot","FRED/Fed","DFEDTARU·DFEDTARL·SEP","일/—","SEP 2026 median 3.8%(수동)"],
 ["S2_Inflation","Core PCE·CPI YoY","FRED","PCEPILFE(SA)·CPIAUCNS·CPILFENS(NSA)","월","Core PCE는 SA, CPI는 NSA(BLS 공식 보도치와 일치) — 조정방식이 다르다"],
 ["S3_Oil","WTI·Brent","FRED","DCOILWTICO·DCOILBRENTEU","일","피크 idxmax=Brent 138.21(4/7)"],
 ["S4_SPR","전략비축유 재고","EIA","WCSSTUS1","주","계획172M/실제17.5M(4/24)/재고397.9M=주석"],
 ["S5_InflExp","기대인플레 SCE+5y5y","NY Fed/FRED","SCE 1y·3y·5y·T5YIFR","월","핵심 대비 차트"],
 ["S5b_Gas","휘발유 가격 기대","NY Fed","SCE gas","월","6월 1.5%로 급락"],
 ["S6_Consumer","카드 연체율","FRED","DRCCLACBS","분기","Equifax 13.12%와 다른 지표"],
 ["S7_Labor","실업률·고용증감","FRED","UNRATE·PAYEMS","월","4.2% / +57k — 해석은 S10 참조"],
 ["S8_EPU","경제정책 불확실성","FRED","USEPUINDXM","월","2026-06 ≈198"],
 ["S10_LaborSupply","실업률·고용률·참가율","FRED","UNRATE·EMRATIO·CIVPART·LNS11300060·U6RATE(SA)","월","분모(참가율) 축소 분해 — 반사실은 차트에서 계산"],
 ["S11_LaborComp","노동력 구성·시급","FRED","CLF16OV·LNU01073395·LNU01373395·NILFWJN·CES0500000003","월","외국인 LF·LFPR은 NSA · 26년 1월 인구통제 재벤치마킹 단절 주의"],
]
for j,h in enumerate(hdr,1):
    c=rm.cell(4,j,h); c.font=Font(bold=True,color="FFFFFF"); c.fill=PatternFill("solid",fgColor=HEADFILL)
for i,r in enumerate(rows,5):
    for j,v in enumerate(r,1): rm.cell(i,j,v).border=border
for col,w in zip("ABCDEF",[17,26,12,38,8,52]): rm.column_dimensions[col].width=w
_annrow=5+len(rows)+1
rm.cell(_annrow,1,"주석/이벤트(annotations.json):").font=Font(bold=True)
rm.cell(_annrow+1,1,f"SEP 2026 median {ann['sep_2026_yearend_median']['value']}% · SPR 계획 {ann['spr_release']['planned_mbbl']}M/실제 {ann['spr_release']['released_through_2026_04_24_mbbl']}M · 유가피크 Brent {ann['oil_peak_derived']['brent_peak_value']}(4/7)")
rm.cell(_annrow+2,1,"이벤트: "+" / ".join(f"{e['date']} {e['label']}" for e in ann['oil_events']))

def sheet(name,csv,title,sub,src):
    ws=wb.create_sheet(name); head(ws,title,sub,src)
    df=pd.read_csv(DATA/csv,index_col=0)
    last=add_df(ws,df)
    return ws,df,last

# S1
ws,df,last=sheet("S1_FedPath","s1_fedpath.csv","① 연준 정책금리 경로","목표범위 3.50–3.75% 동결, SEP 2026 median 3.8%","FRED/Fed")
lchart(ws,"정책금리 목표범위(%)",3,last,2,3,"H3","%")
# S2
ws,df,last=sheet("S2_Inflation","s2_inflation.csv","② 인플레이션 (YoY)","Core PCE 3.4% · CPI=NSA 공식치 일치","FRED")
lchart(ws,"전년동월비(%)",3,last,2,4,"H3","%")
# S3
ws,df,last=sheet("S3_Oil","s3_oil.csv","③ 유가 WTI·Brent","4월 피크(Brent 138) 후 되돌림","FRED")
lchart(ws,"$/배럴",3,last,2,3,"F3","$/bbl")
# S4
ws,df,last=sheet("S4_SPR","s4_spr.csv","④ SPR 전략비축유 재고","1983년 이후 최저 부근 — 완충 소진","EIA WCSSTUS1")
ch=AreaChart(); ch.title="SPR 재고(백만 배럴)"; ch.height=9; ch.width=20
d=Reference(ws,min_col=2,min_row=3,max_row=last); cats=Reference(ws,min_col=1,min_row=4,max_row=last)
ch.add_data(d,titles_from_data=True); ch.set_categories(cats); ws.add_chart(ch,"F3")
# S5
ws,df,last=sheet("S5_InflExp","s5_sce.csv","⑤ 기대인플레 (핵심)","1y·3y 상승 vs 5y 안정","NY Fed SCE")
lchart(ws,"기대 인플레이션(%)",3,last,2,4,"G3","%")
# S5b gas
ws,df,last=sheet("S5b_Gas","s5b_gas.csv","⑤b 휘발유 가격 기대","6월 1.5%로 급락 — 기대상승이 유가발 아님","NY Fed SCE")
lchart(ws,"휘발유 기대(%)",3,last,2,2,"E3","%")
# S6
ws,df,last=sheet("S6_Consumer","s6_consumer.csv","⑥ 카드 연체율","완만(2.92%) — tail","FRED DRCCLACBS")
lchart(ws,"연체율(%)",3,last,2,2,"E3","%")
# S7 (2 charts, no dual axis)
ws,df,last=sheet("S7_Labor","s7_labor.csv","⑦ 노동 (실업률 · 고용증감)","4.2% / +57k — 표면 수치. 분모 효과는 S10 시트에서 분해","FRED")
lchart(ws,"실업률(%)",3,last,2,2,"E3","%")
bc=BarChart(); bc.title="월간 고용증감(천명)"; bc.height=8; bc.width=20
d=Reference(ws,min_col=3,min_row=3,max_row=last); cats=Reference(ws,min_col=1,min_row=4,max_row=last)
bc.add_data(d,titles_from_data=True); bc.set_categories(cats); ws.add_chart(bc,"E20")
# S8
ws,df,last=sheet("S8_EPU","s8_epu.csv","⑧ 경제정책 불확실성","2015~ 정상범위 상단","FRED USEPUINDXM")
lchart(ws,"EPU 지수",3,last,2,2,"E3","idx")
# S10 (2 charts) — 실업률 하락의 분자/분모 분해. 차트 ⑩의 반사실은 여기서 계산하지 않는다(시트는 원자료만).
ws,df,last=sheet("S10_LaborSupply","s10_laborsupply.csv","⑩ 노동공급 분해 (실업률 · 고용률 · 참가율)",
                 "2025-11 → 2026-06: 실업률 4.5→4.2%인데 고용률도 59.6→59.0% · 참가율 62.5→61.5%","FRED (모두 SA)")
lchart(ws,"고용률 · 참가율 (%)",3,last,3,5,"H3","%")
lchart(ws,"실업률 U-3 (%)",3,last,2,2,"H21","%")
# S11
ws,df,last=sheet("S11_LaborComp","s11_laborcomposition.csv","⑪ 노동력 구성 · 시급",
                 "총 노동력 -1,022k 중 외국인 -700k(68%) · 단 외국인 LFPR도 66.3→65.6 · AHE YoY 3.86→3.52%","FRED")
lchart(ws,"노동력 수준(천명) — 총계 SA / 외국인 NSA",3,last,2,3,"I3","천명")
lchart(ws,"시간당 임금 YoY(%)",3,last,7,7,"I21","%")

wb.move_sheet("README",-(len(wb.sheetnames)-1))
wb.save(OUT)
print("wrote",OUT,"sheets:",wb.sheetnames)
