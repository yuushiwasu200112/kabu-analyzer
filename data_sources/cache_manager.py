"""
分析データキャッシュ
EDINETから取得したデータをローカルに保存し、再取得を防ぐ
"""
import json
import os
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")


def _ensure_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")


def get_cache(key, max_age_hours=24):
    """
    キャッシュを取得。有効期限切れならNoneを返す
    """
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        # 有効期限チェック
        if time.time() - data.get("timestamp", 0) > max_age_hours * 3600:
            return None
        return data.get("value")
    except:
        return None


def set_cache(key, value):
    """キャッシュに保存"""
    _ensure_dir()
    path = _cache_path(key)
    try:
        with open(path, "w") as f:
            json.dump({"timestamp": time.time(), "value": value}, f, ensure_ascii=False)
    except:
        pass
