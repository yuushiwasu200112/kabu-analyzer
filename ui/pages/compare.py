"""
複数社比較ページ
"""
import streamlit as st
import os
import json
import plotly.graph_objects as go
from dotenv import load_dotenv

try:
    load_dotenv()
except:
    pass

try:
    if 'EDINET_API_KEY' in st.secrets:
        os.environ['EDINET_API_KEY'] = st.secrets['EDINET_API_KEY']
except:
    pass


@st.cache_data
def load_code_map():
    # 複数のパスを試す
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'edinet_code_map.json'),
        os.path.join(os.getcwd(), 'config', 'edinet_code_map.json'),
    ]
    path = None
    for p in candidates:
        if os.path.exists(p):
            path = p
            break
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CODE_MAP = load_code_map()

st.title("⚖️ 複数社比較")
st.caption("最大3社まで並べて比較できます")

# ── 銘柄入力 ──
cols_input = st.columns(3)
codes = []
for i in range(3):
    with cols_input[i]:
        code = st.text_input(f"銘柄{i+1}", max_chars=4, key=f"compare_{i}",
                             placeholder="証券コード")
        if code and len(code) == 4 and code.isdigit() and code in CODE_MAP:
            codes.append(code)
            st.caption(f"✅ {CODE_MAP[code]['name']}")
        elif code:
            st.caption("❌ 未対応")

if len(codes) >= 2:
    if st.button("🔍 比較分析を実行", type="primary"):
        from parsers.xbrl_parser import download_and_parse
        from analysis.indicators import calc_indicators, calc_growth
        from analysis.scoring import calc_total_score
        from data_sources.stock_client import get_stock_info
        from data_sources.cache_manager import get_cache, set_cache
        import datetime
        import requests

        API_KEY = os.getenv("EDINET_API_KEY")
        results = {}

        for code in codes:
            company = CODE_MAP[code]
            name = company["name"]
            edinet_code = company["edinet_code"]

            with st.spinner(f"{name} を分析中..."):
                # 株価
                stock_info = get_stock_info(code)
                price = stock_info["current_price"] if stock_info else 0

                # 有報検索
                cache_key_docs = f"docs_{edinet_code}"
                docs = get_cache(cache_key_docs, max_age_hours=168)
                if not docs:
                    url = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
                    found = []
                    today = datetime.date.today()
                    for year in range(today.year, today.year - 5, -1):
                        for month in [6, 7, 3, 4, 5, 8, 9]:
                            for day in range(15, 31):
                                try:
                                    d = datetime.date(year, month, day)
                                    if d > today:
                                        continue
                                    resp = requests.get(url, params={
                                        "date": f"{year}-{month:02d}-{day:02d}",
                                        "type": 2, "Subscription-Key": API_KEY,
                                    }, timeout=30)
                                    for doc in resp.json().get("results", []):
                                        if doc.get("edinetCode") == edinet_code and doc.get("docTypeCode") == "120":
                                            if doc["docID"] not in [d["docID"] for d in found]:
                                                found.append({
                                                    "docID": doc["docID"],
                                                    "periodEnd": doc.get("periodEnd", ""),
                                                    "docDescription": doc.get("docDescription", ""),
                                                })
                                except:
                                    continue
                            if any(str(year) in d.get("periodEnd", "") for d in found):
                                break
                        if len(found) >= 2:
                            break
                    found.sort(key=lambda x: x.get("periodEnd", ""), reverse=True)
                    docs = found[:4]
                    if docs:
                        set_cache(cache_key_docs, docs)

                if not docs:
                    st.warning(f"⚠️ {name} の有報が見つかりませんでした")
                    continue

                # 財務データ
                cache_cur = f"xbrl_{docs[0]['docID']}"
                current = get_cache(cache_cur)
                if not current:
                    current = download_and_parse(docs[0]["docID"], API_KEY)
                    if current:
                        set_cache(cache_cur, current)

                previous = None
                if len(docs) > 1:
                    cache_prev = f"xbrl_{docs[1]['docID']}"
                    previous = get_cache(cache_prev)
                    if not previous:
                        previous = download_and_parse(docs[1]["docID"], API_KEY)
                        if previous:
                            set_cache(cache_prev, previous)

                if current:
                    indicators = calc_indicators(current, price)
                    if previous:
                        growth = calc_growth(current, previous)
                        indicators.update(growth)
                    score_result = calc_total_score(indicators, "バランス", "中期")
                    results[code] = {
                        "name": name,
                        "indicators": indicators,
                        "score": score_result,
                        "price": price,
                    }

        if len(results) >= 2:
            st.divider()

            # ── 総合スコア比較 ──
            st.subheader("🏆 総合スコア比較")
            score_cols = st.columns(len(results))
            for i, (code, data) in enumerate(results.items()):
                with score_cols[i]:
                    s = data["score"]["total_score"]
                    if s >= 75:
                        color = "🟢"
                    elif s >= 50:
                        color = "🟡"
                    else:
                        color = "🔴"
                    st.metric(data["name"], f"{color} {s}点")

            # ── レーダーチャート重ね合わせ ──
            st.subheader("📊 カテゴリ別スコア比較")
            fig_radar = go.Figure()
            colors = ["#2E75B6", "#E74C3C", "#2ECC71"]
            for i, (code, data) in enumerate(results.items()):
                cats = list(data["score"]["category_scores"].keys())
                vals = list(data["score"]["category_scores"].values())
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]],
                    theta=cats + [cats[0]],
                    fill='toself',
                    name=data["name"],
                    line_color=colors[i % 3],
                    fillcolor=f"rgba({','.join(str(int(colors[i % 3].lstrip('#')[j:j+2], 16)) for j in (0,2,4))},0.15)",
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                height=450,
                legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            # ── カテゴリ別バー ──
            st.subheader("📈 カテゴリ別スコア")
            for cat in ["収益性", "安全性", "成長性", "割安度"]:
                st.markdown(f"**{cat}**")
                bar_cols = st.columns(len(results))
                for i, (code, data) in enumerate(results.items()):
                    with bar_cols[i]:
                        val = data["score"]["category_scores"].get(cat, 0)
                        st.progress(val / 100, text=f"{data['name']}: {val}点")

            # ── 主要指標比較テーブル ──
            st.divider()
            st.subheader("📋 主要指標比較")

            import pandas as pd
            compare_metrics = [
                "ROE", "ROA", "営業利益率", "自己資本比率",
                "PER", "PBR", "配当利回り",
                "売上高成長率", "営業利益成長率", "純利益成長率",
            ]
            table_data = {}
            for code, data in results.items():
                col_data = {}
                for m in compare_metrics:
                    val = data["indicators"].get(m)
                    if val is not None:
                        col_data[m] = f"{val:.2f}"
                    else:
                        col_data[m] = "---"
                table_data[data["name"]] = col_data

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)

elif len(codes) == 1:
    st.info("📌 2社以上入力してください")
else:
    st.info("📌 比較したい銘柄の証券コードを2〜3社分入力してください")
