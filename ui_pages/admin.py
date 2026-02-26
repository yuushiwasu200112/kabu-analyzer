st.title("🛡️ 管理者ダッシュボード")

import datetime
import json

# ユーザー情報取得
try:
    users_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth", "users.json")
    if not os.path.exists(users_path):
        users_path = "auth/users.json"
    with open(users_path, "r") as f:
        users = json.load(f)
except:
    users = {}

# DB統計
try:
    from data.database import get_scores_count, get_all_scores
    db_scores = get_scores_count()
except:
    db_scores = 0

# サマリーカード
st.subheader("📊 サービス概要")
ad1, ad2, ad3, ad4 = st.columns(4)
ad1.metric("総ユーザー数", f"{len(users)}人")
ad2.metric("分析済み銘柄", f"{db_scores}銘柄")

free_count = sum(1 for u in users.values() if u.get("plan", "free") == "free")
pro_count = sum(1 for u in users.values() if u.get("plan", "free") == "pro")
premium_count = sum(1 for u in users.values() if u.get("plan", "free") == "premium")
ad3.metric("有料ユーザー", f"{pro_count + premium_count}人")
ad4.metric("月間推定収益", f"¥{pro_count * 980 + premium_count * 2980:,}")

# プラン分布
st.divider()
st.subheader("📈 プラン分布")
plan_col1, plan_col2 = st.columns(2)
with plan_col1:
    import plotly.graph_objects as go
    fig = go.Figure(data=[go.Pie(
        labels=["Free", "Pro", "Premium"],
        values=[free_count, pro_count, premium_count],
        marker_colors=["#8899AA", "#F39C12", "#2E75B6"],
        hole=0.4,
    )])
    fig.update_layout(height=300, title="プラン別ユーザー数")
    st.plotly_chart(fig, use_container_width=True)

with plan_col2:
    st.markdown(f"""
| プラン | ユーザー数 | 割合 |
|--------|-----------|------|
| 🆓 Free | {free_count}人 | {free_count*100//max(len(users),1)}% |
| ⭐ Pro | {pro_count}人 | {pro_count*100//max(len(users),1)}% |
| 💎 Premium | {premium_count}人 | {premium_count*100//max(len(users),1)}% |
    """)

# ユーザー一覧
st.divider()
st.subheader("👥 ユーザー一覧")
if users:
    import pandas as pd
    user_rows = []
    for uname, udata in users.items():
        user_rows.append({
            "ユーザー名": uname,
            "メール": udata.get("email", ""),
            "プラン": udata.get("plan", "free"),
            "今月の利用": udata.get("monthly_usage", 0),
            "登録日": udata.get("created_at", "不明"),
        })
    df = pd.DataFrame(user_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

# スコア分布
st.divider()
st.subheader("📊 スコア分布")
try:
    scores = get_all_scores(limit=9999)
    if scores:
        import plotly.graph_objects as go
        score_vals = [s["total_score"] for s in scores]
        fig2 = go.Figure(data=[go.Histogram(
            x=score_vals, nbinsx=20,
            marker_color="#2E75B6",
        )])
        fig2.update_layout(height=350, xaxis_title="総合スコア", yaxis_title="銘柄数", xaxis_range=[0, 100])
        st.plotly_chart(fig2, use_container_width=True)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("平均スコア", f"{sum(score_vals)/len(score_vals):.1f}点")
        sc2.metric("最高スコア", f"{max(score_vals)}点")
        sc3.metric("最低スコア", f"{min(score_vals)}点")
        sc4.metric("中央値", f"{sorted(score_vals)[len(score_vals)//2]}点")
except:
    st.info("スコアデータがありません")

# DB管理
st.divider()
st.subheader("🗄️ DB管理")
db_col1, db_col2 = st.columns(2)
with db_col1:
    if st.button("🔄 スコアキャッシュをクリア", key="admin_clear_scores"):
        try:
            from data.database import get_connection
            conn = get_connection()
            conn.execute("DELETE FROM stock_scores")
            conn.commit()
            conn.close()
            st.success("✅ スコアキャッシュをクリアしました")
        except Exception as e:
            st.error(f"❌ {e}")
with db_col2:
    if st.button("🔄 全キャッシュクリア", key="admin_clear_cache"):
        st.cache_data.clear()
        st.success("✅ キャッシュをクリアしました")

st.divider()
st.stop()
