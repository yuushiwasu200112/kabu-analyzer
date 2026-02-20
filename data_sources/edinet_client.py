"""
EDINET API クライアント
証券コードからXBRL財務データを取得する
"""
import os
import requests
import zipfile
import io
import datetime
from dotenv import load_dotenv

load_dotenv()

EDINET_API_KEY = os.getenv("EDINET_API_KEY")
BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"

# 証券コード → EDINETコードのマッピング（主要企業）
# 本番ではEDINETのコードリストCSVから自動生成する
CODE_MAP = {
    "7203": "E02144",  # トヨタ自動車
    "6758": "E01777",  # ソニーグループ
    "9984": "E05080",  # ソフトバンクグループ
    "6861": "E02274",  # キーエンス
    "8306": "E03606",  # 三菱UFJ
    "7974": "E01onal",  # 任天堂（後で正式コード追加）
}


def get_edinet_code(stock_code):
    """証券コードからEDINETコードを取得"""
    return CODE_MAP.get(stock_code)


def search_documents(stock_code, years=5):
    """
    有価証券報告書の書類一覧を取得する
    決算期（3月〜6月）に絞って効率的に検索
    """
    edinet_code = get_edinet_code(stock_code)
    if not edinet_code:
        print(f"❌ 証券コード {stock_code} のEDINETコードが見つかりません")
        return []

    documents = []
    today = datetime.date.today()

    print(f"📡 EDINET検索中（EDINETコード: {edinet_code}）...")

    for year_offset in range(years):
        target_year = today.year - year_offset
        # 有報は通常4〜6月に提出されるので、その期間を重点検索
        for month in [6, 5, 4, 3, 7, 8]:
            # その月の各週の初日を検索
            for day in [1, 8, 15, 22]:
                date_str = f"{target_year}-{month:02d}-{day:02d}"
                try:
                    date_check = datetime.date(target_year, month, day)
                    if date_check > today:
                        continue
                except ValueError:
                    continue

                try:
                    resp = requests.get(
                        f"{BASE_URL}/documents.json",
                        params={
                            "date": date_str,
                            "type": 2,
                            "Subscription-Key": EDINET_API_KEY,
                        },
                        timeout=30,
                    )
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    if "results" not in data:
                        continue

                    for doc in data["results"]:
                        if (doc.get("edinetCode") == edinet_code
                                and doc.get("docTypeCode") == "120"
                                and doc.get("docID")):
                            doc_ids = [d["docID"] for d in documents]
                            if doc["docID"] not in doc_ids:
                                documents.append({
                                    "docID": doc["docID"],
                                    "filerName": doc.get("filerName", ""),
                                    "docDescription": doc.get("docDescription", ""),
                                    "submitDateTime": doc.get("submitDateTime", ""),
                                    "periodStart": doc.get("periodStart", ""),
                                    "periodEnd": doc.get("periodEnd", ""),
                                })
                                print(f"  📄 発見: {doc.get('docDescription', '')} ({doc.get('periodEnd', '')[:7]})")
                except Exception as e:
                    continue

            # この年の有報が見つかったら次の年へ
            if any(str(target_year) in d.get("periodEnd", "") or str(target_year) in d.get("submitDateTime", "") for d in documents):
                break

    documents.sort(key=lambda x: x.get("periodEnd", ""), reverse=True)
    print(f"✅ {len(documents)} 件の有報を発見")
    return documents


def download_xbrl(doc_id):
    """docIDを指定してXBRLデータをダウンロード・展開する"""
    print(f"  ⬇️  ダウンロード中: {doc_id}")
    resp = requests.get(
        f"{BASE_URL}/documents/{doc_id}",
        params={
            "type": 1,
            "Subscription-Key": EDINET_API_KEY,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"  ❌ ダウンロード失敗: status={resp.status_code}")
        return None

    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xbrl_files = {}
            for name in zf.namelist():
                if name.endswith(".xbrl"):
                    xbrl_files[name] = zf.read(name)
            print(f"  ✅ {len(xbrl_files)} 個のXBRLファイルを展開")
            return xbrl_files
    except zipfile.BadZipFile:
        print("  ❌ ZIPファイルの展開に失敗")
        return None
