import streamlit as st

def show_tutorial():
    """初回ログイン時のチュートリアル"""
    st.markdown("""
    <style>
    .tutorial-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .step-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="tutorial-card"><h1>🎉 Kabu Analyzerへようこそ！</h1><p>日本株3,732銘柄を瞬時に分析できるツールです</p></div>', unsafe_allow_html=True)

    step = st.session_state.get("tutorial_step", 1)

    if step == 1:
        st.subheader("📊 Step 1: 銘柄を分析してみよう")
        st.markdown("""
        左メニューの **「銘柄分析」** で、気になる企業を分析できます。
        
        1️⃣ 証券コードまたは企業名を入力（例: 7203 トヨタ）  
        2️⃣ 投資スタイルと期間を選択  
        3️⃣ 「分析開始」ボタンで即座にスコアが表示されます
        """)
        st.info("💡 スコアは収益性・安全性・成長性・割安度の4カテゴリで100点満点です")
        if st.button("次へ ▶", key="tut_next1", type="primary"):
            st.session_state["tutorial_step"] = 2
            st.rerun()

    elif step == 2:
        st.subheader("🏆 Step 2: ランキング＆スクリーニング")
        st.markdown("""
        **2,171銘柄のスコアがDB登録済み！** 待ち時間ゼロで使えます。
        
        🏆 **ランキング** — 総合スコアTOP銘柄を一覧表示  
        🔎 **スクリーニング** — ROE・配当利回り・PERなどで絞り込み  
        📈 **セクター分析** — 業種別の傾向を可視化
        """)
        st.info("💡 CSVやExcelでダウンロードもできます")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("◀ 戻る", key="tut_back2"):
                st.session_state["tutorial_step"] = 1
                st.rerun()
        with col2:
            if st.button("次へ ▶", key="tut_next2", type="primary"):
                st.session_state["tutorial_step"] = 3
                st.rerun()

    elif step == 3:
        st.subheader("⭐ Step 3: ウォッチリスト＆ポートフォリオ")
        st.markdown("""
        気になる銘柄を管理しましょう。
        
        ⭐ **ウォッチリスト** — 注目銘柄をブックマーク  
        💼 **ポートフォリオ** — 保有株の総合評価を確認  
        🛒 **買い増し最適化** — どの銘柄を買い増すべきか提案  
        📅 **配当カレンダー** — 配当スケジュールを一覧表示
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("◀ 戻る", key="tut_back3"):
                st.session_state["tutorial_step"] = 2
                st.rerun()
        with col2:
            if st.button("次へ ▶", key="tut_next3", type="primary"):
                st.session_state["tutorial_step"] = 4
                st.rerun()

    elif step == 4:
        st.subheader("🚀 Step 4: さらに便利な機能")
        st.markdown("""
        📊 **定期レポート** — 分析結果をPDFで出力  
        🔔 **アラート** — スコア変動を通知  
        📈 **バックテスト** — 過去データでシミュレーション  
        🔄 **複数社比較** — 最大5社を並べて比較
        """)

        st.divider()
        st.markdown("### 📌 プランについて")
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            st.markdown("**🆓 Free**\n\n月5回分析")
        with pc2:
            st.markdown("**⭐ Pro ¥980/月**\n\n月50回 + 全機能")
        with pc3:
            st.markdown("**💎 Premium ¥2,980/月**\n\n無制限 + AI分析")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("◀ 戻る", key="tut_back4"):
                st.session_state["tutorial_step"] = 3
                st.rerun()
        with col2:
            if st.button("✅ チュートリアル完了！分析を始める", key="tut_done", type="primary"):
                st.session_state["tutorial_done"] = True
                st.session_state["tutorial_step"] = 1
                # users.jsonに記録
                try:
                    import json
                    users_path = "auth/users.json"
                    with open(users_path, "r") as f:
                        users = json.load(f)
                    username = st.session_state.get("username", "")
                    if username in users:
                        users[username]["tutorial_done"] = True
                        with open(users_path, "w") as f:
                            json.dump(users, f, ensure_ascii=False, indent=2)
                except:
                    pass
                st.rerun()
