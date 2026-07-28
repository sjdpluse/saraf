"""
لایهٔ API عمومی Saraf — برای مصرف توسط وب‌سایت فرانت‌اند (React).

این فایل کاملاً مستقل از bot.py اجرا می‌شود (پردازهٔ web جداگانه روی Railway،
در کنار پردازهٔ worker ربات تلگرام) اما دقیقاً از همان لایهٔ سرویس‌ها
(rate_engine, gold_rate_engine, converter_service, spread_service,
supabase_service) استفاده می‌کند، بنابراین اعدادی که در سایت نمایش داده
می‌شوند همیشه با آنچه ربات تلگرام گزارش می‌دهد یکی است.

اجرای محلی:
    uvicorn api:app --reload --port 8000

اجرای production (Railway):
    uvicorn api:app --host 0.0.0.0 --port $PORT
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import TRACKED_CURRENCIES, GOLD_KARATS
from services import (
    currency_service,
    converter_service,
    gold_service,
    gold_rate_engine,
    gold_market_service,
    rate_engine,
    spread_service,
)
from services import supabase_service as db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Saraf API",
    description="نرخ لحظه‌ای ارز و طلا در افغانستان — بازار سرای شهزاده و منابع بین‌المللی",
    version="1.0.0",
)

# دادهٔ این API کاملاً عمومی است (بدون احراز هویت)، پس CORS باز نگه داشته می‌شود.
_ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _ALLOWED_ORIGINS == "*" else _ALLOWED_ORIGINS.split(","),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# اسکیماهای پاسخ
# ---------------------------------------------------------------------------
class ConvertResponse(BaseModel):
    from_code: str
    to_code: str
    amount: float
    result: float
    unit_rate: float


def _pct_change(old: float, new: float) -> float:
    if not old:
        return 0.0
    return round((new - old) / old * 100, 4)


# ---------------------------------------------------------------------------
# متادیتا
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/api/currencies")
async def list_currencies():
    return [{"code": code, "name": name} for code, name in TRACKED_CURRENCIES.items()]


@app.get("/api/karats")
async def list_karats():
    return sorted(GOLD_KARATS.keys(), reverse=True)


# ---------------------------------------------------------------------------
# نرخ ارز
# ---------------------------------------------------------------------------
@app.get("/api/rates")
async def get_all_rates():
    quotes = await rate_engine.get_full_quotes(list(TRACKED_CURRENCIES.keys()))
    if not quotes:
        raise HTTPException(status_code=503, detail="در حال حاضر هیچ نرخی در دسترس نیست.")
    out = []
    for code, name in TRACKED_CURRENCIES.items():
        if code in quotes:
            q = quotes[code]
            out.append({"code": code, "name": name, **q})
    return out


@app.get("/api/rates/{code}")
async def get_rate(code: str):
    code = code.lower()
    if code not in TRACKED_CURRENCIES:
        raise HTTPException(status_code=404, detail=f"ارز «{code}» پیگیری نمی‌شود.")
    try:
        quote = await rate_engine.get_full_quote(code)
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ %s", code)
        raise HTTPException(status_code=503, detail=str(exc))
    return {"code": code, "name": TRACKED_CURRENCIES[code], **quote}


# ---------------------------------------------------------------------------
# نرخ طلا
# ---------------------------------------------------------------------------
@app.get("/api/gold")
async def get_all_gold():
    out = []
    for karat in sorted(GOLD_KARATS.keys(), reverse=True):
        try:
            quote = await gold_rate_engine.get_full_gold_quote(karat)
            out.append(quote)
        except Exception:
            logger.exception("خطا در دریافت نرخ طلای عیار %s", karat)
    coins = {}
    try:
        coins = await gold_rate_engine.get_herat_coins()
    except Exception:
        logger.warning("سکه‌های کارتی هرات در دسترس نیست")
    if not out:
        raise HTTPException(status_code=503, detail="در حال حاضر هیچ نرخ طلایی در دسترس نیست.")
    return {"karats": out, "herat_coins": coins}


@app.get("/api/gold/{karat}")
async def get_gold(karat: int):
    if karat not in GOLD_KARATS:
        raise HTTPException(status_code=404, detail=f"عیار {karat} پشتیبانی نمی‌شود.")
    try:
        return await gold_rate_engine.get_full_gold_quote(karat)
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ طلا")
        raise HTTPException(status_code=503, detail=str(exc))


# ---------------------------------------------------------------------------
# مبدل ارز جهانی
# ---------------------------------------------------------------------------
@app.get("/api/convert", response_model=ConvertResponse)
async def convert(
    from_code: str = Query(..., alias="from"),
    to_code: str = Query(..., alias="to"),
    amount: float = Query(1.0, gt=0),
):
    try:
        result = await converter_service.convert(from_code, to_code, amount)
        unit_rate = await converter_service.get_unit_rate(from_code, to_code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ConvertResponse(
        from_code=from_code.lower(),
        to_code=to_code.lower(),
        amount=amount,
        result=result,
        unit_rate=unit_rate,
    )


# ---------------------------------------------------------------------------
# مقایسهٔ تاریخی
# ---------------------------------------------------------------------------
@app.get("/api/compare/currency/{code}")
async def compare_currency(code: str, days: int = Query(7, ge=1, le=365)):
    code = code.lower()
    if code not in TRACKED_CURRENCIES:
        raise HTTPException(status_code=404, detail=f"ارز «{code}» پیگیری نمی‌شود.")

    when = db.time_ago(days=days)
    try:
        quote = await rate_engine.get_full_quote(code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    old_basis_rate, old_basis = await rate_engine.get_historical_basis_rate(code, when)

    response = {
        "code": code,
        "name": TRACKED_CURRENCIES[code],
        "days": days,
        "current": quote["saraf_quote"],
        "historical_available": old_basis_rate is not None,
    }
    if old_basis_rate is not None:
        old_buy, old_sell = spread_service.apply_spread(old_basis_rate, code)
        response["historical"] = {
            "buy": old_buy,
            "sell": old_sell,
            "basis": old_basis,
            "basis_rate": old_basis_rate,
        }
        response["change_percent"] = _pct_change(
            old_basis_rate, quote["saraf_quote"]["basis_rate"]
        )
    return response


@app.get("/api/compare/gold")
async def compare_gold(days: int = Query(7, ge=1, le=365)):
    when = db.time_ago(days=days)

    price_usd = await gold_service.get_gold_price_usd_per_oz()
    rates, _source = await currency_service.get_afn_rates()
    afn_per_usd = rates.get("usd")
    if not afn_per_usd:
        raise HTTPException(status_code=503, detail="نرخ دالر برای محاسبهٔ طلا در دسترس نیست.")

    breakdown = gold_service.build_gold_breakdown(price_usd, afn_per_usd)
    current = breakdown["afn_per_gram_24k"]
    old = db.get_closest_gold_rate(when)

    response = {
        "days": days,
        "current_afn_per_gram_24k": current,
        "historical_available": old is not None,
    }
    if old is not None:
        response["historical_afn_per_gram_24k"] = old
        response["change_percent"] = _pct_change(old, current)
    return response
