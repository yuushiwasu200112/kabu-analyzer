"""Supabase版認証マネージャー"""
import hashlib
import os
import datetime

def _get_client():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
    except:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        try:
            with open(os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')) as f:
                for line in f:
                    if 'SUPABASE_URL' in line and '=' in line:
                        url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if 'SUPABASE_KEY' in line and '=' in line:
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
        except:
            pass
    from supabase import create_client
    return create_client(url, key)

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    client = _get_client()
    result = client.table("users").select("username").eq("username", username).execute()
    if result.data:
        return False, "このユーザー名は既に使われています"
    if len(password) < 6:
        return False, "パスワードは6文字以上で設定してください"
    row = {
        "username": username,
        "password": _hash_password(password),
        "email": email,
        "plan": "free",
        "monthly_usage": 0,
        "tutorial_done": False,
    }
    client.table("users").insert(row).execute()
    return True, "登録完了"

def login_user(username, password):
    client = _get_client()
    result = client.table("users").select("*").eq("username", username).execute()
    if not result.data:
        return False, None
    user = result.data[0]
    if user["password"] != _hash_password(password):
        return False, None
    return True, user

def get_user_info(username):
    client = _get_client()
    result = client.table("users").select("*").eq("username", username).execute()
    if result.data:
        return result.data[0]
    return None

def update_usage(username):
    client = _get_client()
    user = get_user_info(username)
    if not user:
        return
    now = datetime.datetime.now()
    current_month = now.strftime("%Y-%m")
    if user.get("usage_reset_month") != current_month:
        client.table("users").update({"monthly_usage": 1, "usage_reset_month": current_month}).eq("username", username).execute()
    else:
        client.table("users").update({"monthly_usage": (user.get("monthly_usage", 0) or 0) + 1}).eq("username", username).execute()

def check_usage_limit(username):
    user = get_user_info(username)
    if not user:
        return False, 0, 0
    plan = user.get("plan", "free")
    usage = user.get("monthly_usage", 0) or 0
    limits = {"free": 5, "pro": 50, "premium": 99999}
    limit = limits.get(plan, 5)
    return usage < limit, usage, limit

def reset_password(username, email, new_password):
    client = _get_client()
    result = client.table("users").select("*").eq("username", username).execute()
    if not result.data:
        return False, "ユーザーが見つかりません"
    if result.data[0].get("email", "") != email:
        return False, "メールアドレスが一致しません"
    if len(new_password) < 6:
        return False, "パスワードは6文字以上で設定してください"
    client.table("users").update({"password": _hash_password(new_password)}).eq("username", username).execute()
    return True, "パスワードをリセットしました"

def show_login_page():
    import streamlit as st
    st.markdown("""
    <style>
    .login-header {
        text-align: center;
        padding: 2rem 0;
    }
    </style>
    <div class='login-header'>
        <h1>📈 Kabu Analyzer</h1>
        <p>日本株AI分析ツール</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register, tab_reset = st.tabs(["🔑 ログイン", "📝 新規登録", "🔄 パスワードリセット"])

    with tab_login:
        st.subheader("🔑 ログイン")
        username = st.text_input("ユーザー名", key="login_user")
        password = st.text_input("パスワード", type="password", key="login_pass")
        if st.button("ログイン", type="primary", key="btn_login"):
            if username and password:
                success, user = login_user(username, password)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.session_state["plan"] = user.get("plan", "free")
                    try:
                        from utils.logger import log_login
                        log_login(username)
                    except: pass
                    st.rerun()
                else:
                    st.error("ユーザー名またはパスワードが違います")
            else:
                st.error("ユーザー名とパスワードを入力してください")

        if st.button("🔓 ゲストとして利用", key="btn_guest"):
            st.session_state["logged_in"] = True
            st.session_state["username"] = "guest"
            st.session_state["plan"] = "free"
            st.rerun()

    with tab_register:
        st.subheader("📝 新規登録")
        reg_user = st.text_input("ユーザー名", key="reg_user")
        reg_email = st.text_input("メールアドレス", key="reg_email")
        reg_pass = st.text_input("パスワード（6文字以上）", type="password", key="reg_pass")
        reg_pass2 = st.text_input("パスワード（確認）", type="password", key="reg_pass2")
        agree = st.checkbox("利用規約に同意する", key="reg_agree")

        if st.button("登録", type="primary", key="btn_register"):
            if not agree:
                st.error("利用規約に同意してください")
            elif not reg_user or not reg_pass or not reg_email:
                st.error("すべての項目を入力してください")
            elif reg_pass != reg_pass2:
                st.error("パスワードが一致しません")
            else:
                success, msg = register_user(reg_user, reg_pass, reg_email)
                if success:
                    st.success("✅ 登録完了！ログインタブからログインしてください。")
                    try:
                        from utils.logger import log_register
                        log_register(reg_user)
                    except: pass
                else:
                    st.error(f"❌ {msg}")

    with tab_reset:
        st.subheader("🔄 パスワードリセット")
        st.caption("登録時のユーザー名とメールアドレスを入力してください")
        reset_user = st.text_input("ユーザー名", key="reset_user")
        reset_email = st.text_input("メールアドレス", key="reset_email")
        reset_pass = st.text_input("新しいパスワード（6文字以上）", type="password", key="reset_pass")
        reset_pass2 = st.text_input("新しいパスワード（確認）", type="password", key="reset_pass2")
        if st.button("🔄 パスワードをリセット", type="primary", key="btn_reset"):
            if not reset_user or not reset_email or not reset_pass:
                st.error("すべての項目を入力してください")
            elif reset_pass != reset_pass2:
                st.error("パスワードが一致しません")
            else:
                success, msg = reset_password(reset_user, reset_email, reset_pass)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    # プラン紹介
    st.divider()
    st.subheader("📌 プラン一覧")
    plan_cols = st.columns(3)
    with plan_cols[0]:
        st.markdown("### 🆓 Free")
        st.markdown("**¥0/月**")
        st.markdown("月5回分析")
    with plan_cols[1]:
        st.markdown("### ⭐ Pro")
        st.markdown("**¥980/月**")
        st.markdown("月50回分析")
        st.link_button("⭐ Proに登録", "https://buy.stripe.com/test_aFa5kD3JK9mY3tYbRBa3u00", type="primary", use_container_width=True)
    with plan_cols[2]:
        st.markdown("### 💎 Premium")
        st.markdown("**¥2,980/月**")
        st.markdown("無制限分析")
        st.link_button("💎 Premiumに登録", "https://buy.stripe.com/test_eVq9ATbcc56I6Ga2h1a3u01", type="primary", use_container_width=True)

    st.stop()
