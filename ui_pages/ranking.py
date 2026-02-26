if page == "ランキング":
    st.title("🏆 銘柄ランキング")

    from data.database import get_all_scores, get_scores_count
    db_count = get_scores_count()

    if db_count > 0:
        st.caption(f"📊 {db_count}銘柄のスコアデータ（バッチ分析済み）")

        rank_col1, rank_col2 = st.columns(2)
        with rank_col1:
            rank_count = st.selectbox("表示件数", ["上位30銘柄", "上位100銘柄", "上位500銘柄", f"全{db_count}銘柄"], index=0)
        with rank_col2:
            sort_by = st.selectbox("並び替え基準", ["総合スコア", "収益性", "安全性", "成長性", "割安度"], index=0)

        count_map = {"上位30銘柄": 30, "上位100銘柄": 100, "上位500銘柄": 500}
        max_count = count_map.get(rank_count, db_count)

        all_scores = get_all_scores(min_score=0, limit=max_count)
        rankings = []
        for s in all_scores:
            rankings.append({
                "code": s["stock_code"], "name": s["company_name"],
                "total": s["total_score"], "profitability": s["profitability"],
                "safety": s["safety"], "growth": s["growth"], "value": s["value"],
                "roe": s.get("roe", 0), "per": s.get("per", 0), "dividend": s.get("dividend_yield", 0),
            })

        sort_key_map = {"総合スコア": "total", "収益性": "profitability", "安全性": "safety", "成長性": "growth", "割安度": "value"}
        sort_k = sort_key_map.get(sort_by, "total")
        rankings.sort(key=lambda x: x[sort_k], reverse=True)

        if rankings:
            import pandas as pd
            import plotly.graph_objects as go

            st.subheader("🥇 総合スコア TOP10")
            for i, r in enumerate(rankings[:10]):
                score = r["total"]
                color = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}位"
                st.markdown(f"{medal} **{r['name']}**（{r['code']}）: {color} **{score}点** ｜ 収益性{r['profitability']} / 安全性{r['safety']} / 成長性{r['growth']} / 割安度{r['value']}")

            st.divider()
            st.subheader("📊 全銘柄スコア一覧")
            df = pd.DataFrame(rankings)
            df.columns = ["証券コード", "企業名", "総合スコア", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"]
            df["順位"] = range(1, len(df) + 1)
            df = df[["順位", "証券コード", "企業名", "総合スコア", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"]]
            st.dataframe(df, use_container_width=True, hide_index=True)

            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 CSVダウンロード", csv, "ranking.csv", "text/csv", key="rank_csv")
            with exp_col2:
                buf = io.BytesIO()
                df.to_excel(buf, index=False, engine="openpyxl")
                st.download_button("📥 Excelダウンロード", buf.getvalue(), "ranking.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="rank_xlsx")

            st.divider()
            cat_cols = st.columns(4)
            for i, (cat_name, cat_key) in enumerate([("収益性","profitability"),("安全性","safety"),("成長性","growth"),("割安度","value")]):
                with cat_cols[i]:
                    st.markdown(f"**{cat_name} TOP5**")
                    sorted_cat = sorted(rankings, key=lambda x: x[cat_key], reverse=True)
                    for j, r in enumerate(sorted_cat[:5]):
                        st.caption(f"{j+1}. {r['name'][:10]} ({r[cat_key]}点)")

            st.divider()
            st.subheader("📈 スコア分布")
            fig_bar = go.Figure(data=[go.Bar(
                x=[r["name"][:6] for r in rankings[:20]],
                y=[r["total"] for r in rankings[:20]],
                marker_color=["#27AE60" if r["total"]>=75 else "#F39C12" if r["total"]>=50 else "#E74C3C" for r in rankings[:20]],
            )])
            fig_bar.update_layout(height=400, yaxis_range=[0, 100])
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("📌 バッチ分析が未実行です。管理者にお問い合わせください。")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()
# ウォッチリストページ
# ========================================
