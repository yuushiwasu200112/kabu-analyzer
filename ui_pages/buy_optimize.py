if page == "買い増し最適化":
    st.title("💰 買い増し最適化")
    st.caption("予算に応じた最適な買い増し銘柄をシミュレーション")

    # 保有株入力
    st.subheader("📋 保有銘柄を入力")
    if "buy_holdings" not in st.session_state:
        st.session_state.buy_holdings = []

    bh_col1, bh_col2, bh_col3, bh_col4 = st.columns([2, 2, 2, 1])
    with bh_col1:
        bh_code = st.text_input("証券コード", max_chars=4, key="bh_code", placeholder="7203")
    with bh_col2:
        bh_shares = st.number_input("保有株数", min_value=0, value=100, step=100, key="bh_shares")
    with bh_col3:
        bh_cost = st.number_input("取得単価（円）", min_value=0, value=0, step=100, key="bh_cost")
    with bh_col4:
        st.write("")
        st.write("")
        if st.button("➕ 追加", key="bh_add"):
            if bh_code and len(bh_code) == 4 and bh_code in CODE_MAP:
                st.session_state.buy_holdings.append({
                    "code": bh_code,
                    "name": CODE_MAP[bh_code]["name"],
                    "shares": bh_shares,
                    "cost": bh_cost,
                })
                st.rerun()
            elif bh_code:
                st.error("❌ 未対応の証券コードです。4桁の証券コードを入力してください。")

    # ウォッチリストから追加
    if st.session_state.get("watchlist"):
        if st.button("⭐ ウォッチリストから追加"):
            for code in st.session_state.watchlist:
                if code in CODE_MAP and code not in [h["code"] for h in st.session_state.buy_holdings]:
                    st.session_state.buy_holdings.append({
                        "code": code, "name": CODE_MAP[code]["name"],
                        "shares": 100, "cost": 0,
                    })
            st.rerun()

    # 保有銘柄一覧
    if st.session_state.buy_holdings:
        st.divider()
        for i, h in enumerate(st.session_state.buy_holdings):
            hc1, hc2, hc3, hc4 = st.columns([3, 2, 2, 1])
            hc1.markdown(f"**{h['code']}** {h['name'][:10]}")
            hc2.markdown(f"{h['shares']}株")
            hc3.markdown(f"@¥{h['cost']:,}" if h['cost'] > 0 else "取得単価未入力")
            if hc4.button("🗑️", key=f"bh_del_{i}"):
                st.session_state.buy_holdings.pop(i)
                st.rerun()

        # 予算入力
        st.divider()
        st.subheader("💵 買い増し予算")
        budget = st.number_input("投資予算（万円）", min_value=10, value=100, step=10, key="buy_budget")
        budget_yen = budget * 10000

        if st.button("🚀 最適化を実行", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")

            # 各銘柄を分析
            progress = st.progress(0, text="銘柄を分析中...")
            holdings_data = []
            for i, h in enumerate(st.session_state.buy_holdings):
                progress.progress((i+1)/len(st.session_state.buy_holdings), text=f"{h['name']} を分析中...")
                try:
                    r = analyze_company(h["code"], API_KEY)
                    if r:
                        price = r["stock_info"]["current_price"] if r["stock_info"] else 0
                        holdings_data.append({
                            "code": h["code"], "name": h["name"],
                            "shares": h["shares"], "cost": h["cost"],
                            "price": price,
                            "score": r["score"]["total_score"],
                            "cats": r["score"]["category_scores"],
                            "roe": r["indicators"].get("ROE", 0),
                            "per": r["indicators"].get("PER", 0),
                            "dividend": r["indicators"].get("配当利回り", 0),
                        })
                except:
                    continue
            progress.empty()

            if not holdings_data:
                st.error("❌ 分析データの取得に失敗しました")
            else:
                # 貪欲法で買い増し最適化（100株単位）
                st.divider()
                st.subheader("🎯 最適化結果")

                # スコア÷株価で効率スコアを計算
                candidates = []
                for hd in holdings_data:
                    if hd["price"] > 0:
                        cost_per_100 = hd["price"] * 100
                        efficiency = hd["score"] / (hd["price"] / 1000)
                        candidates.append({**hd, "cost_per_100": cost_per_100, "efficiency": efficiency, "buy_shares": 0})

                # 効率スコア順にソートして貪欲法で割当
                candidates.sort(key=lambda x: x["efficiency"], reverse=True)
                remaining = budget_yen
                for c in candidates:
                    while remaining >= c["cost_per_100"]:
                        c["buy_shares"] += 100
                        remaining -= c["cost_per_100"]

                bought = [c for c in candidates if c["buy_shares"] > 0]
                not_bought = [c for c in candidates if c["buy_shares"] == 0]

                if bought:
                    # 買い増し提案テーブル
                    st.markdown("### 📊 買い増し提案")
                    for b in bought:
                        total_cost = b["price"] * b["buy_shares"]
                        pct = total_cost / budget_yen * 100
                        st.markdown(f"""
                        <div style='background:#1B2332;border-radius:10px;padding:15px;margin:10px 0;border-left:4px solid #2E75B6'>
                            <span style='font-size:1.1rem;font-weight:bold'>{b['name']}（{b['code']}）</span><br>
                            <span style='color:#2ECC71;font-size:1.2rem'>+{b['buy_shares']}株</span>
                            <span style='color:#8899AA;margin-left:15px'>@¥{b['price']:,.0f} = ¥{total_cost:,.0f}（予算の{pct:.0f}%）</span><br>
                            <span style='color:#5BA3E6'>スコア: {b['score']}点 | ROE: {b['roe']:.1f}% | 配当: {b['dividend']:.2f}%</span>
                        </div>""", unsafe_allow_html=True)

                    used = budget_yen - remaining
                    st.info(f"💰 使用額: ¥{used:,.0f} / ¥{budget_yen:,.0f}（残り: ¥{remaining:,.0f}）")

                    # シミュレーション（買い増し前 vs 後）
                    st.divider()
                    st.subheader("📈 ポートフォリオ変化シミュレーション")

                    # 買い増し前の加重平均スコア
                    before_total_val = sum(c["price"] * c["shares"] for c in candidates if c["price"] > 0)
                    before_avg = sum(c["score"] * c["price"] * c["shares"] for c in candidates if c["price"] > 0)
                    before_avg = before_avg / before_total_val if before_total_val > 0 else 0

                    # 買い増し後
                    after_total_val = sum(c["price"] * (c["shares"] + c["buy_shares"]) for c in candidates if c["price"] > 0)
                    after_avg = sum(c["score"] * c["price"] * (c["shares"] + c["buy_shares"]) for c in candidates if c["price"] > 0)
                    after_avg = after_avg / after_total_val if after_total_val > 0 else 0

                    sim_col1, sim_col2, sim_col3 = st.columns(3)
                    sim_col1.metric("買い増し前スコア", f"{before_avg:.1f}点")
                    sim_col2.metric("買い増し後スコア", f"{after_avg:.1f}点", delta=f"{after_avg - before_avg:+.1f}点")
                    sim_col3.metric("総評価額", f"¥{after_total_val:,.0f}")

                    # 構成比の変化（パイチャート）
                    fig_pie = go.Figure()
                    fig_pie.add_trace(go.Pie(
                        labels=[c["name"][:8] for c in candidates],
                        values=[c["price"] * (c["shares"] + c["buy_shares"]) for c in candidates],
                        hole=0.4, textinfo="label+percent",
                    ))
                    fig_pie.update_layout(height=400, title="買い増し後の構成比")
                    st.plotly_chart(fig_pie, use_container_width=True)

                    # カテゴリ別の変化レーダー
                    cat_names = ["収益性", "安全性", "成長性", "割安度"]
                    before_cats = [0, 0, 0, 0]
                    after_cats = [0, 0, 0, 0]
                    for c in candidates:
                        w_before = c["price"] * c["shares"]
                        w_after = c["price"] * (c["shares"] + c["buy_shares"])
                        for j, cat in enumerate(cat_names):
                            before_cats[j] += c["cats"].get(cat, 0) * w_before
                            after_cats[j] += c["cats"].get(cat, 0) * w_after
                    if before_total_val > 0:
                        before_cats = [v / before_total_val for v in before_cats]
                    if after_total_val > 0:
                        after_cats = [v / after_total_val for v in after_cats]

                    fig_radar = go.Figure()
                    fig_radar.add_trace(go.Scatterpolar(r=before_cats + [before_cats[0]], theta=cat_names + [cat_names[0]], fill="toself", name="買い増し前", line_color="#E74C3C"))
                    fig_radar.add_trace(go.Scatterpolar(r=after_cats + [after_cats[0]], theta=cat_names + [cat_names[0]], fill="toself", name="買い増し後", line_color="#2E75B6"))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.warning("予算内で購入できる銘柄がありません。予算を増やしてみてください。")

    else:
        st.info("📌 保有銘柄を追加してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# 買い増し最適化ページ
# ========================================
if page == "買い増し最適化":
    st.title("💰 買い増し最適化")
    st.caption("予算に応じた最適な買い増し銘柄をシミュレーション")

    # 保有株入力
    st.subheader("📋 保有銘柄を入力")
    if "buy_holdings" not in st.session_state:
        st.session_state.buy_holdings = []

    bh_col1, bh_col2, bh_col3, bh_col4 = st.columns([2, 2, 2, 1])
    with bh_col1:
        bh_code = st.text_input("証券コード", max_chars=4, key="bh_code", placeholder="7203")
    with bh_col2:
        bh_shares = st.number_input("保有株数", min_value=0, value=100, step=100, key="bh_shares")
    with bh_col3:
        bh_cost = st.number_input("取得単価（円）", min_value=0, value=0, step=100, key="bh_cost")
    with bh_col4:
        st.write("")
        st.write("")
        if st.button("➕ 追加", key="bh_add"):
            if bh_code and len(bh_code) == 4 and bh_code in CODE_MAP:
                st.session_state.buy_holdings.append({
                    "code": bh_code,
                    "name": CODE_MAP[bh_code]["name"],
                    "shares": bh_shares,
                    "cost": bh_cost,
                })
                st.rerun()
            elif bh_code:
                st.error("❌ 未対応の証券コード")

    # ウォッチリストから追加
    if st.session_state.get("watchlist"):
        if st.button("⭐ ウォッチリストから追加"):
            for code in st.session_state.watchlist:
                if code in CODE_MAP and code not in [h["code"] for h in st.session_state.buy_holdings]:
                    st.session_state.buy_holdings.append({
                        "code": code, "name": CODE_MAP[code]["name"],
                        "shares": 100, "cost": 0,
                    })
            st.rerun()

    # 保有銘柄一覧
    if st.session_state.buy_holdings:
        st.divider()
        for i, h in enumerate(st.session_state.buy_holdings):
            hc1, hc2, hc3, hc4 = st.columns([3, 2, 2, 1])
            hc1.markdown(f"**{h['code']}** {h['name'][:10]}")
            hc2.markdown(f"{h['shares']}株")
            hc3.markdown(f"@¥{h['cost']:,}" if h['cost'] > 0 else "取得単価未入力")
            if hc4.button("🗑️", key=f"bh_del_{i}"):
                st.session_state.buy_holdings.pop(i)
                st.rerun()

        # 予算入力
        st.divider()
        st.subheader("💵 買い増し予算")
        budget = st.number_input("投資予算（万円）", min_value=10, value=100, step=10, key="buy_budget")
        budget_yen = budget * 10000

        if st.button("🚀 最適化を実行", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")

            # 各銘柄を分析
            progress = st.progress(0, text="銘柄を分析中...")
            holdings_data = []
            for i, h in enumerate(st.session_state.buy_holdings):
                progress.progress((i+1)/len(st.session_state.buy_holdings), text=f"{h['name']} を分析中...")
                try:
                    r = analyze_company(h["code"], API_KEY)
                    if r:
                        price = r["stock_info"]["current_price"] if r["stock_info"] else 0
                        holdings_data.append({
                            "code": h["code"], "name": h["name"],
                            "shares": h["shares"], "cost": h["cost"],
                            "price": price,
                            "score": r["score"]["total_score"],
                            "cats": r["score"]["category_scores"],
                            "roe": r["indicators"].get("ROE", 0),
                            "per": r["indicators"].get("PER", 0),
                            "dividend": r["indicators"].get("配当利回り", 0),
                        })
                except:
                    continue
            progress.empty()

            if not holdings_data:
                st.error("❌ 分析データの取得に失敗しました")
            else:
                # 貪欲法で買い増し最適化（100株単位）
                st.divider()
                st.subheader("🎯 最適化結果")

                # スコア÷株価で効率スコアを計算
                candidates = []
                for hd in holdings_data:
                    if hd["price"] > 0:
                        cost_per_100 = hd["price"] * 100
                        efficiency = hd["score"] / (hd["price"] / 1000)
                        candidates.append({**hd, "cost_per_100": cost_per_100, "efficiency": efficiency, "buy_shares": 0})

                # 効率スコア順にソートして貪欲法で割当
                candidates.sort(key=lambda x: x["efficiency"], reverse=True)
                remaining = budget_yen
                for c in candidates:
                    while remaining >= c["cost_per_100"]:
                        c["buy_shares"] += 100
                        remaining -= c["cost_per_100"]

                bought = [c for c in candidates if c["buy_shares"] > 0]
                not_bought = [c for c in candidates if c["buy_shares"] == 0]

                if bought:
                    # 買い増し提案テーブル
                    st.markdown("### 📊 買い増し提案")
                    for b in bought:
                        total_cost = b["price"] * b["buy_shares"]
                        pct = total_cost / budget_yen * 100
                        st.markdown(f"""
                        <div style='background:#1B2332;border-radius:10px;padding:15px;margin:10px 0;border-left:4px solid #2E75B6'>
                            <span style='font-size:1.1rem;font-weight:bold'>{b['name']}（{b['code']}）</span><br>
                            <span style='color:#2ECC71;font-size:1.2rem'>+{b['buy_shares']}株</span>
                            <span style='color:#8899AA;margin-left:15px'>@¥{b['price']:,.0f} = ¥{total_cost:,.0f}（予算の{pct:.0f}%）</span><br>
                            <span style='color:#5BA3E6'>スコア: {b['score']}点 | ROE: {b['roe']:.1f}% | 配当: {b['dividend']:.2f}%</span>
                        </div>""", unsafe_allow_html=True)

                    used = budget_yen - remaining
                    st.info(f"💰 使用額: ¥{used:,.0f} / ¥{budget_yen:,.0f}（残り: ¥{remaining:,.0f}）")

                    # シミュレーション（買い増し前 vs 後）
                    st.divider()
                    st.subheader("📈 ポートフォリオ変化シミュレーション")

                    # 買い増し前の加重平均スコア
                    before_total_val = sum(c["price"] * c["shares"] for c in candidates if c["price"] > 0)
                    before_avg = sum(c["score"] * c["price"] * c["shares"] for c in candidates if c["price"] > 0)
                    before_avg = before_avg / before_total_val if before_total_val > 0 else 0

                    # 買い増し後
                    after_total_val = sum(c["price"] * (c["shares"] + c["buy_shares"]) for c in candidates if c["price"] > 0)
                    after_avg = sum(c["score"] * c["price"] * (c["shares"] + c["buy_shares"]) for c in candidates if c["price"] > 0)
                    after_avg = after_avg / after_total_val if after_total_val > 0 else 0

                    sim_col1, sim_col2, sim_col3 = st.columns(3)
                    sim_col1.metric("買い増し前スコア", f"{before_avg:.1f}点")
                    sim_col2.metric("買い増し後スコア", f"{after_avg:.1f}点", delta=f"{after_avg - before_avg:+.1f}点")
                    sim_col3.metric("総評価額", f"¥{after_total_val:,.0f}")

                    # 構成比の変化（パイチャート）
                    fig_pie = go.Figure()
                    fig_pie.add_trace(go.Pie(
                        labels=[c["name"][:8] for c in candidates],
                        values=[c["price"] * (c["shares"] + c["buy_shares"]) for c in candidates],
                        hole=0.4, textinfo="label+percent",
                    ))
                    fig_pie.update_layout(height=400, title="買い増し後の構成比")
                    st.plotly_chart(fig_pie, use_container_width=True)

                    # カテゴリ別の変化レーダー
                    cat_names = ["収益性", "安全性", "成長性", "割安度"]
                    before_cats = [0, 0, 0, 0]
                    after_cats = [0, 0, 0, 0]
                    for c in candidates:
                        w_before = c["price"] * c["shares"]
                        w_after = c["price"] * (c["shares"] + c["buy_shares"])
                        for j, cat in enumerate(cat_names):
                            before_cats[j] += c["cats"].get(cat, 0) * w_before
                            after_cats[j] += c["cats"].get(cat, 0) * w_after
                    if before_total_val > 0:
                        before_cats = [v / before_total_val for v in before_cats]
                    if after_total_val > 0:
                        after_cats = [v / after_total_val for v in after_cats]

                    fig_radar = go.Figure()
                    fig_radar.add_trace(go.Scatterpolar(r=before_cats + [before_cats[0]], theta=cat_names + [cat_names[0]], fill="toself", name="買い増し前", line_color="#E74C3C"))
                    fig_radar.add_trace(go.Scatterpolar(r=after_cats + [after_cats[0]], theta=cat_names + [cat_names[0]], fill="toself", name="買い増し後", line_color="#2E75B6"))
                    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.warning("予算内で購入できる銘柄がありません。予算を増やしてみてください。")

    else:
        st.info("📌 保有銘柄を追加してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# 定期レポートページ
# ========================================
