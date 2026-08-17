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


def _extract_graph_error(resp: httpx.Response) -> str:
    """پیام خطای واقعی Meta Graph API را از پاسخ استخراج می‌کند (همان کمکی که
    facebook_service دارد) — تا دلیل دقیق شکست (کمبود permission، توکن نامعتبر،
    شناسهٔ اکانت اشتباه و...) در پیام نتیجهٔ دکمهٔ نشر دستی دیده شود."""
    try:
        err = resp.json().get("error", {})
        parts = [err.get("message") or resp.text[:300]]
        if err.get("type"):
            parts.append(f"type={err['type']}")
        if err.get("code") is not None:
            parts.append(f"code={err['code']}")
        if err.get("error_subcode") is not None:
            parts.append(f"subcode={err['error_subcode']}")
        return " | ".join(str(p) for p in parts)
    except Exception:
        return (resp.text or "پاسخ نامشخص از Graph API")[:300]


async def _create_media_container(image_url: str, caption: str) -> tuple[Optional[str], str]:
    url = f"{GRAPH_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    params = {"image_url": image_url, "caption": caption, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, params=params)
        if resp.status_code >= 400:
            detail = _extract_graph_error(resp)
            logger.error("خطای Graph API هنگام ساخت کانتینر رسانهٔ اینستاگرام (HTTP %s): %s", resp.status_code, detail)
            return None, detail
        return resp.json().get("id"), "ok"
    except Exception as exc:
        logger.exception("خطا در ساخت کانتینر رسانهٔ اینستاگرام (media container)")
        return None, f"خطای شبکه/غیرمنتظره: {exc}"


async def _wait_until_ready(creation_id: str) -> tuple[bool, str]:
    """اینستاگرام گاهی چند ثانیه طول می‌دهد تا image_url را دانلود/پردازش کند؛
    قبل از media_publish، وضعیت را چک می‌کنیم تا خطای «رسانه آماده نیست» نگیریم."""
    url = f"{GRAPH_BASE}/{creation_id}"
    params = {"fields": "status_code", "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    last_detail = "ok"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for _ in range(_PUBLISH_POLL_ATTEMPTS):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code >= 400:
                    last_detail = _extract_graph_error(resp)
                else:
                    status = resp.json().get("status_code")
                    if status == "FINISHED":
                        return True, "ok"
                    if status == "ERROR":
                        last_detail = "پردازش رسانه در سمت اینستاگرام با خطا مواجه شد (status_code=ERROR) — معمولاً یعنی image_url در دسترس نبود یا فرمت تصویر پذیرفته نشد."
                        logger.error(last_detail)
                        return False, last_detail
            except Exception as exc:
                last_detail = f"خطای شبکه/غیرمنتظره: {exc}"
                logger.exception("خطا در بررسی وضعیت کانتینر رسانهٔ اینستاگرام")
            await asyncio.sleep(_PUBLISH_POLL_DELAY_SECONDS)
    # اگر بعد از همهٔ تلاش‌ها هنوز FINISHED نشد، بازهم یک تلاش نهایی برای publish
    # می‌کنیم (در عمل معمولاً تا این مرحله آماده است؛ عدم قطعیت شبکه را نباید به
    # معنای شکست قطعی گرفت).
    return True, last_detail


async def _publish_container(creation_id: str) -> tuple[bool, str]:
    url = f"{GRAPH_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    params = {"creation_id": creation_id, "access_token": FACEBOOK_PAGE_ACCESS_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, params=params)
        if resp.status_code >= 400:
            detail = _extract_graph_error(resp)
            logger.error("خطای Graph API هنگام انتشار نهایی پست اینستاگرام (HTTP %s): %s", resp.status_code, detail)
            return False, detail
        logger.info("پست اینستاگرام با موفقیت منتشر شد.")
        return True, "ok"
    except Exception as exc:
        logger.exception("خطا در انتشار نهایی پست اینستاگرام (media_publish)")
        return False, f"خطای شبکه/غیرمنتظره: {exc}"


async def _post_to_instagram(image_bytes: bytes, caption: str) -> tuple[bool, str]:
    if not INSTAGRAM_BUSINESS_ACCOUNT_ID or not FACEBOOK_PAGE_ACCESS_TOKEN:
        msg = "INSTAGRAM_BUSINESS_ACCOUNT_ID یا FACEBOOK_PAGE_ACCESS_TOKEN تنظیم نشده"
        logger.warning(msg)
        return False, msg

    image_url = await _upload_image_get_public_url(image_bytes)
    if not image_url:
        msg = "آپلود تصویر پست به باکت عمومی Supabase ناموفق بود (بررسی کنید باکت social-posts وجود دارد و public است)"
        logger.error(msg)
        return False, msg

    creation_id, detail = await _create_media_container(image_url, caption)
    if not creation_id:
        return False, detail

    ready, detail = await _wait_until_ready(creation_id)
    if not ready:
        return False, detail

    return await _publish_container(creation_id)


async def check_and_maybe_post(
    quotes: dict, gold_breakdown: Optional[dict], silver_breakdown: Optional[dict] = None, force: bool = False
) -> tuple[bool, str]:
    """
    الگوی این تابع دقیقاً مثل facebook_service.check_and_maybe_post است (همان
    منطق تشخیص تغییر محسوس)، فقط با جدول وضعیت و آستانهٔ جداگانهٔ اینستاگرام،
    تا زمان‌بندی/آستانهٔ دو پلتفرم مستقل از هم قابل‌تنظیم باشد.

    force: اگر True باشد، بررسی «تغییر محسوس نرخ» نادیده گرفته می‌شود — برای
        نشر دستی (دکمهٔ ادمین در ربات) استفاده می‌شود.

    خروجی: (True, "ok") اگر پست واقعاً با موفقیت منتشر شد؛ در غیر این صورت
    (False, دلیل‌به‌فارسی) — دقیقاً مثل facebook_service، برای نمایش مستقیم به
    ادمین در پیام نتیجهٔ دکمهٔ نشر دستی.
    """
    if not quotes:
        return False, "نرخی در دسترس نیست"

    current_state = _build_current_state(quotes, gold_breakdown, silver_breakdown)
    if not current_state:
        return False, "نرخی در دسترس نیست"

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
        return False, "تغییر محسوس نرخ رخ نداده (پست لازم نبود)"

    usd_quote = quotes.get("usd")
    if not usd_quote or not gold_breakdown:
        msg = "نرخ دالر یا اطلاعات طلا در دسترس نیست"
        logger.warning(msg)
        return False, msg

    try:
        date_str = get_afghan_datetime_str()
        image_bytes = await post_image_service.generate_facebook_post_image(
            usd_quote, gold_breakdown, date_str, silver_breakdown=silver_breakdown
        )
    except Exception as exc:
        logger.exception("خطا در تولید تصویر پست اینستاگرام")
        return False, f"خطا در تولید تصویر: {exc}"

    caption = _build_caption(quotes, gold_breakdown, silver_breakdown)

    ok, detail = await _post_to_instagram(image_bytes, caption)
    if ok:
        db.set_ig_post_state(current_state)
    return ok, detail
