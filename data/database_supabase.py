"""Supabase版データベース関数"""
import os

def _get_client():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
    except:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
    
    if not url or not key:
        # secrets.tomlから直接読む
        try:
            with open(os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml')) as f:
                for line in f:
                    if 'SUPABASE_URL' in line and '=' in line:
                        url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    if 'SUPABASE_KEY' in line and '=' in line:
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
        except:
            pass
    
    from supabase import create_client
    return create_client(url, key)


# ===== stock_scores =====

def get_all_scores(min_score=0, limit=100):
    client = _get_client()
    result = client.table("stock_scores").select("*").gte("total_score", min_score).order("total_score", desc=True).limit(limit).execute()
    return result.data


def get_scores_count():
    client = _get_client()
    result = client.table("stock_scores").select("*", count="exact").limit(1).execute()
    return result.count or 0


def save_stock_score(stock_code, name, score_result, indicators):
    client = _get_client()
    row = {
        "stock_code": stock_code,
        "company_name": name,
        "total_score": score_result["total_score"],
        "profitability": score_result["category_scores"].get("収益性", 0),
        "safety": score_result["category_scores"].get("安全性", 0),
        "growth": score_result["category_scores"].get("成長性", 0),
        "value": score_result["category_scores"].get("割安度", 0),
        "roe": indicators.get("ROE", 0),
        "roa": indicators.get("ROA", 0),
        "per": indicators.get("PER", 0),
        "pbr": indicators.get("PBR", 0),
        "dividend_yield": indicators.get("配当利回り", 0),
        "operating_margin": indicators.get("営業利益率", 0),
        "equity_ratio": indicators.get("自己資本比率", 0),
        "judgment": score_result["judgment"],
    }
    client.table("stock_scores").upsert(row).execute()


# ===== watchlist =====

def get_watchlist(username):
    client = _get_client()
    result = client.table("watchlist").select("stock_code").eq("username", username).execute()
    return [r["stock_code"] for r in result.data]


def save_watchlist(username, stock_code):
    client = _get_client()
    client.table("watchlist").upsert({"username": username, "stock_code": stock_code}).execute()


def remove_watchlist(username, stock_code):
    client = _get_client()
    client.table("watchlist").delete().eq("username", username).eq("stock_code", stock_code).execute()


# ===== portfolio =====

def get_portfolio(username):
    client = _get_client()
    result = client.table("portfolio").select("*").eq("username", username).execute()
    return result.data


def save_portfolio(username, stock_code, company_name, amount):
    client = _get_client()
    client.table("portfolio").upsert({"username": username, "stock_code": stock_code, "company_name": company_name, "amount": amount}).execute()


def remove_portfolio(username, stock_code):
    client = _get_client()
    client.table("portfolio").delete().eq("username", username).eq("stock_code", stock_code).execute()


# ===== analysis_history =====

def save_analysis_history(username, stock_code, company_name, total_score):
    client = _get_client()
    client.table("analysis_history").insert({"username": username, "stock_code": stock_code, "company_name": company_name, "total_score": total_score}).execute()


def get_analysis_history(username, limit=10):
    client = _get_client()
    result = client.table("analysis_history").select("*").eq("username", username).order("created_at", desc=True).limit(limit).execute()
    return result.data


def get_user_stats(username):
    client = _get_client()
    result = client.table("analysis_history").select("*").eq("username", username).execute()
    data = result.data
    if not data:
        return {"total_analyses": 0, "unique_stocks": 0}
    unique = set(r["stock_code"] for r in data)
    return {"total_analyses": len(data), "unique_stocks": len(unique)}


# ===== 互換性のため =====

def init_db():
    pass  # Supabaseでは不要

def get_connection():
    return None  # Supabase使用時は不要
