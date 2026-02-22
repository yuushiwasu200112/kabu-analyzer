"""全銘柄バッチ分析スクリプト"""
import os, sys, json, time, datetime, requests, zipfile, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.database import save_stock_score, get_scores_count
from analysis.indicators import calc_indicators, calc_growth
from analysis.scoring import calc_total_score
from parsers.xbrl_parser import parse_xbrl
import yfinance as yf

# APIキー
API_KEY = ""
with open(os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')) as f:
    for line in f:
        if 'EDINET_API_KEY' in line:
            API_KEY = line.split('=')[1].strip().strip('"').strip("'")

# CODE_MAP
with open(os.path.join(os.path.dirname(__file__), 'config', 'edinet_code_map.json'), 'r', encoding='utf-8') as f:
    CODE_MAP = json.load(f)

# Step 1: まず全日付をスキャンして有報一覧を集める
print("📡 EDINET有報一覧を収集中...")
all_docs = {}  # edinet_code -> doc

# 有報が多い日付を重点検索（2024年6-7月 = 3月決算企業の提出期間）
search_dates = []
for year in [2024, 2025]:
    for month in [6, 7, 3, 4, 5, 8, 9, 10, 11, 12]:
        for day in [1, 5, 10, 15, 20, 25, 28]:
            try:
                d = datetime.date(year, month, day)
                if d <= datetime.date.today():
                    search_dates.append(d.isoformat())
            except:
                pass

# 最新を優先
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
            if doc.get("docTypeCode") == "120" and ec and ec not in all_docs:
                all_docs[ec] = doc
                found += 1
        print(f"  {date_str}: +{len([d for d in data.get('results',[]) if d.get('docTypeCode')=='120'])}件 (累計{found}件)")
    except Exception as e:
        print(f"  {date_str}: エラー {str(e)[:30]}")
    time.sleep(0.3)
    
    # 十分な数が集まったら終了
    if found >= 2000:
        break

print(f"✅ 有報{len(all_docs)}件収集完了")
print("=" * 50)

# edinet_codeから証券コードへの逆引きマップ
edinet_to_stock = {v["edinet_code"]: k for k, v in CODE_MAP.items()}

# Step 2: 各有報を分析
print(f"📊 分析開始（対象: {len(all_docs)}件）")
success = fail = 0
start_time = time.time()

for i, (edinet_code, doc) in enumerate(all_docs.items(), 1):
    stock_code = edinet_to_stock.get(edinet_code)
    if not stock_code:
        continue

    name = CODE_MAP[stock_code]["name"]
    try:
        # XBRL取得
        doc_id = doc["docID"]
        xbrl_url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}?type=1&Subscription-Key={API_KEY}"
        resp = requests.get(xbrl_url, timeout=60)
        if resp.status_code != 200:
            fail += 1
            continue

        financial = parse_xbrl(resp.content)
        if not financial:
            fail += 1
            continue

        # 株価
        try:
            ticker = yf.Ticker(f"{stock_code}.T")
            hist = ticker.history(period="5d")
            price = hist["Close"].iloc[-1] if len(hist) > 0 else 0
        except:
            price = 0

        indicators = calc_indicators(financial, price)
        score_result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        save_stock_score(stock_code, name, score_result, indicators)
        success += 1

        elapsed = time.time() - start_time
        rate = success / (elapsed / 60) if elapsed > 0 else 0
        eta = (len(all_docs) - i) / rate if rate > 0 else 0
        print(f"[{i}/{len(all_docs)}] ✅ {name}({stock_code}) {score_result['total_score']}点 | {rate:.1f}/分 | 残り{eta:.0f}分")

    except Exception as e:
        fail += 1

    time.sleep(0.5)

elapsed = time.time() - start_time
print("=" * 50)
print(f"🏁 完了！ 成功:{success} 失敗:{fail}")
print(f"DB登録数: {get_scores_count()}件")
print(f"所要時間: {elapsed/3600:.1f}時間")
