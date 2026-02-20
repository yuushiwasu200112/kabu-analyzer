import streamlit as st
import os
import json
from dotenv import load_dotenv

try:
    load_dotenv()
except:
    pass

st.set_page_config(page_title="Kabu Analyzer", page_icon="📊", layout="wide")

try:
    if 'EDINET_API_KEY' in st.secrets:
        os.environ['EDINET_API_KEY'] = st.secrets['EDINET_API_KEY']
except:
    pass

# ── EDINETコードマップ読み込み ──
@st.cache_data
def load_code_map():
    path = os.path.join(os.path.dirname(__file__), "config", "edinet_code_map.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

CODE_MAP = load_code_map()

# 指標の表示フォーマット
INDICATOR_FORMAT = {
    "ROE": ("%", "収益性"), "ROA": ("%", "収益性"),
    "営業利益率": ("%", "収益性"), "配当利回り": ("%", "収益性"),
    "自己資本比率": ("%", "安全性"), "流動比率": ("%", "安全性"),
    "有利子負債比率": ("%", "安全性"), "ICR": ("倍", "安全性"),
    "PER": ("倍", "割安度"), "PBR": ("倍", "割安度"),
    "EPS": ("円", "割安度"), "BPS": ("円", "割安度"),
    "売上高成長率": ("%", "成長性"), "営業利益成長率": ("%", "成長性"),
    "純利益成長率": ("%", "成長性"), "総資産成長率": ("%", "成長性"),
}

# ── ヘッダー ──
st.title("📊 Kabu Analyzer")
st.subheader("株式投資分析ツール")

# ── サイドバー ──
with st.sidebar:
    st.header("⚙️ 分析設定")
    style = st.selectbox("投資スタイル", [
        "バランス", "バリュー投資", "グロース投資", "高配当投資", "安定性重視"
    ])
    period = st.selectbox("投資期間", ["中期（1〜3年）", "短期（〜1年）", "長期（3年以上）"])
    st.divider()
    st.markdown(f"**📌 対応銘柄数: {len(CODE_MAP):,}社**")
    st.caption("東証上場企業に対応")
    st.caption("Free版: 月5銘柄まで分析可能")

st.divider()

# 検索方法の選択
search_tab1, search_tab2 = st.tabs(["📝 証券コードで検索", "🔎 企業名で検索"])

with search_tab1:
    stock_code = st.text_input("証券コードを入力（例: 7203）", max_chars=4, key="code_input")

with search_tab2:
    search_name = st.text_input("企業名を入力（例: トヨタ）", key="name_input")
    if search_name and len(search_name) >= 2:
        matches = {k: v for k, v in CODE_MAP.items() if search_name in v["name"]}
        if matches:
            options = [f"{k} - {v['name']}" for k, v in list(matches.items())[:20]]
            selected = st.selectbox("該当企業を選択", options, key="name_select")
            if selected:
                stock_code = selected.split(" - ")[0]
        else:
            st.info("該当する企業が見つかりませんでした")
            stock_code = None
    else:
        stock_code = None

if stock_code:
    if len(stock_code) != 4 or not stock_code.isdigit():
        st.error("❌ 4桁の数字を入力してください")
    elif stock_code not in CODE_MAP:
        st.warning(f"⚠️ 証券コード {stock_code} はEDINETに登録されていません")
    else:
        company_info = CODE_MAP[stock_code]
        company_name = company_info["name"]
        edinet_code = company_info["edinet_code"]
        st.success(f"✅ {company_name}（{stock_code}）を分析中...")

        # ── 株価取得 ──
        with st.spinner("株価データを取得中..."):
            from data_sources.stock_client import get_stock_info
            stock_info = get_stock_info(stock_code)

        if not stock_info:
            st.warning("⚠️ 株価データを取得できませんでした。財務データのみで分析します。")
            stock_info = {
                "stock_code": stock_code, "name": company_name,
                "current_price": 0, "market_cap": 0,
                "per": 0, "pbr": 0, "eps": 0, "bps": 0,
                "dividend_yield": 0, "sector": "不明", "industry": "不明",
            }

        # 株価情報表示
        if stock_info["current_price"] > 0:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("現在株価", f"¥{stock_info['current_price']:,.0f}")
            col2.metric("PER", f"{stock_info['per']:.1f}倍" if stock_info['per'] else "---")
            col3.metric("PBR", f"{stock_info['pbr']:.2f}倍" if stock_info['pbr'] else "---")
            cap = stock_info['market_cap']
            if cap >= 1e12:
                col4.metric("時価総額", f"¥{cap/1e12:.1f}兆")
            elif cap > 0:
                col4.metric("時価総額", f"¥{cap/1e8:.0f}億")
            else:
                col4.metric("時価総額", "---")

        # ── EDINET有報を自動検索 ──
        from data_sources.cache_manager import get_cache, set_cache

        @st.cache_data(ttl=86400, show_spinner=False)
        def search_yuho(edinet_code, api_key):
            """有価証券報告書を自動検索"""
            import requests
            import datetime
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
                                "type": 2, "Subscription-Key": api_key,
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
                    if any(str(year) in d.get("periodEnd", "") or str(year) in d.get("docDescription", "") for d in found):
                        break
                if len(found) >= 4:
                    break

            found.sort(key=lambda x: x.get("periodEnd", ""), reverse=True)
            return found[:4]

        API_KEY = os.getenv("EDINET_API_KEY")

        # キャッシュされた有報リストを確認
        cache_key_docs = f"docs_{edinet_code}"
        docs = get_cache(cache_key_docs, max_age_hours=168)  # 1週間キャッシュ
        if not docs:
            with st.spinner("有価証券報告書を検索中（初回は時間がかかります）..."):
                docs = search_yuho(edinet_code, API_KEY)
                if docs:
                    set_cache(cache_key_docs, docs)

        if not docs:
            st.error("❌ 有価証券報告書が見つかりませんでした。この銘柄は未対応の可能性があります。")
        else:
            # ── 財務データ取得 ──
            with st.spinner("財務データを取得中..."):
                from parsers.xbrl_parser import download_and_parse
                from analysis.indicators import calc_indicators, calc_growth
                from analysis.scoring import calc_total_score

                current = None
                previous = None

                # 最新期
                cache_key_cur = f"xbrl_{docs[0]['docID']}"
                current = get_cache(cache_key_cur)
                if not current:
                    current = download_and_parse(docs[0]["docID"], API_KEY)
                    if current:
                        set_cache(cache_key_cur, current)

                # 前期
                if len(docs) > 1:
                    cache_key_prev = f"xbrl_{docs[1]['docID']}"
                    previous = get_cache(cache_key_prev)
                    if not previous:
                        previous = download_and_parse(docs[1]["docID"], API_KEY)
                        if previous:
                            set_cache(cache_key_prev, previous)

            if not current:
                st.error("❌ 財務データの取得に失敗しました")
            else:
                indicators = calc_indicators(current, stock_info["current_price"])
                if previous:
                    growth = calc_growth(current, previous)
                    indicators.update(growth)

                period_map = {"短期（〜1年）": "短期", "中期（1〜3年）": "中期", "長期（3年以上）": "長期"}
                period_key = period_map.get(period, "中期")
                result = calc_total_score(indicators, style, period_key)

                # ── 強制フィルター ──
                from analysis.filters import check_filters
                filter_warnings = check_filters(current, previous)

                if filter_warnings:
                    st.divider()
                    for w in filter_warnings:
                        if w['level'] == 'danger':
                            st.error(f"{w['icon']} **{w['title']}**: {w['message']}")
                        else:
                            st.warning(f"{w['icon']} **{w['title']}**: {w['message']}")

                st.divider()

                # ── ゲージチャート ──
                import plotly.graph_objects as go

                score = result["total_score"]
                judgment = result["judgment"]
                if score >= 75:
                    score_color = "🟢"
                elif score >= 50:
                    score_color = "🟡"
                else:
                    score_color = "🔴"

                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score,
                    title={"text": f"{company_name} 総合スコア", "font": {"size": 20}},
                    number={"suffix": "点", "font": {"size": 48}},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 2},
                        "bar": {"color": "#2E75B6"},
                        "steps": [
                            {"range": [0, 50], "color": "#FFCDD2"},
                            {"range": [50, 75], "color": "#FFF9C4"},
                            {"range": [75, 100], "color": "#C8E6C9"},
                        ],
                        "threshold": {
                            "line": {"color": "#1B3A5C", "width": 4},
                            "thickness": 0.75, "value": score,
                        },
                    },
                ))
                fig_gauge.update_layout(height=280, margin=dict(t=60, b=20, l=30, r=30))
                st.plotly_chart(fig_gauge, use_container_width=True)
                st.markdown(f"### {score_color} {judgment}")
                st.caption(f"投資スタイル: {style} ｜ 投資期間: {period}")

                # ── レーダーチャート + カテゴリバー ──
                categories = list(result["category_scores"].keys())
                scores_list = list(result["category_scores"].values())

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=scores_list + [scores_list[0]],
                    theta=categories + [categories[0]],
                    fill='toself', name=company_name,
                    line_color='#2E75B6', fillcolor='rgba(46,117,182,0.3)',
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title=f"{company_name} カテゴリ別スコア", height=420,
                )

                col_chart, col_detail = st.columns([1, 1])
                with col_chart:
                    st.plotly_chart(fig, use_container_width=True)
                with col_detail:
                    st.subheader("📊 カテゴリ別スコア")
                    for cat, cat_score in result["category_scores"].items():
                        st.progress(cat_score / 100, text=f"{cat}: {cat_score}点")

                # ── 時系列チャート ──
                st.divider()
                st.subheader("📉 主要指標の推移")

                if len(docs) >= 2:
                    all_years = {}
                    for doc in docs:
                        ck = f"xbrl_{doc['docID']}"
                        yd = get_cache(ck)
                        if not yd:
                            yd = download_and_parse(doc["docID"], API_KEY)
                            if yd:
                                set_cache(ck, yd)
                        if yd:
                            yi = calc_indicators(yd, stock_info["current_price"])
                            p = doc["periodEnd"][:4]
                            all_years[p] = yi

                    if len(all_years) >= 2:
                        years = sorted(all_years.keys())
                        trend_metrics = {
                            "ROE (%)": [all_years[y].get("ROE", 0) for y in years],
                            "ROA (%)": [all_years[y].get("ROA", 0) for y in years],
                            "営業利益率 (%)": [all_years[y].get("営業利益率", 0) for y in years],
                            "自己資本比率 (%)": [all_years[y].get("自己資本比率", 0) for y in years],
                        }
                        fig_trend = go.Figure()
                        colors = ["#2E75B6", "#E74C3C", "#2ECC71", "#F39C12"]
                        for i, (name, vals) in enumerate(trend_metrics.items()):
                            fig_trend.add_trace(go.Scatter(
                                x=years, y=vals, mode="lines+markers",
                                name=name, line=dict(color=colors[i], width=2),
                                marker=dict(size=8),
                            ))
                        fig_trend.update_layout(height=400, xaxis_title="年度", yaxis_title="%",
                                                legend=dict(orientation="h", y=-0.2))
                        st.plotly_chart(fig_trend, use_container_width=True)

                # ── 株価チャート ──
                st.divider()
                st.subheader("📈 株価チャート（過去1年）")
                try:
                    import yfinance as yf
                    import time
                    time.sleep(1)
                    ticker = yf.Ticker(f"{stock_code}.T")
                    hist = ticker.history(period="1y")
                    if not hist.empty and len(hist) > 10:
                        fig_candle = go.Figure(data=[go.Candlestick(
                            x=hist.index, open=hist["Open"], high=hist["High"],
                            low=hist["Low"], close=hist["Close"],
                            increasing_line_color="#2E75B6", decreasing_line_color="#E74C3C",
                        )])
                        fig_candle.update_layout(height=400, xaxis_rangeslider_visible=False,
                                                 xaxis_title="日付", yaxis_title="株価（円）")
                        st.plotly_chart(fig_candle, use_container_width=True)
                    else:
                        st.info("ℹ️ 株価チャートのデータを取得できませんでした")
                except:
                    st.info("ℹ️ 株価チャートは一時的に利用できません（Rate Limit）")

                # ── 指標一覧 ──
                st.divider()
                st.subheader("📋 財務指標一覧")
                for category in ["収益性", "安全性", "成長性", "割安度"]:
                    cat_indicators = {
                        k: v for k, v in indicators.items()
                        if k in INDICATOR_FORMAT and INDICATOR_FORMAT[k][1] == category
                    }
                    if cat_indicators:
                        st.markdown(f"**{category}**")
                        cols = st.columns(len(cat_indicators))
                        for i, (name, val) in enumerate(cat_indicators.items()):
                            unit = INDICATOR_FORMAT[name][0]
                            if unit == "円":
                                cols[i].metric(name, f"{val:,.0f}{unit}")
                            else:
                                cols[i].metric(name, f"{val:.2f}{unit}")

# ── フッター ──
st.divider()
st.caption("⚠️ 本ツールは投資助言ではありません。投資判断はご自身の責任で行ってください。データの正確性は保証されません。")
