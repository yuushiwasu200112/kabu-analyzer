"""
認証マネージャー
Free/Pro/Premium の3プランを管理
"""
import streamlit as st
import hashlib
import json
import os
import datetime


# プラン定義
PLANS = {
    "free": {
        "name": "Free",
        "monthly_analyses": 5,
        "features": ["銘柄分析", "複数社比較"],
        "price": 0,
    },
    "pro": {
        "name": "Pro",
        "monthly_analyses": 50,
        "features": ["銘柄分析", "複数社比較", "ランキング", "ウォッチリスト", "ポートフォリオ", "配当カレンダー", "PDFレポート"],
        "price": 980,
    },
    "premium": {
        "name": "Premium",
        "monthly_analyses": -1,  # 無制限
        "features": ["全機能", "AI定性分析", "アラート", "優先サポート"],
        "price": 2980,
    },
}


def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _get_users_path():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'users.json'),
        os.path.join(os.getcwd(), 'data', 'users.json'),
    ]
    for p in candidates:
        d = os.path.dirname(p)
        if os.path.exists(d):
            return p
    # デフォルト
    p = candidates[0]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def _load_users():
    path = _get_users_path()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_users(users):
    path = _get_users_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register_user(username, password, email):
    """新規ユーザー登録"""
    users = _load_users()
    if username in users:
        return False, "このユーザー名は既に使用されています"
    users[username] = {
        "password": _hash_password(password),
        "email": email,
        "plan": "free",
        "created_at": datetime.datetime.now().isoformat(),
        "monthly_usage": 0,
        "usage_reset_month": datetime.datetime.now().strftime("%Y-%m"),
    }
    _save_users(users)
    return True, "登録成功！"


def login_user(username, password):
    """ログイン"""
    users = _load_users()
    if username not in users:
        return False, "ユーザーが見つかりません"
    if users[username]["password"] != _hash_password(password):
        return False, "パスワードが違います"
    return True, users[username]


def get_user_info(username):
    """ユーザー情報取得"""
    users = _load_users()
    return users.get(username)


def update_usage(username):
    """分析回数を更新"""
    users = _load_users()
    if username not in users:
        return
    user = users[username]
    current_month = datetime.datetime.now().strftime("%Y-%m")
    if user.get("usage_reset_month") != current_month:
        user["monthly_usage"] = 0
        user["usage_reset_month"] = current_month
    user["monthly_usage"] += 1
    _save_users(users)


def check_usage_limit(username):
    """使用制限チェック"""
    users = _load_users()
    if username not in users:
        return False, 0, 0
    user = users[username]
    plan = PLANS.get(user.get("plan", "free"), PLANS["free"])
    limit = plan["monthly_analyses"]

    current_month = datetime.datetime.now().strftime("%Y-%m")
    if user.get("usage_reset_month") != current_month:
        usage = 0
    else:
        usage = user.get("monthly_usage", 0)

    if limit == -1:  # 無制限
        return True, usage, -1
    return usage < limit, usage, limit


def show_login_page():
    """ログイン/登録ページを表示"""
    st.markdown("""
    <div class='main-header'>
        <h1>📊 Kabu Analyzer</h1>
        <p>AI搭載 株式投資分析ツール</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 ログイン", "📝 新規登録"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            submitted = st.form_submit_button("ログイン", type="primary")

            if submitted:
                if username and password:
                    success, result = login_user(username, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_info = result
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")
                else:
                    st.warning("ユーザー名とパスワードを入力してください")

        # ゲストログイン
        st.divider()
        if st.button("👤 ゲストとして利用（月5回まで）"):
            st.session_state.logged_in = True
            st.session_state.username = "guest"
            st.session_state.user_info = {"plan": "free", "email": ""}
            st.rerun()

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("ユーザー名（英数字）", key="reg_user")
            new_email = st.text_input("メールアドレス", key="reg_email")
            new_password = st.text_input("パスワード（6文字以上）", type="password", key="reg_pass")
            new_password2 = st.text_input("パスワード（確認）", type="password", key="reg_pass2")
            reg_submitted = st.form_submit_button("登録", type="primary")

            if reg_submitted:
                if not new_username or not new_password or not new_email:
                    st.warning("すべての項目を入力してください")
                elif len(new_password) < 6:
                    st.warning("パスワードは6文字以上にしてください")
                elif new_password != new_password2:
                    st.error("パスワードが一致しません")
                else:
                    success, msg = register_user(new_username, new_password, new_email)
                    if success:
                        st.success(f"✅ {msg} ログインしてください。")
                    else:
                        st.error(f"❌ {msg}")

    # プラン紹介
    st.divider()
    st.subheader("📋 プラン一覧")
    plan_cols = st.columns(3)
    for i, (key, plan) in enumerate(PLANS.items()):
        with plan_cols[i]:
            st.markdown(f"### {plan['name']}")
            if plan['price'] == 0:
                st.markdown("**無料**")
            else:
                st.markdown(f"**¥{plan['price']:,}/月**")
            limit = plan['monthly_analyses']
            st.markdown(f"月{limit}回分析" if limit > 0 else "無制限")
            for f in plan['features']:
                st.caption(f"✅ {f}")
