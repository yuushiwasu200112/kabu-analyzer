if page == "複数社比較":
    st.title("⚖️ 複数社比較")
    st.caption(f"最大3社まで並べて比較できます（対応: {len(CODE_MAP):,}社）")

    cols_input = st.columns(3)
    codes = []
    for i in range(3):
        with cols_input[i]:
            code = st.text_input(f"銘柄{i+1}", max_chars=4, key=f"cmp_{i}", placeholder="証券コード")
            if code and len(code) == 4 and code.isdigit() and code in CODE_MAP:
                codes.append(code)
                st.caption(f"✅ {CODE_MAP[code]['name']}")
            elif code and len(code) == 4:
                st.caption("❌ 未対応")

    if len(codes) >= 2:
        if st.button("🔍 比較分析を実行", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")
            results = {}
            for code in codes:
                with st.spinner(f"{CODE_MAP[code]['name']} を分析中..."):
                    r = analyze_company(code, API_KEY)
                    if r: results[code] = r

            if len(results) >= 2:
                st.divider()
                st.subheader("🏆 総合スコア比較")
                score_cols = st.columns(len(results))
                for i, (code, data) in enumerate(results.items()):
                    with score_cols[i]:
                        s = data["score"]["total_score"]
                        color = "🟢" if s >= 75 else "🟡" if s >= 50 else "🔴"
                        st.metric(data["name"], f"{color} {s}点")

                st.subheader("📊 カテゴリ別スコア比較")
                fig_radar = go.Figure()
                radar_colors = ["#2E75B6", "#E74C3C", "#2ECC71"]
                for i, (code, data) in enumerate(results.items()):
                    cats = list(data["score"]["category_scores"].keys())
                    vals = list(data["score"]["category_scores"].values())
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=cats + [cats[0]],
                        fill="toself", name=data["name"], line_color=radar_colors[i % 3]))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                        height=450, legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_radar, use_container_width=True)

                for cat in ["収益性", "安全性", "成長性", "割安度"]:
                    st.markdown(f"**{cat}**")
                    bar_cols = st.columns(len(results))
                    for i, (code, data) in enumerate(results.items()):
                        with bar_cols[i]:
                            val = data["score"]["category_scores"].get(cat, 0)
                            st.progress(val / 100, text=f"{data['name']}: {val}点")

                st.divider()
                st.subheader("📋 主要指標比較")
                metrics = ["ROE", "ROA", "営業利益率", "自己資本比率", "PER", "PBR",
                           "配当利回り", "売上高成長率", "営業利益成長率", "純利益成長率"]
                table = {}
                for code, data in results.items():
                    table[data["name"]] = {m: f"{data['indicators'].get(m, 0):.2f}" if data['indicators'].get(m) is not None else "---" for m in metrics}
                st.dataframe(pd.DataFrame(table), use_container_width=True)
    elif len(codes) == 1:
        st.info("📌 2社以上入力してください")
    else:
        st.info("📌 比較したい銘柄の証券コードを2〜3社分入力してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# ランキングページ
# ========================================
