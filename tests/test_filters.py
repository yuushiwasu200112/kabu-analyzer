"""フィルター（警告）のテスト"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.filters import check_filters


class TestFilters:
    def test_no_warnings_healthy(self):
        current = {"自己資本": 5000000, "総資産": 10000000, "純利益": 500000, "営業利益": 800000}
        warnings = check_filters(current, None)
        danger = [w for w in warnings if w["level"] == "danger"]
        assert len(danger) == 0

    def test_low_equity_ratio(self):
        current = {"自己資本": 500000, "総資産": 10000000, "純利益": 100000}
        warnings = check_filters(current, None)
        titles = [w["title"] for w in warnings]
        assert any("債務超過" in t for t in titles)

    def test_negative_profit(self):
        current = {"自己資本": 5000000, "総資産": 10000000, "純利益": -500000}
        warnings = check_filters(current, None)
        titles = [w["title"] for w in warnings]
        assert any("赤字" in t for t in titles)

    def test_consecutive_loss(self):
        current = {"自己資本": 5000000, "総資産": 10000000, "純利益": -500000}
        previous = {"純利益": -300000}
        warnings = check_filters(current, previous)
        danger = [w for w in warnings if w["level"] == "danger"]
        assert len(danger) >= 1

    def test_empty_data(self):
        warnings = check_filters({}, None)
        assert isinstance(warnings, list)
