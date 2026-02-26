if page == "セクター分析":
    st.title("🏭 セクター分析")
    st.caption("業種別の投資魅力度を比較")

    SECTORS = {
        "自動車": ["7203","7267","7269","7270","7201","7202","7211","6902"],
        "電機・精密": ["6758","6501","6503","6752","6971","6981","6762","6594","6645","6504","7751","7741","7733","7735","7752"],
        "半導体": ["8035","6920","6857","6723"],
        "商社": ["8058","8001","8031","8053","8002"],
        "銀行・金融": ["8306","8316","8411","8591","8601","8604"],
        "保険": ["8766","8750","8630","8725"],
        "不動産": ["8801","8802"],
        "通信": ["9432","9433","9434"],
        "医薬品": ["4502","4519","4523","4568","4507","4578"],
        "食品・日用品": ["2801","2802","2502","2503","4452","2914","4911"],
        "化学・素材": ["4063","4901","5108","5401","5713","5802","3861"],
        "機械": ["6301","6273","6367","6954","7011"],
        "サービス・IT": ["6098","9983","3382","4661","3659","4689","7974"],
        "運輸": ["9020","9022","9101","9104","9201","9202","9001","9005","9009","9064"],
        "エネルギー": ["9501","9503","9531"],
    }

    # セクター選択
    selected_sectors = st.multiselect("分析するセクターを選択", list(SECTORS.keys()), default=list(SECTORS.keys())[:5])

    if selected_sectors and st.button("🔍 セクター分析を実行", type="primary"):
        import plotly.graph_objects as go
        import pandas as pd
        API_KEY = os.getenv("EDINET_API_KEY")

        sector_results = {}
        all_stocks = []
        total_stocks = sum(len(SECTORS[s]) for s in selected_sectors)
        progress = st.progress(0, text="分析中...")
        done = 0

        for sector in selected_sectors:
            sector_scores = []
            for code in SECTORS[sector]:
                done += 1
                if code not in CODE_MAP:
                    continue
                progress.progress(done / total_stocks, text=f"{sector} - {CODE_MAP[code]['name']} を分析中...")
                try:
                    r = analyze_company(code, API_KEY)
                    if r:
                        stock_data = {
                            "sector": sector, "code": code, "name": r["name"][:10],
                            "total": r["score"]["total_score"],
                            "profitability": r["score"]["category_scores"].get("収益性", 0),
                            "safety": r["score"]["category_scores"].get("安全性", 0),
                            "growth": r["score"]["category_scores"].get("成長性", 0),
                            "value": r["score"]["category_scores"].get("割安度", 0),
                        }
                        sector_scores.append(stock_data)
                        all_stocks.append(stock_data)
                except:
                    continue

            if sector_scores:
                avg_total = sum(s["total"] for s in sector_scores) / len(sector_scores)
                avg_prof = sum(s["profitability"] for s in sector_scores) / len(sector_scores)
                avg_safe = sum(s["safety"] for s in sector_scores) / len(sector_scores)
                avg_grow = sum(s["growth"] for s in sector_scores) / len(sector_scores)
                avg_val = sum(s["value"] for s in sector_scores) / len(sector_scores)
                sector_results[sector] = {
                    "avg_total": avg_total, "avg_prof": avg_prof, "avg_safe": avg_safe,
                    "avg_grow": avg_grow, "avg_val": avg_val, "count": len(sector_scores),
                    "stocks": sector_scores,
                }
        progress.empty()

        if sector_results:
            # セクター別総合スコアランキング
            st.divider()
            st.subheader("🏆 セクター別総合スコア")
            sorted_sectors = sorted(sector_results.items(), key=lambda x: x[1]["avg_total"], reverse=True)

            fig_sector = go.Figure(data=[go.Bar(
                x=[s[0] for s in sorted_sectors],
                y=[s[1]["avg_total"] for s in sorted_sectors],
                marker_color=["#27AE60" if s[1]["avg_total"] >= 75 else "#F39C12" if s[1]["avg_total"] >= 60 else "#E74C3C" for s in sorted_sectors],
                text=[f"{s[1]['avg_total']:.0f}点" for s in sorted_sectors],
                textposition="outside",
            )])
            fig_sector.update_layout(height=400, yaxis_range=[0, 100], xaxis_title="セクター", yaxis_title="平均スコア")
            st.plotly_chart(fig_sector, use_container_width=True)

            # セクター別レーダーチャート
            st.subheader("📊 セクター別カテゴリ比較")
            fig_radar = go.Figure()
            colors = ["#2E75B6","#E74C3C","#2ECC71","#F39C12","#9B59B6","#1ABC9C","#E67E22","#3498DB"]
            for i, (sector, data) in enumerate(sorted_sectors):
                cats = ["収益性","安全性","成長性","割安度"]
                vals = [data["avg_prof"], data["avg_safe"], data["avg_grow"], data["avg_val"]]
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=cats + [cats[0]],
                    fill="toself", name=f"{sector}({data['avg_total']:.0f}点)",
                    line_color=colors[i % len(colors)],
                ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_radar, use_container_width=True)

            # セクター詳細テーブル
            st.divider()
            st.subheader("📋 セクター別詳細")
            sector_table = []
            for sector, data in sorted_sectors:
                sector_table.append({
                    "セクター": sector, "銘柄数": data["count"],
                    "総合": f"{data['avg_total']:.0f}", "収益性": f"{data['avg_prof']:.0f}",
                    "安全性": f"{data['avg_safe']:.0f}", "成長性": f"{data['avg_grow']:.0f}",
                    "割安度": f"{data['avg_val']:.0f}",
                })
            st.dataframe(pd.DataFrame(sector_table), use_container_width=True, hide_index=True)

            # セクター内銘柄ランキング
            st.divider()
            st.subheader("🔍 セクター内銘柄ランキング")
            selected_detail = st.selectbox("セクターを選択", [s[0] for s in sorted_sectors])
            if selected_detail and selected_detail in sector_results:
                stocks = sorted(sector_results[selected_detail]["stocks"], key=lambda x: x["total"], reverse=True)
                for i, s in enumerate(stocks):
                    color = "🟢" if s["total"] >= 75 else "🟡" if s["total"] >= 50 else "🔴"
                    medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}位"
                    st.markdown(f"{medal} **{s['name']}**（{s['code']}）: {color} **{s['total']}点** ｜ 収益{s['profitability']} / 安全{s['safety']} / 成長{s['growth']} / 割安{s['value']}")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# バックテストページ
# ========================================
