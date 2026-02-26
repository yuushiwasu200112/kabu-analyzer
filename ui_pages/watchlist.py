if page == "ウォッチリスト":
    st.title("⭐ ウォッチリスト")
    st.caption("お気に入り銘柄を管理できます")

    # セッション初期化
    if "watchlist" not in st.session_state:
        try:
            from data.database import get_watchlist
            st.session_state.watchlist = get_watchlist(st.session_state.get("username", "guest"))
        except:
            st.session_state.watchlist = []

    # 銘柄追加
    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_code = st.text_input("銘柄を追加（証券コード）", max_chars=4, key="wl_add", placeholder="例: 7203")
    with add_col2:
        st.write("")
        st.write("")
        if st.button("➕ 追加", type="primary"):
            if new_code and len(new_code) == 4 and new_code.isdigit() and new_code in CODE_MAP:
                if new_code not in st.session_state.watchlist:
                    st.session_state.watchlist.append(new_code)
                    st.success(f"✅ {CODE_MAP[new_code]['name']} を追加しました")
                else:
                    st.info("既に追加済みです")
            elif new_code:
                st.error("❌ 未対応の証券コードです")

    # ウォッチリスト表示
    if st.session_state.watchlist:
        st.divider()

        # 一括分析ボタン
        if st.button("📊 ウォッチリストを一括分析", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")
            results = []
            progress = st.progress(0, text="分析中...")

            for idx, code in enumerate(st.session_state.watchlist):
                name = CODE_MAP[code]["name"]
                progress.progress((idx + 1) / len(st.session_state.watchlist), text=f"{name} を分析中...")
                try:
                    r = analyze_company(code, API_KEY)
                    if r:
                        results.append({
                            "code": code,
                            "name": r["name"],
                            "total": r["score"]["total_score"],
                            "profitability": r["score"]["category_scores"].get("収益性", 0),
                            "safety": r["score"]["category_scores"].get("安全性", 0),
                            "growth": r["score"]["category_scores"].get("成長性", 0),
                            "value": r["score"]["category_scores"].get("割安度", 0),
                            "roe": r["indicators"].get("ROE", 0),
                            "per": r["indicators"].get("PER", 0),
                            "dividend": r["indicators"].get("配当利回り", 0),
                        })
                except:
                    continue

            progress.empty()

            if results:
                results.sort(key=lambda x: x["total"], reverse=True)

                # レーダーチャート重ね合わせ
                st.subheader("📊 ウォッチリスト比較")
                fig_radar = go.Figure()
                colors = ["#2E75B6", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB"]
                for i, r in enumerate(results):
                    cats = ["収益性", "安全性", "成長性", "割安度"]
                    vals = [r["profitability"], r["safety"], r["growth"], r["value"]]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=cats + [cats[0]],
                        fill="toself", name=f"{r['name'][:8]} ({r['total']}点)",
                        line_color=colors[i % len(colors)],
                    ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(fig_radar, use_container_width=True)

                # スコアテーブル
                st.subheader("📋 スコア一覧")
                df = pd.DataFrame(results)
                df.columns = ["証券コード", "企業名", "総合", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"]
                st.dataframe(df, use_container_width=True, hide_index=True)

        # 銘柄リスト（削除ボタン付き）
        st.divider()
        st.subheader("📌 登録銘柄")
        for code in st.session_state.watchlist:
            wl_col1, wl_col2, wl_col3 = st.columns([1, 3, 1])
            with wl_col1:
                st.markdown(f"**{code}**")
            with wl_col2:
                st.markdown(CODE_MAP[code]["name"])
            with wl_col3:
                if st.button("🗑️", key=f"del_{code}"):
                    st.session_state.watchlist.remove(code)
                    st.rerun()

        # 全削除
        if st.button("🗑️ ウォッチリストをクリア"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.info("📌 証券コードを入力してウォッチリストに追加してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# ポートフォリオ分析ページ
# ========================================
