"""
株価データ取得クライアント
yfinanceがRate Limitの場合はフォールバックデータを使用
"""
import yfinance as yf
import time

# yfinanceがRate Limitの時のフォールバック
FALLBACK = {
    "7203": {
        "stock_code": "7203", "name": "トヨタ自動車",
        "current_price": 3635, "market_cap": 47_000_000_000_000,
        "per": 12.79, "pbr": 1.22, "eps": 284.0, "bps": 2979.0,
        "dividend_yield": 0.022, "sector": "Consumer Cyclical", "industry": "Auto Manufacturers",
    },
}

def get_stock_info(stock_code, retry=2):
    """株価情報を取得（Rate Limit時はフォールバック）"""
    ticker = yf.Ticker(f"{stock_code}.T")

    try:
        time.sleep(1)
        hist = ticker.history(period="5d")
        if not hist.empty:
            latest_price = hist.iloc[-1]["Close"]
            info = {}
            try:
                time.sleep(2)
                info = ticker.info
            except:
                pass

            return {
                "stock_code": stock_code,
                "name": info.get("longName") or info.get("shortName", "不明"),
                "current_price": latest_price,
                "market_cap": info.get("marketCap", 0),
                "per": info.get("trailingPE", 0) or 0,
                "pbr": info.get("priceToBook", 0) or 0,
                "eps": info.get("trailingEps", 0) or 0,
                "bps": info.get("bookValue", 0) or 0,
                "dividend_yield": info.get("dividendYield", 0) or 0,
                "sector": info.get("sector", "不明"),
                "industry": info.get("industry", "不明"),
            }
    except:
        pass

    # フォールバック
    if stock_code in FALLBACK:
        print(f"⚠️ yfinance Rate Limit: フォールバックデータを使用")
        return FALLBACK[stock_code]

    return None

def get_stock_history(stock_code, period="5y"):
    ticker = yf.Ticker(f"{stock_code}.T")
    return ticker.history(period=period)

def get_dividends(stock_code):
    ticker = yf.Ticker(f"{stock_code}.T")
    return ticker.dividends
