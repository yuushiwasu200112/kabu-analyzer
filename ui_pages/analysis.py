
# ========================================
# 銘柄分析ページ

# ── 利用規約等は先に処理済みなのでここで停止 ──
if page in ["利用規約", "設定", "プロフィール"]:
    st.stop()

# ── ダッシュボード ──
st.markdown("""
<div class='main-header'>
    <h1>📊 Kabu Analyzer</h1>
    <p>AI搭載 株式投資分析ツール ｜ 3,700社以上対応</p>
</div>
""", unsafe_allow_html=True)

dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
wl = len(st.session_state.get("watchlist", []))
pf = len(st.session_state.get("portfolio", []))
al = len([a for a in st.session_state.get("alerts", []) if a.get("active")])
for col, icon, label, val, color in [
    (dash_col1, "📊", "対応銘柄", f"{len(CODE_MAP):,}社", "#2E75B6"),
    (dash_col2, "⭐", "ウォッチリスト", f"{wl}銘柄", "#F39C12"),
    (dash_col3, "💼", "ポートフォリオ", f"{pf}銘柄", "#2ECC71"),
    (dash_col4, "🔔", "アラート", f"{al}件", "#E74C3C"),
]:
    col.markdown(f"""
    <div style='background:linear-gradient(135deg,#1B2332,#1E2A3E);border-radius:12px;padding:18px;text-align:center;border:1px solid {color}33;box-shadow:0 4px 15px rgba(0,0,0,0.2)'>
        <div style='font-size:1.5rem'>{icon}</div>
        <p style='color:#8899AA;margin:5px 0 2px 0;font-size:0.8rem'>{label}</p>
        <p style='color:#FFFFFF;margin:0;font-size:1.6rem;font-weight:bold'>{val}</p>
    </div>""", unsafe_allow_html=True)

st.write("")
qc1, qc2, qc3 = st.columns(3)
with qc1:
    st.markdown("""<div style='background:linear-gradient(135deg,#1B3A5C,#2E75B6);border-radius:10px;padding:15px;cursor:pointer'>
    <p style='color:white;margin:0;font-size:1rem'>💡 人気銘柄</p>
    <p style='color:#B8D4E8;margin:5px 0 0 0;font-size:0.85rem'>トヨタ / ソニー / KDDI</p></div>""", unsafe_allow_html=True)
    qc1_pick = st.selectbox("分析する", ["","7203 トヨタ","6758 ソニー","9433 KDDI"], key="qc1_pick", label_visibility="collapsed")
with qc2:
    st.markdown("""<div style='background:linear-gradient(135deg,#1B4332,#27AE60);border-radius:10px;padding:15px;cursor:pointer'>
    <p style='color:white;margin:0;font-size:1rem'>📈 高配当銘柄</p>
    <p style='color:#B8E8D4;margin:5px 0 0 0;font-size:0.85rem'>JT / 三菱商事 / KDDI</p></div>""", unsafe_allow_html=True)
    qc2_pick = st.selectbox("分析する", ["","2914 JT","8058 三菱商事","9433 KDDI"], key="qc2_pick", label_visibility="collapsed")
with qc3:
    st.markdown("""<div style='background:linear-gradient(135deg,#4A1942,#9B59B6);border-radius:10px;padding:15px;cursor:pointer'>
    <p style='color:white;margin:0;font-size:1rem'>🚀 成長銘柄</p>
    <p style='color:#E8B8E8;margin:5px 0 0 0;font-size:0.85rem'>東京エレクトロン / レーザーテック</p></div>""", unsafe_allow_html=True)
    qc3_pick = st.selectbox("分析する", ["","8035 東京エレクトロン","6920 レーザーテック"], key="qc3_pick", label_visibility="collapsed")
quick_pick = qc1_pick or qc2_pick or qc3_pick
if quick_pick:
    stock_code = quick_pick.split(" ")[0]

username = st.session_state.get("username", "guest")
if username != "guest":
    try:
        history = get_analysis_history(username, limit=5)
        if history:
            st.markdown("**📜 最近の分析**")
            for h in history:
                sc = "🟢" if h["total_score"] >= 75 else "🟡" if h["total_score"] >= 50 else "🔴"
                st.caption(f"{sc} {h['company_name']}({h['stock_code']}) {h['total_score']}点 - {h['analyzed_at'][:16]}")
        stats = get_user_stats(username)
        if stats["total_analyses"] > 0:
            st.markdown(f"**📊 累計{stats['total_analyses']}回分析 / {stats['unique_stocks']}銘柄**")
    except: pass

if st.session_state.get("alert_history"):
    st.markdown("**🔔 最近のアラート**")
    for h in list(reversed(st.session_state.get("alert_history", [])))[:3]:
        st.caption(f"🔔 {h.get('time','')} | {h['name']}（{h['code']}）: {h['type']} → {h['actual']:.2f}")

st.divider()

if not (qc1_pick or qc2_pick or qc3_pick):
    stock_code = st.text_input("🔍 証券コードまたは企業名を入力（例: 7203 / トヨタ）", key="main_input")

if stock_code and not stock_code.isdigit():
    matches = {k: v for k, v in CODE_MAP.items() if stock_code in v["name"]}
    if matches:
        options = [f"{k} - {v['name']}" for k, v in list(matches.items())[:20]]
        selected = st.selectbox("該当企業を選択", options, key="name_select")
        if selected: stock_code = selected.split(" - ")[0]
    else:
        st.info("該当する企業が見つかりませんでした")
        stock_code = None

if stock_code:
    if len(stock_code) != 4 or not stock_code.isdigit():
        st.error("❌ 4桁の数字を入力してください")
    elif stock_code not in CODE_MAP:
        st.warning(f"⚠️ 証券コード {stock_code} はEDINETに登録されていません")
    else:
        company_name = CODE_MAP[stock_code]["name"]
        st.success(f"✅ {company_name}（{stock_code}）を分析中...")
        API_KEY = os.getenv("EDINET_API_KEY")

        # 使用制限チェック
        username = st.session_state.get("username", "guest")
        if username == "guest":
            guest_usage = st.session_state.get("guest_usage", 0)
            can_use = guest_usage < 5
            usage = guest_usage
            limit = 5
        else:
            can_use, usage, limit = check_usage_limit(username)
        if not can_use:
            st.error(f"❌ 今月の分析回数上限（{limit}回）に達しました。")
            st.markdown("### 🚀 プランをアップグレードして分析を続けましょう")
            up_col1, up_col2 = st.columns(2)
            with up_col1:
                st.markdown("**⭐ Pro** ¥980/月（月50回）")
                st.link_button("⭐ Proに登録", "https://buy.stripe.com/test_aFa5kD3JK9mY3tYbRBa3u00", type="primary")
            with up_col2:
                st.markdown("**💎 Premium** ¥2,980/月（無制限）")
                st.link_button("💎 Premiumに登録", "https://buy.stripe.com/test_eVq9ATbcc56I6Ga2h1a3u01", type="primary")
            st.stop()

        with st.spinner("分析データを取得中..."):
            result = analyze_company(stock_code, API_KEY)
            if result:
                if username == "guest":
                    st.session_state.guest_usage = st.session_state.get("guest_usage", 0) + 1
                else:
                    update_usage(username)

        if not result:
            st.error("❌ 分析データの取得に失敗しました")
        else:
            stock_info = result["stock_info"]
            indicators = result["indicators"]
            score_result = result["score"]

            # 分析履歴をDBに保存
            try:
                save_analysis(
                    st.session_state.get("username", "guest"),
                    stock_code, company_name, score_result, indicators, style, period
                )
            except: pass

            if stock_info and stock_info["current_price"] > 0:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("現在株価", f"¥{stock_info['current_price']:,.0f}")
                c2.metric("PER", f"{stock_info['per']:.1f}倍" if stock_info['per'] else "---")
                c3.metric("PBR", f"{stock_info['pbr']:.2f}倍" if stock_info['pbr'] else "---")
                cap = stock_info['market_cap']
                c4.metric("時価総額", f"¥{cap/1e12:.1f}兆" if cap >= 1e12 else f"¥{cap/1e8:.0f}億" if cap > 0 else "---")

            from analysis.filters import check_filters
            warnings = check_filters(result["current"], result["previous"])
            if warnings:
                st.divider()
                for w in warnings:
                    if w['level'] == 'danger':
                        st.error(f"{w['icon']} **{w['title']}**: {w['message']}")
                    else:
                        st.warning(f"{w['icon']} **{w['title']}**: {w['message']}")

            st.divider()
            import plotly.graph_objects as go

            score = score_result["total_score"]
            judgment = score_result["judgment"]
            sc = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"

            fig_g = go.Figure(go.Indicator(mode="gauge+number", value=score,
                title={"text": f"{company_name} 総合スコア", "font": {"size": 20}},
                number={"suffix": "点", "font": {"size": 48}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#2E75B6"},
                       "steps": [{"range": [0,50], "color": "#FFCDD2"}, {"range": [50,75], "color": "#FFF9C4"}, {"range": [75,100], "color": "#C8E6C9"}],
                       "threshold": {"line": {"color": "#1B3A5C", "width": 4}, "thickness": 0.75, "value": score}}))
            fig_g.update_layout(height=280, margin=dict(t=60, b=20, l=30, r=30))
            st.plotly_chart(fig_g, use_container_width=True)
            st.markdown(f"### {sc} {judgment}")
            st.caption(f"投資スタイル: {style} ｜ 投資期間: {period}")

            cats = list(score_result["category_scores"].keys())
            vals = list(score_result["category_scores"].values())
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]], fill='toself', line_color='#2E75B6', fillcolor='rgba(46,117,182,0.3)'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])), height=420)

            cc, cd = st.columns([1, 1])
            with cc: st.plotly_chart(fig_r, use_container_width=True)
            with cd:
                st.subheader("📊 カテゴリ別スコア")
                for cat, cs in score_result["category_scores"].items():
                    st.progress(cs / 100, text=f"{cat}: {cs}点")

            if "watchlist" not in st.session_state:
                st.session_state.watchlist = []
            if stock_code not in st.session_state.watchlist:
                if st.button("⭐ ウォッチリストに追加"):
                    st.session_state.watchlist.append(stock_code)
                    try:
                        from data.database import save_watchlist
                        save_watchlist(st.session_state.get("username", "guest"), stock_code)
                    except: pass
                    st.success("✅ ウォッチリストに追加しました")
            else:
                st.info("⭐ ウォッチリスト登録済み")

            # SNSシェア
            cats = score_result["category_scores"]
            share_text = f"{company_name}({stock_code})の投資スコア: {score}点 収益性{cats.get('収益性',0)} / 安全性{cats.get('安全性',0)} / 成長性{cats.get('成長性',0)} / 割安度{cats.get('割安度',0)} #KabuAnalyzer #株式投資"
            import urllib.parse
            tweet_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(share_text)}&url=https://kabu-analyzer.streamlit.app/"
            line_url = f"https://social-plugins.line.me/lineit/share?url=https://kabu-analyzer.streamlit.app/&text={urllib.parse.quote(share_text)}"

            st.divider()
            share_col1, share_col2, share_col3 = st.columns(3)
            with share_col1:
                st.link_button("🐦 Xでシェア", tweet_url, use_container_width=True)
            with share_col2:
                st.link_button("💬 LINEでシェア", line_url, use_container_width=True)
            with share_col3:
                st.code(f"{company_name}({stock_code}) {score}点", language=None)

            import datetime as dt_mod
            from reports.pdf_report import generate_pdf
            from analysis.filters import check_filters as cf2
            pdf_warnings = cf2(result['current'], result['previous'])
            pdf_bytes = generate_pdf(company_name, stock_code, indicators, score_result, warnings=pdf_warnings, stock_info=stock_info)
            st.download_button(label="📄 PDFレポートをダウンロード", data=pdf_bytes, file_name=f"kabu_analyzer_{stock_code}_{dt_mod.datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

            st.divider()
            st.subheader("📉 主要指標の推移")
            docs = result["docs"]
            if len(docs) >= 2:
                from parsers.xbrl_parser import download_and_parse
                from analysis.indicators import calc_indicators
                from data_sources.cache_manager import get_cache, set_cache
                all_y = {}
                for doc in docs:
                    ck = f"xbrl_{doc['docID']}"
                    yd = get_cache(ck)
                    if not yd:
                        yd = download_and_parse(doc["docID"], API_KEY)
                        if yd: set_cache(ck, yd)
                    if yd:
                        all_y[doc["periodEnd"][:4]] = calc_indicators(yd, result["price"])
                if len(all_y) >= 2:
                    yrs = sorted(all_y.keys())
                    fig_t = go.Figure()
                    for i, (n, k) in enumerate([("ROE","ROE"),("ROA","ROA"),("営業利益率","営業利益率"),("自己資本比率","自己資本比率")]):
                        fig_t.add_trace(go.Scatter(x=yrs, y=[all_y[y].get(k,0) for y in yrs], mode="lines+markers", name=n, line=dict(color=["#2E75B6","#E74C3C","#2ECC71","#F39C12"][i], width=2)))
                    fig_t.update_layout(height=400, xaxis_title="年度", yaxis_title="%", legend=dict(orientation="h", y=-0.2))
                    st.plotly_chart(fig_t, use_container_width=True)

            st.divider()
            st.subheader("📈 株価チャート（過去1年）")
            try:
                import yfinance as yf, time
                time.sleep(0.5)
                hist = yf.Ticker(f"{stock_code}.T").history(period="1y")
                if not hist.empty and len(hist) > 10:
                    fig_c = go.Figure(data=[go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], increasing_line_color="#2E75B6", decreasing_line_color="#E74C3C")])
                    fig_c.update_layout(height=400, xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig_c, use_container_width=True)
                else: st.info("ℹ️ 株価チャートを取得できませんでした")
            except: st.warning("⏳ 株価データの取得に制限がかかっています。1分ほどお待ちいただくと表示されます。")

            st.divider()
            st.subheader("📋 財務指標一覧")
            for category in ["収益性", "安全性", "成長性", "割安度"]:
                ci = {k: v for k, v in indicators.items() if k in INDICATOR_FORMAT and INDICATOR_FORMAT[k][1] == category}
                if ci:
                    st.markdown(f"**{category}**")
                    cols = st.columns(len(ci))
                    for i, (n, v) in enumerate(ci.items()):
                        u = INDICATOR_FORMAT[n][0]
                        cols[i].metric(n, f"{v:,.0f}{u}" if u == "円" else f"{v:.2f}{u}")

st.divider()
st.caption("⚠️ 本ツールは投資助言ではありません。投資判断はご自身の責任で行ってください。| 📜 利用規約はメニューから確認できます")
