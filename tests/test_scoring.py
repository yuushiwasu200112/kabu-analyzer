"""スコアリングのテスト"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.scoring import calc_total_score, score_indicator


class TestScoreIndicator:
    """個別指標スコアのテスト"""

    def test_roe_excellent(self):
        assert score_indicator("ROE", 30) == 100

    def test_roe_zero(self):
        assert score_indicator("ROE", 0) == 0

    def test_roe_mid(self):
        s = score_indicator("ROE", 15)
        assert 40 <= s <= 60

    def test_per_low_is_good(self):
        assert score_indicator("PER", 5) == 100

    def test_per_high_is_bad(self):
        assert score_indicator("PER", 50) == 0

    def test_pbr_low_is_good(self):
        assert score_indicator("PBR", 0.3) == 100

    def test_unknown_indicator(self):
        assert score_indicator("不明な指標", 10) is None

    def test_none_value(self):
        assert score_indicator("ROE", None) is None


class TestScoring:
    """calc_total_score のテスト"""

    def test_high_score_company(self):
        indicators = {
            "ROE": 25.0, "ROA": 12.0, "営業利益率": 20.0,
            "自己資本比率": 70.0, "流動比率": 350.0, "ICR": 40.0,
            "有利子負債比率": 5.0,
            "売上高成長率": 15.0, "営業利益成長率": 25.0, "純利益成長率": 30.0, "総資産成長率": 10.0,
            "PER": 8.0, "PBR": 0.6, "配当利回り": 5.0,
        }
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert result["total_score"] >= 75
        assert result["judgment"] == "★ スコア高"

    def test_low_score_company(self):
        indicators = {
            "ROE": 2.0, "ROA": 1.0, "営業利益率": 2.0,
            "自己資本比率": 15.0, "流動比率": 80.0, "ICR": 1.0,
            "有利子負債比率": 70.0,
            "売上高成長率": -10.0, "営業利益成長率": -20.0, "純利益成長率": -30.0, "総資産成長率": -5.0,
            "PER": 50.0, "PBR": 5.0, "配当利回り": 0.0,
        }
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert result["total_score"] < 30
        assert result["judgment"] == "✖ スコア低"

    def test_mid_score_company(self):
        indicators = {
            "ROE": 8.0, "ROA": 3.0, "営業利益率": 7.0, "配当利回り": 2.0,
            "自己資本比率": 35.0, "流動比率": 130.0, "有利子負債比率": 45.0, "ICR": 5.0,
            "売上高成長率": 2.0, "営業利益成長率": 3.0, "純利益成長率": 5.0, "総資産成長率": 2.0,
            "PER": 18.0, "PBR": 1.8,
        }
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert 25 <= result["total_score"] <= 55

    def test_all_styles(self):
        indicators = {
            "ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0,
            "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0,
            "PER": 15.0, "PBR": 1.5, "配当利回り": 2.0,
        }
        styles = ["バランス", "バリュー投資", "グロース投資", "高配当投資", "安定性重視"]
        for s in styles:
            result = calc_total_score(indicators, s, "中期（1〜3年）")
            assert 0 <= result["total_score"] <= 100
            assert len(result["category_scores"]) == 4

    def test_all_periods(self):
        indicators = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0}
        periods = ["短期（〜1年）", "中期（1〜3年）", "長期（3年以上）"]
        for p in periods:
            result = calc_total_score(indicators, "バランス", p)
            assert 0 <= result["total_score"] <= 100

    def test_score_categories(self):
        indicators = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0}
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        cats = result["category_scores"]
        assert "収益性" in cats
        assert "安全性" in cats
        assert "成長性" in cats
        assert "割安度" in cats
        for v in cats.values():
            assert 0 <= v <= 100

    def test_empty_indicators(self):
        result = calc_total_score({}, "バランス", "中期（1〜3年）")
        assert result["total_score"] == 0

    def test_value_style_favors_low_per(self):
        cheap = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0, "PER": 8.0, "PBR": 0.8, "配当利回り": 3.5}
        expensive = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0, "PER": 40.0, "PBR": 4.0, "配当利回り": 0.5}
        cheap_score = calc_total_score(cheap, "バリュー投資", "中期（1〜3年）")
        expensive_score = calc_total_score(expensive, "バリュー投資", "中期（1〜3年）")
        assert cheap_score["total_score"] > expensive_score["total_score"]

    def test_growth_style_favors_high_growth(self):
        high_growth = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0,
                       "売上高成長率": 20.0, "営業利益成長率": 30.0, "純利益成長率": 40.0, "総資産成長率": 15.0}
        low_growth = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0,
                      "売上高成長率": -5.0, "営業利益成長率": -10.0, "純利益成長率": -15.0, "総資産成長率": -5.0}
        high_score = calc_total_score(high_growth, "グロース投資", "中期（1〜3年）")
        low_score = calc_total_score(low_growth, "グロース投資", "中期（1〜3年）")
        assert high_score["total_score"] > low_score["total_score"]

    def test_missing_categories_reported(self):
        indicators = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0}
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert "missing_categories" in result
        assert "成長性" in result["missing_categories"]

    def test_no_missing_with_full_data(self):
        indicators = {
            "ROE": 15.0, "ROA": 7.0, "営業利益率": 12.0, "配当利回り": 3.0,
            "自己資本比率": 50.0, "流動比率": 200.0, "有利子負債比率": 20.0, "ICR": 15.0,
            "売上高成長率": 10.0, "営業利益成長率": 15.0, "純利益成長率": 20.0, "総資産成長率": 8.0,
            "PER": 12.0, "PBR": 1.2,
        }
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert result["missing_categories"] == []

    def test_score_capped_at_100(self):
        extreme = {
            "ROE": 100.0, "ROA": 50.0, "営業利益率": 80.0, "配当利回り": 20.0,
            "自己資本比率": 99.0, "流動比率": 1000.0, "有利子負債比率": 0.0, "ICR": 200.0,
            "売上高成長率": 50.0, "営業利益成長率": 80.0, "純利益成長率": 100.0, "総資産成長率": 30.0,
            "PER": 3.0, "PBR": 0.2,
        }
        result = calc_total_score(extreme, "バランス", "中期（1〜3年）")
        assert result["total_score"] <= 100

    def test_unknown_style_defaults_to_balance(self):
        indicators = {"ROE": 10.0, "ROA": 5.0}
        result = calc_total_score(indicators, "存在しないスタイル", "中期（1〜3年）")
        assert 0 <= result["total_score"] <= 100
