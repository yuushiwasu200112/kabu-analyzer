st.title("⭐ プランアップグレード")

import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", st.secrets.get("STRIPE_SECRET_KEY", ""))

username = st.session_state.get("username", "")
current_plan = st.session_state.get("plan", "free")

st.markdown(f"**現在のプラン:** {'🆓 Free' if current_plan == 'free' else '⭐ Pro' if current_plan == 'pro' else '💎 Premium'}")

# プラン一覧
st.divider()
plan_cols = st.columns(3)
with plan_cols[0]:
    st.markdown("### 🆓 Free")
    st.markdown("**¥0/月**")
    st.markdown("月5回分析")
    if current_plan == "free":
        st.success("✅ 現在のプラン")

with plan_cols[1]:
    st.markdown("### ⭐ Pro")
    st.markdown("**¥980/月**")
    st.markdown("月50回分析 + 全機能")
    if current_plan == "pro":
        st.success("✅ 現在のプラン")
    else:
        st.link_button("⭐ Proに登録", "https://buy.stripe.com/test_aFa5kD3JK9mY3tYbRBa3u00", type="primary", use_container_width=True)

with plan_cols[2]:
    st.markdown("### 💎 Premium")
    st.markdown("**¥2,980/月**")
    st.markdown("無制限 + AI分析")
    if current_plan == "premium":
        st.success("✅ 現在のプラン")
    else:
        st.link_button("💎 Premiumに登録", "https://buy.stripe.com/test_eVq9ATbcc56I6Ga2h1a3u01", type="primary", use_container_width=True)

# 課金確認セクション
st.divider()
st.subheader("🔄 課金確認")
st.caption("Stripeで支払い完了後、メールアドレスを入力して確認ボタンを押してください")

confirm_email = st.text_input("Stripeで登録したメールアドレス", key="stripe_email")

if st.button("✅ 課金状態を確認", type="primary", key="btn_confirm_stripe"):
    if not confirm_email:
        st.error("メールアドレスを入力してください")
    elif not stripe.api_key:
        st.error("Stripe設定エラー。管理者にお問い合わせください。")
    else:
        with st.spinner("Stripeに問い合わせ中..."):
            try:
                # メールアドレスでStripe顧客を検索
                customers = stripe.Customer.list(email=confirm_email, limit=1)
                if not customers.data:
                    st.warning("このメールアドレスの課金情報が見つかりません。Stripeで使用したメールアドレスを確認してください。")
                else:
                    customer = customers.data[0]
                    # サブスクリプション確認
                    subs = stripe.Subscription.list(customer=customer.id, status="active", limit=10)

                    new_plan = "free"
                    for sub in subs.data:
                        for item in sub["items"]["data"]:
                            amount = item["price"]["unit_amount"]
                            if amount >= 2980:
                                new_plan = "premium"
                                break
                            elif amount >= 980:
                                new_plan = "pro"
                        if new_plan == "premium":
                            break

                    if new_plan != "free":
                        # プラン更新
                        import json
                        users_path = os.path.join(os.path.dirname(os.path.abspath(".")), "auth", "users.json")
                        if not os.path.exists(users_path):
                            users_path = "auth/users.json"
                        try:
                            with open(users_path, "r") as f:
                                users = json.load(f)
                            if username in users:
                                users[username]["plan"] = new_plan
                                users[username]["stripe_email"] = confirm_email
                                with open(users_path, "w") as f:
                                    json.dump(users, f, ensure_ascii=False, indent=2)
                        except:
                            pass

                        st.session_state["plan"] = new_plan
                        plan_name = "⭐ Pro" if new_plan == "pro" else "💎 Premium"
                        st.success(f"🎉 {plan_name}プランが有効になりました！")
                        st.balloons()
                    else:
                        st.warning("アクティブなサブスクリプションが見つかりません。支払いが完了しているか確認してください。")

            except Exception as e:
                st.error(f"確認中にエラーが発生しました: {str(e)}")

st.divider()
st.stop()
