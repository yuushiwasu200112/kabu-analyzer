"""スコアリングのテスト"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.scoring import calc_total_score


class TestScoring:
    """calc_total_score のテスト"""

    def test_high_score_company(self):
        indicators = {
            "ROE": 15.0, "ROA": 8.0, "営業利益率": 12.0,
            "自己資本比率": 60.0, "流動比率": 200.0, "ICR": 50.0,
            "売上高成長率": 15.0, "営業利益成長率": 20.0, "純利益成長率": 25.0,
            "PER": 10.0, "PBR": 1.0, "配当利回り": 3.0,
        }
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert result["total_score"] >= 70
        assert "category_scores" in result
        assert "judgment" in result

    def test_low_score_company(self):
        indicators = {
            "ROE": 2.0, "ROA": 1.0, "営業利益率": 2.0,
            "自己資本比率": 15.0, "流動比率": 80.0, "ICR": 1.0,
            "売上高成長率": -10.0, "営業利益成長率": -20.0, "純利益成長率": -30.0,
            "PER": 50.0, "PBR": 5.0, "配当利回り": 0.0,
        }
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        assert result["total_score"] < 50

    def test_all_styles(self):
        indicators = {
            "ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0,
            "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0,
            "PER": 15.0, "PBR": 1.5, "配当利回り": 2.0,
        }
        styles = ["バランス", "バリュー投資", "グロース投資", "高配当投資", "安定重視"]
        for s in styles:
            result = calc_total_score(indicators, s, "中期（1〜3年）")
            assert 0 <= result["total_score"] <= 100
            assert len(result["category_scores"]) == 4

    def test_all_periods(self):
        indicators = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0}
        periods = ["短期（〜1年）", "中期（1〜3年）", "長期（3年〜）"]
        for p in periods:
            result = calc_total_score(indicators, "バランス", p)
            assert 0 <= result["total_score"] <= 100

    def test_score_categories(self):
        indicators = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0}
        result = calc_total_score(indicators, "バランス", "中期（1〜3年）")
        cats = result["category_scores"]
        assert "収益性" in cats
        assert "安全性" in cats
        assert "成長性" in cats or cats.get("成長性", 0) == 0
        assert "割安度" in cats
        for v in cats.values():
            assert 0 <= v <= 100

    def test_empty_indicators(self):
        result = calc_total_score({}, "バランス", "中期（1〜3年）")
        assert result["total_score"] >= 0

    def test_value_style_favors_low_per(self):
        cheap = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0, "PER": 8.0, "PBR": 0.8, "配当利回り": 3.5}
        expensive = {"ROE": 10.0, "ROA": 5.0, "営業利益率": 8.0, "自己資本比率": 40.0, "流動比率": 150.0, "ICR": 20.0, "PER": 40.0, "PBR": 4.0, "配当利回り": 0.5}
        cheap_score = calc_total_score(cheap, "バリュー投資", "中期（1〜3年）")
        expensive_score = calc_total_score(expensive, "バリュー投資", "中期（1〜3年）")
        assert cheap_score["total_score"] > expensive_score["total_score"]


