"""
強制フィルター
スコアに関係なく危険な状態を警告する
"""


def check_filters(current_data, previous_data=None, ai_risk=False):
    """
    強制フィルターを適用し、警告リストを返す
    """
    warnings = []

    # 1. 債務超過リスク: 自己資本比率 < 10%
    equity = current_data.get("自己資本", 0)
    assets = current_data.get("総資産", 0)
    if assets > 0:
        equity_ratio = equity / assets * 100
        if equity_ratio < 10:
            warnings.append({
                "level": "danger",
                "icon": "🔴",
                "title": "債務超過リスク",
                "message": f"自己資本比率が {equity_ratio:.1f}% と非常に低いです。財務破綻リスクがあります。",
            })

    # 2. 赤字継続: 直近の純利益がマイナス
    net_income = current_data.get("純利益", 0)
    if net_income < 0:
        msg = "直近期が純損失です。"
        # 前年もチェック
        if previous_data and previous_data.get("純利益", 0) < 0:
            msg = "2期連続で純損失です。収益性に深刻な問題があります。"
            warnings.append({
                "level": "danger",
                "icon": "🔴",
                "title": "赤字継続",
                "message": msg,
            })
        else:
            warnings.append({
                "level": "warning",
                "icon": "🟡",
                "title": "直近期赤字",
                "message": msg,
            })

    # 3. 営業CFマイナス
    op_cf = current_data.get("営業CF", 0)
    if op_cf < 0:
        msg = "直近期の営業キャッシュフローがマイナスです。"
        if previous_data and previous_data.get("営業CF", 0) < 0:
            msg = "2期連続で営業CFがマイナスです。事業存続性に懸念があります。"
            warnings.append({
                "level": "danger",
                "icon": "🔴",
                "title": "営業CF連続マイナス",
                "message": msg,
            })
        else:
            warnings.append({
                "level": "warning",
                "icon": "🟡",
                "title": "営業CFマイナス",
                "message": msg,
            })

    # 4. 有利子負債比率が極端に高い
    debt = current_data.get("有利子負債", 0)
    if assets > 0 and debt > 0:
        debt_ratio = debt / assets * 100
        if debt_ratio > 60:
            warnings.append({
                "level": "warning",
                "icon": "🟡",
                "title": "有利子負債過多",
                "message": f"有利子負債比率が {debt_ratio:.1f}% と高水準です。金利上昇リスクに注意してください。",
            })

    # 5. 流動比率が低すぎる
    ca = current_data.get("流動資産", 0)
    cl = current_data.get("流動負債", 0)
    if cl > 0:
        current_ratio = ca / cl * 100
        if current_ratio < 100:
            warnings.append({
                "level": "warning",
                "icon": "🟡",
                "title": "短期支払能力に懸念",
                "message": f"流動比率が {current_ratio:.0f}% です。短期的な支払い能力に注意が必要です。",
            })

    return warnings
