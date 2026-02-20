"""
財務指標計算エンジン
XBRLから抽出した財務データをもとに各種指標を計算する
"""


def calc_indicators(financial_data, stock_price=None):
    """
    1年分の財務データから各種指標を計算する
    financial_data: xbrl_parserの出力（辞書）
    stock_price: 現在株価（yfinanceから取得）
    """
    d = financial_data
    indicators = {}

    # ── 収益性 ──
    if d.get("純利益") and d.get("自己資本"):
        roe = d["純利益"] / d["自己資本"] * 100
        indicators["ROE"] = round(roe, 2)

    if d.get("純利益") and d.get("総資産"):
        roa = d["純利益"] / d["総資産"] * 100
        indicators["ROA"] = round(roa, 2)

    if d.get("営業利益") and d.get("売上高"):
        margin = d["営業利益"] / d["売上高"] * 100
        indicators["営業利益率"] = round(margin, 2)

    if d.get("1株配当") and stock_price and stock_price > 0:
        div_yield = d["1株配当"] / stock_price * 100
        indicators["配当利回り"] = round(div_yield, 2)

    # ── 安全性 ──
    if d.get("自己資本") and d.get("総資産"):
        equity_ratio = d["自己資本"] / d["総資産"] * 100
        indicators["自己資本比率"] = round(equity_ratio, 2)

    if d.get("流動資産") and d.get("流動負債") and d["流動負債"] > 0:
        current_ratio = d["流動資産"] / d["流動負債"] * 100
        indicators["流動比率"] = round(current_ratio, 2)

    if d.get("有利子負債") and d.get("総資産"):
        debt_ratio = d["有利子負債"] / d["総資産"] * 100
        indicators["有利子負債比率"] = round(debt_ratio, 2)

    if d.get("営業利益") and d.get("支払利息") and d["支払利息"] > 0:
        icr = d["営業利益"] / d["支払利息"]
        indicators["ICR"] = round(icr, 2)

    # ── 割安度（株価が必要） ──
    if stock_price and d.get("純利益") and d.get("発行済株式数") and d["発行済株式数"] > 0:
        eps = d["純利益"] / d["発行済株式数"]
        indicators["EPS"] = round(eps, 2)
        if eps > 0:
            indicators["PER"] = round(stock_price / eps, 2)

    if stock_price and d.get("自己資本") and d.get("発行済株式数") and d["発行済株式数"] > 0:
        bps = d["自己資本"] / d["発行済株式数"]
        indicators["BPS"] = round(bps, 2)
        if bps > 0:
            indicators["PBR"] = round(stock_price / bps, 2)

    return indicators


def calc_growth(current_data, previous_data):
    """
    前年比の成長率を計算する
    """
    growth = {}
    pairs = [
        ("売上高", "売上高成長率"),
        ("営業利益", "営業利益成長率"),
        ("純利益", "純利益成長率"),
        ("総資産", "総資産成長率"),
    ]
    for key, label in pairs:
        curr = current_data.get(key)
        prev = previous_data.get(key)
        if curr and prev and prev != 0:
            rate = (curr - prev) / abs(prev) * 100
            growth[label] = round(rate, 2)

    return growth
