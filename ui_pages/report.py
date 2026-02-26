if page == "定期レポート":
    st.title("📬 定期レポート")
    st.caption("ウォッチリスト・ポートフォリオの定期分析レポートを生成")

    # レポート設定
    st.subheader("⚙️ レポート設定")
    rp_col1, rp_col2 = st.columns(2)
    with rp_col1:
        rp_freq = st.selectbox("レポート頻度", ["週次（毎週月曜）", "月次（毎月1日）"], key="rp_freq")
    with rp_col2:
        rp_target = st.selectbox("対象銘柄", ["ウォッチリストの銘柄", "ポートフォリオの銘柄", "手動で選択"], key="rp_target")

    # 手動選択の場合
    target_codes = []
    if rp_target == "ウォッチリストの銘柄":
        target_codes = st.session_state.get("watchlist", [])
        if target_codes:
            st.info(f"⭐ ウォッチリスト: {len(target_codes)}銘柄")
        else:
            st.warning("ウォッチリストが空です。先に銘柄を追加してください。")
    elif rp_target == "ポートフォリオの銘柄":
        pf = st.session_state.get("portfolio", [])
        target_codes = [p["code"] for p in pf] if pf else []
        if target_codes:
            st.info(f"💼 ポートフォリオ: {len(target_codes)}銘柄")
        else:
            st.warning("ポートフォリオが空です。先に銘柄を追加してください。")
    else:
        rp_manual = st.text_input("証券コードをカンマ区切りで入力", placeholder="7203,6758,9433", key="rp_manual")
        if rp_manual:
            target_codes = [c.strip() for c in rp_manual.split(",") if c.strip()]

    # メール設定（将来用）
    st.divider()
    st.subheader("📧 メール通知（準備中）")
    rp_email = st.text_input("通知先メールアドレス", placeholder="your@email.com", key="rp_email")
    st.caption("📌 メール通知は近日対応予定です。現在はレポートの即時生成のみ利用できます。")

    # レポート生成
    st.divider()
    if target_codes and st.button("📊 レポートを今すぐ生成", type="primary"):
        import plotly.graph_objects as go
        import pandas as pd
        import datetime as dt_report
        API_KEY = os.getenv("EDINET_API_KEY")

        results = []
        progress = st.progress(0, text="レポート生成中...")
        for i, code in enumerate(target_codes):
            if code not in CODE_MAP:
                continue
            progress.progress((i+1)/len(target_codes), text=f"{CODE_MAP[code]['name']} を分析中...")
            try:
                r = analyze_company(code, API_KEY)
                if r:
                    results.append({
                        "code": code, "name": r["name"],
                        "score": r["score"]["total_score"],
                        "prof": r["score"]["category_scores"].get("収益性", 0),
                        "safe": r["score"]["category_scores"].get("安全性", 0),
                        "grow": r["score"]["category_scores"].get("成長性", 0),
                        "val": r["score"]["category_scores"].get("割安度", 0),
                        "roe": r["indicators"].get("ROE", 0),
                        "per": r["indicators"].get("PER", 0),
                        "dividend": r["indicators"].get("配当利回り", 0),
                        "judgment": r["score"]["judgment"],
                    })
            except:
                continue
        progress.empty()

        if results:
            now = dt_report.datetime.now().strftime("%Y年%m月%d日 %H:%M")
            freq_label = "週次" if "週次" in rp_freq else "月次"

            # レポートヘッダー
            st.markdown(f"""
            <div style='background:linear-gradient(135deg,#1B3A5C,#2E75B6);border-radius:12px;padding:25px;margin:10px 0'>
                <h2 style='color:white;margin:0'>📬 {freq_label}レポート</h2>
                <p style='color:#B8D4E8;margin:5px 0 0 0'>{now} 生成 | {len(results)}銘柄</p>
            </div>""", unsafe_allow_html=True)

            # サマリー
            avg_score = sum(r["score"] for r in results) / len(results)
            best = max(results, key=lambda x: x["score"])
            worst = min(results, key=lambda x: x["score"])

            st.write("")
            sum_col1, sum_col2, sum_col3 = st.columns(3)
            sum_col1.metric("平均スコア", f"{avg_score:.0f}点")
            sum_col2.metric("最高スコア", f"{best['score']}点", delta=f"{best['name'][:8]}")
            sum_col3.metric("最低スコア", f"{worst['score']}点", delta=f"{worst['name'][:8]}")

            # 銘柄別詳細
            st.divider()
            st.subheader("📋 銘柄別スコア")
            results.sort(key=lambda x: x["score"], reverse=True)

            for r in results:
                sc = "🟢" if r["score"] >= 75 else "🟡" if r["score"] >= 50 else "🔴"
                st.markdown(f"""
                <div style='background:#1B2332;border-radius:10px;padding:15px;margin:8px 0;border-left:4px solid {"#2ECC71" if r["score"]>=75 else "#F39C12" if r["score"]>=50 else "#E74C3C"}'>
                    <span style='font-size:1.1rem;font-weight:bold'>{sc} {r['name']}（{r['code']}）</span>
                    <span style='float:right;font-size:1.3rem;font-weight:bold;color:#5BA3E6'>{r['score']}点</span><br>
                    <span style='color:#8899AA'>収益{r['prof']} / 安全{r['safe']} / 成長{r['grow']} / 割安{r['val']} | ROE {r['roe']:.1f}% | PER {r['per']:.1f}倍 | 配当 {r['dividend']:.2f}%</span>
                </div>""", unsafe_allow_html=True)

            # スコア分布チャート
            st.divider()
            st.subheader("📊 スコア分布")
            fig_bar = go.Figure(data=[go.Bar(
                x=[r["name"][:8] for r in results],
                y=[r["score"] for r in results],
                marker_color=["#2ECC71" if r["score"]>=75 else "#F39C12" if r["score"]>=50 else "#E74C3C" for r in results],
                text=[f"{r['score']}点" for r in results],
                textposition="outside",
            )])
            fig_bar.update_layout(height=400, yaxis_range=[0, 100])
            st.plotly_chart(fig_bar, use_container_width=True)

            # レーダー比較（上位5銘柄）
            if len(results) >= 2:
                st.subheader("📊 上位銘柄レーダー")
                fig_rd = go.Figure()
                colors = ["#2E75B6","#E74C3C","#2ECC71","#F39C12","#9B59B6"]
                for i, r in enumerate(results[:5]):
                    cats = ["収益性","安全性","成長性","割安度"]
                    vals = [r["prof"], r["safe"], r["grow"], r["val"]]
                    fig_rd.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself", name=f"{r['name'][:8]}({r['score']}点)", line_color=colors[i%5]))
                fig_rd.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])), height=450)
                st.plotly_chart(fig_rd, use_container_width=True)

            # データテーブル
            st.divider()
            st.subheader("📋 データ一覧")
            df = pd.DataFrame(results)
            df = df[["code","name","score","prof","safe","grow","val","roe","per","dividend"]]
            df.columns = ["コード","企業名","総合","収益性","安全性","成長性","割安度","ROE","PER","配当利回り"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # CSV/Excelエクスポート
            rp_exp1, rp_exp2 = st.columns(2)
            with rp_exp1:
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📥 CSVダウンロード", csv, f"report_{dt_report.datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="rp_csv")
            with rp_exp2:
                buf = io.BytesIO()
                df.to_excel(buf, index=False, engine="openpyxl")
                st.download_button("📥 Excelダウンロード", buf.getvalue(), f"report_{dt_report.datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="rp_xlsx")

            # レポート履歴をDBに保存
            try:
                from data.database import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS report_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, frequency TEXT, stock_count INTEGER, avg_score REAL, generated_at TEXT)")
                c.execute("INSERT INTO report_history (username, frequency, stock_count, avg_score, generated_at) VALUES (?,?,?,?,?)",
                    (st.session_state.get("username","guest"), freq_label, len(results), avg_score, now))
                conn.commit()
                conn.close()
            except: pass

        else:
            st.error("❌ レポートの生成に失敗しました")

    # 過去のレポート履歴
    try:
        from data.database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM report_history WHERE username=? ORDER BY generated_at DESC LIMIT 5", (st.session_state.get("username","guest"),))
        history = c.fetchall()
        conn.close()
        if history:
            st.divider()
            st.subheader("📜 レポート履歴")
            for h in history:
                st.caption(f"📬 {h[5]} | {h[2]}レポート | {h[3]}銘柄 | 平均{h[4]:.0f}点")
    except: pass

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# 利用規約ページ
# ========================================
