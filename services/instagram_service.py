"""
سرویس ارسال خودکار پست به اینستاگرام (اکانت کسب‌وکاری/سازنده که به صفحهٔ فیسبوک
بالا وصل است) — همان تصویر برندشدهٔ ۱۰۸۰×۱۰۸۰ فیسبوک (نرخ دالر + طلا + نقره) را
با یک کپشن مخصوص اینستاگرام (کوتاه‌تر، با هشتگ‌های اینستاگرامی) منتشر می‌کند.

تفاوت کلیدی با فیسبوک: Instagram Graph API آپلود مستقیم فایل باینری را قبول
نمی‌کند — فقط یک image_url عمومی می‌پذیرد. برای همین، تصویر ابتدا در یک باکت
**عمومی** Supabase Storage آپلود می‌شود (services/supabase_service.upload_public_file)
و لینک عمومی همان به Instagram داده می‌شود.

جریان انتشار طبق Instagram Content Publishing API (Graph API):
  ۱) POST /{ig-user-id}/media  با image_url و caption  → creation_id (کانتینر رسانه)
  ۲) (اختیاری ولی توصیه‌شده) چند بار GET /{creation_id}?fields=status_code
     تا وضعیت FINISHED شود (اینستاگرام گاهی چند ثانیه طول می‌دهد تا تصویر را
     دانلود/پردازش کند)
  ۳) POST /{ig-user-id}/media_publish با creation_id  → پست نهایی منتشر می‌شود

نیازمند: INSTAGRAM_BUSINESS_ACCOUNT_ID و همان FACEBOOK_PAGE_ACCESS_TOKEN (چون
اکانت اینستاگرام کسب‌وکاری زیرمجموعهٔ همان صفحهٔ فیسبوک است و توکن صفحه برای
هر دو کار می‌کند) — راهنمای کامل ساخت/اتصال در README.

فقط زمانی پست جدید ارسال می‌شود که تغییر محسوس نرخ (بیشتر یا مساوی
INSTAGRAM_CHANGE_THRESHOLD_PERCENT) نسبت به آخرین پست اینستاگرام رخ داده باشد؛
این وضعیت جدا از فیسبوک، در جدول Supabase (`ig_post_state`) نگهداری می‌شود.
"""
import asyncio
import logging
import time
from typing import Optional

import httpx

from config import (
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    FACEBOOK_PAGE_ACCESS_TOKEN,
    INSTAGRAM_CHANGE_THRESHOLD_PERCENT,
    INSTAGRAM_HASHTAGS,
    FACEBOOK_POST_SITE_URL,
    TELEGRAM_BOT_LINK,
    SOCIAL_POSTS_BUCKET,
)
from persian_date import get_afghan_datetime_str
from services import post_image_service
from services import supabase_service as db
from services.facebook_service import _build_current_state  # همان منطق تشخیص تغییر نرخ فیسبوک

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"
_TIMEOUT = 30.0
_PUBLISH_POLL_ATTEMPTS = 8
_PUBLISH_POLL_DELAY_SECONDS = 2.5


def _build_caption(quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict]) -> str:
    """
    کپشن اینستاگرام عمداً کوتاه‌تر و متفاوت از کپشن فیسبوک است: اینستاگرام برخلاف
    فیسبوک، کپشن‌های طولانیِ جدول‌مانند را به‌خوبی نمایش نمی‌دهد (بعد از چند خط
    "...more" می‌شود) و فرهنگ هشتگ‌گذاری‌اش هم متفاوت است — این‌جا فقط نرخ‌های
    کلیدی (دالر، طلا، نقره) + دعوت به ربات + هشتگ‌ها آورده می‌شود، نه تفکیک کامل
    همهٔ ارزها و همهٔ عیارهای طلا (که در خودِ تصویر پست هم به‌طور خلاصه دیده می‌شود).
    """
    usd_quote = quotes.get("usd")
    date_str = get_afghan_datetime_str()

    lines = [
        "💵 نرخ لحظه‌یی دالر، طلا و نقره در برابر افغانی — صراف",
        date_str,
        "",
    ]

    if usd_quote:
        local = usd_quote.get("local")
        saraf = usd_quote["saraf_quote"]
        buy = local["buy"] if local else saraf["buy"]
        sell = local["sell"] if local else saraf["sell"]
        lines.append(f"🇺🇸 دالر امریکایی — خرید: {buy:,.2f}   |   فروش: {sell:,.2f}")

    if gold_breakdown:
        gold_24k = gold_breakdown["karats"][24]
        lines.append(f"🥇 طلای ۲۴ عیار — {gold_24k['afn_per_gram']:,.0f} افغانی هر گرم")

    if silver_breakdown:
        lines.append(f"🥈 نقرهٔ خالص (۹۹۹) — {silver_breakdown['afn_per_gram']:,.0f} افغانی هر گرم")

    lines.append("")
    lines.append("🚀 نرخ همهٔ ارزها، مبدل جهانی و ماشین‌حساب طلا/نقره، رایگان و لحظه‌یی:")
    lines.append(TELEGRAM_BOT_LINK)
    if FACEBOOK_POST_SITE_URL:
        lines.append(FACEBOOK_POST_SITE_URL)

    if INSTAGRAM_HASHTAGS:
        lines.append("")
        lines.append(INSTAGRAM_HASHTAGS)

    caption = "\n".join(lines)
    # سقف کپشن اینستاگرام ۲۲۰۰ کاراکتر است — به‌عنوان محافظ نهایی کوتاه می‌شود
    # (در عمل با این ساختار خلاصه تقریباً هرگز به این سقف نمی‌رسد).
    if len(caption) > 2200:
        caption = caption[:2190].rstrip() + "…"
    return caption


async def _upload_image_get_public_url(image_bytes: bytes) -> Optional[str]:
    filename = f"rates-{int(time.time())}.png"
    return await asyncio.to_thread(db.upload_public_file, SOCIAL_POSTS_BUCKET, image_bytes, filename, "image/png")


async def _create_media_container(image_url: str, caption: str) -> Optional[str]:
    url = f"{GRAPH_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    params = {"image_url": image_url, "caption": caption, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, params=params)
            resp.raise_for_status()
        return resp.json().get("id")
    except Exception:
        logger.exception("خطا در ساخت کانتینر رسانهٔ اینستاگرام (media container)")
        return None


async def _wait_until_ready(creation_id: str) -> bool:
    """اینستاگرام گاهی چند ثانیه طول می‌دهد تا image_url را دانلود/پردازش کند؛
    قبل از media_publish، وضعیت را چک می‌کنیم تا خطای «رسانه آماده نیست» نگیریم."""
    url = f"{GRAPH_BASE}/{creation_id}"
    params = {"fields": "status_code", "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for _ in range(_PUBLISH_POLL_ATTEMPTS):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                status = resp.json().get("status_code")
                if status == "FINISHED":
                    return True
                if status == "ERROR":
                    logger.error("پردازش رسانهٔ اینستاگرام با خطا مواجه شد (status_code=ERROR).")
                    return False
            except Exception:
                logger.exception("خطا در بررسی وضعیت کانتینر رسانهٔ اینستاگرام")
            await asyncio.sleep(_PUBLISH_POLL_DELAY_SECONDS)
    # اگر بعد از همهٔ تلاش‌ها هنوز FINISHED نشد، بازهم یک تلاش نهایی برای publish
    # می‌کنیم (در عمل معمولاً تا این مرحله آماده است؛ عدم قطعیت شبکه را نباید به
    # معنای شکست قطعی گرفت).
    return True


async def _publish_container(creation_id: str) -> bool:
    url = f"{GRAPH_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    params = {"creation_id": creation_id, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, params=params)
            resp.raise_for_status()
        logger.info("پست اینستاگرام با موفقیت منتشر شد.")
        return True
    except Exception:
        logger.exception("خطا در انتشار نهایی پست اینستاگرام (media_publish)")
        return False


async def _post_to_instagram(image_bytes: bytes, caption: str) -> bool:
    if not INSTAGRAM_BUSINESS_ACCOUNT_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.warning("INSTAGRAM_BUSINESS_ACCOUNT_ID یا FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده؛ پست انجام نشد.")
        return False

    image_url = await _upload_image_get_public_url(image_bytes)
    if not image_url:
        logger.error("آپلود تصویر پست به باکت عمومی Supabase ناموفق بود؛ اینستاگرام پست نشد.")
        return False

    creation_id = await _create_media_container(image_url, caption)
    if not creation_id:
        return False

    if not await _wait_until_ready(creation_id):
        return False

    return await _publish_container(creation_id)


async def check_and_maybe_post(
    quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None, force: bool = False
) -> bool:
    """
    الگوی این تابع دقیقاً مثل facebook_service.check_and_maybe_post است (همان
    منطق تشخیص تغییر محسوس)، فقط با جدول وضعیت و آستانهٔ جداگانهٔ اینستاگرام،
    تا زمان‌بندی/آستانهٔ دو پلتفرم مستقل از هم قابل‌تنظیم باشد.

    force: اگر True باشد، بررسی «تغییر محسوس نرخ» نادیده گرفته می‌شود — برای
        نشر دستی (دکمهٔ ادمین در ربات) استفاده می‌شود.

    خروجی: True اگر پست واقعاً با موفقیت منتشر شد، در غیر این صورت False.
    """
    if not quotes:
        return False

    current_state = _build_current_state(quotes, gold_breakdown, silver_breakdown)
    if not current_state:
        return False

    last_state = db.get_ig_post_state()

    def _has_significant_change(current: dict, last: dict) -> bool:
        if not last:
            return True
        for key, value in current.items():
            old = last.get(key)
            if not old:
                continue
            pct = abs(value - old) / old * 100
            if pct >= INSTAGRAM_CHANGE_THRESHOLD_PERCENT:
                return True
        return False

    if not force and not _has_significant_change(current_state, last_state):
        return False

    usd_quote = quotes.get("usd")
    if not usd_quote or not gold_breakdown:
        logger.warning("نرخ دالر یا اطلاعات طلا در دسترس نیست؛ تولید تصویر پست اینستاگرام ممکن نیست.")
        return False

    try:
        date_str = get_afghan_datetime_str()
        image_bytes = await post_image_service.generate_facebook_post_image(
            usd_quote, gold_breakdown, date_str, silver_breakdown=silver_breakdown
        )
    except Exception:
        logger.exception("خطا در تولید تصویر پست اینستاگرام")
        return False

    caption = _build_caption(quotes, gold_breakdown, silver_breakdown)

    if await _post_to_instagram(image_bytes, caption):
        db.set_ig_post_state(current_state)
        return True
    return False
