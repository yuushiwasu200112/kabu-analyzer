if page == "スクリーニング":
    st.title("🔎 スクリーニング")

    from data.database import get_all_scores, get_scores_count
    db_count = get_scores_count()

    if db_count > 0:
        st.caption(f"📊 {db_count}銘柄からフィルタリング")

        # フィルター条件
        st.subheader("📋 条件設定")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            min_score = st.slider("総合スコア（最低）", 0, 100, 0, key="scr_score")
        with f_col2:
            min_roe = st.slider("ROE（最低%）", 0.0, 50.0, 0.0, step=1.0, key="scr_roe")
        with f_col3:
            min_div = st.slider("配当利回り（最低%）", 0.0, 10.0, 0.0, step=0.5, key="scr_div")
        with f_col4:
            max_per = st.slider("PER（最大）", 0.0, 100.0, 100.0, step=5.0, key="scr_per")

        f_col5, f_col6, f_col7, f_col8 = st.columns(4)
        with f_col5:
            min_prof = st.slider("収益性（最低）", 0, 100, 0, key="scr_prof")
        with f_col6:
            min_safe = st.slider("安全性（最低）", 0, 100, 0, key="scr_safe")
        with f_col7:
            min_grow = st.slider("成長性（最低）", 0, 100, 0, key="scr_grow")
        with f_col8:
            min_val = st.slider("割安度（最低）", 0, 100, 0, key="scr_val")

        # DBから全スコア取得してフィルタリング
        all_scores = get_all_scores(min_score=0, limit=db_count)
        filtered = []
        for s in all_scores:
            if s["total_score"] < min_score: continue
            if s.get("roe", 0) < min_roe: continue
            if s.get("dividend_yield", 0) < min_div: continue
            if max_per < 100 and (s.get("per", 0) == 0 or s.get("per", 0) > max_per): continue
            if s["profitability"] < min_prof: continue
            if s["safety"] < min_safe: continue
            if s["growth"] < min_grow: continue
            if s["value"] < min_val: continue
            filtered.append(s)

        st.markdown(f"**該当: {len(filtered)}銘柄 / {db_count}銘柄**")

        if filtered:
            import pandas as pd
            import plotly.graph_objects as go

            rows = []
            for s in filtered:
                rows.append({
                    "証券コード": s["stock_code"], "企業名": s["company_name"],
                    "総合": s["total_score"], "収益性": s["profitability"],
                    "安全性": s["safety"], "成長性": s["growth"], "割安度": s["value"],
                    "ROE": s.get("roe", 0), "PER": s.get("per", 0), "配当利回り": s.get("dividend_yield", 0),
                })
            df = pd.DataFrame(rows)
            df = df.sort_values("総合", ascending=False).reset_index(drop=True)
            df.index = df.index + 1
            df.index.name = "順位"
            st.dataframe(df, use_container_width=True)

            # エクスポート
            exp1, exp2 = st.columns(2)
            with exp1:
                csv = df.to_csv(index=True).encode("utf-8-sig")
                st.download_button("📥 CSVダウンロード", csv, "screening.csv", "text/csv", key="scr_csv")
            with exp2:
                buf = io.BytesIO()
                df.to_excel(buf, index=True, engine="openpyxl")
                st.download_button("📥 Excelダウンロード", buf.getvalue(), "screening.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="scr_xlsx")

            # 散布図
            st.divider()
            st.subheader("📈 散布図")
            sc_col1, sc_col2 = st.columns(2)
            with sc_col1:
                x_axis = st.selectbox("X軸", ["ROE", "PER", "配当利回り", "総合", "収益性", "安全性", "成長性", "割安度"], index=0, key="scr_x")
            with sc_col2:
                y_axis = st.selectbox("Y軸", ["総合", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"], index=0, key="scr_y")

            fig = go.Figure(data=[go.Scatter(
                x=df[x_axis], y=df[y_axis], mode="markers+text",
                text=df["企業名"].str[:6], textposition="top center",
                marker=dict(size=10, color=df["総合"], colorscale="Viridis", showscale=True, colorbar=dict(title="総合")),
            )])
            fig.update_layout(height=500, xaxis_title=x_axis, yaxis_title=y_axis)
            st.plotly_chart(fig, use_container_width=True)
        elif min_score > 0 or min_roe > 0 or min_div > 0:
            st.warning("条件に該当する銘柄がありません。条件を緩めてください。")
    else:
        st.warning("📌 バッチ分析が未実行です。管理者にお問い合わせください。")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()
# 買い増し最適化ページ
# ========================================
