"""
XBRLパーサー - IFRS/日本基準対応・セグメント除外版
"""
import requests, zipfile, io
from lxml import etree

TAG_GROUPS = {
    "売上高": [
        "SalesAndFinancialServicesRevenueIFRS",
        "TotalNetRevenuesIFRS",
        "RevenueIFRS",
        "NetSalesIFRS",
        "NetSalesSummaryOfBusinessResults",
        "NetSales",
        "Revenue",
    ],
    "営業利益": [
        "OperatingProfitLossIFRS",
        "OperatingIncome",
    ],
    "純利益": [
        "ProfitLossAttributableToOwnersOfParentIFRS",
        "ProfitLossAttributableToOwnersOfParent",
        "NetIncomeLossSummaryOfBusinessResults",
        "NetIncome",
    ],
    "総資産": [
        "AssetsIFRS",
        "TotalAssetsIFRSSummaryOfBusinessResults",
        "TotalAssets",
        "Assets",
    ],
    "自己資本": [
        "EquityAttributableToOwnersOfParentIFRS",
        "ShareholdersEquity",
    ],
    "純資産": ["EquityIFRS", "NetAssets"],
    "流動資産": ["CurrentAssetsIFRS", "CurrentAssets"],
    "流動負債": ["CurrentLiabilitiesIFRS", "CurrentLiabilities"],
    "支払利息": ["InterestExpensesNOE", "InterestExpense", "FinanceCosts"],
    "営業CF": [
        "NetCashProvidedByUsedInOperatingActivitiesIFRS",
        "CashFlowsFromOperatingActivities",
    ],
    "1株配当": ["DividendPaidPerShareSummaryOfBusinessResults", "DividendPerShare"],
    "発行済株式数": [
        "TotalNumberOfIssuedSharesSummaryOfBusinessResults",
        "NumberOfIssuedSharesAsOfFiscalYearEndIssuedSharesTotalNumberOfSharesEtc",
    ],
    "有利子負債_短期": ["InterestBearingLiabilitiesCLIFRS"],
    "有利子負債_長期": ["InterestBearingLiabilitiesNCLIFRS"],
    "有利子負債": ["InterestBearingDebt"],
}


def _is_current_consolidated(context_ref):
    """当期の連結全体データかどうか判定"""
    if not context_ref:
        return False
    # セグメント別データを除外
    segment_keywords = [
        "_jpcrp030000", "Segment", "Game", "Music", "Picture",
        "Enter", "Imag", "Finan", "Reportable",
        "NonConsolidated", "Elimination",
    ]
    for kw in segment_keywords:
        if kw in context_ref:
            return False
    # 前期を除外
    if "Prior" in context_ref:
        return False
    # 当期の連結
    if "CurrentYear" in context_ref:
        return True
    if "Current" in context_ref:
        return True
    return False


def _is_current_any(context_ref):
    """当期データかどうか（セグメントも含む広い判定）"""
    if not context_ref:
        return False
    if "Prior" in context_ref:
        return False
    return True


def download_and_parse(doc_id, api_key):
    resp = requests.get(
        f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}",
        params={"type": 1, "Subscription-Key": api_key},
        timeout=60,
    )
    if resp.status_code != 200:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            xbrl_files = [n for n in zf.namelist() if n.endswith(".xbrl")]
            if not xbrl_files:
                return None
            main_xbrl = max(xbrl_files, key=lambda n: len(zf.read(n)))
            xml_data = zf.read(main_xbrl)
    except zipfile.BadZipFile:
        return None
    return parse_xbrl(xml_data)


def extract_xbrl_from_zip(zip_data):
    """ZIPからXBRLファイルを抽出"""
    try:
        z = zipfile.ZipFile(io.BytesIO(zip_data))
        for name in z.namelist():
            if name.endswith('.xbrl') and 'XBRL/PublicDoc/' in name:
                return z.read(name)
        # PublicDocがない場合
        for name in z.namelist():
            if name.endswith('.xbrl'):
                return z.read(name)
    except:
        pass
    return None


def parse_xbrl(xml_data):
    # ZIPの場合は展開
    if xml_data[:2] == b'PK':
        xml_data = extract_xbrl_from_zip(xml_data)
        if not xml_data:
            return None
    root = etree.fromstring(xml_data)

    # 全タグを収集（contextRef付き）
    all_entries = {}
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        ctx = elem.get("contextRef", "")
        if elem.text:
            try:
                val = float(elem.text.replace(",", ""))
                if tag not in all_entries:
                    all_entries[tag] = []
                all_entries[tag].append({"value": val, "context": ctx})
            except ValueError:
                pass

    def get_current_consolidated(tag_name):
        """当期の連結全体の値を取得"""
        entries = all_entries.get(tag_name, [])
        if not entries:
            return None

        # まず当期連結でフィルタ
        current = [e for e in entries if _is_current_consolidated(e["context"])]
        if current:
            # 連結全体は通常最大値（セグメント合計 > 個別セグメント）
            return max(current, key=lambda e: abs(e["value"]))["value"]

        # 当期連結が見つからなければ、当期のデータから
        current_any = [e for e in entries if _is_current_any(e["context"])]
        if current_any:
            return max(current_any, key=lambda e: abs(e["value"]))["value"]

        # それでもなければ全体から最大値
        return max(entries, key=lambda e: abs(e["value"]))["value"]

    # 優先度順でマッチング
    results = {}
    for label, tag_list in TAG_GROUPS.items():
        for tag_name in tag_list:
            val = get_current_consolidated(tag_name)
            if val is not None:
                results[label] = val
                break

    # 有利子負債 = 短期 + 長期
    if "有利子負債_短期" in results or "有利子負債_長期" in results:
        short = results.pop("有利子負債_短期", 0)
        long_d = results.pop("有利子負債_長期", 0)
        if "有利子負債" not in results:
            results["有利子負債"] = short + long_d
    results.pop("有利子負債_短期", None)
    results.pop("有利子負債_長期", None)

    # 自己資本フォールバック
    if "自己資本" not in results and "純資産" in results:
        results["自己資本"] = results["純資産"]

    # 整合性チェック
    if results.get("自己資本", 0) > results.get("総資産", float("inf")):
        if "純資産" in results:
            results["自己資本"] = results["純資産"]

    return results


def fetch_multi_year(doc_list, api_key):
    all_data = {}
    for doc in doc_list:
        doc_id = doc["docID"]
        period_end = doc.get("periodEnd", "不明")
        desc = doc.get("docDescription", "")
        print(f"  📥 {desc} を処理中...")
        data = download_and_parse(doc_id, api_key)
        if data:
            all_data[period_end] = data
            print(f"     ✅ {len(data)} 項目取得")
        else:
            print(f"     ❌ 取得失敗")
    return all_data
