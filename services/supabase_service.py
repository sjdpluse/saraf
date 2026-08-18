"""
لایهٔ ارتباط با Supabase.
مسئولیت‌ها:
  - ثبت/به‌روزرسانی کاربران ربات (برای پیام همگانی / broadcast)
  - ذخیرهٔ تاریخچهٔ نرخ ارز و طلا (نرخ مرجع بین‌المللی)
  - ذخیرهٔ تاریخچهٔ نرخ بازارهای محلی افغانستان (سرای شهزاده، خراسان، د افغانستان بانک)
  - مدیریت تنظیمات حاشیهٔ سود صراف (spread) به ازای هر ارز
  - بازیابی نزدیک‌ترین رکورد تاریخی برای مقایسه
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL و SUPABASE_KEY باید در متغیرهای محیطی تنظیم شوند."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ---------------------------------------------------------------------------
# کاربران
# ---------------------------------------------------------------------------
def upsert_user(chat_id: int, username: str | None, full_name: str | None) -> None:
    try:
        get_client().table("users").upsert(
            {
                "chat_id": chat_id,
                "username": username,
                "full_name": full_name,
                "is_active": True,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="chat_id",
        ).execute()
    except Exception:
        logger.exception("خطا در ثبت کاربر در Supabase")

# ---------------------------------------------------------------------------
# سفارش‌های خرید و فروش تتر (USDT)
# ---------------------------------------------------------------------------
def insert_usdt_order(order: dict) -> Optional[dict]:
    """سفارش را ثبت می‌کند و ردیف کامل (شامل id) را برمی‌گرداند، یا None در صورت خطا."""
    try:
        res = get_client().table("usdt_orders").insert(order).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception:
        logger.exception("خطا در ثبت سفارش تتر")
        return None


def update_usdt_order_status(order_id: int, status: str, **extra_fields) -> None:
    try:
        fields = {"status": status, **extra_fields}
        get_client().table("usdt_orders").update(fields).eq("id", order_id).execute()
    except Exception:
        logger.exception("خطا در به‌روزرسانی وضعیت سفارش تتر")


def update_usdt_order_status_audited(
    order_id: int, status: str, *, changed_by: Optional[int] = None, reason: Optional[str] = None, **extra_fields
) -> None:
    """مثل update_usdt_order_status، ولی علاوه بر آن actor/reason را روی ردیف
    تاریخچه‌ای که trigger پایگاه‌داده خودش ساخته می‌نویسد.

    این کار در دو مرحله (نه یک تراکنش اتمیک واحد) انجام می‌شود، چون هر فراخوانی
    PostgREST یک تراکنش مستقل است و امکان انتقال یک session variable بین دو
    HTTP request به سرور جداگانه وجود ندارد. مرحلهٔ دوم best-effort است: اگر
    شکست بخورد، خودِ تغییر وضعیت (که مرحلهٔ حیاتی است) قبلاً با موفقیت ثبت شده و
    خراب نمی‌شود — فقط attribution آن روی جدول تاریخچه گم می‌شود، که در audit_log
    عمومی (که همزمان توسط لایهٔ سرویس نوشته می‌شود) همچنان قابل ردیابی است.
    """
    update_usdt_order_status(order_id, status, **extra_fields)
    if changed_by is None and reason is None:
        return
    try:
        patch = {}
        if changed_by is not None:
            patch["changed_by"] = changed_by
        if reason is not None:
            patch["reason"] = reason
        (
            get_client()
            .table("usdt_order_status_history")
            .update(patch)
            .eq("order_id", order_id)
            .eq("to_status", status)
            .is_("changed_by", "null")
            .execute()
        )
    except Exception:
        logger.exception("خطا در ثبت actor/reason روی تاریخچهٔ وضعیت سفارش %s", order_id)


def mark_usdt_order_confirmed(order_id: int) -> None:
    update_usdt_order_status(order_id, "confirmed", confirmed_at=datetime.now(timezone.utc).isoformat())


def mark_usdt_order_completed(order_id: int) -> None:
    update_usdt_order_status(order_id, "completed", completed_at=datetime.now(timezone.utc).isoformat())


def mark_usdt_order_cancelled(order_id: int) -> None:
    update_usdt_order_status(order_id, "cancelled", cancelled_at=datetime.now(timezone.utc).isoformat())


def set_usdt_order_rating(order_id: int, chat_id: int, rating: int, comment: Optional[str] = None) -> bool:
    """فقط صاحب سفارش (chat_id مطابق) و فقط برای سفارش‌های completed می‌تواند امتیاز ثبت کند."""
    try:
        order = get_usdt_order_by_id(order_id)
        if not order or order.get("chat_id") != chat_id or order.get("status") != "completed":
            return False
        get_client().table("usdt_orders").update(
            {
                "rating": rating,
                "rating_comment": comment,
                "rated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", order_id).execute()
        return True
    except Exception:
        logger.exception("خطا در ثبت امتیاز سفارش تتر")
        return False


def get_usdt_stats() -> dict:
    """آمار اعتمادساز عمومی — تعداد معاملات تکمیل‌شده و میانگین امتیاز."""
    try:
        completed_res = (
            get_client()
            .table("usdt_orders")
            .select("id", count="exact")
            .eq("status", "completed")
            .execute()
        )
        completed_count = completed_res.count or 0

        rating_res = (
            get_client()
            .table("usdt_orders")
            .select("rating")
            .not_.is_("rating", "null")
            .execute()
        )
        ratings = [r["rating"] for r in (rating_res.data or []) if r.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        return {
            "completed_orders": completed_count,
            "average_rating": avg_rating,
            "rating_count": len(ratings),
        }
    except Exception:
        logger.exception("خطا در محاسبهٔ آمار تتر")
        return {"completed_orders": 0, "average_rating": None, "rating_count": 0}


def get_pending_usdt_orders(limit: int = 20) -> list[dict]:
    try:
        res = (
            get_client()
            .table("usdt_orders")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        logger.exception("خطا در خواندن سفارش‌های در انتظار تتر")
        return []


def get_usdt_order_by_id(order_id: int) -> Optional[dict]:
    try:
        res = (
            get_client()
            .table("usdt_orders")
            .select("*")
            .eq("id", order_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        logger.exception("خطا در خواندن سفارش تتر")
        return None


def set_order_card_path(order_id: int, path: str) -> None:
    try:
        get_client().table("usdt_orders").update({"card_image_path": path}).eq("id", order_id).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ مسیر کارت دیجیتال سفارش")


def get_usdt_orders_by_chat_id(chat_id: int, limit: int = 50) -> list[dict]:
    """تاریخچهٔ سفارش‌های یک کاربر خاص — برای صفحهٔ «سفارش‌های من» در مینی‌اپ."""
    try:
        res = (
            get_client()
            .table("usdt_orders")
            .select("*")
            .eq("chat_id", chat_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        logger.exception("خطا در خواندن تاریخچهٔ سفارش‌های کاربر")
        return []


def upload_public_file(bucket: str, file_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
    """
    فایل را در یک باکت **عمومی** Supabase Storage آپلود می‌کند و لینک عمومی دائمی
    آن را برمی‌گرداند. برخلاف upload_private_file (که برای مدارک KYC/رسیدها به‌کار
    می‌رود)، اینجا هیچ داده‌ی حساسی وجود ندارد — فقط تصویر پست نرخ ارز که قرار است
    به‌هرحال به‌صورت عمومی در فیسبوک/اینستاگرام منتشر شود؛ تنها دلیل آپلودش این
    است که Instagram Graph API (برخلاف فیسبوک) آپلود مستقیم فایل باینری را قبول
    نمی‌کند و صرفاً یک image_url عمومی می‌پذیرد.

    ⚠️ **نیازمند اقدام دستی در Supabase**: باکت (پیش‌فرض SOCIAL_POSTS_BUCKET =
    "social-posts") باید public ساخته شود — رجوع کنید به
    supabase/migrations/20260816_001_instagram_automation.sql
    """
    try:
        storage = get_client().storage.from_(bucket)
        storage.upload(filename, file_bytes, {"content-type": content_type, "upsert": "true"})
        return storage.get_public_url(filename)
    except Exception:
        logger.exception("خطا در آپلود فایل عمومی به باکت %s", bucket)
        return None


def upload_usdt_receipt(file_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
    """
    رسید/اسکرین‌شات ارسالی از مینی‌اپ را در یک باکت **خصوصی** Supabase Storage
    آپلود می‌کند و یک signed URL ۲۴ساعته برمی‌گرداند (نه لینک عمومی دائمی).

    ⚠️ تغییر امنیتی (SARAF 2.0 Spec §11): این تابع قبلاً از storage.get_public_url
    استفاده می‌کرد؛ چون نام فایل از الگوی قابل‌حدس‌زدن `{chat_id}_{timestamp}.ext`
    ساخته می‌شود، رسید پرداخت (که می‌تواند شمارهٔ حساب/کارت را نشان دهد) عملاً
    برای هرکسی که لینک را حدس بزند در دسترس بود.

    **این یک راه‌حل میانی است، نه ایده‌آل**: مقدار برگشتی همچنان یک URL منقضی‌شونده
    است (نه یک شناسهٔ پایدار)، چون قرارداد فعلی API (`receipt_url` که مستقیماً در
    ثبت سفارش استفاده می‌شود) بدون تغییر فرانت‌اند مینی‌اپ حفظ شده است. اعتبار ۲۴
    ساعته برای این‌که ادمین طی همان روز سفارش را بررسی کند کافی است، اما اگر
    بررسی دیرتر انجام شود، لینک منقضی می‌شود. راه‌حل کامل این است که فقط مسیر
    داخلی فایل ذخیره شود و صفحهٔ بررسی ادمین هر بار یک signed URL تازه بسازد —
    این تغییر نیازمند بازبینی جریان بررسی سفارش در admin_bot.py/فرانت‌اند است که
    خارج از محدودهٔ این تغییر انجام نشده.

    **نیازمند اقدام دستی در Supabase**: باکت USDT_RECEIPTS_BUCKET باید به‌صورت
    private ساخته/تنظیم شود (دقیقاً مثل USDT_KYC_DOCS_BUCKET که از قبل private
    است) — این کار از طریق کد قابل‌انجام نیست.
    """
    from config import USDT_RECEIPTS_BUCKET

    path = upload_private_file(USDT_RECEIPTS_BUCKET, file_bytes, filename, content_type)
    if not path:
        return None
    return get_signed_url(USDT_RECEIPTS_BUCKET, path, expires_in=24 * 60 * 60)

# ---------------------------------------------------------------------------
# وضعیت آخرین پست فیسبوک (برای تشخیص تغییر محسوس نرخ)
# ---------------------------------------------------------------------------
def get_fb_post_state() -> dict:
    try:
        res = (
            get_client()
            .table("fb_post_state")
            .select("rates")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["rates"] or {}
        return {}
    except Exception:
        logger.exception("خطا در خواندن وضعیت پست فیسبوک")
        return {}


def set_fb_post_state(state: dict) -> None:
    try:
        get_client().table("fb_post_state").upsert(
            {"id": 1, "rates": state, "updated_at": datetime.now(timezone.utc).isoformat()},
            on_conflict="id",
        ).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ وضعیت پست فیسبوک")


# ---------------------------------------------------------------------------
# وضعیت آخرین پست اینستاگرام (برای تشخیص تغییر محسوس نرخ) — دقیقاً همان الگوی
# fb_post_state، فقط در جدول جداگانه چون چرخهٔ پست اینستاگرام مستقل از فیسبوک
# است (ممکن است threshold یا زمان‌بندی متفاوتی داشته باشند).
# ---------------------------------------------------------------------------
def get_ig_post_state() -> dict:
    try:
        res = (
            get_client()
            .table("ig_post_state")
            .select("rates")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["rates"] or {}
        return {}
    except Exception:
        logger.exception("خطا در خواندن وضعیت پست اینستاگرام")
        return {}


def set_ig_post_state(state: dict) -> None:
    try:
        get_client().table("ig_post_state").upsert(
            {"id": 1, "rates": state, "updated_at": datetime.now(timezone.utc).isoformat()},
            on_conflict="id",
        ).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ وضعیت پست اینستاگرام")


# ---------------------------------------------------------------------------
# اتوماسیون کامنت اینستاگرام: idempotency برای وبهوک (متا گاهی همان event را
# دوباره ارسال می‌کند/retry می‌کند؛ بدون این جدول، همان کامنت دوبار پاسخ AI یا
# دوبار دایرکت می‌گرفت). comment_id کلید primary است — تلاش دوم برای همان
# comment_id با خطای unique constraint شکست می‌خورد که یعنی «قبلاً پردازش شده،
# نادیده بگیر».
# ---------------------------------------------------------------------------
def _is_unique_violation(
    exc: Exception,
) -> bool:
    code = getattr(
        exc,
        "code",
        None,
    )

    if str(code) == "23505":
        return True

    text = str(
        exc
    ).lower()

    return (
        "23505" in text
        or "duplicate key" in text
        or "unique constraint" in text
    )


def try_claim_ig_comment_event(
    comment_id: str,
    media_id: Optional[str],
    username: Optional[str],
    text: str,
) -> bool:
    """
    comment_id فقط یک بار قابل claim است.

    duplicate:
        False

    Database failure واقعی:
        Exception
    """

    try:
        (
            get_client()
            .table(
                "ig_comment_events"
            )
            .insert(
                {
                    "comment_id": (
                        str(comment_id)
                    ),
                    "media_id": (
                        str(media_id)
                        if media_id
                        else None
                    ),
                    "commenter_username": (
                        username
                        or None
                    ),
                    "comment_text": (
                        text
                        or ""
                    ),
                    "dm_sent": False,
                    "ai_replied": False,
                    "created_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                }
            )
            .execute()
        )

        logger.info(
            "Instagram comment event "
            "claimed comment_id=%s",
            comment_id,
        )

        return True

    except Exception as exc:
        if _is_unique_violation(
            exc
        ):
            logger.info(
                "Duplicate Instagram "
                "comment ignored "
                "comment_id=%s",
                comment_id,
            )

            return False

        logger.exception(
            "خطای واقعی Supabase هنگام "
            "ثبت Instagram comment "
            "comment_id=%s",
            comment_id,
        )

        raise


def mark_ig_comment_event(
    comment_id: str,
    *,
    dm_sent: Optional[bool] = None,
    ai_replied: Optional[bool] = None,
) -> None:
    updates = {}

    if dm_sent is not None:
        updates[
            "dm_sent"
        ] = bool(
            dm_sent
        )

    if ai_replied is not None:
        updates[
            "ai_replied"
        ] = bool(
            ai_replied
        )

    if not updates:
        return

    try:
        (
            get_client()
            .table(
                "ig_comment_events"
            )
            .update(
                updates
            )
            .eq(
                "comment_id",
                str(comment_id),
            )
            .execute()
        )

    except Exception:
        logger.exception(
            "خطا در به‌روزرسانی "
            "Instagram comment event "
            "comment_id=%s",
            comment_id,
        )

def mark_ig_comment_event(comment_id: str, *, dm_sent: Optional[bool] = None, ai_replied: Optional[bool] = None) -> None:
    updates = {}
    if dm_sent is not None:
        updates["dm_sent"] = dm_sent
    if ai_replied is not None:
        updates["ai_replied"] = ai_replied
    if not updates:
        return
    try:
        get_client().table("ig_comment_events").update(updates).eq("comment_id", comment_id).execute()
    except Exception:
        logger.exception("خطا در به‌روزرسانی وضعیت رویداد کامنت اینستاگرام %s", comment_id)


def deactivate_user(chat_id: int) -> None:
    try:
        get_client().table("users").update({"is_active": False}).eq(
            "chat_id", chat_id
        ).execute()
    except Exception:
        logger.exception("خطا در غیرفعال‌سازی کاربر")


def get_all_active_chat_ids() -> list[int]:
    try:
        res = (
            get_client()
            .table("users")
            .select("chat_id")
            .eq("is_active", True)
            .execute()
        )
        return [row["chat_id"] for row in res.data]
    except Exception:
        logger.exception("خطا در خواندن لیست کاربران")
        return []


def count_active_users() -> int:
    try:
        res = (
            get_client()
            .table("users")
            .select("chat_id", count="exact")
            .eq("is_active", True)
            .execute()
        )
        return res.count or 0
    except Exception:
        logger.exception("خطا در شمارش کاربران")
        return 0


# ---------------------------------------------------------------------------
# تاریخچهٔ نرخ ارز (مرجع بین‌المللی)
# ---------------------------------------------------------------------------
def insert_currency_snapshot(rates: dict[str, float]) -> None:
    """rates: {"usd": 71.20, "eur": 77.5, ...} -> افغانی به ازای ۱ واحد ارز"""
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {"currency": code, "afn_rate": rate, "recorded_at": now}
        for code, rate in rates.items()
    ]
    try:
        get_client().table("currency_history").insert(rows).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ تاریخچهٔ نرخ ارز")


def get_closest_currency_rate(currency: str, when: datetime) -> Optional[float]:
    try:
        res = (
            get_client()
            .table("currency_history")
            .select("afn_rate, recorded_at")
            .eq("currency", currency)
            .lte("recorded_at", when.isoformat())
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return float(res.data[0]["afn_rate"])
        return None
    except Exception:
        logger.exception("خطا در بازیابی نرخ تاریخی ارز")
        return None


# ---------------------------------------------------------------------------
# تاریخچهٔ طلا
# ---------------------------------------------------------------------------

def insert_gold_snapshot(
    price_usd_per_oz: float,
    afn_per_gram_24k: float,
) -> None:
    now = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    try:
        (
            get_client()
            .table(
                "gold_history"
            )
            .insert(
                {
                    "price_usd_per_oz": (
                        price_usd_per_oz
                    ),
                    "afn_per_gram_24k": (
                        afn_per_gram_24k
                    ),
                    "recorded_at": now,
                }
            )
            .execute()
        )

    except Exception:
        logger.exception(
            "خطا در ذخیرهٔ تاریخچهٔ طلا"
        )


def get_closest_gold_rate(
    when: datetime,
) -> Optional[float]:
    try:
        res = (
            get_client()
            .table(
                "gold_history"
            )
            .select(
                "afn_per_gram_24k, "
                "recorded_at"
            )
            .lte(
                "recorded_at",
                when.isoformat(),
            )
            .order(
                "recorded_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        if res.data:
            return float(
                res.data[0][
                    "afn_per_gram_24k"
                ]
            )

        return None

    except Exception:
        logger.exception(
            "خطا در بازیابی "
            "نرخ تاریخی طلا"
        )

        return None


# ---------------------------------------------------------------------------
# تاریخچهٔ نقره
# ---------------------------------------------------------------------------

def insert_silver_snapshot(
    price_usd_per_oz: float,
    afn_per_gram: float,
) -> None:
    """
    نرخ جهانی نقره و قیمت هر گرم به AFN را
    در silver_history ذخیره می‌کند.

    jobs.fetch_and_store_snapshot این تابع را
    مستقیماً فراخوانی می‌کند.
    """

    now = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    try:
        (
            get_client()
            .table(
                "silver_history"
            )
            .insert(
                {
                    "price_usd_per_oz": (
                        price_usd_per_oz
                    ),
                    "afn_per_gram": (
                        afn_per_gram
                    ),
                    "recorded_at": now,
                }
            )
            .execute()
        )

        logger.info(
            "تاریخچهٔ نقره "
            "در Supabase ذخیره شد."
        )

    except Exception:
        logger.exception(
            "خطا در ذخیرهٔ "
            "تاریخچهٔ نقره"
        )


def get_closest_silver_rate(
    when: datetime,
) -> Optional[float]:
    """
    نزدیک‌ترین نرخ نقره در قبل از زمان مشخص.
    """

    try:
        res = (
            get_client()
            .table(
                "silver_history"
            )
            .select(
                "afn_per_gram, "
                "recorded_at"
            )
            .lte(
                "recorded_at",
                when.isoformat(),
            )
            .order(
                "recorded_at",
                desc=True,
            )
            .limit(1)
            .execute()
        )

        if res.data:
            return float(
                res.data[0][
                    "afn_per_gram"
                ]
            )

        return None

    except Exception:
        logger.exception(
            "خطا در بازیابی "
            "نرخ تاریخی نقره"
        )

        return None


def get_silver_rate_series(
    since: datetime,
) -> list[float]:
    """
    سری روزانه نرخ نقره برای نمودار/آمار.

    از آخرین مقدار هر روز UTC استفاده می‌کند.
    """

    try:
        res = (
            get_client()
            .table(
                "silver_history"
            )
            .select(
                "afn_per_gram, "
                "recorded_at"
            )
            .gte(
                "recorded_at",
                since.isoformat(),
            )
            .order(
                "recorded_at"
            )
            .execute()
        )

        daily: dict[
            str,
            float,
        ] = {}

        for row in (
            res.data
            or []
        ):
            timestamp = (
                row.get(
                    "recorded_at"
                )
            )

            value = (
                row.get(
                    "afn_per_gram"
                )
            )

            if (
                not timestamp
                or value is None
            ):
                continue

            day = (
                timestamp[:10]
            )

            daily[day] = float(
                value
            )

        return [
            daily[day]
            for day
            in sorted(
                daily.keys()
            )
        ]

    except Exception:
        logger.exception(
            "خطا در بازیابی "
            "سری تاریخی نقره"
        )

        return []


# ---------------------------------------------------------------------------
# تنظیمات حاشیهٔ سود صراف (spread) — به ازای هر ارز
# ---------------------------------------------------------------------------
def get_all_spread_settings() -> dict[str, float]:
    """{"usd": 1.2, "eur": 1.5, ...} -> درصد اسپرد هر ارز"""
    try:
        res = get_client().table("spread_settings").select("currency, spread_percent").execute()
        return {row["currency"]: float(row["spread_percent"]) for row in res.data}
    except Exception:
        logger.exception("خطا در خواندن تنظیمات اسپرد")
        return {}


def set_spread(currency: str, spread_percent: float) -> None:
    try:
        get_client().table("spread_settings").upsert(
            {
                "currency": currency.lower(),
                "spread_percent": spread_percent,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="currency",
        ).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ تنظیم اسپرد")
        raise


# ---------------------------------------------------------------------------
# تاریخچهٔ نرخ بازارهای محلی (سرای شهزاده / خراسان / د افغانستان بانک)
# ---------------------------------------------------------------------------
def insert_local_market_snapshot(market: str, rates: dict[str, dict]) -> None:
    """rates: {"usd": {"buy": 65.9, "sell": 65.95}, ...}"""
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "market": market,
            "currency": code,
            "buy": vals["buy"],
            "sell": vals["sell"],
            "recorded_at": now,
        }
        for code, vals in rates.items()
    ]
    if not rows:
        return
    try:
        get_client().table("local_market_history").insert(rows).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ تاریخچهٔ بازار محلی")


def get_closest_local_market_rate(
    market: str, currency: str, when: datetime
) -> Optional[dict]:
    try:
        res = (
            get_client()
            .table("local_market_history")
            .select("buy, sell, recorded_at")
            .eq("market", market)
            .eq("currency", currency)
            .lte("recorded_at", when.isoformat())
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return {"buy": float(res.data[0]["buy"]), "sell": float(res.data[0]["sell"])}
        return None
    except Exception:
        logger.exception("خطا در بازیابی نرخ تاریخی بازار محلی")
        return None


def time_ago(days: int = 0, hours: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)


# ---------------------------------------------------------------------------
# Trust Profile — پروفایل احراز هویت و اعتبار کاربران (KYC)
# ---------------------------------------------------------------------------
def get_user_profile(chat_id: int) -> Optional[dict]:
    try:
        res = (
            get_client()
            .table("user_profiles")
            .select("*")
            .eq("chat_id", chat_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception:
        logger.exception("خطا در خواندن پروفایل کاربر")
        return None


def is_kyc_complete(chat_id: int) -> bool:
    """آیا کاربر قبلاً فرم کامل احراز هویت (شامل مدارک) را یک‌بار تکمیل کرده
    (صرف‌نظر از تایید نهایی ادمین)؟ فقط توسط جریان گفتگویی ربات استفاده می‌شود؛
    مینی‌اپ از has_basic_profile/has_identity_verification استفاده می‌کند
    (دو سطحی — نگاه کنید به همین فایل)."""
    profile = get_user_profile(chat_id)
    if not profile:
        return False
    required = (
        profile.get("first_name"),
        profile.get("last_name"),
        profile.get("phone"),
        profile.get("payment_info"),
        profile.get("id_document_path"),
        profile.get("selfie_path"),
    )
    return all(required)


def has_basic_profile(chat_id: int) -> bool:
    """مینی‌اپ — مرحلهٔ اول: آیا نام، نام‌خانوادگی و شماره تماس ثبت شده؟ این سطح
    برای ثبت سفارش‌های زیر آستانهٔ احراز هویت (USDT_IDENTITY_VERIFICATION_THRESHOLD_USD)
    کافی است."""
    profile = get_user_profile(chat_id)
    if not profile:
        return False
    return bool(profile.get("first_name")) and bool(profile.get("last_name")) and bool(profile.get("phone"))


def has_identity_verification(chat_id: int) -> bool:
    """مینی‌اپ — مرحلهٔ دوم (اختیاری، فقط برای سفارش‌های بزرگ‌تر از آستانه): آیا
    مدرک هویتی و سلفی ارسال شده؟ اطلاعات پرداخت عمداً در این شرط نیست چون
    اختیاری است."""
    profile = get_user_profile(chat_id)
    if not profile:
        return False
    return bool(profile.get("id_document_path")) and bool(profile.get("selfie_path"))


def save_basic_profile(chat_id: int, first_name: str, last_name: str, phone: str) -> None:
    """مینی‌اپ — ثبت/به‌روزرسانی فقط اطلاعات پایهٔ پروفایل. عمداً فقط همین سه
    فیلد را می‌نویسد (upsert جزئی): اگر کاربر قبلاً مدارک هویتی هم ارسال کرده
    باشد، آن فیلدها دست‌نخورده باقی می‌مانند."""
    try:
        get_client().table("user_profiles").upsert(
            {"chat_id": chat_id, "first_name": first_name, "last_name": last_name, "phone": phone},
            on_conflict="chat_id",
        ).execute()
    except Exception:
        logger.exception("خطا در ثبت اطلاعات پایهٔ پروفایل کاربر")
        raise


def save_identity_verification(
    chat_id: int, id_document_path: str, selfie_path: str, payment_info: Optional[str] = None
) -> None:
    """مینی‌اپ — ثبت مرحلهٔ دوم (مدارک هویتی + اطلاعات پرداخت اختیاری). نیازمند
    این است که پروفایل پایه از قبل با save_basic_profile ساخته شده باشد
    (این تابع UPDATE می‌کند، نه upsert، تا اگر به اشتباه بدون پروفایل پایه صدا
    زده شد، سرصدا خاموش شکست بخورد نه یک ردیف ناقص جدید بسازد)."""
    fields = {"id_document_path": id_document_path, "selfie_path": selfie_path, "kyc_status": "pending"}
    if payment_info:
        fields["payment_info"] = payment_info
    try:
        get_client().table("user_profiles").update(fields).eq("chat_id", chat_id).execute()
    except Exception:
        logger.exception("خطا در ثبت مدارک احراز هویت کاربر")
        raise


def create_user_profile(
    chat_id: int,
    first_name: str,
    last_name: str,
    phone: str,
    payment_info: str,
    id_document_path: str,
    selfie_path: str,
) -> None:
    try:
        get_client().table("user_profiles").upsert(
            {
                "chat_id": chat_id,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "payment_info": payment_info,
                "id_document_path": id_document_path,
                "selfie_path": selfie_path,
                "kyc_status": "pending",
            },
            on_conflict="chat_id",
        ).execute()
    except Exception:
        logger.exception("خطا در ثبت پروفایل احراز هویت کاربر")
        raise


def update_payment_info(chat_id: int, new_payment_info: str) -> None:
    """اگر اطلاعات پرداخت نسبت به قبل تغییر کرده باشد، شمارندهٔ تغییر افزایش می‌یابد
    (این شمارنده یکی از ورودی‌های Risk Engine است — تغییر مکرر اطلاعات پرداخت مشکوک است)."""
    try:
        profile = get_user_profile(chat_id)
        if not profile:
            return
        changed = bool(profile.get("payment_info") and profile["payment_info"] != new_payment_info)
        fields = {"payment_info": new_payment_info}
        if changed:
            fields["payment_info_change_count"] = (profile.get("payment_info_change_count") or 0) + 1
        get_client().table("user_profiles").update(fields).eq("chat_id", chat_id).execute()
        if changed:
            # ایمپورت داخل تابع برای جلوگیری از وابستگی حلقوی (audit_service <-> این ماژول)
            from services import audit_service

            audit_service.record(
                action="payment_info_changed",
                entity="user_profile",
                entity_id=chat_id,
                actor=chat_id,
                before=audit_service.mask_dict({"payment_info": profile.get("payment_info")}),
                after=audit_service.mask_dict({"payment_info": new_payment_info}),
            )
    except Exception:
        logger.exception("خطا در به‌روزرسانی اطلاعات پرداخت کاربر")


def set_kyc_status(chat_id: int, status: str, verified_by: Optional[int] = None, reason: Optional[str] = None) -> None:
    try:
        previous = get_user_profile(chat_id)
        fields = {"kyc_status": status}
        if status in ("verified", "trusted"):
            fields["verified_by"] = verified_by
            fields["verified_at"] = datetime.now(timezone.utc).isoformat()
        if status == "restricted":
            fields["restricted_reason"] = reason
        get_client().table("user_profiles").update(fields).eq("chat_id", chat_id).execute()

        from services import audit_service

        audit_service.record(
            action=f"kyc_{status}",
            entity="user_profile",
            entity_id=chat_id,
            actor=verified_by,
            before={"kyc_status": previous.get("kyc_status")} if previous else None,
            after={"kyc_status": status},
            reason=reason,
        )
    except Exception:
        logger.exception("خطا در به‌روزرسانی وضعیت KYC کاربر")


def record_order_outcome(chat_id: int, amount_usdt: float, success: bool) -> None:
    """
    بعد از تکمیل یا لغو هر سفارش صدا زده می‌شود؛ آمار Trust Profile و Trust Score را
    طبق فرمول شفاف زیر به‌روزرسانی می‌کند:
      - پایه: ۵۰ امتیاز بعد از تایید هویت (verified/trusted)
      - +۲ امتیاز به‌ازای هر معاملهٔ موفق (سقف ۴۰ امتیاز از این بخش)
      - −۱۰ امتیاز به‌ازای هر معاملهٔ لغوشده/مشکوک
      - +۱۰ امتیاز و ارتقا به 🟢 Trusted اگر ۱۰ معاملهٔ موفق پیاپی بدون لغو ثبت شود
    """
    from config import (
        TRUST_SCORE_BASE_VERIFIED,
        TRUST_SCORE_PER_SUCCESS,
        TRUST_SCORE_SUCCESS_CAP,
        TRUST_SCORE_CANCEL_PENALTY,
        TRUST_SCORE_STREAK_BONUS,
        TRUST_SCORE_STREAK_LENGTH,
    )

    profile = get_user_profile(chat_id)
    if not profile:
        return

    from services.money import D, to_float

    total_orders = (profile.get("total_orders") or 0) + 1
    successful = profile.get("successful_orders") or 0
    cancelled = profile.get("cancelled_orders") or 0
    streak = profile.get("current_success_streak") or 0
    volume = D(profile.get("total_volume_usdt") or 0)
    kyc_status = profile.get("kyc_status") or "pending"

    if success:
        successful += 1
        streak += 1
        volume += D(amount_usdt)
    else:
        cancelled += 1
        streak = 0

    base = TRUST_SCORE_BASE_VERIFIED if kyc_status in ("verified", "trusted") else 0
    success_component = min(successful * TRUST_SCORE_PER_SUCCESS, TRUST_SCORE_SUCCESS_CAP)
    cancel_penalty = cancelled * TRUST_SCORE_CANCEL_PENALTY
    streak_bonus = TRUST_SCORE_STREAK_BONUS if streak >= TRUST_SCORE_STREAK_LENGTH else 0
    trust_score = max(0, base + success_component + streak_bonus - cancel_penalty)

    fields = {
        "total_orders": total_orders,
        "successful_orders": successful,
        "cancelled_orders": cancelled,
        "current_success_streak": streak,
        "total_volume_usdt": to_float(volume),
        "trust_score": trust_score,
        "last_order_at": datetime.now(timezone.utc).isoformat(),
    }
    if streak >= TRUST_SCORE_STREAK_LENGTH and kyc_status == "verified":
        fields["kyc_status"] = "trusted"

    try:
        get_client().table("user_profiles").update(fields).eq("chat_id", chat_id).execute()
    except Exception:
        logger.exception("خطا در به‌روزرسانی Trust Profile کاربر")


# ---------------------------------------------------------------------------
# ذخیره‌سازی خصوصی مدارک KYC و کارت‌های دیجیتال (باکت‌های Private)
# ---------------------------------------------------------------------------
def upload_private_file(bucket: str, file_bytes: bytes, filename: str, content_type: str) -> Optional[str]:
    """آپلود به یک باکت خصوصی؛ فقط مسیر داخلی فایل را برمی‌گرداند (نه لینک عمومی)."""
    try:
        storage = get_client().storage.from_(bucket)
        storage.upload(filename, file_bytes, {"content-type": content_type, "upsert": "true"})
        return filename
    except Exception:
        logger.exception("خطا در آپلود فایل خصوصی به باکت %s", bucket)
        return None


def get_signed_url(bucket: str, path: str, expires_in: int = 600) -> Optional[str]:
    """لینک موقت (چند دقیقه‌یی) برای مشاهدهٔ یک فایل خصوصی — فقط برای ادمین استفاده شود."""
    if not path:
        return None
    try:
        storage = get_client().storage.from_(bucket)
        res = storage.create_signed_url(path, expires_in)
        return res.get("signedURL") or res.get("signed_url")
    except Exception:
        logger.exception("خطا در ساخت لینک موقت برای %s/%s", bucket, path)
        return None


def download_private_file(bucket: str, path: str) -> Optional[bytes]:
    """دانلود مستقیم محتوای یک فایل خصوصی (برای مثال، سلفی کاربر جهت ساخت کارت)."""
    if not path:
        return None
    try:
        return get_client().storage.from_(bucket).download(path)
    except Exception:
        logger.exception("خطا در دانلود فایل خصوصی از %s/%s", bucket, path)
        return None
