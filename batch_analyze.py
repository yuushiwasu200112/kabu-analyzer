"""全銘柄バッチ分析スクリプト v2 - 成長性+株価対応"""
import os, sys, json, time, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import save_stock_score, get_scores_count
from analysis.indicators import calc_indicators, calc_growth
from analysis.scoring import calc_total_score
from parsers.xbrl_parser import parse_xbrl

# APIキー
API_KEY = ""
with open(os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')) as f:
    for line in f:
        if 'EDINET_API_KEY' in line:
            API_KEY = line.split('=')[1].strip().strip('"').strip("'")

# CODE_MAP
with open(os.path.join(os.path.dirname(__file__), 'config', 'edinet_code_map.json'), 'r', encoding='utf-8') as f:
    CODE_MAP = json.load(f)

# Step 1: 有報収集（2年分 - 成長率計算のため）
print("📡 EDINET有報一覧を収集中（2年分）...")
all_docs = {}  # edinet_code -> [doc_new, doc_old]

search_dates = []
for year in [2024, 2025, 2023]:
    for month in [6, 7, 3, 4, 5, 8, 9, 10, 11, 12]:
        for day in [1, 5, 10, 15, 20, 25, 28]:
            try:
                d = datetime.date(year, month, day)
                if d <= datetime.date.today():
                    search_dates.append(d.isoformat())
            except:
                pass
search_dates.sort(reverse=True)

found = 0
for date_str in search_dates:
    try:
        url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?date={date_str}&type=2&Subscription-Key={API_KEY}"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            continue
        data = resp.json()
        for doc in data.get("results", []):
            ec = doc.get("edinetCode", "")
            if doc.get("docTypeCode") == "120" and ec:
                if ec not in all_docs:
                    all_docs[ec] = []
                if len(all_docs[ec]) < 2:
                    all_docs[ec].append(doc)
                    found += 1
        print(f"  {date_str}: 累計{found}件", flush=True)
    except:
        pass
    time.sleep(0.3)
    if found >= 4000:
        break

print(f"✅ 有報収集完了（{len(all_docs)}社）", flush=True)

# edinet→stock逆引き
edinet_to_stock = {v["edinet_code"]: k for k, v in CODE_MAP.items()}

# Step 2: 株価をstooqから取得
print("📈 株価をstooq APIから取得中...", flush=True)
stock_codes_to_fetch = [edinet_to_stock[ec] for ec in all_docs if ec in edinet_to_stock]
prices = {}
for j, code in enumerate(stock_codes_to_fetch):
    try:
        url = f"https://stooq.com/q/l/?s={code}.jp&f=sd2t2ohlcv&h&e=csv"
        r = requests.get(url, timeout=10)
        lines = r.text.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split(",")
            if len(parts) > 6 and parts[6] != "N/D":
                prices[code] = float(parts[6])
    except:
        pass
    if (j+1) % 100 == 0:
        print(f"  株価取得: {j+1}/{len(stock_codes_to_fetch)} ({len(prices)}件成功)", flush=True)
    time.sleep(0.15)
print(f"✅ 株価取得完了（{len(prices)}銘柄）", flush=True)

# Step 3: 分析
print(f"📊 分析開始（対象: {len(all_docs)}社）", flush=True)
print("=" * 50, flush=True)
success = fail = 0
start_time = time.time()

for i, (edinet_code, docs) in enumerate(all_docs.items(), 1):
    stock_code = edinet_to_stock.get(edinet_code)
    if not stock_code:
        continue
    name = CODE_MAP[stock_code]["name"]

    try:
        # 最新有報のXBRL取得・パース
        doc_id = docs[0]["docID"]
        r = requests.get(f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}?type=1&Subscription-Key={API_KEY}", timeout=60)
        if r.status_code != 200:
            fail += 1
            continue
        financial = parse_xbrl(r.content)
        if not financial:
            fail += 1
            continue

        # 株価（stooqから事前取得済み）
        price = prices.get(stock_code, 0)

        # 指標計算
        indicators = calc_indicators(financial, price)

        # 成長率（前年有報がある場合）
        if len(docs) >= 2:
            try:
                r2 = requests.get(f"https://api.edinet-fsa.go.jp/api/v2/documents/{docs[1]['docID']}?type=1&Subscription-Key={API_KEY}", timeout=60)
                if r2.status_code == 200:
                    prev_fin = parse_xbrl(r2.content)
                    if prev_fin:
                        growth = calc_growth(financial, prev_fin)
                        indicators.update(growth)
            except:
                pass

        # スコア
        score_result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        save_stock_score(stock_code, name, score_result, indicators)
        success += 1

        elapsed = time.time() - start_time
        rate = success / (elapsed / 60) if elapsed > 0 else 0
        eta = (len(all_docs) - i) / rate if rate > 0 else 0
        print(f"[{i}/{len(all_docs)}] ✅ {name[:15]}({stock_code}) {score_result['total_score']}点 成長{score_result['category_scores'].get('成長性',0)} 割安{score_result['category_scores'].get('割安度',0)} | 残り{eta:.0f}分", flush=True)

    except Exception as e:
        fail += 1

    time.sleep(0.3)

elapsed = time.time() - start_time
print("=" * 50, flush=True)
print(f"🏁 完了！ 成功:{success} 失敗:{fail}", flush=True)
print(f"DB登録数: {get_scores_count()}件", flush=True)
print(f"所要時間: {elapsed/3600:.1f}時間", flush=True)
