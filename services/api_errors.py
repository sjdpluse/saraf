"""
استانداردسازی پاسخ خطای API — SARAF 2.0 Spec §16.

فرانت‌اند مینی‌اپ فعلی به فیلد `detail` (رفتار پیش‌فرض FastAPI/HTTPException) متکی
است. برای این‌که این تغییر چیزی را نشکند، پاسخ خطا هم `detail` قدیمی و هم ساختار
جدید `success`/`error` را همزمان برمی‌گرداند:

    {
      "detail": "...",                  <- سازگاری با فرانت‌اند فعلی
      "success": false,
      "error": {"code": "QUOTE_EXPIRED", "message": "..."}
    }

برای کدهای دقیق (مثل QUOTE_EXPIRED، QUOTE_MISMATCH) به‌جای HTTPException خام از
ApiError استفاده کنید. سایر HTTPException های موجود در کد (که فقط status_code
دارند) هم پوشش داده می‌شوند — کدشان از روی status_code حدس زده می‌شود (مثلاً
409 -> CONFLICT)، که دقیق‌تر از هیچ‌چیز است، هرچند به‌اندازهٔ ApiError صریح نیست.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_STATUS_CODE_MAP = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


class ApiError(HTTPException):
    """HTTPException با یک error code صریح (به‌جای حدس زدن از روی status_code)."""

    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code


def register(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        code = getattr(exc, "code", None) or _STATUS_CODE_MAP.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "success": False, "error": {"code": code, "message": exc.detail}},
            headers=getattr(exc, "headers", None) or {},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception):
        # هرگز جزئیات خام یک exception پیش‌بینی‌نشده (که ممکن است شامل اطلاعات
        # داخلی/حساس باشد) به کلاینت برنمی‌گردد — فقط لاگ می‌شود.
        logger.exception("خطای پیش‌بینی‌نشده در API: %s %s", request.method, request.url.path)
        message = "خطای داخلی سرور رخ داد."
        return JSONResponse(
            status_code=500,
            content={"detail": message, "success": False, "error": {"code": "INTERNAL_ERROR", "message": message}},
        )
