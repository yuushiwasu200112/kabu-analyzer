import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Kabu Analyzer", page_icon="📊", layout="wide")

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
    st.markdown("**📌 対応銘柄**")
    st.caption("7203 トヨタ自動車")
    st.caption("6758 ソニーグループ")
    st.caption("9984 ソフトバンクG")
    st.caption("8306 三菱UFJ")
    st.caption("6861 キーエンス")
    st.divider()
    st.caption("Free版: 月5銘柄まで分析可能")

# ── 対応銘柄データ ──
CODE_MAP = {
    "7203": "トヨタ自動車",
    "6758": "ソニーグループ",
    "9984": "ソフトバンクグループ",
    "8306": "三菱UFJフィナンシャル・グループ",
    "6861": "キーエンス",
}

DOC_IDS = {
    "7203": [
        {"docID": "S100TR7I", "periodEnd": "2024-03-31", "docDescription": "第120期"},
        {"docID": "S100QZHY", "periodEnd": "2023-03-31", "docDescription": "第119期"},
        {"docID": "S100OC13", "periodEnd": "2022-03-31", "docDescription": "第118期"},
        {"docID": "S100LO6W", "periodEnd": "2021-03-31", "docDescription": "第117期"},
    ],
    "6758": [
        {"docID": "S100W19Q", "periodEnd": "2025-03-31", "docDescription": "第108期"},
        {"docID": "S100TS7P", "periodEnd": "2024-03-31", "docDescription": "第107期"},
    ],
    "9984": [
        {"docID": "S100VHZ5", "periodEnd": "2024-12-31", "docDescription": "第28期"},
        {"docID": "S100T4X3", "periodEnd": "2023-12-31", "docDescription": "第27期"},
    ],
    "8306": [
        {"docID": "S100W4FB", "periodEnd": "2025-03-31", "docDescription": "第20期"},
        {"docID": "S100TRA1", "periodEnd": "2024-03-31", "docDescription": "第19期"},
    ],
    "6861": [
        {"docID": "S100VHZZ", "periodEnd": "2024-12-31", "docDescription": "第124期"},
        {"docID": "S100T58N", "periodEnd": "2023-12-31", "docDescription": "第123期"},
    ],
}

# フォールバック株価
FALLBACK_PRICES = {
    "7203": {"name": "トヨタ自動車", "price": 3635, "per": 12.79, "pbr": 1.22, "cap": 47_000_000_000_000},
    "6758": {"name": "ソニーグループ", "price": 3900, "per": 17.5, "pbr": 2.8, "cap": 24_000_000_000_000},
    "9984": {"name": "ソフトバンクG", "price": 9200, "per": 15.2, "pbr": 2.1, "cap": 13_000_000_000_000},
    "8306": {"name": "三菱UFJ", "price": 2050, "per": 12.5, "pbr": 1.1, "cap": 24_000_000_000_000},
    "6861": {"name": "キーエンス", "price": 65000, "per": 38.0, "pbr": 8.5, "cap": 16_000_000_000_000},
}

# 指標の表示フォーマット
INDICATOR_FORMAT = {
    "ROE": ("ROE", "%", "収益性"),
    "ROA": ("ROA", "%", "収益性"),
    "営業利益率": ("営業利益率", "%", "収益性"),
    "配当利回り": ("配当利回り", "%", "収益性"),
    "自己資本比率": ("自己資本比率", "%", "安全性"),
    "流動比率": ("流動比率", "%", "安全性"),
    "有利子負債比率": ("有利子負債比率", "%", "安全性"),
    "ICR": ("ICR", "倍", "安全性"),
    "PER": ("PER", "倍", "割安度"),
    "PBR": ("PBR", "倍", "割安度"),
    "EPS": ("EPS", "円", "割安度"),
    "BPS": ("BPS", "円", "割安度"),
    "売上高成長率": ("売上高成長率", "%", "成長性"),
    "営業利益成長率": ("営業利益成長率", "%", "成長性"),
    "純利益成長率": ("純利益成長率", "%", "成長性"),
    "総資産成長率": ("総資産成長率", "%", "成長性"),
}

st.divider()

stock_code = st.text_input("🔍 証券コードを入力（例: 7203）", max_chars=4)

if stock_code:
    if len(stock_code) != 4 or not stock_code.isdigit():
        st.error("❌ 4桁の数字を入力してください")
    elif stock_code not in CODE_MAP:
        st.warning(f"⚠️ 証券コード {stock_code} は現在未対応です")
    else:
        company_name = CODE_MAP[stock_code]
        st.success(f"✅ {company_name}（{stock_code}）を分析中...")

        # ── 株価取得 ──
        with st.spinner("株価データを取得中..."):
            from data_sources.stock_client import get_stock_info
            stock_info = get_stock_info(stock_code)

        # フォールバック
        if not stock_info and stock_code in FALLBACK_PRICES:
            fb = FALLBACK_PRICES[stock_code]
            stock_info = {
                "stock_code": stock_code, "name": fb["name"],
                "current_price": fb["price"], "market_cap": fb["cap"],
                "per": fb["per"], "pbr": fb["pbr"],
                "eps": 0, "bps": 0, "dividend_yield": 0,
                "sector": "不明", "industry": "不明",
            }
            st.info("ℹ️ 株価はキャッシュデータを使用しています")

        if not stock_info:
            st.error("❌ 株価データの取得に失敗しました")
        else:
            # 株価情報
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

            # ── EDINET財務データ ──
            if stock_code in DOC_IDS:
                with st.spinner("財務データを取得中..."):
                    from parsers.xbrl_parser import download_and_parse
                    from analysis.indicators import calc_indicators, calc_growth
                    from analysis.scoring import calc_total_score
                    from data_sources.cache_manager import get_cache, set_cache

                    API_KEY = os.getenv("EDINET_API_KEY")
                    docs = DOC_IDS[stock_code]

                    # キャッシュチェック
                    cache_key_cur = f"xbrl_{docs[0]['docID']}"
                    current = get_cache(cache_key_cur)
                    if not current:
                        current = download_and_parse(docs[0]["docID"], API_KEY)
                        if current:
                            set_cache(cache_key_cur, current)

                    previous = None
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

                    # 投資期間を変換
                    period_map = {"短期（〜1年）": "短期", "中期（1〜3年）": "中期", "長期（3年以上）": "長期"}
                    period_key = period_map.get(period, "中期")
                    result = calc_total_score(indicators, style, period_key)
                    # ── 強制フィルター（警告） ──
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

                    # ── 総合スコア ──
                    score = result["total_score"]
                    judgment = result["judgment"]
                    if score >= 75:
                        score_color = "🟢"
                    elif score >= 50:
                        score_color = "🟡"
                    else:
                        score_color = "🔴"

                    # ── ゲージチャート ──
                    import plotly.graph_objects as go
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
                                "thickness": 0.75,
                                "value": score,
                            },
                        },
                    ))
                    fig_gauge.update_layout(height=280, margin=dict(t=60, b=20, l=30, r=30))
                    st.plotly_chart(fig_gauge, use_container_width=True)
                    st.markdown(f"### {score_color} {judgment}")
                    st.caption(f"投資スタイル: {style}")

                    # ── レーダーチャート + カテゴリバー ──
                    import plotly.graph_objects as go

                    categories = list(result["category_scores"].keys())
                    scores = list(result["category_scores"].values())

                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=scores + [scores[0]],
                        theta=categories + [categories[0]],
                        fill='toself',
                        name=company_name,
                        line_color='#2E75B6',
                        fillcolor='rgba(46,117,182,0.3)',
                    ))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        title=f"{company_name} カテゴリ別スコア",
                        height=420,
                    )

                    col_chart, col_detail = st.columns([1, 1])
                    with col_chart:
                        st.plotly_chart(fig, use_container_width=True)
                    with col_detail:
                        st.subheader("📊 カテゴリ別スコア")
                        for cat, cat_score in result["category_scores"].items():
                            st.progress(cat_score / 100, text=f"{cat}: {cat_score}点")

                    # ── 時系列チャート（指標推移） ──
                    st.divider()
                    st.subheader("📉 主要指標の推移")

                    if stock_code in DOC_IDS and len(DOC_IDS[stock_code]) >= 2:
                        from parsers.xbrl_parser import download_and_parse as dp2
                        from analysis.indicators import calc_indicators as ci2

                        all_years = {}
                        for doc in DOC_IDS[stock_code]:
                            cache_key = f"xbrl_{doc['docID']}"
                            year_data = get_cache(cache_key)
                            if not year_data:
                                year_data = dp2(doc["docID"], API_KEY)
                                if year_data:
                                    set_cache(cache_key, year_data)
                            if year_data:
                                year_ind = ci2(year_data, stock_info["current_price"])
                                period = doc["periodEnd"][:4]
                                all_years[period] = year_ind

                        if len(all_years) >= 2:
                            import plotly.graph_objects as go_ts
                            years = sorted(all_years.keys())
                            
                            trend_metrics = {
                                "ROE (%)": [all_years[y].get("ROE", 0) for y in years],
                                "ROA (%)": [all_years[y].get("ROA", 0) for y in years],
                                "営業利益率 (%)": [all_years[y].get("営業利益率", 0) for y in years],
                                "自己資本比率 (%)": [all_years[y].get("自己資本比率", 0) for y in years],
                            }

                            fig_trend = go_ts.Figure()
                            colors = ["#2E75B6", "#E74C3C", "#2ECC71", "#F39C12"]
                            for i, (name, vals) in enumerate(trend_metrics.items()):
                                fig_trend.add_trace(go_ts.Scatter(
                                    x=years, y=vals, mode="lines+markers",
                                    name=name, line=dict(color=colors[i], width=2),
                                    marker=dict(size=8),
                                ))
                            fig_trend.update_layout(
                                height=400,
                                xaxis_title="年度",
                                yaxis_title="%",
                                legend=dict(orientation="h", y=-0.2),
                            )
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
                            import plotly.graph_objects as go_chart
                            fig_candle = go_chart.Figure(data=[go_chart.Candlestick(
                                x=hist.index,
                                open=hist["Open"],
                                high=hist["High"],
                                low=hist["Low"],
                                close=hist["Close"],
                                increasing_line_color="#2E75B6",
                                decreasing_line_color="#E74C3C",
                            )])
                            fig_candle.update_layout(
                                height=400,
                                xaxis_rangeslider_visible=False,
                                xaxis_title="日付",
                                yaxis_title="株価（円）",
                            )
                            st.plotly_chart(fig_candle, use_container_width=True)
                        else:
                            st.info("ℹ️ 株価チャートのデータを取得できませんでした")
                    except Exception as e:
                        st.info("ℹ️ 株価チャートは一時的に利用できません（Rate Limit）")

                    # ── 指標一覧（カテゴリ別・単位付き） ──
                    st.divider()
                    st.subheader("📋 財務指標一覧")

                    for category in ["収益性", "安全性", "成長性", "割安度"]:
                        cat_indicators = {
                            k: v for k, v in indicators.items()
                            if k in INDICATOR_FORMAT and INDICATOR_FORMAT[k][2] == category
                        }
                        if cat_indicators:
                            st.markdown(f"**{category}**")
                            cols = st.columns(len(cat_indicators))
                            for i, (name, val) in enumerate(cat_indicators.items()):
                                label, unit, _ = INDICATOR_FORMAT[name]
                                if unit == "円":
                                    cols[i].metric(label, f"{val:,.0f}{unit}")
                                else:
                                    cols[i].metric(label, f"{val:.2f}{unit}")

            else:
                st.info(f"ℹ️ {company_name} の有報データは準備中です。株価情報のみ表示しています。")

# ── フッター ──
st.divider()
st.caption("⚠️ 本ツールは投資助言ではありません。投資判断はご自身の責任で行ってください。データの正確性は保証されません。")
