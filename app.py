import streamlit as st
import os
import json
import io
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
from data.database import save_analysis, get_analysis_history, get_user_stats, init_db

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
    page = st.radio("📌 メニュー", ["銘柄分析", "複数社比較", "ランキング", "ウォッチリスト", "ポートフォリオ", "配当カレンダー", "アラート", "セクター分析", "バックテスト", "スクリーニング", "買い増し最適化", "定期レポート", "利用規約", "設定", "プロフィール"], index=0)
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

    user_plan = user_info.get("plan", "free")
    if user_plan == "free" and username != "guest":
        st.divider()
        st.markdown("**🚀 アップグレード**")
        st.link_button("⭐ Pro ¥980/月", "https://buy.stripe.com/test_aFa5kD3JK9mY3tYbRBa3u00", use_container_width=True)
        st.link_button("💎 Premium ¥2,980/月", "https://buy.stripe.com/test_eVq9ATbcc56I6Ga2h1a3u01", use_container_width=True)

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


@st.cache_data(ttl=3600)
def _load_major_stocks():
    for p in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'major_stocks.json'),
        os.path.join(os.getcwd(), 'config', 'major_stocks.json'),
    ]:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def analyze_company_safe(code, api_key, style="バランス", period="中期（1〜3年）"):
    """エラーハンドリング付きの分析ラッパー"""
    try:
        return analyze_company(code, api_key, style, period)
    except ConnectionError:
        return {"error": "ネットワークエラー: インターネット接続を確認してください"}
    except TimeoutError:
        return {"error": "タイムアウト: EDINET APIの応答に時間がかかっています。しばらくしてから再度お試しください"}
    except Exception as e:
        error_msg = str(e)
        if "Rate Limit" in error_msg or "429" in error_msg:
            return {"error": "API制限: リクエスト上限に達しました。1分ほどお待ちください"}
        elif "404" in error_msg:
            return {"error": "データなし: この銘柄の有価証券報告書が見つかりません"}
        elif "EDINET" in error_msg:
            return {"error": "EDINET APIエラー: 金融庁のシステムが一時的に利用できません"}
        return {"error": f"分析エラー: {error_msg[:100]}"}

@st.cache_data(ttl=3600, show_spinner=False)
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

# ========================================
# ページルーティング
# ========================================
if page == "複数社比較":
    exec(open("ui_pages/compare.py", encoding="utf-8").read())

if page == "ランキング":
    exec(open("ui_pages/ranking.py", encoding="utf-8").read())

if page == "ウォッチリスト":
    exec(open("ui_pages/watchlist.py", encoding="utf-8").read())

if page == "ポートフォリオ":
    exec(open("ui_pages/portfolio.py", encoding="utf-8").read())

if page == "配当カレンダー":
    exec(open("ui_pages/dividend.py", encoding="utf-8").read())

if page == "アラート":
    exec(open("ui_pages/alert.py", encoding="utf-8").read())

if page == "セクター分析":
    exec(open("ui_pages/sector.py", encoding="utf-8").read())

if page == "バックテスト":
    exec(open("ui_pages/backtest.py", encoding="utf-8").read())

if page == "スクリーニング":
    exec(open("ui_pages/screening.py", encoding="utf-8").read())

if page == "買い増し最適化":
    exec(open("ui_pages/buy_optimize.py", encoding="utf-8").read())

if page == "定期レポート":
    exec(open("ui_pages/report.py", encoding="utf-8").read())

if page == "設定":
    exec(open("ui_pages/settings.py", encoding="utf-8").read())

if page == "プロフィール":
    exec(open("ui_pages/profile.py", encoding="utf-8").read())

if page == "利用規約":
    exec(open("ui_pages/terms.py", encoding="utf-8").read())

# 利用規約/設定/プロフィールはst.stop()済み
if page in ["利用規約", "設定", "プロフィール"]:
    st.stop()

# ========================================
# 銘柄分析ページ（デフォルト）
# ========================================
exec(open("ui_pages/analysis.py", encoding="utf-8").read())
