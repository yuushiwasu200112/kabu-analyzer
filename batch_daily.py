"""毎日100銘柄ずつ自動バッチ分析
- どこまで処理したかJSONで記録
- 約37日で全3,732社完了
- 翌月また最初から
"""
import os, sys, json, time, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import save_stock_score, get_scores_count, init_db
from analysis.indicators import calc_indicators, calc_growth
from analysis.scoring import calc_total_score
from parsers.xbrl_parser import parse_xbrl

init_db()

BATCH_SIZE = 100
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), 'batch_progress.json')

# APIキー
API_KEY = ""
secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        for line in f:
            if 'EDINET_API_KEY' in line:
                API_KEY = line.split('=')[1].strip().strip('"').strip("'")
if not API_KEY:
    API_KEY = os.environ.get("EDINET_API_KEY", "")
if not API_KEY:
    print("❌ EDINET_API_KEYが見つかりません")
    sys.exit(1)

# CODE_MAP
with open(os.path.join(os.path.dirname(__file__), 'config', 'edinet_code_map.json'), 'r', encoding='utf-8') as f:
    CODE_MAP = json.load(f)

all_codes = list(CODE_MAP.keys())

# 進捗読み込み
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"offset": 0, "cycle": 1, "last_run": "", "total_success": 0}

def save_progress(prog):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(prog, f, indent=2)

progress = load_progress()
offset = progress["offset"]

# 1サイクル完了したらリセット
if offset >= len(all_codes):
    offset = 0
    progress["cycle"] += 1
    print(f"🔄 サイクル{progress['cycle']}開始！全銘柄を最初から再分析します", flush=True)

today_codes = all_codes[offset:offset + BATCH_SIZE]
print(f"📊 日次バッチ開始（サイクル{progress['cycle']}）", flush=True)
print(f"対象: {offset+1}〜{offset+len(today_codes)} / {len(all_codes)}銘柄", flush=True)
print(f"前回: {progress['last_run']}", flush=True)
print("=" * 50, flush=True)

# 有報収集（対象銘柄のEDINETコードのみ）
target_edinet = {}
for code in today_codes:
    ec = CODE_MAP[code].get("edinet_code", "")
    if ec:
        target_edinet[ec] = code

print(f"📡 有報検索中（{len(target_edinet)}社）...", flush=True)
all_docs = {}  # edinet_code -> [doc_new, doc_old]

search_dates = []
for year in [2025, 2024, 2023]:
    for month in range(1, 13):
        for day in [1, 5, 10, 15, 20, 25, 28]:
            try:
                d = datetime.date(year, month, day)
                if d <= datetime.date.today():
                    search_dates.append(d.isoformat())
            except:
                pass
search_dates.sort(reverse=True)

for date_str in search_dates:
    try:
        url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?date={date_str}&type=2&Subscription-Key={API_KEY}"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            continue
        data = resp.json()
        for doc in data.get("results", []):
            ec = doc.get("edinetCode", "")
            if doc.get("docTypeCode") == "120" and ec in target_edinet:
                if ec not in all_docs:
                    all_docs[ec] = []
                if len(all_docs[ec]) < 2:
                    all_docs[ec].append(doc)
    except:
        pass
    time.sleep(0.3)
    # 全対象が2年分見つかったら終了
    has_two = sum(1 for v in all_docs.values() if len(v) >= 2)
    if has_two >= len(target_edinet) * 0.8:
        break

print(f"✅ 有報{len(all_docs)}社分収集完了", flush=True)

# 株価取得（Yahoo Finance API）
print("📈 株価取得中...", flush=True)
prices = {}
headers = {"User-Agent": "Mozilla/5.0"}
for j, code in enumerate(today_codes):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?interval=1d&range=5d"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            valid = [c for c in closes if c]
            if valid:
                prices[code] = float(valid[-1])
    except:
        pass
    if (j+1) % 50 == 0:
        print(f"  株価: {j+1}/{len(today_codes)} ({len(prices)}件)", flush=True)
    time.sleep(0.2)
print(f"✅ 株価{len(prices)}件取得完了", flush=True)

# 分析
print("📊 分析中...", flush=True)
success = fail = skip = 0

for code in today_codes:
    name = CODE_MAP[code]["name"]
    ec = CODE_MAP[code].get("edinet_code", "")

    if ec not in all_docs:
        skip += 1
        continue

    docs = all_docs[ec]
    try:
        # 最新有報
        doc_id = docs[0]["docID"]
        r = requests.get(f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}?type=1&Subscription-Key={API_KEY}", timeout=60)
        if r.status_code != 200:
            fail += 1
            continue

        financial = parse_xbrl(r.content)
        if not financial:
            fail += 1
            continue

        price = prices.get(code, 0)
        indicators = calc_indicators(financial, price)

        # 成長率
        if len(docs) >= 2:
            try:
                r2 = requests.get(f"https://api.edinet-fsa.go.jp/api/v2/documents/{docs[1]['docID']}?type=1&Subscription-Key={API_KEY}", timeout=60)
                if r2.status_code == 200:
                    prev_fin = parse_xbrl(r2.content)
                    if prev_fin:
                        indicators.update(calc_growth(financial, prev_fin))
            except:
                pass

        score_result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        save_stock_score(code, name, score_result, indicators)
        success += 1
        print(f"  ✅ {name[:15]}({code}) {score_result['total_score']}点 成長{score_result['category_scores'].get('成長性',0)} 割安{score_result['category_scores'].get('割安度',0)}", flush=True)

    except Exception as e:
        fail += 1

    time.sleep(0.3)

# 進捗更新
progress["offset"] = offset + BATCH_SIZE
progress["last_run"] = datetime.datetime.now().isoformat()
progress["total_success"] = progress.get("total_success", 0) + success
save_progress(progress)

print("=" * 50, flush=True)
print(f"🏁 日次バッチ完了！ 成功:{success} 失敗:{fail} スキップ:{skip}", flush=True)
print(f"DB登録数: {get_scores_count()}件", flush=True)
print(f"進捗: {progress['offset']}/{len(all_codes)} ({progress['offset']*100//len(all_codes)}%)", flush=True)
next_complete = (len(all_codes) - progress['offset']) // BATCH_SIZE
print(f"全銘柄完了まで: あと約{next_complete}日", flush=True)
