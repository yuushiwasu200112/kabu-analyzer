import streamlit as st
import os
import json
import datetime
from dotenv import load_dotenv

try:
    load_dotenv()
except:
    pass

st.set_page_config(page_title="Kabu Analyzer", page_icon="📊", layout="wide")

try:
    if 'EDINET_API_KEY' in st.secrets:
        os.environ['EDINET_API_KEY'] = st.secrets['EDINET_API_KEY']
except:
    pass

# ── EDINETコードマップ読み込み ──
CODE_MAP = {}
_try_paths = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'edinet_code_map.json'),
    os.path.join(os.getcwd(), 'config', 'edinet_code_map.json'),
]
for _try_path in _try_paths:
    if os.path.exists(_try_path):
        with open(_try_path, 'r', encoding='utf-8') as _f:
            CODE_MAP = json.load(_f)
        break

INDICATOR_FORMAT = {
    "ROE": ("%", "収益性"), "ROA": ("%", "収益性"),
    "営業利益率": ("%", "収益性"), "配当利回り": ("%", "収益性"),
    "自己資本比率": ("%", "安全性"), "流動比率": ("%", "安全性"),
    "有利子負債比率": ("%", "安全性"), "ICR": ("倍", "安全性"),
    "PER": ("倍", "割安度"), "PBR": ("倍", "割安度"),
    "EPS": ("円", "割安度"), "BPS": ("円", "割安度"),
    "売上高成長率": ("%", "成長性"), "営業利益成長率": ("%", "成長性"),
    "純利益成長率": ("%", "成長性"), "総資産成長率": ("%", "成長性"),
}

# ── 認証チェック ──
from auth.auth_manager import show_login_page, check_usage_limit, update_usage, PLANS

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    show_login_page()
    st.stop()

# ゲストの分析回数管理
if st.session_state.get("username") == "guest":
    if "guest_usage" not in st.session_state:
        st.session_state.guest_usage = 0

# ── カスタムCSS ──
st.markdown("""
<style>
    /* メインヘッダー */
    .main-header {
        background: linear-gradient(135deg, #1B3A5C 0%, #2E75B6 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        margin: 0;
    }
    .main-header p {
        color: #B8D4E8;
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
    }

    /* メトリックカード */
    [data-testid="stMetric"] {
        background: #1B2332;
        border: 1px solid #2E75B6;
        border-radius: 10px;
        padding: 15px;
    }
    [data-testid="stMetric"] label {
        color: #8899AA;
        font-size: 0.85rem;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-size: 1.8rem;
    }

    /* プログレスバー */
    .stProgress > div > div {
        background-color: #2E75B6;
        border-radius: 5px;
    }

    /* ボタン */
    .stButton > button {
        background: linear-gradient(135deg, #2E75B6, #1B3A5C);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3A8FD4, #2E75B6);
    }

    /* サイドバー */
    section[data-testid="stSidebar"] {
        background: #0A1628;
        border-right: 1px solid #1B2332;
    }

    /* データフレーム */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* 区切り線 */
    hr {
        border-color: #1B2332;
    }

    /* フッター非表示 */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── サイドバー ──
with st.sidebar:
    page = st.radio("📌 メニュー", ["銘柄分析", "複数社比較", "ランキング", "ウォッチリスト", "ポートフォリオ", "配当カレンダー", "アラート", "セクター分析", "バックテスト"], index=0)
    st.divider()
    st.header("⚙️ 分析設定")
    style = st.selectbox("投資スタイル", ["バランス", "バリュー投資", "グロース投資", "高配当投資", "安定性重視"])
    period = st.selectbox("投資期間", ["中期（1〜3年）", "短期（〜1年）", "長期（3年以上）"])
    st.divider()
    st.markdown(f"**📌 対応銘柄数: {len(CODE_MAP):,}社**")

    # ユーザー情報
    st.divider()
    username = st.session_state.get("username", "guest")
    user_info = st.session_state.get("user_info", {})
    plan_name = PLANS.get(user_info.get("plan", "free"), PLANS["free"])["name"]
    st.markdown(f"👤 **{username}** ({plan_name})")

    if username == "guest":
        g_usage = st.session_state.get("guest_usage", 0)
        st.caption(f"今月の分析: {g_usage}/5回")
        st.progress(min(g_usage / 5, 1.0))
    else:
        can_use, usage, limit = check_usage_limit(username)
        if limit == -1:
            st.caption(f"今月の分析: {usage}回（無制限）")
        else:
            st.caption(f"今月の分析: {usage}/{limit}回")
            st.progress(min(usage / limit, 1.0))

    if st.button("🚪 ログアウト"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_info = None
        st.rerun()

# ── 共通関数 ──
def search_yuho(edinet_code, api_key):
    import requests, datetime
    url = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
    found = []
    today = datetime.date.today()
    for year in range(today.year, today.year - 5, -1):
        for month in [6, 7, 3, 4, 5, 8, 9]:
            for day in range(15, 31):
                try:
                    d = datetime.date(year, month, day)
                    if d > today: continue
                    resp = requests.get(url, params={
                        "date": f"{year}-{month:02d}-{day:02d}",
                        "type": 2, "Subscription-Key": api_key,
                    }, timeout=30)
                    for doc in resp.json().get("results", []):
                        if doc.get("edinetCode") == edinet_code and doc.get("docTypeCode") == "120":
                            if doc["docID"] not in [x["docID"] for x in found]:
                                found.append({"docID": doc["docID"], "periodEnd": doc.get("periodEnd", ""), "docDescription": doc.get("docDescription", "")})
                except:
                    continue
            if any(str(year) in x.get("periodEnd", "") for x in found):
                break
        if len(found) >= 4:
            break
    found.sort(key=lambda x: x.get("periodEnd", ""), reverse=True)
    return found[:4]

def analyze_company(code, api_key):
    from data_sources.stock_client import get_stock_info
    from data_sources.cache_manager import get_cache, set_cache
    from parsers.xbrl_parser import download_and_parse
    from analysis.indicators import calc_indicators, calc_growth
    from analysis.scoring import calc_total_score

    company = CODE_MAP[code]
    edinet_code = company["edinet_code"]

    stock_info = get_stock_info(code)
    price = stock_info["current_price"] if stock_info else 0

    cache_key_docs = f"docs_{edinet_code}"
    docs = get_cache(cache_key_docs, max_age_hours=168)
    if not docs:
        docs = search_yuho(edinet_code, api_key)
        if docs: set_cache(cache_key_docs, docs)

    if not docs: return None

    cache_cur = f"xbrl_{docs[0]['docID']}"
    current = get_cache(cache_cur)
    if not current:
        current = download_and_parse(docs[0]["docID"], api_key)
        if current: set_cache(cache_cur, current)

    previous = None
    if len(docs) > 1:
        cache_prev = f"xbrl_{docs[1]['docID']}"
        previous = get_cache(cache_prev)
        if not previous:
            previous = download_and_parse(docs[1]["docID"], api_key)
            if previous: set_cache(cache_prev, previous)

    if not current: return None

    indicators = calc_indicators(current, price)
    if previous:
        indicators.update(calc_growth(current, previous))

    period_map = {"短期（〜1年）": "短期", "中期（1〜3年）": "中期", "長期（3年以上）": "長期"}
    score_result = calc_total_score(indicators, style, period_map.get(period, "中期"))

    return {"name": company["name"], "stock_info": stock_info, "current": current,
            "previous": previous, "indicators": indicators, "score": score_result,
            "docs": docs, "price": price}

# ========================================
# 複数社比較ページ
# ========================================
if page == "複数社比較":
    st.title("⚖️ 複数社比較")
    st.caption(f"最大3社まで並べて比較できます（対応: {len(CODE_MAP):,}社）")

    cols_input = st.columns(3)
    codes = []
    for i in range(3):
        with cols_input[i]:
            code = st.text_input(f"銘柄{i+1}", max_chars=4, key=f"cmp_{i}", placeholder="証券コード")
            if code and len(code) == 4 and code.isdigit() and code in CODE_MAP:
                codes.append(code)
                st.caption(f"✅ {CODE_MAP[code]['name']}")
            elif code and len(code) == 4:
                st.caption("❌ 未対応")

    if len(codes) >= 2:
        if st.button("🔍 比較分析を実行", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")
            results = {}
            for code in codes:
                with st.spinner(f"{CODE_MAP[code]['name']} を分析中..."):
                    r = analyze_company(code, API_KEY)
                    if r: results[code] = r

            if len(results) >= 2:
                st.divider()
                st.subheader("🏆 総合スコア比較")
                score_cols = st.columns(len(results))
                for i, (code, data) in enumerate(results.items()):
                    with score_cols[i]:
                        s = data["score"]["total_score"]
                        color = "🟢" if s >= 75 else "🟡" if s >= 50 else "🔴"
                        st.metric(data["name"], f"{color} {s}点")

                st.subheader("📊 カテゴリ別スコア比較")
                fig_radar = go.Figure()
                radar_colors = ["#2E75B6", "#E74C3C", "#2ECC71"]
                for i, (code, data) in enumerate(results.items()):
                    cats = list(data["score"]["category_scores"].keys())
                    vals = list(data["score"]["category_scores"].values())
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=cats + [cats[0]],
                        fill="toself", name=data["name"], line_color=radar_colors[i % 3]))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                        height=450, legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_radar, use_container_width=True)

                for cat in ["収益性", "安全性", "成長性", "割安度"]:
                    st.markdown(f"**{cat}**")
                    bar_cols = st.columns(len(results))
                    for i, (code, data) in enumerate(results.items()):
                        with bar_cols[i]:
                            val = data["score"]["category_scores"].get(cat, 0)
                            st.progress(val / 100, text=f"{data['name']}: {val}点")

                st.divider()
                st.subheader("📋 主要指標比較")
                metrics = ["ROE", "ROA", "営業利益率", "自己資本比率", "PER", "PBR",
                           "配当利回り", "売上高成長率", "営業利益成長率", "純利益成長率"]
                table = {}
                for code, data in results.items():
                    table[data["name"]] = {m: f"{data['indicators'].get(m, 0):.2f}" if data['indicators'].get(m) is not None else "---" for m in metrics}
                st.dataframe(pd.DataFrame(table), use_container_width=True)
    elif len(codes) == 1:
        st.info("📌 2社以上入力してください")
    else:
        st.info("📌 比較したい銘柄の証券コードを2〜3社分入力してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# ランキングページ
# ========================================
if page == "ランキング":
    st.title("🏆 銘柄ランキング")
    st.caption(f"投資スタイル: {style} ｜ 投資期間: {period}")

    # 主要銘柄リスト読み込み
    major_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'major_stocks.json')
    if not os.path.exists(major_path):
        major_path = os.path.join(os.getcwd(), 'config', 'major_stocks.json')
    major_stocks = {}
    if os.path.exists(major_path):
        with open(major_path, 'r', encoding='utf-8') as f:
            major_stocks = json.load(f)

    rank_col1, rank_col2 = st.columns(2)
    with rank_col1:
        rank_count = st.selectbox("分析銘柄数", ["上位30銘柄（速い）", "上位50銘柄", "全100銘柄（時間かかる）"], index=0)
    with rank_col2:
        sort_by = st.selectbox("並び替え基準", ["総合スコア", "収益性", "安全性", "成長性", "割安度"], index=0)

    count_map = {"上位30銘柄（速い）": 30, "上位50銘柄": 50, "全100銘柄（時間かかる）": 100}
    max_count = count_map[rank_count]
    target_stocks = dict(list(major_stocks.items())[:max_count])

    st.markdown(f"**対象: {len(target_stocks)}銘柄**")

    if st.button("🔍 ランキングを生成", type="primary"):
        API_KEY = os.getenv("EDINET_API_KEY")
        rankings = []
        progress = st.progress(0, text="分析中...")
        total = len(target_stocks)

        for idx, (code, name) in enumerate(target_stocks.items()):
            progress.progress((idx + 1) / total, text=f"{name}（{code}）を分析中... ({idx+1}/{total})")
            if code not in CODE_MAP:
                continue
            try:
                r = analyze_company(code, API_KEY)
                if r:
                    rankings.append({
                        "code": code,
                        "name": r["name"],
                        "total": r["score"]["total_score"],
                        "profitability": r["score"]["category_scores"].get("収益性", 0),
                        "safety": r["score"]["category_scores"].get("安全性", 0),
                        "growth": r["score"]["category_scores"].get("成長性", 0),
                        "value": r["score"]["category_scores"].get("割安度", 0),
                        "roe": r["indicators"].get("ROE", 0),
                        "per": r["indicators"].get("PER", 0),
                        "dividend": r["indicators"].get("配当利回り", 0),
                    })
            except:
                continue

        progress.empty()

        if rankings:
            import pandas as pd
            import plotly.graph_objects as go

            # ソート基準に応じて並び替え
            sort_key_map = {"総合スコア": "total", "収益性": "profitability", "安全性": "safety", "成長性": "growth", "割安度": "value"}
            sort_k = sort_key_map.get(sort_by, "total")
            rankings.sort(key=lambda x: x[sort_k], reverse=True)

            # 上位表示
            st.subheader("🥇 総合スコア TOP10")
            for i, r in enumerate(rankings[:10]):
                score = r["total"]
                color = "🟢" if score >= 75 else "🟡" if score >= 50 else "🔴"
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}位"
                st.markdown(f"{medal} **{r['name']}**（{r['code']}）: {color} **{score}点** ｜ 収益性{r['profitability']} / 安全性{r['safety']} / 成長性{r['growth']} / 割安度{r['value']}")

            st.divider()

            # 全銘柄テーブル
            st.subheader("📊 全銘柄スコア一覧")
            df = pd.DataFrame(rankings)
            df.columns = ["証券コード", "企業名", "総合スコア", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"]
            df["順位"] = range(1, len(df) + 1)
            df = df[["順位", "証券コード", "企業名", "総合スコア", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"]]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # カテゴリ別TOP5
            st.divider()
            cat_cols = st.columns(4)
            categories_rank = [
                ("収益性", "profitability"),
                ("安全性", "safety"),
                ("成長性", "growth"),
                ("割安度", "value"),
            ]
            for i, (cat_name, cat_key) in enumerate(categories_rank):
                with cat_cols[i]:
                    st.markdown(f"**{cat_name} TOP5**")
                    sorted_cat = sorted(rankings, key=lambda x: x[cat_key], reverse=True)
                    for j, r in enumerate(sorted_cat[:5]):
                        st.caption(f"{j+1}. {r['name']} ({r[cat_key]}点)")

            # バーチャート
            st.divider()
            st.subheader("📈 スコア分布")
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=[r["name"][:6] for r in rankings[:15]],
                    y=[r["total"] for r in rankings[:15]],
                    marker_color=["#27AE60" if r["total"] >= 75 else "#F39C12" if r["total"] >= 50 else "#E74C3C" for r in rankings[:15]],
                )
            ])
            fig_bar.update_layout(height=400, xaxis_title="銘柄", yaxis_title="総合スコア", yaxis_range=[0, 100])
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.error("❌ ランキングデータを取得できませんでした")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# ウォッチリストページ
# ========================================
if page == "ウォッチリスト":
    st.title("⭐ ウォッチリスト")
    st.caption("お気に入り銘柄を管理できます")

    # セッション初期化
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    # 銘柄追加
    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_code = st.text_input("銘柄を追加（証券コード）", max_chars=4, key="wl_add", placeholder="例: 7203")
    with add_col2:
        st.write("")
        st.write("")
        if st.button("➕ 追加", type="primary"):
            if new_code and len(new_code) == 4 and new_code.isdigit() and new_code in CODE_MAP:
                if new_code not in st.session_state.watchlist:
                    st.session_state.watchlist.append(new_code)
                    st.success(f"✅ {CODE_MAP[new_code]['name']} を追加しました")
                else:
                    st.info("既に追加済みです")
            elif new_code:
                st.error("❌ 未対応の証券コードです")

    # ウォッチリスト表示
    if st.session_state.watchlist:
        st.divider()

        # 一括分析ボタン
        if st.button("📊 ウォッチリストを一括分析", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")
            results = []
            progress = st.progress(0, text="分析中...")

            for idx, code in enumerate(st.session_state.watchlist):
                name = CODE_MAP[code]["name"]
                progress.progress((idx + 1) / len(st.session_state.watchlist), text=f"{name} を分析中...")
                try:
                    r = analyze_company(code, API_KEY)
                    if r:
                        results.append({
                            "code": code,
                            "name": r["name"],
                            "total": r["score"]["total_score"],
                            "profitability": r["score"]["category_scores"].get("収益性", 0),
                            "safety": r["score"]["category_scores"].get("安全性", 0),
                            "growth": r["score"]["category_scores"].get("成長性", 0),
                            "value": r["score"]["category_scores"].get("割安度", 0),
                            "roe": r["indicators"].get("ROE", 0),
                            "per": r["indicators"].get("PER", 0),
                            "dividend": r["indicators"].get("配当利回り", 0),
                        })
                except:
                    continue

            progress.empty()

            if results:
                results.sort(key=lambda x: x["total"], reverse=True)

                # レーダーチャート重ね合わせ
                st.subheader("📊 ウォッチリスト比較")
                fig_radar = go.Figure()
                colors = ["#2E75B6", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB"]
                for i, r in enumerate(results):
                    cats = ["収益性", "安全性", "成長性", "割安度"]
                    vals = [r["profitability"], r["safety"], r["growth"], r["value"]]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=cats + [cats[0]],
                        fill="toself", name=f"{r['name'][:8]} ({r['total']}点)",
                        line_color=colors[i % len(colors)],
                    ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(fig_radar, use_container_width=True)

                # スコアテーブル
                st.subheader("📋 スコア一覧")
                df = pd.DataFrame(results)
                df.columns = ["証券コード", "企業名", "総合", "収益性", "安全性", "成長性", "割安度", "ROE", "PER", "配当利回り"]
                st.dataframe(df, use_container_width=True, hide_index=True)

        # 銘柄リスト（削除ボタン付き）
        st.divider()
        st.subheader("📌 登録銘柄")
        for code in st.session_state.watchlist:
            wl_col1, wl_col2, wl_col3 = st.columns([1, 3, 1])
            with wl_col1:
                st.markdown(f"**{code}**")
            with wl_col2:
                st.markdown(CODE_MAP[code]["name"])
            with wl_col3:
                if st.button("🗑️", key=f"del_{code}"):
                    st.session_state.watchlist.remove(code)
                    st.rerun()

        # 全削除
        if st.button("🗑️ ウォッチリストをクリア"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.info("📌 証券コードを入力してウォッチリストに追加してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# ポートフォリオ分析ページ
# ========================================
if page == "ポートフォリオ":
    st.title("💼 ポートフォリオ分析")
    st.caption("保有銘柄のバランスとリスク分散をチェック")

    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

    # 銘柄追加
    pf_col1, pf_col2, pf_col3 = st.columns([2, 2, 1])
    with pf_col1:
        pf_code = st.text_input("証券コード", max_chars=4, key="pf_code", placeholder="例: 7203")
    with pf_col2:
        pf_amount = st.number_input("投資金額（万円）", min_value=1, value=100, step=10, key="pf_amount")
    with pf_col3:
        st.write("")
        st.write("")
        if st.button("➕ 追加", key="pf_add", type="primary"):
            if pf_code and len(pf_code) == 4 and pf_code in CODE_MAP:
                existing = [p for p in st.session_state.portfolio if p["code"] == pf_code]
                if existing:
                    existing[0]["amount"] += pf_amount
                    st.success(f"✅ {CODE_MAP[pf_code]['name']} の投資額を更新")
                else:
                    st.session_state.portfolio.append({"code": pf_code, "name": CODE_MAP[pf_code]["name"], "amount": pf_amount})
                    st.success(f"✅ {CODE_MAP[pf_code]['name']} を追加")
            elif pf_code:
                st.error("❌ 未対応の証券コードです")

    if st.session_state.portfolio:
        st.divider()
        total_amount = sum(p["amount"] for p in st.session_state.portfolio)
        st.markdown(f"**総投資額: {total_amount:,}万円 ｜ {len(st.session_state.portfolio)}銘柄**")

        # 保有銘柄一覧
        st.subheader("📌 保有銘柄")
        for i, p in enumerate(st.session_state.portfolio):
            pc1, pc2, pc3, pc4 = st.columns([2, 2, 2, 1])
            with pc1:
                st.markdown(f"**{p['code']}** {p['name'][:10]}")
            with pc2:
                st.markdown(f"{p['amount']:,}万円")
            with pc3:
                ratio = p['amount'] / total_amount * 100
                st.markdown(f"構成比: {ratio:.1f}%")
            with pc4:
                if st.button("🗑️", key=f"pf_del_{i}"):
                    st.session_state.portfolio.pop(i)
                    st.rerun()

        # 分析実行
        if st.button("📊 ポートフォリオを分析", type="primary"):
            import plotly.graph_objects as go
            import pandas as pd
            API_KEY = os.getenv("EDINET_API_KEY")

            results = []
            progress = st.progress(0, text="分析中...")
            for idx, p in enumerate(st.session_state.portfolio):
                progress.progress((idx + 1) / len(st.session_state.portfolio), text=f"{p['name']} を分析中...")
                try:
                    r = analyze_company(p["code"], API_KEY)
                    if r:
                        results.append({
                            "code": p["code"], "name": p["name"], "amount": p["amount"],
                            "ratio": p["amount"] / total_amount * 100,
                            "total": r["score"]["total_score"],
                            "profitability": r["score"]["category_scores"].get("収益性", 0),
                            "safety": r["score"]["category_scores"].get("安全性", 0),
                            "growth": r["score"]["category_scores"].get("成長性", 0),
                            "value": r["score"]["category_scores"].get("割安度", 0),
                            "roe": r["indicators"].get("ROE", 0),
                            "dividend": r["indicators"].get("配当利回り", 0),
                        })
                except:
                    continue
            progress.empty()

            if results:
                st.divider()

                # ポートフォリオ総合スコア（加重平均）
                weighted_score = sum(r["total"] * r["ratio"] / 100 for r in results)
                weighted_prof = sum(r["profitability"] * r["ratio"] / 100 for r in results)
                weighted_safe = sum(r["safety"] * r["ratio"] / 100 for r in results)
                weighted_grow = sum(r["growth"] * r["ratio"] / 100 for r in results)
                weighted_val = sum(r["value"] * r["ratio"] / 100 for r in results)

                sc = "🟢" if weighted_score >= 75 else "🟡" if weighted_score >= 50 else "🔴"
                st.subheader(f"{sc} ポートフォリオ総合スコア: {weighted_score:.0f}点")

                pf_score_cols = st.columns(4)
                pf_score_cols[0].metric("収益性", f"{weighted_prof:.0f}点")
                pf_score_cols[1].metric("安全性", f"{weighted_safe:.0f}点")
                pf_score_cols[2].metric("成長性", f"{weighted_grow:.0f}点")
                pf_score_cols[3].metric("割安度", f"{weighted_val:.0f}点")

                # 構成比 円グラフ
                st.divider()
                pie_col, radar_col = st.columns(2)

                with pie_col:
                    st.subheader("🥧 構成比")
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=[r["name"][:8] for r in results],
                        values=[r["amount"] for r in results],
                        hole=0.4,
                        marker=dict(colors=["#2E75B6", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB"]),
                    )])
                    fig_pie.update_layout(height=400)
                    st.plotly_chart(fig_pie, use_container_width=True)

                with radar_col:
                    st.subheader("📊 ポートフォリオバランス")
                    fig_pf_radar = go.Figure()
                    fig_pf_radar.add_trace(go.Scatterpolar(
                        r=[weighted_prof, weighted_safe, weighted_grow, weighted_val, weighted_prof],
                        theta=["収益性", "安全性", "成長性", "割安度", "収益性"],
                        fill="toself", name="ポートフォリオ", line_color="#2E75B6",
                    ))
                    fig_pf_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400)
                    st.plotly_chart(fig_pf_radar, use_container_width=True)

                # リスク分散チェック
                st.divider()
                st.subheader("⚠️ リスク分散チェック")
                max_ratio = max(r["ratio"] for r in results)
                if max_ratio > 50:
                    st.error(f"🔴 **集中リスク**: 1銘柄に{max_ratio:.0f}%集中しています。30%以下に分散を推奨します。")
                elif max_ratio > 30:
                    st.warning(f"🟡 **やや集中**: 最大構成比が{max_ratio:.0f}%です。もう少し分散すると安心です。")
                else:
                    st.success(f"🟢 **分散良好**: 最大構成比は{max_ratio:.0f}%で適切に分散されています。")

                if len(results) < 3:
                    st.warning("🟡 **銘柄数不足**: 3銘柄以上に分散することをお勧めします。")
                elif len(results) < 5:
                    st.info("📌 5銘柄以上に分散するとさらにリスク低減効果が高まります。")
                else:
                    st.success(f"🟢 **銘柄数適切**: {len(results)}銘柄に分散されています。")

                avg_safety = weighted_safe
                if avg_safety < 50:
                    st.warning(f"🟡 **安全性に注意**: ポートフォリオ全体の安全性スコアが{avg_safety:.0f}点です。")

                # 銘柄別スコアテーブル
                st.divider()
                st.subheader("📋 銘柄別スコア")
                df = pd.DataFrame(results)
                df = df[["code", "name", "amount", "ratio", "total", "profitability", "safety", "growth", "value", "roe", "dividend"]]
                df.columns = ["コード", "企業名", "金額(万)", "構成比%", "総合", "収益性", "安全性", "成長性", "割安度", "ROE", "配当利回り"]
                df["構成比%"] = df["構成比%"].round(1)
                st.dataframe(df, use_container_width=True, hide_index=True)

        # クリアボタン
        if st.button("🗑️ ポートフォリオをクリア", key="pf_clear"):
            st.session_state.portfolio = []
            st.rerun()
    else:
        st.info("📌 証券コードと投資金額を入力してポートフォリオを構築してください")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# 配当カレンダーページ
# ========================================
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
if page == "アラート":
    st.title("🔔 アラート設定")
    st.caption("銘柄の条件を設定して、条件達成時に通知を受け取れます")

    # セッション初期化
    if "alerts" not in st.session_state:
        st.session_state.alerts = []
    if "alert_history" not in st.session_state:
        st.session_state.alert_history = []

    # アラート追加
    st.subheader("➕ 新しいアラートを作成")
    al_col1, al_col2, al_col3, al_col4 = st.columns([2, 2, 2, 1])
    with al_col1:
        al_code = st.text_input("証券コード", max_chars=4, key="al_code", placeholder="例: 7203")
    with al_col2:
        al_type = st.selectbox("条件タイプ", [
            "総合スコアが○点以上", "総合スコアが○点以下",
            "収益性が○点以上", "安全性が○点以上",
            "成長性が○点以上", "割安度が○点以上",
            "ROEが○%以上", "PERが○倍以下",
            "配当利回りが○%以上",
        ], key="al_type")
    with al_col3:
        al_value = st.number_input("しきい値", min_value=0.0, value=70.0, step=5.0, key="al_value")
    with al_col4:
        st.write("")
        st.write("")
        if st.button("🔔 追加", type="primary", key="al_add"):
            if al_code and len(al_code) == 4 and al_code in CODE_MAP:
                alert = {
                    "code": al_code,
                    "name": CODE_MAP[al_code]["name"],
                    "type": al_type,
                    "value": al_value,
                    "active": True,
                    "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M") if "datetime" in dir() else "now",
                }
                st.session_state.alerts.append(alert)
                st.success(f"✅ {CODE_MAP[al_code]['name']} のアラートを設定しました")
            elif al_code:
                st.error("❌ 未対応の証券コードです")

    # アラート一覧
    if st.session_state.alerts:
        st.divider()
        st.subheader("📋 設定中のアラート")

        for i, alert in enumerate(st.session_state.alerts):
            acol1, acol2, acol3, acol4 = st.columns([2, 3, 2, 1])
            with acol1:
                status = "🟢" if alert["active"] else "⏸️"
                st.markdown(f"{status} **{alert['code']}** {alert['name'][:8]}")
            with acol2:
                st.markdown(f"{alert['type']}（{alert['value']}）")
            with acol3:
                if alert["active"]:
                    if st.button("⏸️ 停止", key=f"al_pause_{i}"):
                        st.session_state.alerts[i]["active"] = False
                        st.rerun()
                else:
                    if st.button("▶️ 再開", key=f"al_resume_{i}"):
                        st.session_state.alerts[i]["active"] = True
                        st.rerun()
            with acol4:
                if st.button("🗑️", key=f"al_del_{i}"):
                    st.session_state.alerts.pop(i)
                    st.rerun()

        # アラートチェック実行
        st.divider()
        if st.button("🔍 アラートを今すぐチェック", type="primary"):
            API_KEY = os.getenv("EDINET_API_KEY")
            active_alerts = [a for a in st.session_state.alerts if a["active"]]
            triggered = []

            progress = st.progress(0, text="チェック中...")
            codes_to_check = list(set(a["code"] for a in active_alerts))
            results_cache = {}

            for idx, code in enumerate(codes_to_check):
                progress.progress((idx + 1) / len(codes_to_check), text=f"{CODE_MAP[code]['name']} をチェック中...")
                try:
                    r = analyze_company(code, API_KEY)
                    if r:
                        results_cache[code] = r
                except:
                    continue
            progress.empty()

            for alert in active_alerts:
                r = results_cache.get(alert["code"])
                if not r:
                    continue

                score = r["score"]["total_score"]
                cats = r["score"]["category_scores"]
                inds = r["indicators"]
                val = alert["value"]
                met = False
                actual = 0

                if "総合スコアが" in alert["type"] and "以上" in alert["type"]:
                    met = score >= val
                    actual = score
                elif "総合スコアが" in alert["type"] and "以下" in alert["type"]:
                    met = score <= val
                    actual = score
                elif "収益性が" in alert["type"]:
                    actual = cats.get("収益性", 0)
                    met = actual >= val
                elif "安全性が" in alert["type"]:
                    actual = cats.get("安全性", 0)
                    met = actual >= val
                elif "成長性が" in alert["type"]:
                    actual = cats.get("成長性", 0)
                    met = actual >= val
                elif "割安度が" in alert["type"]:
                    actual = cats.get("割安度", 0)
                    met = actual >= val
                elif "ROEが" in alert["type"]:
                    actual = inds.get("ROE", 0)
                    met = actual >= val
                elif "PERが" in alert["type"] and "以下" in alert["type"]:
                    actual = inds.get("PER", 999)
                    met = actual <= val and actual > 0
                elif "配当利回りが" in alert["type"]:
                    actual = inds.get("配当利回り", 0)
                    met = actual >= val

                if met:
                    triggered.append({
                        "code": alert["code"],
                        "name": alert["name"],
                        "type": alert["type"],
                        "threshold": val,
                        "actual": actual,
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M") if "datetime" in dir() else "now",
                    })

            if triggered:
                st.subheader("🚨 アラート発動！")
                for t in triggered:
                    st.success(f"🔔 **{t['name']}（{t['code']}）**: {t['type']}（設定値: {t['threshold']} → 実績値: {t['actual']:.2f}）")
                    st.session_state.alert_history.append(t)
            else:
                st.info("📌 条件を満たすアラートはありませんでした")

    # アラート履歴
    if st.session_state.alert_history:
        st.divider()
        st.subheader("📜 アラート履歴")
        for h in reversed(st.session_state.alert_history[-10:]):
            st.caption(f"🔔 {h.get('time','')} | {h['name']}（{h['code']}）: {h['type']} → {h['actual']:.2f}")

    if not st.session_state.alerts:
        st.info("📌 アラートを設定すると、条件達成時に通知を受け取れます")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# セクター分析ページ
# ========================================
if page == "セクター分析":
    st.title("🏭 セクター分析")
    st.caption("業種別の投資魅力度を比較")

    SECTORS = {
        "自動車": ["7203","7267","7269","7270","7201","7202","7211","6902"],
        "電機・精密": ["6758","6501","6503","6752","6971","6981","6762","6594","6645","6504","7751","7741","7733","7735","7752"],
        "半導体": ["8035","6920","6857","6723"],
        "商社": ["8058","8001","8031","8053","8002"],
        "銀行・金融": ["8306","8316","8411","8591","8601","8604"],
        "保険": ["8766","8750","8630","8725"],
        "不動産": ["8801","8802"],
        "通信": ["9432","9433","9434"],
        "医薬品": ["4502","4519","4523","4568","4507","4578"],
        "食品・日用品": ["2801","2802","2502","2503","4452","2914","4911"],
        "化学・素材": ["4063","4901","5108","5401","5713","5802","3861"],
        "機械": ["6301","6273","6367","6954","7011"],
        "サービス・IT": ["6098","9983","3382","4661","3659","4689","7974"],
        "運輸": ["9020","9022","9101","9104","9201","9202","9001","9005","9009","9064"],
        "エネルギー": ["9501","9503","9531"],
    }

    # セクター選択
    selected_sectors = st.multiselect("分析するセクターを選択", list(SECTORS.keys()), default=list(SECTORS.keys())[:5])

    if selected_sectors and st.button("🔍 セクター分析を実行", type="primary"):
        import plotly.graph_objects as go
        import pandas as pd
        API_KEY = os.getenv("EDINET_API_KEY")

        sector_results = {}
        all_stocks = []
        total_stocks = sum(len(SECTORS[s]) for s in selected_sectors)
        progress = st.progress(0, text="分析中...")
        done = 0

        for sector in selected_sectors:
            sector_scores = []
            for code in SECTORS[sector]:
                done += 1
                if code not in CODE_MAP:
                    continue
                progress.progress(done / total_stocks, text=f"{sector} - {CODE_MAP[code]['name']} を分析中...")
                try:
                    r = analyze_company(code, API_KEY)
                    if r:
                        stock_data = {
                            "sector": sector, "code": code, "name": r["name"][:10],
                            "total": r["score"]["total_score"],
                            "profitability": r["score"]["category_scores"].get("収益性", 0),
                            "safety": r["score"]["category_scores"].get("安全性", 0),
                            "growth": r["score"]["category_scores"].get("成長性", 0),
                            "value": r["score"]["category_scores"].get("割安度", 0),
                        }
                        sector_scores.append(stock_data)
                        all_stocks.append(stock_data)
                except:
                    continue

            if sector_scores:
                avg_total = sum(s["total"] for s in sector_scores) / len(sector_scores)
                avg_prof = sum(s["profitability"] for s in sector_scores) / len(sector_scores)
                avg_safe = sum(s["safety"] for s in sector_scores) / len(sector_scores)
                avg_grow = sum(s["growth"] for s in sector_scores) / len(sector_scores)
                avg_val = sum(s["value"] for s in sector_scores) / len(sector_scores)
                sector_results[sector] = {
                    "avg_total": avg_total, "avg_prof": avg_prof, "avg_safe": avg_safe,
                    "avg_grow": avg_grow, "avg_val": avg_val, "count": len(sector_scores),
                    "stocks": sector_scores,
                }
        progress.empty()

        if sector_results:
            # セクター別総合スコアランキング
            st.divider()
            st.subheader("🏆 セクター別総合スコア")
            sorted_sectors = sorted(sector_results.items(), key=lambda x: x[1]["avg_total"], reverse=True)

            fig_sector = go.Figure(data=[go.Bar(
                x=[s[0] for s in sorted_sectors],
                y=[s[1]["avg_total"] for s in sorted_sectors],
                marker_color=["#27AE60" if s[1]["avg_total"] >= 75 else "#F39C12" if s[1]["avg_total"] >= 60 else "#E74C3C" for s in sorted_sectors],
                text=[f"{s[1]['avg_total']:.0f}点" for s in sorted_sectors],
                textposition="outside",
            )])
            fig_sector.update_layout(height=400, yaxis_range=[0, 100], xaxis_title="セクター", yaxis_title="平均スコア")
            st.plotly_chart(fig_sector, use_container_width=True)

            # セクター別レーダーチャート
            st.subheader("📊 セクター別カテゴリ比較")
            fig_radar = go.Figure()
            colors = ["#2E75B6","#E74C3C","#2ECC71","#F39C12","#9B59B6","#1ABC9C","#E67E22","#3498DB"]
            for i, (sector, data) in enumerate(sorted_sectors):
                cats = ["収益性","安全性","成長性","割安度"]
                vals = [data["avg_prof"], data["avg_safe"], data["avg_grow"], data["avg_val"]]
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=cats + [cats[0]],
                    fill="toself", name=f"{sector}({data['avg_total']:.0f}点)",
                    line_color=colors[i % len(colors)],
                ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_radar, use_container_width=True)

            # セクター詳細テーブル
            st.divider()
            st.subheader("📋 セクター別詳細")
            sector_table = []
            for sector, data in sorted_sectors:
                sector_table.append({
                    "セクター": sector, "銘柄数": data["count"],
                    "総合": f"{data['avg_total']:.0f}", "収益性": f"{data['avg_prof']:.0f}",
                    "安全性": f"{data['avg_safe']:.0f}", "成長性": f"{data['avg_grow']:.0f}",
                    "割安度": f"{data['avg_val']:.0f}",
                })
            st.dataframe(pd.DataFrame(sector_table), use_container_width=True, hide_index=True)

            # セクター内銘柄ランキング
            st.divider()
            st.subheader("🔍 セクター内銘柄ランキング")
            selected_detail = st.selectbox("セクターを選択", [s[0] for s in sorted_sectors])
            if selected_detail and selected_detail in sector_results:
                stocks = sorted(sector_results[selected_detail]["stocks"], key=lambda x: x["total"], reverse=True)
                for i, s in enumerate(stocks):
                    color = "🟢" if s["total"] >= 75 else "🟡" if s["total"] >= 50 else "🔴"
                    medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}位"
                    st.markdown(f"{medal} **{s['name']}**（{s['code']}）: {color} **{s['total']}点** ｜ 収益{s['profitability']} / 安全{s['safety']} / 成長{s['growth']} / 割安{s['value']}")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。")
    st.stop()

# ========================================
# バックテストページ
# ========================================
if page == "バックテスト":
    st.title("🔬 バックテスト")
    st.caption("過去のスコア推移と株価パフォーマンスを検証")

    bt_code = st.text_input("証券コードを入力", max_chars=4, key="bt_code", placeholder="例: 7203")

    if bt_code and len(bt_code) == 4 and bt_code.isdigit() and bt_code in CODE_MAP:
        company = CODE_MAP[bt_code]
        st.success(f"✅ {company['name']}（{bt_code}）")

        if st.button("🔍 バックテスト実行", type="primary"):
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import pandas as pd
            from parsers.xbrl_parser import download_and_parse
            from analysis.indicators import calc_indicators, calc_growth
            from analysis.scoring import calc_total_score
            from data_sources.cache_manager import get_cache, set_cache

            API_KEY = os.getenv("EDINET_API_KEY")
            edinet_code = company["edinet_code"]

            with st.spinner("過去の有報を検索中..."):
                docs = get_cache(f"docs_{edinet_code}", max_age_hours=168)
                if not docs:
                    docs = search_yuho(edinet_code, API_KEY)
                    if docs: set_cache(f"docs_{edinet_code}", docs)

            if not docs or len(docs) < 2:
                st.error("❌ バックテストには2年以上のデータが必要です")
            else:
                st.info(f"📊 {len(docs)}期分のデータを分析中...")

                # 各年度のデータを取得
                yearly_data = {}
                progress = st.progress(0, text="分析中...")
                for i, doc in enumerate(docs):
                    progress.progress((i+1)/len(docs), text=f"{doc['periodEnd'][:4]}年度を分析中...")
                    ck = f"xbrl_{doc['docID']}"
                    xbrl = get_cache(ck)
                    if not xbrl:
                        xbrl = download_and_parse(doc["docID"], API_KEY)
                        if xbrl: set_cache(ck, xbrl)
                    if xbrl:
                        yearly_data[doc["periodEnd"][:4]] = {"xbrl": xbrl, "doc": doc}
                progress.empty()

                if len(yearly_data) < 2:
                    st.error("❌ 十分なデータを取得できませんでした")
                else:
                    years = sorted(yearly_data.keys())
                    scores_by_year = {}
                    indicators_by_year = {}

                    for i, year in enumerate(years):
                        xbrl = yearly_data[year]["xbrl"]
                        ind = calc_indicators(xbrl, 0)

                        if i > 0:
                            prev_xbrl = yearly_data[years[i-1]]["xbrl"]
                            growth = calc_growth(xbrl, prev_xbrl)
                            ind.update(growth)

                        score = calc_total_score(ind, style, "中期")
                        scores_by_year[year] = score
                        indicators_by_year[year] = ind

                    # 株価データ取得
                    st.divider()
                    stock_prices = {}
                    try:
                        import yfinance as yf, time
                        time.sleep(1)
                        ticker = yf.Ticker(f"{bt_code}.T")
                        hist = ticker.history(period="5y")
                        if not hist.empty:
                            for year in years:
                                year_data = hist[hist.index.year == int(year)]
                                if not year_data.empty:
                                    stock_prices[year] = {
                                        "start": year_data.iloc[0]["Close"],
                                        "end": year_data.iloc[-1]["Close"],
                                        "high": year_data["High"].max(),
                                        "low": year_data["Low"].min(),
                                    }
                    except:
                        pass

                    # スコア推移チャート
                    st.subheader("📈 スコア推移")
                    fig_score = make_subplots(specs=[[{"secondary_y": True}]])

                    total_scores = [scores_by_year[y]["total_score"] for y in years]
                    fig_score.add_trace(go.Scatter(
                        x=years, y=total_scores, mode="lines+markers",
                        name="総合スコア", line=dict(color="#2E75B6", width=3),
                        marker=dict(size=10),
                    ), secondary_y=False)

                    if stock_prices:
                        prices = [stock_prices[y]["end"] for y in years if y in stock_prices]
                        price_years = [y for y in years if y in stock_prices]
                        fig_score.add_trace(go.Scatter(
                            x=price_years, y=prices, mode="lines+markers",
                            name="株価(年末)", line=dict(color="#F39C12", width=2, dash="dot"),
                            marker=dict(size=8),
                        ), secondary_y=True)

                    fig_score.update_layout(height=450, legend=dict(orientation="h", y=-0.15))
                    fig_score.update_yaxes(title_text="スコア", range=[0, 100], secondary_y=False)
                    fig_score.update_yaxes(title_text="株価（円）", secondary_y=True)
                    st.plotly_chart(fig_score, use_container_width=True)

                    # カテゴリ別スコア推移
                    st.subheader("📊 カテゴリ別スコア推移")
                    fig_cat = go.Figure()
                    colors = {"収益性": "#2E75B6", "安全性": "#2ECC71", "成長性": "#E74C3C", "割安度": "#F39C12"}
                    for cat in ["収益性", "安全性", "成長性", "割安度"]:
                        cat_scores = [scores_by_year[y]["category_scores"].get(cat, 0) for y in years]
                        fig_cat.add_trace(go.Scatter(
                            x=years, y=cat_scores, mode="lines+markers",
                            name=cat, line=dict(color=colors[cat], width=2),
                        ))
                    fig_cat.update_layout(height=400, yaxis_range=[0, 100], legend=dict(orientation="h", y=-0.15))
                    st.plotly_chart(fig_cat, use_container_width=True)

                    # 主要指標推移テーブル
                    st.subheader("📋 主要指標の推移")
                    metrics = ["ROE", "ROA", "営業利益率", "自己資本比率", "配当利回り"]
                    table_data = {"指標": metrics}
                    for year in years:
                        ind = indicators_by_year[year]
                        table_data[f"{year}年"] = [f"{ind.get(m, 0):.2f}" for m in metrics]
                    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

                    # スコア変動サマリー
                    st.divider()
                    st.subheader("📝 バックテストサマリー")
                    first_score = total_scores[0]
                    last_score = total_scores[-1]
                    score_change = last_score - first_score

                    sum_col1, sum_col2, sum_col3 = st.columns(3)
                    sum_col1.metric(f"{years[0]}年スコア", f"{first_score}点")
                    sum_col2.metric(f"{years[-1]}年スコア", f"{last_score}点", delta=f"{score_change:+.0f}点")

                    if stock_prices and years[0] in stock_prices and years[-1] in stock_prices:
                        p_start = stock_prices[years[0]]["start"]
                        p_end = stock_prices[years[-1]]["end"]
                        p_return = (p_end - p_start) / p_start * 100
                        sum_col3.metric("株価リターン", f"{p_return:+.1f}%")

                    # 判定
                    if score_change > 10:
                        st.success(f"📈 **改善傾向**: スコアが{years[0]}年から{score_change:+.0f}点上昇。ファンダメンタルズが改善しています。")
                    elif score_change < -10:
                        st.warning(f"📉 **悪化傾向**: スコアが{years[0]}年から{score_change:+.0f}点下落。注意が必要です。")
                    else:
                        st.info(f"➡️ **安定**: スコアは{years[0]}年から大きな変動なく推移しています。")

    elif bt_code and len(bt_code) == 4:
        st.error("❌ 未対応の証券コードです")

    st.divider()
    st.caption("⚠️ 本ツールは投資助言ではありません。過去の実績は将来の結果を保証しません。")
    st.stop()

# ========================================
# 銘柄分析ページ

# ── ダッシュボード ──
st.markdown("""
<div class='main-header'>
    <h1>📊 Kabu Analyzer</h1>
    <p>AI搭載 株式投資分析ツール ｜ 3,700社以上対応</p>
</div>
""", unsafe_allow_html=True)

dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
dash_col1.metric("対応銘柄", f"{len(CODE_MAP):,}社")
dash_col2.metric("ウォッチリスト", f"{len(st.session_state.get('watchlist', []))}銘柄")
dash_col3.metric("ポートフォリオ", f"{len(st.session_state.get('portfolio', []))}銘柄")
dash_col4.metric("アラート", f"{len([a for a in st.session_state.get('alerts', []) if a.get('active')])}件")

st.write("")
qc1, qc2, qc3 = st.columns(3)
qc1.info("💡 **人気** トヨタ(7203) / ソニー(6758)")
qc2.info("📈 **高配当** JT(2914) / 三菱商事(8058)")
qc3.info("🚀 **成長** 東京エレクトロン(8035)")

if st.session_state.get("alert_history"):
    st.markdown("**🔔 最近のアラート**")
    for h in list(reversed(st.session_state.get("alert_history", [])))[:3]:
        st.caption(f"🔔 {h.get('time','')} | {h['name']}（{h['code']}）: {h['type']} → {h['actual']:.2f}")

st.divider()

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
                    st.success("✅ ウォッチリストに追加しました")
            else:
                st.info("⭐ ウォッチリスト登録済み")

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
                time.sleep(1)
                hist = yf.Ticker(f"{stock_code}.T").history(period="1y")
                if not hist.empty and len(hist) > 10:
                    fig_c = go.Figure(data=[go.Candlestick(x=hist.index, open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], increasing_line_color="#2E75B6", decreasing_line_color="#E74C3C")])
                    fig_c.update_layout(height=400, xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig_c, use_container_width=True)
                else: st.info("ℹ️ 株価チャートを取得できませんでした")
            except: st.info("ℹ️ 株価チャートは一時的に利用できません（Rate Limit）")

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
st.caption("⚠️ 本ツールは投資助言ではありません。投資判断はご自身の責任で行ってください。")
