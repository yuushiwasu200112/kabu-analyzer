if page == "配当カレンダー":
    st.title("📅 配当カレンダー")
    st.caption("銘柄の決算月から配当受取スケジュールを確認")

    # 主要銘柄の決算月データ（決算月→配当支払は約3ヶ月後）
    SETTLEMENT_MONTHS = {
        "3月決算": {"settlement": 3, "interim": 9, "stocks": [
            "7203","6758","9984","8306","6861","9432","6501","6098","8035","9433",
            "4063","7741","6902","4519","7974","8058","6367","4661","8001","3382",
            "4502","8766","6954","7267","6981","6594","6762","7751","8031","8053",
            "4901","6701","6702","7752","6503","7011","6301","6273","6645","4543",
            "4578","4911","7269","7270","8002","8316","8411","8591","8750","8801",
            "8802","9020","9022","9101","9104","2801","2502","2503","4452","4507",
            "4523","3861","5108","5401","5713","5802","6504","6752","6971","7201",
            "7202","7211","7733","7735","7832","7912","7951","8015","8601","8604",
            "8630","8725","9001","9005","9009","9064","9201","9202","9301","9501",
            "9503","9531",
        ]},
        "12月決算": {"settlement": 12, "interim": 6, "stocks": [
            "6861","6920","3659","2914","9983","6723","6857","4689",
        ]},
    }

    # 入力方法の選択
    cal_mode = st.radio("銘柄の選択方法", ["手動入力", "ウォッチリストから", "ポートフォリオから"], horizontal=True)

    cal_codes = []
    if cal_mode == "手動入力":
        cal_input = st.text_input("証券コードをカンマ区切りで入力（例: 7203,6758,9433）", key="cal_input")
        if cal_input:
            cal_codes = [c.strip() for c in cal_input.split(",") if c.strip() in CODE_MAP]
    elif cal_mode == "ウォッチリストから":
        if "watchlist" in st.session_state and st.session_state.watchlist:
            cal_codes = st.session_state.watchlist
            st.info(f"ウォッチリストから{len(cal_codes)}銘柄を読み込みました")
        else:
            st.warning("ウォッチリストが空です。先に銘柄を追加してください。")
    elif cal_mode == "ポートフォリオから":
        if "portfolio" in st.session_state and st.session_state.portfolio:
            cal_codes = [p["code"] for p in st.session_state.portfolio]
            st.info(f"ポートフォリオから{len(cal_codes)}銘柄を読み込みました")
        else:
            st.warning("ポートフォリオが空です。先に銘柄を追加してください。")

    if cal_codes:
        st.divider()

        # 各銘柄の決算月を特定
        stock_schedule = []
        for code in cal_codes:
            name = CODE_MAP.get(code, {}).get("name", code)
            # 決算月を推定
            settle_month = 3  # デフォルト3月
            for group_name, group_data in SETTLEMENT_MONTHS.items():
                if code in group_data["stocks"]:
                    settle_month = group_data["settlement"]
                    break

            # 配当スケジュール（期末配当: 決算月+3ヶ月, 中間配当: 中間月+3ヶ月）
            final_pay = (settle_month + 3 - 1) % 12 + 1  # 期末配当支払月
            interim_month = (settle_month + 6 - 1) % 12 + 1  # 中間決算月
            interim_pay = (interim_month + 3 - 1) % 12 + 1  # 中間配当支払月

            stock_schedule.append({
                "code": code,
                "name": name[:12],
                "settlement": settle_month,
                "final_pay": final_pay,
                "interim_pay": interim_pay,
            })

        # 月別カレンダー表示
        st.subheader("📅 月別配当スケジュール")

        months = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
        calendar_data = {m: {"期末配当": [], "中間配当": []} for m in range(1, 13)}

        for s in stock_schedule:
            calendar_data[s["final_pay"]]["期末配当"].append(f"{s['name']}({s['code']})")
            calendar_data[s["interim_pay"]]["中間配当"].append(f"{s['name']}({s['code']})")

        # 4列×3行で表示
        for row in range(3):
            cols = st.columns(4)
            for col_idx in range(4):
                month = row * 4 + col_idx + 1
                with cols[col_idx]:
                    finals = calendar_data[month]["期末配当"]
                    interims = calendar_data[month]["中間配当"]
                    total = len(finals) + len(interims)

                    if total > 0:
                        st.markdown(f"### 📅 {months[month-1]}")
                        if finals:
                            for f in finals:
                                st.markdown(f"🔵 {f}")
                        if interims:
                            for i in interims:
                                st.markdown(f"🟡 {i}")
                    else:
                        st.markdown(f"### {months[month-1]}")
                        st.caption("配当なし")

        st.divider()
        st.caption("🔵 期末配当 ｜ 🟡 中間配当 ｜ ※配当支払月は目安です（実際と異なる場合があります）")

        # 月別配当件数チャート
        import plotly.graph_objects as go
        final_counts = [len(calendar_data[m]["期末配当"]) for m in range(1, 13)]
        interim_counts = [len(calendar_data[m]["中間配当"]) for m in range(1, 13)]

        fig_cal = go.Figure()
        fig_cal.add_trace(go.Bar(x=months, y=final_counts, name="期末配当", marker_color="#2E75B6"))
        fig_cal.add_trace(go.Bar(x=months, y=interim_counts, name="中間配当", marker_color="#F39C12"))
        fig_cal.update_layout(barmode="stack", height=350, xaxis_title="月", yaxis_title="銘柄数",
                              legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_cal, use_container_width=True)

        # 配当集中リスク
        max_month_count = max(final_counts[m] + interim_counts[m] for m in range(12))
        if max_month_count > len(cal_codes) * 0.5:
            st.warning("🟡 **配当集中**: 特定の月に配当が集中しています。決算月の異なる銘柄を追加すると、毎月の収入が安定します。")
        else:
            st.success("🟢 **配当分散良好**: 配当が複数月に分散されています。")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# アラートページ
# ========================================
