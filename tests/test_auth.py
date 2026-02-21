"""認証のテスト"""
import pytest
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auth.auth_manager import _hash_password, register_user, login_user, check_usage_limit, update_usage


class TestAuth:
    """認証機能のテスト"""

    def test_hash_password(self):
        h1 = _hash_password("test123")
        h2 = _hash_password("test123")
        h3 = _hash_password("different")
        assert h1 == h2
        assert h1 != h3

    def test_hash_not_plaintext(self):
        h = _hash_password("mypassword")
        assert h != "mypassword"
        assert len(h) == 64  # SHA256

    def test_plans_defined(self):
        from auth.auth_manager import PLANS
        assert "free" in PLANS
        assert "pro" in PLANS
        assert "premium" in PLANS
        assert PLANS["free"]["monthly_analyses"] == 5
        assert PLANS["pro"]["monthly_analyses"] == 50
        assert PLANS["premium"]["monthly_analyses"] == -1


