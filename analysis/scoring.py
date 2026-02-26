"""
スコアリングエンジン - v3（厳格化：100点はトップ企業のみ）
"""
THRESHOLDS = {
    # 収益性 - 日本企業の上位5%で100点
    "ROE":       {"excellent": 30, "zero": 0, "higher_is_better": True},
    "ROA":       {"excellent": 15, "zero": 0, "higher_is_better": True},
    "営業利益率": {"excellent": 25, "zero": 0, "higher_is_better": True},
    "配当利回り": {"excellent": 6,  "zero": 0, "higher_is_better": True},
    # 安全性 - 厳格化
    "自己資本比率": {"excellent": 80, "zero": 10, "higher_is_better": True},
    "流動比率":     {"excellent": 400, "zero": 80, "higher_is_better": True},
    "有利子負債比率":{"excellent": 0,  "zero": 80, "higher_is_better": False},
    "ICR":          {"excellent": 50, "zero": 1,  "higher_is_better": True},
    # 成長性 - 高成長のみ高得点
    "売上高成長率":   {"excellent": 20, "zero": -5, "higher_is_better": True},
    "営業利益成長率": {"excellent": 30, "zero": -10, "higher_is_better": True},
    "純利益成長率":   {"excellent": 40, "zero": -15, "higher_is_better": True},
    "総資産成長率":   {"excellent": 15, "zero": -5, "higher_is_better": True},
    # 割安度
    "PER": {"excellent": 8,   "zero": 50, "higher_is_better": False},
    "PBR": {"excellent": 0.5, "zero": 4,  "higher_is_better": False},
}

CATEGORIES = {
    "収益性": {"ROE": 30, "ROA": 25, "営業利益率": 25, "配当利回り": 20},
    "安全性": {"自己資本比率": 35, "流動比率": 25, "有利子負債比率": 20, "ICR": 20},
    "成長性": {"売上高成長率": 30, "営業利益成長率": 30, "純利益成長率": 20, "総資産成長率": 20},
    "割安度": {"PER": 35, "PBR": 35, "配当利回り": 30},
}

STYLE_PERIOD_WEIGHTS = {
    "バリュー投資": {
        "短期（〜1年）": {"収益性": 15, "安全性": 20, "成長性": 10, "割安度": 55},
        "中期（1〜3年）": {"収益性": 20, "安全性": 25, "成長性": 15, "割安度": 40},
        "長期（3年以上）": {"収益性": 25, "安全性": 25, "成長性": 20, "割安度": 30},
    },
    "グロース投資": {
        "短期（〜1年）": {"収益性": 20, "安全性": 10, "成長性": 50, "割安度": 20},
        "中期（1〜3年）": {"収益性": 25, "安全性": 15, "成長性": 40, "割安度": 20},
        "長期（3年以上）": {"収益性": 25, "安全性": 15, "成長性": 45, "割安度": 15},
    },
    "高配当投資": {
        "短期（〜1年）": {"収益性": 40, "安全性": 30, "成長性": 10, "割安度": 20},
        "中期（1〜3年）": {"収益性": 35, "安全性": 30, "成長性": 15, "割安度": 20},
        "長期（3年以上）": {"収益性": 35, "安全性": 25, "成長性": 15, "割安度": 25},
    },
    "安定性重視": {
        "短期（〜1年）": {"収益性": 20, "安全性": 45, "成長性": 10, "割安度": 25},
        "中期（1〜3年）": {"収益性": 25, "安全性": 40, "成長性": 10, "割安度": 25},
        "長期（3年以上）": {"収益性": 25, "安全性": 35, "成長性": 15, "割安度": 25},
    },
    "バランス": {
        "短期（〜1年）": {"収益性": 25, "安全性": 25, "成長性": 25, "割安度": 25},
        "中期（1〜3年）": {"収益性": 25, "安全性": 25, "成長性": 25, "割安度": 25},
        "長期（3年以上）": {"収益性": 25, "安全性": 25, "成長性": 25, "割安度": 25},
    },
}


def score_indicator(name, value):
    if name not in THRESHOLDS or value is None:
        return None
    t = THRESHOLDS[name]
    excellent = t["excellent"]
    zero = t["zero"]
    if t["higher_is_better"]:
        if value >= excellent:
            return 100
        elif value <= zero:
            return 0
        else:
            return round((value - zero) / (excellent - zero) * 100)
    else:
        if value <= excellent:
            return 100
        elif value >= zero:
            return 0
        else:
            return round((zero - value) / (zero - excellent) * 100)


def score_category(category_name, indicators):
    if category_name not in CATEGORIES:
        return 0, {}
    config = CATEGORIES[category_name]
    scores = {}
    total_weight = 0
    weighted_sum = 0
    for indicator_name, weight in config.items():
        value = indicators.get(indicator_name)
        if value is not None:
            s = score_indicator(indicator_name, value)
            if s is not None:
                scores[indicator_name] = {"value": value, "score": s, "weight": weight}
                weighted_sum += s * weight
                total_weight += weight
    if total_weight == 0:
        return 0, scores
    category_score = round(weighted_sum / total_weight)
    return category_score, scores


def calc_total_score(indicators, style="バランス", period="中期（1〜3年）"):
    weights = STYLE_PERIOD_WEIGHTS.get(style, STYLE_PERIOD_WEIGHTS["バランス"])
    matched = None
    for k in weights:
        if period in k or k in period:
            matched = weights[k]
            break
    if not matched:
        matched = list(weights.values())[1]

    category_scores = {}
    detail = {}
    for cat_name in CATEGORIES:
        score, scores = score_category(cat_name, indicators)
        category_scores[cat_name] = score
        detail[cat_name] = scores

    total = 0
    for cat_name, weight in matched.items():
        total += category_scores.get(cat_name, 0) * weight / 100

    total = max(0, min(100, round(total)))

    if total >= 75:
        judgment = "★ スコア高"
    elif total >= 50:
        judgment = "▲ 標準的"
    else:
        judgment = "✖ スコア低"

    return {
        "total_score": total,
        "judgment": judgment,
        "style": style,
        "period": period,
        "category_scores": category_scores,
        "detail": detail,
    }
