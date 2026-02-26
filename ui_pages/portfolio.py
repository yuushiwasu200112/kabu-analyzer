if page == "ポートフォリオ":
    st.title("💼 ポートフォリオ分析")
    st.caption("保有銘柄のバランスとリスク分散をチェック")

    if "portfolio" not in st.session_state:
        try:
            from data.database import get_portfolio
            pf_rows = get_portfolio(st.session_state.get("username", "guest"))
            st.session_state.portfolio = [{"code": p["stock_code"], "name": p["company_name"], "shares": p.get("amount", 0)} for p in pf_rows]
        except:
            st.session_state.portfolio = []

    # 銘柄追加
    pf_col1, pf_col2, pf_col3 = st.columns([2, 2, 1])
    with pf_col1:
        pf_code = st.text_input("証券コード", max_chars=4, key="pf_code", placeholder="例: 7203")
    with pf_col2:
        pf_amount = st.number_input("投資金額（万円）", min_value=1, value=100, step=10, key="pf_amount")
    with pf_col3:
        st.write("")
        st.write("")
        if st.button("➕ 追加", key="pf_add", type="primary"):
            if pf_code and len(pf_code) == 4 and pf_code in CODE_MAP:
                existing = [p for p in st.session_state.portfolio if p["code"] == pf_code]
                if existing:
                    existing[0]["amount"] += pf_amount
                    st.success(f"✅ {CODE_MAP[pf_code]['name']} の投資額を更新")
                else:
                    st.session_state.portfolio.append({"code": pf_code, "name": CODE_MAP[pf_code]["name"], "amount": pf_amount})
                    st.success(f"✅ {CODE_MAP[pf_code]['name']} を追加")
            elif pf_code:
                st.error("❌ 未対応の証券コードです")

    if st.session_state.portfolio:
        st.divider()
        total_amount = sum(p["amount"] for p in st.session_state.portfolio)
        st.markdown(f"**総投資額: {total_amount:,}万円 ｜ {len(st.session_state.portfolio)}銘柄**")

        # 保有銘柄一覧
        st.subheader("📌 保有銘柄")
        for i, p in enumerate(st.session_state.portfolio):
            pc1, pc2, pc3, pc4 = st.columns([2, 2, 2, 1])
            with pc1:
                st.markdown(f"**{p['code']}** {p['name'][:10]}")
            with pc2:
                st.markdown(f"{p['amount']:,}万円")
            with pc3:
                ratio = p['amount'] / total_amount * 100
                st.markdown(f"構成比: {ratio:.1f}%")
            with pc4:
                if st.button("🗑️", key=f"pf_del_{i}"):
                    st.session_state.portfolio.pop(i)
                    st.rerun()

        # 分析実行
        if st.button("📊 ポートフォリオを分析", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")

            results = []
            progress = st.progress(0, text="分析中...")
            for idx, p in enumerate(st.session_state.portfolio):
                progress.progress((idx + 1) / len(st.session_state.portfolio), text=f"{p['name']} を分析中...")
                try:
                    r = analyze_company(p["code"], API_KEY)
                    if r:
                        results.append({
                            "code": p["code"], "name": p["name"], "amount": p["amount"],
                            "ratio": p["amount"] / total_amount * 100,
                            "total": r["score"]["total_score"],
                            "profitability": r["score"]["category_scores"].get("収益性", 0),
                            "safety": r["score"]["category_scores"].get("安全性", 0),
                            "growth": r["score"]["category_scores"].get("成長性", 0),
                            "value": r["score"]["category_scores"].get("割安度", 0),
                            "roe": r["indicators"].get("ROE", 0),
                            "dividend": r["indicators"].get("配当利回り", 0),
                        })
                except:
                    continue
            progress.empty()

            if results:
                st.divider()

                # ポートフォリオ総合スコア（加重平均）
                weighted_score = sum(r["total"] * r["ratio"] / 100 for r in results)
                weighted_prof = sum(r["profitability"] * r["ratio"] / 100 for r in results)
                weighted_safe = sum(r["safety"] * r["ratio"] / 100 for r in results)
                weighted_grow = sum(r["growth"] * r["ratio"] / 100 for r in results)
                weighted_val = sum(r["value"] * r["ratio"] / 100 for r in results)

                sc = "🟢" if weighted_score >= 75 else "🟡" if weighted_score >= 50 else "🔴"
                st.subheader(f"{sc} ポートフォリオ総合スコア: {weighted_score:.0f}点")

                pf_score_cols = st.columns(4)
                pf_score_cols[0].metric("収益性", f"{weighted_prof:.0f}点")
                pf_score_cols[1].metric("安全性", f"{weighted_safe:.0f}点")
                pf_score_cols[2].metric("成長性", f"{weighted_grow:.0f}点")
                pf_score_cols[3].metric("割安度", f"{weighted_val:.0f}点")

                # 構成比 円グラフ
                st.divider()
                pie_col, radar_col = st.columns(2)

                with pie_col:
                    st.subheader("🥧 構成比")
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=[r["name"][:8] for r in results],
                        values=[r["amount"] for r in results],
                        hole=0.4,
                        marker=dict(colors=["#2E75B6", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB"]),
                    )])
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with radar_col:
                    st.subheader("📊 ポートフォリオバランス")
                    fig_pf_radar = go.Figure()
                    fig_pf_radar.add_trace(go.Scatterpolar(
                        r=[weighted_prof, weighted_safe, weighted_grow, weighted_val, weighted_prof],
                        theta=["収益性", "安全性", "成長性", "割安度", "収益性"],
                        fill="toself", name="ポートフォリオ", line_color="#2E75B6",
                    ))
                    fig_pf_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
                    st.plotly_chart(fig_pf_radar, use_container_width=True)

                # リスク分散チェック
                st.divider()
                st.subheader("⚠️ リスク分散チェック")
                max_ratio = max(r["ratio"] for r in results)
                if max_ratio > 50:
                    st.error(f"🔴 **集中リスク**: 1銘柄に{max_ratio:.0f}%集中しています。30%以下に分散を推奨します。")
                elif max_ratio > 30:
                    st.warning(f"🟡 **やや集中**: 最大構成比が{max_ratio:.0f}%です。もう少し分散すると安心です。")
                else:
                    st.success(f"🟢 **分散良好**: 最大構成比は{max_ratio:.0f}%で適切に分散されています。")

                if len(results) < 3:
                    st.warning("🟡 **銘柄数不足**: 3銘柄以上に分散することをお勧めします。")
                elif len(results) < 5:
                    st.info("📌 5銘柄以上に分散するとさらにリスク低減効果が高まります。")
                else:
                    st.success(f"🟢 **銘柄数適切**: {len(results)}銘柄に分散されています。")

                avg_safety = weighted_safe
                if avg_safety < 50:
                    st.warning(f"🟡 **安全性に注意**: ポートフォリオ全体の安全性スコアが{avg_safety:.0f}点です。")

                # 銘柄別スコアテーブル
                st.divider()
                st.subheader("📋 銘柄別スコア")
                df = pd.DataFrame(results)
                df = df[["code", "name", "amount", "ratio", "total", "profitability", "safety", "growth", "value", "roe", "dividend"]]
                df.columns = ["コード", "企業名", "金額(万)", "構成比%", "総合", "収益性", "安全性", "成長性", "割安度", "ROE", "配当利回り"]
                df["構成比%"] = df["構成比%"].round(1)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # エクスポート
                pf_exp1, pf_exp2 = st.columns(2)
                with pf_exp1:
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 CSVダウンロード", csv, "portfolio.csv", "text/csv", key="pf_csv")
                with pf_exp2:
                    buf = io.BytesIO()
                    df.to_excel(buf, index=False, engine='openpyxl')
                    st.download_button("📥 Excelダウンロード", buf.getvalue(), "portfolio.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="pf_xlsx")

        # クリアボタン
        if st.button("🗑️ ポートフォリオをクリア", key="pf_clear"):
            st.session_state.portfolio = []
            st.rerun()
    else:
        st.info("📌 証券コードと投資金額を入力してポートフォリオを構築してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# 配当カレンダーページ
# ========================================
