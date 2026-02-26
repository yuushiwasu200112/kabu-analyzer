if page == "設定":
    st.title("⚙️ 設定")
    username = st.session_state.get("username", "guest")
    plan = st.session_state.get("plan", "free")
    plan_names = {"free": "🆓 Free", "pro": "⭐ Pro", "premium": "💎 Premium"}
    ac1, ac2 = st.columns(2)
    ac1.metric("ユーザー名", username)
    ac2.metric("プラン", plan_names.get(plan, plan))
    st.divider()
    st.subheader("🗄️ データ管理")
    dc1, dc2 = st.columns(2)
    with dc1:
        if st.button("🗑️ ウォッチリストをクリア"):
            st.session_state.watchlist = []
            st.success("✅ クリアしました")
    with dc2:
        if st.button("🗑️ ポートフォリオをクリア"):
            st.session_state.portfolio = []
            st.success("✅ クリアしました")
    st.divider()
    st.subheader("🔄 キャッシュ")
    if st.button("🔄 キャッシュをクリア"):
        st.cache_data.clear()
        st.success("✅ クリアしました")
    st.divider()
    st.markdown("ℹ️ v1.0.0 | 3,732社対応 | 300銘柄ランキング | 15セクター | 33テスト")
    st.stop()

