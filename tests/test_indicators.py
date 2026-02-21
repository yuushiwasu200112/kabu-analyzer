"""財務指標計算のテスト"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.indicators import calc_indicators, calc_growth


class TestCalcIndicators:
    def setup_method(self):
        self.sample_data = {
            "純利益": 1000000,
            "自己資本": 5000000,
            "総資産": 10000000,
            "営業利益": 800000,
            "売上高": 8000000,
            "支払利息": 10000,
            "流動資産": 3000000,
            "流動負債": 1500000,
            "1株配当": 50,
            "発行済株式数": 10000,
        }

    def test_roe(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["ROE"] == pytest.approx(20.0, rel=0.01)

    def test_roa(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["ROA"] == pytest.approx(10.0, rel=0.01)

    def test_operating_margin(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["営業利益率"] == pytest.approx(10.0, rel=0.01)

    def test_equity_ratio(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["自己資本比率"] == pytest.approx(50.0, rel=0.01)

    def test_current_ratio(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["流動比率"] == pytest.approx(200.0, rel=0.01)

    def test_eps(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["EPS"] == pytest.approx(100.0, rel=0.01)

    def test_bps(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["BPS"] == pytest.approx(500.0, rel=0.01)

    def test_per(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["PER"] == pytest.approx(10.0, rel=0.01)

    def test_pbr(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["PBR"] == pytest.approx(2.0, rel=0.01)

    def test_dividend_yield(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["配当利回り"] == pytest.approx(5.0, rel=0.01)

    def test_zero_price(self):
        result = calc_indicators(self.sample_data, 0)
        assert "PER" not in result or result.get("PER", 0) == 0
        assert "PBR" not in result or result.get("PBR", 0) == 0

    def test_zero_equity(self):
        data = self.sample_data.copy()
        data["自己資本"] = 0
        result = calc_indicators(data, 1000)
        assert "ROE" not in result or result.get("ROE", 0) == 0

    def test_zero_revenue(self):
        data = self.sample_data.copy()
        data["売上高"] = 0
        result = calc_indicators(data, 1000)
        assert "営業利益率" not in result or result.get("営業利益率", 0) == 0

    def test_missing_data(self):
        result = calc_indicators({}, 1000)
        assert isinstance(result, dict)

    def test_icr(self):
        result = calc_indicators(self.sample_data, 1000)
        assert result["ICR"] == pytest.approx(80.0, rel=0.01)


class TestCalcGrowth:
    def test_positive_growth(self):
        current = {"売上高": 1200000, "営業利益": 600000, "純利益": 400000}
        previous = {"売上高": 1000000, "営業利益": 500000, "純利益": 300000}
        result = calc_growth(current, previous)
        assert result["売上高成長率"] == pytest.approx(20.0, rel=0.01)
        assert result["営業利益成長率"] == pytest.approx(20.0, rel=0.01)
        assert result["純利益成長率"] == pytest.approx(33.33, rel=0.01)

    def test_negative_growth(self):
        current = {"売上高": 800000, "営業利益": 400000, "純利益": 200000}
        previous = {"売上高": 1000000, "営業利益": 500000, "純利益": 300000}
        result = calc_growth(current, previous)
        assert result["売上高成長率"] < 0

    def test_zero_previous(self):
        current = {"売上高": 1000000, "営業利益": 500000, "純利益": 300000}
        previous = {"売上高": 0, "営業利益": 0, "純利益": 0}
        result = calc_growth(current, previous)
        assert result.get("売上高成長率", 0) == 0
