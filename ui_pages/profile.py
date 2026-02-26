if page == "プロフィール":
    st.title("👤 マイプロフィール")
    username = st.session_state.get("username", "guest")
    plan = st.session_state.get("plan", "free")
    plan_info = {"free": ("🆓 Free", "#8899AA"), "pro": ("⭐ Pro", "#F39C12"), "premium": ("💎 Premium", "#2E75B6")}
    p_name, p_color = plan_info.get(plan, ("Free", "#8899AA"))
    st.markdown(f"""<div style='background:linear-gradient(135deg,#1B3A5C,#2E75B6);border-radius:16px;padding:30px;text-align:center;margin-bottom:20px'>
        <div style='font-size:3rem;margin-bottom:10px'>👤</div>
        <h2 style='color:white;margin:0'>{username}</h2>
        <span style='background:{p_color};color:white;padding:4px 16px;border-radius:20px;font-size:0.85rem'>{p_name}</span>
    </div>""", unsafe_allow_html=True)
    try:
        from data.database import get_user_stats, get_analysis_history
        stats = get_user_stats(username)
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("累計分析", f"{stats['total_analyses']}回")
        sc2.metric("分析銘柄数", f"{stats['unique_stocks']}銘柄")
        sc3.metric("ウォッチリスト", f"{len(st.session_state.get('watchlist',[]))}銘柄")
        if stats["top_stocks"]:
            st.divider()
            st.subheader("📈 よく分析する銘柄")
            for ts in stats["top_stocks"][:5]:
                st.caption(f"🔹 {ts['company_name']}（{ts['stock_code']}）: {ts['cnt']}回")
        history = get_analysis_history(username, limit=10)
        if history:
            st.divider()
            st.subheader("📜 分析履歴")
            for h in history:
                sc = "🟢" if h["total_score"] >= 75 else "🟡" if h["total_score"] >= 50 else "🔴"
                st.caption(f"{sc} {h['company_name']}({h['stock_code']}) {h['total_score']}点 - {h['analyzed_at'][:16]}")
    except:
        st.info("📌 分析を行うと統計情報が表示されます")
    st.stop()

