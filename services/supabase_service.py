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
def insert_gold_snapshot(price_usd_per_oz: float, afn_per_gram_24k: float) -> None:
    now = datetime.now(timezone.utc).isoformat()
    try:
        get_client().table("gold_history").insert(
            {
                "price_usd_per_oz": price_usd_per_oz,
                "afn_per_gram_24k": afn_per_gram_24k,
                "recorded_at": now,
            }
        ).execute()
    except Exception:
        logger.exception("خطا در ذخیرهٔ تاریخچهٔ طلا")


def get_closest_gold_rate(when: datetime) -> Optional[float]:
    try:
        res = (
            get_client()
            .table("gold_history")
            .select("afn_per_gram_24k, recorded_at")
            .lte("recorded_at", when.isoformat())
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return float(res.data[0]["afn_per_gram_24k"])
        return None
    except Exception:
        logger.exception("خطا در بازیابی نرخ تاریخی طلا")
        return None


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
