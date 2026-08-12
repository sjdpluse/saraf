"""
Rate Limiting — SARAF 2.0 Spec §22.

پیاده‌سازی in-memory (sliding-window ساده با bucket‌های زمانی ثابت) است، نه
Redis-backed. برای استقرار فعلی (یک پردازهٔ web روی Railway) کافی و production-safe
است؛ اگر در آینده به چند instance افقی مقیاس داده شود، این محدودیت per-process
خواهد بود نه global — در آن صورت باید به یک store مشترک (Redis/Supabase) منتقل شود.
این محدودیت به‌صراحت در گزارش نهایی مستند شده است.

طراحی عمداً محافظه‌کارانه است (سقف‌های نسبتاً بالا) تا کاربر عادی هرگز به آن
برخورد نکند؛ فقط رفتار غیرعادی (اسکریپت/حملهٔ brute-force) را کند می‌کند.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from fastapi import HTTPException, Request


class _SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, Optional[float]]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if t > cutoff]
            if len(hits) >= self.max_requests:
                retry_after = self.window_seconds - (now - hits[0])
                self._hits[key] = hits
                return False, max(retry_after, 1.0)
            hits.append(now)
            self._hits[key] = hits
            return True, None


# سقف‌ها: (max_requests, window_seconds) — به‌ازای هر chat_id (اگر احراز هویت شده
# باشد) یا هر IP (برای مسیرهای بدون احراز هویت مثل quote عمومی).
_LIMITERS = {
    "quote": _SlidingWindowLimiter(max_requests=20, window_seconds=60),
    "order": _SlidingWindowLimiter(max_requests=10, window_seconds=60),
    "kyc_upload": _SlidingWindowLimiter(max_requests=15, window_seconds=60),
    "receipt_upload": _SlidingWindowLimiter(max_requests=15, window_seconds=60),
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce(bucket: str, request: Request, identity: Optional[str] = None) -> None:
    """اگر سقف نرخ برای این bucket رد شده باشد، HTTPException 429 با هدر
    Retry-After پرتاب می‌کند. identity در صورت وجود (مثلاً chat_id احرازشده) روی
    IP اولویت دارد، چون چند کاربر پشت یک IP مشترک (NAT/موبایل) نباید یکدیگر را
    محدود کنند."""
    limiter = _LIMITERS.get(bucket)
    if limiter is None:
        return
    key = f"{bucket}:{identity or _client_ip(request)}"
    allowed, retry_after = limiter.check(key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="تعداد درخواست‌های شما بیش از حد مجاز است؛ لطفاً کمی صبر کنید.",
            headers={"Retry-After": str(int(retry_after or 5))},
        )
