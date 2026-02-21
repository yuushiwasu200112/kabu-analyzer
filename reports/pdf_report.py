"""
PDFレポート生成
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
import datetime
import os


def _register_font():
    """日本語フォント登録"""
    font_paths = [
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("JP", fp, subfontIndex=0))
                return "JP"
            except:
                continue
    return "Helvetica"


def generate_pdf(company_name, stock_code, indicators, score_result, warnings=None, stock_info=None):
    """PDFレポートを生成してバイトデータを返す"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    font = _register_font()

    # 色定義
    blue = HexColor("#2E75B6")
    dark = HexColor("#1B3A5C")
    gray = HexColor("#666666")
    red = HexColor("#E74C3C")
    green = HexColor("#27AE60")
    bg_light = HexColor("#F0F4F8")

    y = h - 25 * mm

    # ── ヘッダー ──
    c.setFillColor(dark)
    c.rect(0, h - 45 * mm, w, 45 * mm, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(font, 24)
    c.drawString(20 * mm, h - 25 * mm, "📊 Kabu Analyzer レポート")
    c.setFont(font, 12)
    c.drawString(20 * mm, h - 35 * mm, f"{company_name}（{stock_code}）")
    c.setFont(font, 9)
    c.drawString(20 * mm, h - 42 * mm, f"作成日: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

    y = h - 60 * mm

    # ── 総合スコア ──
    score = score_result["total_score"]
    judgment = score_result["judgment"]
    style_name = score_result.get("style", "バランス")
    period_name = score_result.get("period", "中期")

    c.setFillColor(bg_light)
    c.roundRect(15 * mm, y - 35 * mm, w - 30 * mm, 35 * mm, 5, fill=1)

    c.setFillColor(dark)
    c.setFont(font, 14)
    c.drawString(20 * mm, y - 10 * mm, "■ 総合スコア")

    if score >= 75:
        c.setFillColor(green)
    elif score >= 50:
        c.setFillColor(HexColor("#F39C12"))
    else:
        c.setFillColor(red)
    c.setFont(font, 36)
    c.drawString(25 * mm, y - 30 * mm, f"{score}点")

    c.setFillColor(dark)
    c.setFont(font, 14)
    c.drawString(65 * mm, y - 25 * mm, judgment)
    c.setFillColor(gray)
    c.setFont(font, 10)
    c.drawString(65 * mm, y - 32 * mm, f"投資スタイル: {style_name} ｜ 投資期間: {period_name}")

    y -= 45 * mm

    # ── カテゴリ別スコア ──
    c.setFillColor(dark)
    c.setFont(font, 14)
    c.drawString(20 * mm, y, "■ カテゴリ別スコア")
    y -= 8 * mm

    for cat, cat_score in score_result["category_scores"].items():
        c.setFillColor(dark)
        c.setFont(font, 11)
        c.drawString(25 * mm, y, f"{cat}: {cat_score}点")

        # バー描画
        bar_x = 80 * mm
        bar_w = 100 * mm
        bar_h = 5 * mm
        c.setFillColor(HexColor("#E0E0E0"))
        c.roundRect(bar_x, y - 1, bar_w, bar_h, 2, fill=1)
        if cat_score >= 75:
            c.setFillColor(green)
        elif cat_score >= 50:
            c.setFillColor(HexColor("#F39C12"))
        else:
            c.setFillColor(red)
        c.roundRect(bar_x, y - 1, bar_w * cat_score / 100, bar_h, 2, fill=1)
        y -= 10 * mm

    y -= 5 * mm

    # ── 警告 ──
    if warnings:
        c.setFillColor(dark)
        c.setFont(font, 14)
        c.drawString(20 * mm, y, "■ 警告・注意事項")
        y -= 8 * mm
        for w_item in warnings:
            c.setFillColor(red if w_item["level"] == "danger" else HexColor("#F39C12"))
            c.setFont(font, 10)
            c.drawString(25 * mm, y, f"{w_item['icon']} {w_item['title']}: {w_item['message'][:50]}")
            y -= 7 * mm
        y -= 3 * mm

    # ── 株価情報 ──
    if stock_info and stock_info.get("current_price", 0) > 0:
        c.setFillColor(dark)
        c.setFont(font, 14)
        c.drawString(20 * mm, y, "■ 株価情報")
        y -= 8 * mm
        c.setFont(font, 10)
        c.setFillColor(gray)
        price = stock_info["current_price"]
        cap = stock_info.get("market_cap", 0)
        cap_str = f"¥{cap/1e12:.1f}兆" if cap >= 1e12 else f"¥{cap/1e8:.0f}億" if cap > 0 else "---"
        c.drawString(25 * mm, y, f"株価: ¥{price:,.0f}  ｜  PER: {stock_info.get('per', 0):.1f}倍  ｜  PBR: {stock_info.get('pbr', 0):.2f}倍  ｜  時価総額: {cap_str}")
        y -= 12 * mm

    # ── 主要指標 ──
    c.setFillColor(dark)
    c.setFont(font, 14)
    c.drawString(20 * mm, y, "■ 主要財務指標")
    y -= 8 * mm

    # テーブルヘッダー
    c.setFillColor(blue)
    c.rect(15 * mm, y - 1, w - 30 * mm, 7 * mm, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(font, 9)
    col_x = [20 * mm, 60 * mm, 100 * mm, 140 * mm]
    c.drawString(col_x[0], y + 1, "指標名")
    c.drawString(col_x[1], y + 1, "数値")
    c.drawString(col_x[2], y + 1, "指標名")
    c.drawString(col_x[3], y + 1, "数値")
    y -= 8 * mm

    # 指標データ
    metrics = [
        ("ROE", "%"), ("ROA", "%"), ("営業利益率", "%"), ("配当利回り", "%"),
        ("自己資本比率", "%"), ("流動比率", "%"), ("ICR", "倍"),
        ("PER", "倍"), ("PBR", "倍"), ("EPS", "円"), ("BPS", "円"),
        ("売上高成長率", "%"), ("営業利益成長率", "%"), ("純利益成長率", "%"),
    ]

    c.setFont(font, 9)
    row = 0
    for i, (name, unit) in enumerate(metrics):
        val = indicators.get(name)
        if val is None:
            continue
        col = (row % 2) * 2
        if col == 0 and row > 0 and row % 2 == 0:
            y -= 6 * mm
        if y < 25 * mm:
            c.showPage()
            y = h - 20 * mm
            c.setFont(font, 9)

        c.setFillColor(dark)
        c.drawString(col_x[col], y, name)
        c.setFillColor(gray)
        if unit == "円":
            c.drawString(col_x[col + 1], y, f"{val:,.0f}{unit}")
        else:
            c.drawString(col_x[col + 1], y, f"{val:.2f}{unit}")
        row += 1

    # ── フッター ──
    c.setFillColor(gray)
    c.setFont(font, 8)
    c.drawString(20 * mm, 12 * mm, "※ 本レポートは投資助言ではありません。投資判断はご自身の責任で行ってください。")
    c.drawString(20 * mm, 8 * mm, f"Powered by Kabu Analyzer ｜ データ出典: EDINET")

    c.save()
    buf.seek(0)
    return buf.getvalue()
