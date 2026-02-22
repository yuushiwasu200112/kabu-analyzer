"""SQLiteデータベース管理"""
import sqlite3
import os
import json
import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kabu_analyzer.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """テーブル作成"""
    conn = get_connection()
    c = conn.cursor()

    # ユーザーテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        email TEXT,
        plan TEXT DEFAULT 'free',
        monthly_usage INTEGER DEFAULT 0,
        usage_reset_month TEXT,
        created_at TEXT,
        last_login TEXT
    )''')

    # 分析履歴テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        stock_code TEXT NOT NULL,
        company_name TEXT,
        total_score INTEGER,
        profitability INTEGER,
        safety INTEGER,
        growth INTEGER,
        value INTEGER,
        roe REAL,
        per REAL,
        pbr REAL,
        dividend_yield REAL,
        style TEXT,
        period TEXT,
        analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username) REFERENCES users(username)
    )''')

    # ウォッチリストテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(username, stock_code),
        FOREIGN KEY (username) REFERENCES users(username)
    )''')

    # ポートフォリオテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        company_name TEXT,
        amount INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(username, stock_code),
        FOREIGN KEY (username) REFERENCES users(username)
    )''')

    # アラートテーブル
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        company_name TEXT,
        alert_type TEXT,
        threshold REAL,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username) REFERENCES users(username)
    )''')

    # アラート履歴テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS alert_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        stock_code TEXT,
        company_name TEXT,
        alert_type TEXT,
        threshold REAL,
        actual_value REAL,
        triggered_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute("""CREATE TABLE IF NOT EXISTS stock_scores (
        stock_code TEXT PRIMARY KEY,
        company_name TEXT,
        total_score INTEGER,
        profitability INTEGER,
        safety INTEGER,
        growth INTEGER,
        value INTEGER,
        roe REAL, roa REAL, per REAL, pbr REAL,
        dividend_yield REAL, operating_margin REAL, equity_ratio REAL,
        judgment TEXT, updated_at TEXT
    )""")

    conn.commit()
    conn.close()


# ── 分析履歴 ──
def save_analysis(username, stock_code, company_name, score_result, indicators, style, period):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO analysis_history
        (username, stock_code, company_name, total_score, profitability, safety, growth, value,
         roe, per, pbr, dividend_yield, style, period, analyzed_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (username, stock_code, company_name,
         score_result["total_score"],
         score_result["category_scores"].get("収益性", 0),
         score_result["category_scores"].get("安全性", 0),
         score_result["category_scores"].get("成長性", 0),
         score_result["category_scores"].get("割安度", 0),
         indicators.get("ROE", 0), indicators.get("PER", 0),
         indicators.get("PBR", 0), indicators.get("配当利回り", 0),
         style, period,
         datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_analysis_history(username, limit=20):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT * FROM analysis_history WHERE username=?
                 ORDER BY analyzed_at DESC LIMIT ?''', (username, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_stock_history(stock_code, limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT * FROM analysis_history WHERE stock_code=?
                 ORDER BY analyzed_at DESC LIMIT ?''', (stock_code, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ── ウォッチリスト ──
def save_watchlist(username, stock_code):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO watchlist (username, stock_code) VALUES (?,?)',
                  (username, stock_code))
        conn.commit()
    except:
        pass
    conn.close()


def get_watchlist(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT stock_code FROM watchlist WHERE username=? ORDER BY added_at', (username,))
    codes = [r["stock_code"] for r in c.fetchall()]
    conn.close()
    return codes


def remove_watchlist(username, stock_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM watchlist WHERE username=? AND stock_code=?', (username, stock_code))
    conn.commit()
    conn.close()


# ── ポートフォリオ ──
def save_portfolio(username, stock_code, company_name, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO portfolio (username, stock_code, company_name, amount, updated_at)
                 VALUES (?,?,?,?,?)
                 ON CONFLICT(username, stock_code) DO UPDATE SET amount=?, updated_at=?''',
              (username, stock_code, company_name, amount,
               datetime.datetime.now().isoformat(), amount, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_portfolio(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM portfolio WHERE username=? ORDER BY updated_at', (username,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def remove_portfolio(username, stock_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM portfolio WHERE username=? AND stock_code=?', (username, stock_code))
    conn.commit()
    conn.close()


# ── 統計 ──
def get_user_stats(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as total FROM analysis_history WHERE username=?', (username,))
    total = c.fetchone()["total"]
    c.execute('SELECT COUNT(DISTINCT stock_code) as unique_stocks FROM analysis_history WHERE username=?', (username,))
    unique = c.fetchone()["unique_stocks"]
    c.execute('''SELECT stock_code, company_name, COUNT(*) as cnt FROM analysis_history
                 WHERE username=? GROUP BY stock_code ORDER BY cnt DESC LIMIT 5''', (username,))
    top = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"total_analyses": total, "unique_stocks": unique, "top_stocks": top}


    # スコアキャッシュテーブル
    c.execute("""CREATE TABLE IF NOT EXISTS stock_scores (
        stock_code TEXT PRIMARY KEY,
        company_name TEXT,
        total_score INTEGER,
        profitability INTEGER,
        safety INTEGER,
        growth INTEGER,
        value INTEGER,
        roe REAL, roa REAL, per REAL, pbr REAL,
        dividend_yield REAL, operating_margin REAL, equity_ratio REAL,
        judgment TEXT, updated_at TEXT
    )""")

    conn.commit()
    conn.close()


def save_stock_score(code, name, score_result, indicators):
    import datetime
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO stock_scores
        (stock_code, company_name, total_score, profitability, safety, growth, value,
         roe, roa, per, pbr, dividend_yield, operating_margin, equity_ratio, judgment, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (code, name,
         score_result["total_score"],
         score_result["category_scores"].get("収益性", 0),
         score_result["category_scores"].get("安全性", 0),
         score_result["category_scores"].get("成長性", 0),
         score_result["category_scores"].get("割安度", 0),
         indicators.get("ROE", 0), indicators.get("ROA", 0),
         indicators.get("PER", 0), indicators.get("PBR", 0),
         indicators.get("配当利回り", 0), indicators.get("営業利益率", 0),
         indicators.get("自己資本比率", 0),
         score_result.get("judgment", ""),
         datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_scores(min_score=0, limit=3732):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT * FROM stock_scores WHERE total_score >= ?
                 ORDER BY total_score DESC LIMIT ?""", (min_score, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_scores_count():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM stock_scores")
    cnt = c.fetchone()["cnt"]
    conn.close()
    return cnt


# 初期化実行
init_db()
