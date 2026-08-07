#!/usr/bin/env python3
"""
تست دستی تولید تصویر پست فیسبوک
این اسکریپت مستقل است و نیازی به فایل‌های دیگر پروژه ندارد.

نحوه اجرا در Railway Shell:
    python test_facebook_image.py

یا به‌صورت مستقیم:
    python3 test_facebook_image.py
"""

import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright

# ─── نرخ‌های نمونه برای تست ───
SAMPLE_RATES = {
    "sarai_shahzada": {"buy": 75.20, "sell": 75.45},
    "local_exchanges": [
        {"name": "صرافی عزیزی", "buy": 75.15, "sell": 75.50},
        {"name": "صرافی کابل", "buy": 75.10, "sell": 75.55},
    ],
    "global": {"usd_afn": 75.30, "timestamp": "2026-08-07 20:00"},
    "gold": {
        "24k": 6200,
        "22k": 5680,
        "21k": 5420,
        "18k": 4650,
    },
}

LOGO_URL = "https://i.postimg.cc/B6ZCWdXp/logosaraf.webp"

# ─── قالب HTML پست ───
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700;900&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    width: 1080px; height: 1080px;
    font-family: 'Vazirmatn', sans-serif;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    color: #fff;
    display: flex; flex-direction: column; align-items: center;
    padding: 40px; position: relative; overflow: hidden;
}
.glow {
    position: absolute; width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(56,189,248,0.15) 0%, transparent 70%);
    top: -200px; left: -200px; pointer-events: none;
}
.header {
    display: flex; align-items: center; gap: 20px;
    margin-bottom: 30px; z-index: 1;
}
.logo {
    width: 90px; height: 90px; border-radius: 20px;
    object-fit: contain; background: #fff; padding: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.title-box { text-align: center; }
.title-box h1 {
    font-size: 52px; font-weight: 900;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
}
.title-box p {
    font-size: 22px; color: #94a3b8; margin-top: 4px;
}
.grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; width: 100%; z-index: 1;
}
.card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 24px; padding: 28px;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.2);
}
.card-header {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 16px; padding-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}
.card-icon { font-size: 28px; }
.card-title { font-size: 24px; font-weight: 700; color: #e2e8f0; }
.rate-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.rate-row:last-child { border-bottom: none; }
.rate-label { font-size: 20px; color: #94a3b8; }
.rate-value { font-size: 22px; font-weight: 700; }
.buy { color: #4ade80; }
.sell { color: #f87171; }
.gold-card { grid-column: span 2; }
.gold-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 12px;
}
.gold-item {
    background: rgba(255,215,0,0.08);
    border: 1px solid rgba(255,215,0,0.2);
    border-radius: 16px; padding: 18px; text-align: center;
}
.gold-karat { font-size: 20px; font-weight: 700; color: #fbbf24; margin-bottom: 6px; }
.gold-price { font-size: 22px; font-weight: 900; color: #fff; }
.footer {
    margin-top: auto; padding-top: 24px;
    text-align: center; color: #64748b; font-size: 18px; z-index: 1;
}
.badge {
    display: inline-block; background: rgba(56,189,248,0.15);
    color: #38bdf8; padding: 6px 16px; border-radius: 20px;
    font-size: 16px; font-weight: 700; margin-bottom: 8px;
}
</style>
</head>
<body>
<div class="glow"></div>

<div class="header">
    <img src="{{LOGO_URL}}" class="logo" alt="Saraf Logo">
    <div class="title-box">
        <h1>نرخ لحظه‌ای ارز و طلا</h1>
        <p>کابل، افغانستان &mdash; {{DATE}}</p>
    </div>
</div>

<div class="grid">
    <div class="card">
        <div class="card-header">
            <span class="card-icon">🏛️</span>
            <span class="card-title">سرای شهزاده</span>
        </div>
        <div class="rate-row">
            <span class="rate-label">خرید دالر</span>
            <span class="rate-value buy">{{SARAI_BUY}} AFN</span>
        </div>
        <div class="rate-row">
            <span class="rate-label">فروش دالر</span>
            <span class="rate-value sell">{{SARAI_SELL}} AFN</span>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="card-icon">🌍</span>
            <span class="card-title">بازار جهانی</span>
        </div>
        <div class="rate-row">
            <span class="rate-label">USD/AFN</span>
            <span class="rate-value">{{GLOBAL_RATE}} AFN</span>
        </div>
        <div class="rate-row">
            <span class="rate-label">آخرین به‌روزرسانی</span>
            <span class="rate-value" style="font-size:16px;color:#94a3b8;">{{GLOBAL_TIME}}</span>
        </div>
    </div>

    <div class="card" style="grid-column: span 2;">
        <div class="card-header">
            <span class="card-icon">🏪</span>
            <span class="card-title">صرافی‌های محلی</span>
        </div>
        {{EXCHANGE_ROWS}}
    </div>

    <div class="card gold-card">
        <div class="card-header">
            <span class="card-icon">🥇</span>
            <span class="card-title">نرخ طلا (هر گرام به افغانی)</span>
        </div>
        <div class="gold-grid">
            <div class="gold-item"><div class="gold-karat">۲۴ عیار</div><div class="gold-price">{{GOLD_24}}</div></div>
            <div class="gold-item"><div class="gold-karat">۲۲ عیار</div><div class="gold-price">{{GOLD_22}}</div></div>
            <div class="gold-item"><div class="gold-karat">۲۱ عیار</div><div class="gold-price">{{GOLD_21}}</div></div>
            <div class="gold-item"><div class="gold-karat">۱۸ عیار</div><div class="gold-price">{{GOLD_18}}</div></div>
        </div>
    </div>
</div>

<div class="footer">
    <div class="badge">@sarafiaf_bot</div>
    <p>ربات Saraf &mdash; به‌روزترین نرخ‌های ارز و طلا در کابل</p>
    <p style="margin-top:4px;font-size:14px;">#saraf #صراف #نرخ_ارز #طلا #کابل #افغانستان</p>
</div>
</body>
</html>
"""


def build_html() -> str:
    """قالب HTML را با داده‌های نمونه پر می‌کند."""
    exchange_rows = ""
    for ex in SAMPLE_RATES["local_exchanges"]:
        exchange_rows += f"""
        <div class="rate-row">
            <span class="rate-label">{ex['name']}</span>
            <span>
                <span class="rate-value buy" style="margin-left:16px;">{ex['buy']}</span>
                <span class="rate-value sell">{ex['sell']}</span>
            </span>
        </div>"""

    html = HTML_TEMPLATE
    html = html.replace("{{LOGO_URL}}", LOGO_URL)
    html = html.replace("{{DATE}}", datetime.now().strftime("%Y/%m/%d %H:%M"))
    html = html.replace("{{SARAI_BUY}}", str(SAMPLE_RATES["sarai_shahzada"]["buy"]))
    html = html.replace("{{SARAI_SELL}}", str(SAMPLE_RATES["sarai_shahzada"]["sell"]))
    html = html.replace("{{GLOBAL_RATE}}", str(SAMPLE_RATES["global"]["usd_afn"]))
    html = html.replace("{{GLOBAL_TIME}}", SAMPLE_RATES["global"]["timestamp"])
    html = html.replace("{{EXCHANGE_ROWS}}", exchange_rows)
    html = html.replace("{{GOLD_24}}", f"{SAMPLE_RATES['gold']['24k']:,}")
    html = html.replace("{{GOLD_22}}", f"{SAMPLE_RATES['gold']['22k']:,}")
    html = html.replace("{{GOLD_21}}", f"{SAMPLE_RATES['gold']['21k']:,}")
    html = html.replace("{{GOLD_18}}", f"{SAMPLE_RATES['gold']['18k']:,}")
    return html


async def generate_image(output_path: str = "test_facebook_post.png"):
    """با Playwright یک اسکرین‌شات 1080×1080 از HTML می‌گیرد."""
    html_content = build_html()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1080, "height": 1080})

        # HTML را مستقیماً بارگذاری می‌کنیم
        await page.set_content(html_content, wait_until="networkidle")

        # کمی صبر می‌کنیم تا فونت و تصویر لود شوند
        await page.wait_for_timeout(2000)

        # اسکرین‌شات
        await page.screenshot(path=output_path, full_page=False)
        await browser.close()

    size_kb = os.path.getsize(output_path) / 1024
    print(f"✅ تصویر با موفقیت ساخته شد: {output_path}")
    print(f"   اندازه: {size_kb:.1f} KB")
    print(f"   ابعاد: 1080 × 1080")
    return output_path


if __name__ == "__main__":
    print("🧪 شروع تست تولید تصویر پست فیسبوک...")
    print("-" * 50)
    try:
        path = asyncio.run(generate_image())
        print("-" * 50)
        print("🎉 تست موفق بود! تصویر ساخته شد.")
        print(f"📁 مسیر فایل: {os.path.abspath(path)}")
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
