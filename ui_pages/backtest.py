if page == "バックテスト":
    st.title("🔬 バックテスト")
    st.caption("過去のスコア推移と株価パフォーマンスを検証")

    bt_code = st.text_input("証券コードを入力", max_chars=4, key="bt_code", placeholder="例: 7203")

    if bt_code and len(bt_code) == 4 and bt_code.isdigit() and bt_code in CODE_MAP:
        company = CODE_MAP[bt_code]
        st.success(f"✅ {company['name']}（{bt_code}）")

        if st.button("🔍 バックテスト実行", type="primary"):
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import pandas as pd
            from parsers.xbrl_parser import download_and_parse
            from analysis.indicators import calc_indicators, calc_growth
            from analysis.scoring import calc_total_score
            from data_sources.cache_manager import get_cache, set_cache

            API_KEY = os.getenv("EDINET_API_KEY")
            edinet_code = company["edinet_code"]

            with st.spinner("過去の有報を検索中..."):
                docs = get_cache(f"docs_{edinet_code}", max_age_hours=168)
                if not docs:
                    docs = search_yuho(edinet_code, API_KEY)
                    if docs: set_cache(f"docs_{edinet_code}", docs)

            if not docs or len(docs) < 2:
                st.error("❌ バックテストには2年以上のデータが必要です")
            else:
                st.info(f"📊 {len(docs)}期分のデータを分析中...")

                # 各年度のデータを取得
                yearly_data = {}
                progress = st.progress(0, text="分析中...")
                for i, doc in enumerate(docs):
                    progress.progress((i+1)/len(docs), text=f"{doc['periodEnd'][:4]}年度を分析中...")
                    ck = f"xbrl_{doc['docID']}"
                    xbrl = get_cache(ck)
                    if not xbrl:
                        xbrl = download_and_parse(doc["docID"], API_KEY)
                        if xbrl: set_cache(ck, xbrl)
                    if xbrl:
                        yearly_data[doc["periodEnd"][:4]] = {"xbrl": xbrl, "doc": doc}
                progress.empty()

                if len(yearly_data) < 2:
                    st.error("❌ 十分なデータを取得できませんでした")
                else:
                    years = sorted(yearly_data.keys())
                    scores_by_year = {}
                    indicators_by_year = {}

                    for i, year in enumerate(years):
                        xbrl = yearly_data[year]["xbrl"]
                        ind = calc_indicators(xbrl, 0)

                        if i > 0:
                            prev_xbrl = yearly_data[years[i-1]]["xbrl"]
                            growth = calc_growth(xbrl, prev_xbrl)
                            ind.update(growth)

                        score = calc_total_score(ind, style, "中期")
                        scores_by_year[year] = score
                        indicators_by_year[year] = ind

                    # 株価データ取得
                    st.divider()
                    stock_prices = {}
                    try:
                        import yfinance as yf, time
                        time.sleep(0.5)
                        ticker = yf.Ticker(f"{bt_code}.T")
                        hist = ticker.history(period="5y")
                        if not hist.empty:
                            for year in years:
                                year_data = hist[hist.index.year == int(year)]
                                if not year_data.empty:
                                    stock_prices[year] = {
                                        "start": year_data.iloc[0]["Close"],
                                        "end": year_data.iloc[-1]["Close"],
                                        "high": year_data["High"].max(),
                                        "low": year_data["Low"].min(),
                                    }
                    except:
                        pass

                    # スコア推移チャート
                    st.subheader("📈 スコア推移")
                    fig_score = make_subplots(specs=[[{"secondary_y": True}]])

                    total_scores = [scores_by_year[y]["total_score"] for y in years]
                    fig_score.add_trace(go.Scatter(
                        x=years, y=total_scores, mode="lines+markers",
                        name="総合スコア", line=dict(color="#2E75B6", width=3),
                        marker=dict(size=10),
                    ), secondary_y=False)

                    if stock_prices:
                        prices = [stock_prices[y]["end"] for y in years if y in stock_prices]
                        price_years = [y for y in years if y in stock_prices]
                        fig_score.add_trace(go.Scatter(
                            x=price_years, y=prices, mode="lines+markers",
                            name="株価(年末)", line=dict(color="#F39C12", width=2, dash="dot"),
                            marker=dict(size=8),
                        ), secondary_y=True)

                    fig_score.update_layout(height=450, legend=dict(orientation="h", y=-0.15))
                    fig_score.update_yaxes(title_text="スコア", range=[0, 100], secondary_y=False)
                    fig_score.update_yaxes(title_text="株価（円）", secondary_y=True)
                    st.plotly_chart(fig_score, use_container_width=True)

                    # カテゴリ別スコア推移
                    st.subheader("📊 カテゴリ別スコア推移")
                    fig_cat = go.Figure()
                    colors = {"収益性": "#2E75B6", "安全性": "#2ECC71", "成長性": "#E74C3C", "割安度": "#F39C12"}
                    for cat in ["収益性", "安全性", "成長性", "割安度"]:
                        cat_scores = [scores_by_year[y]["category_scores"].get(cat, 0) for y in years]
                        fig_cat.add_trace(go.Scatter(
                            x=years, y=cat_scores, mode="lines+markers",
                            name=cat, line=dict(color=colors[cat], width=2),
                        ))
                    fig_cat.update_layout(height=400, yaxis_range=[0, 100], legend=dict(orientation="h", y=-0.15))
                    st.plotly_chart(fig_cat, use_container_width=True)

                    # 主要指標推移テーブル
                    st.subheader("📋 主要指標の推移")
                    metrics = ["ROE", "ROA", "営業利益率", "自己資本比率", "配当利回り"]
                    table_data = {"指標": metrics}
                    for year in years:
                        ind = indicators_by_year[year]
                        table_data[f"{year}年"] = [f"{ind.get(m, 0):.2f}" for m in metrics]
                    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

                    # スコア変動サマリー
                    st.divider()
                    st.subheader("📝 バックテストサマリー")
                    first_score = total_scores[0]
                    last_score = total_scores[-1]
                    score_change = last_score - first_score

                    sum_col1, sum_col2, sum_col3 = st.columns(3)
                    sum_col1.metric(f"{years[0]}年スコア", f"{first_score}点")
                    sum_col2.metric(f"{years[-1]}年スコア", f"{last_score}点", delta=f"{score_change:+.0f}点")

                    if stock_prices and years[0] in stock_prices and years[-1] in stock_prices:
                        p_start = stock_prices[years[0]]["start"]
                        p_end = stock_prices[years[-1]]["end"]
                        p_return = (p_end - p_start) / p_start * 100
                        sum_col3.metric("株価リターン", f"{p_return:+.1f}%")

                    # 判定
                    if score_change > 10:
                        st.success(f"📈 **改善傾向**: スコアが{years[0]}年から{score_change:+.0f}点上昇。ファンダメンタルズが改善しています。")
                    elif score_change < -10:
                        st.warning(f"📉 **悪化傾向**: スコアが{years[0]}年から{score_change:+.0f}点下落。注意が必要です。")
                    else:
                        st.info(f"➡️ **安定**: スコアは{years[0]}年から大きな変動なく推移しています。")

    elif bt_code and len(bt_code) == 4:
        st.error("❌ 未対応の証券コードです")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。過去の実績は将来の結果を保証しません。")
    st.stop()

# ========================================
# スクリーニングページ
# ========================================
