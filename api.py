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

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import BOT_TOKEN, TRACKED_CURRENCIES, GOLD_KARATS
from services import (
    currency_service,
    converter_service,
    gold_service,
    rate_engine,
    spread_service,
    usdt_service,
    usdt_order_service,
    webapp_auth,
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

# دادهٔ نرخ ارز/طلا کاملاً عمومی است، ولی endpointهای usdt/* نیازمند initData معتبر
# تلگرام هستند (رجوع کنید به services/webapp_auth.py) — پس CORS باز است، اما هر
# endpoint حساس خودش احراز هویت را جداگانه انجام می‌دهد.
_ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _ALLOWED_ORIGINS == "*" else _ALLOWED_ORIGINS.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
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
async def _get_gold_breakdown() -> dict:
    """دقیقاً همان منطق handlers/gold.py — تا عدد نمایش‌داده‌شده در API و ربات یکی باشد."""
    price_usd = await gold_service.get_gold_price_usd_per_oz()
    rates, _source = await currency_service.get_afn_rates()
    afn_per_usd = rates.get("usd")
    if not afn_per_usd:
        raise RuntimeError("نرخ دالر برای محاسبهٔ طلا در دسترس نیست.")
    return gold_service.build_gold_breakdown(price_usd, afn_per_usd)


@app.get("/api/gold")
async def get_all_gold():
    try:
        breakdown = await _get_gold_breakdown()
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ طلا")
        raise HTTPException(status_code=503, detail=str(exc))
    return breakdown


@app.get("/api/gold/{karat}")
async def get_gold(karat: int):
    if karat not in GOLD_KARATS:
        raise HTTPException(status_code=404, detail=f"عیار {karat} پشتیبانی نمی‌شود.")
    try:
        breakdown = await _get_gold_breakdown()
    except Exception as exc:
        logger.exception("خطا در دریافت نرخ طلا")
        raise HTTPException(status_code=503, detail=str(exc))
    return {"karat": karat, **breakdown["karats"][karat], "price_usd_per_oz": breakdown["price_usd_per_oz"]}


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


# ---------------------------------------------------------------------------
# مینی‌اپ خرید و فروش تتر (USDT) — نیازمند initData معتبر تلگرام
# ---------------------------------------------------------------------------
def _authenticate(x_telegram_init_data: Optional[str] = Header(None)) -> dict:
    """
    initData ارسالی از Mini App تلگرام را در هدر X-Telegram-Init-Data می‌خواند و
    اعتبارسنجی می‌کند. در صورت نامعتبر بودن، خطای 401 برمی‌گرداند.
    """
    try:
        return webapp_auth.verify_init_data(x_telegram_init_data, BOT_TOKEN)
    except webapp_auth.InitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def _full_name(user: dict) -> Optional[str]:
    name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip()
    return name or None


class UsdtQuoteRequest(BaseModel):
    action: str  # "buy" | "sell"
    amount: float


@app.post("/api/usdt/quote")
async def usdt_quote(payload: UsdtQuoteRequest, user: dict = Depends(_authenticate)):
    if payload.action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="نوع معامله باید buy یا sell باشد.")
    try:
        if payload.action == "buy":
            quote = await usdt_service.get_buy_quote(payload.amount)
        else:
            quote = await usdt_service.get_sell_quote(payload.amount)
    except usdt_service.UsdtAmountError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ نرخ تتر (مینی‌اپ)")
        raise HTTPException(status_code=503, detail=str(exc))
    return quote


class UsdtBuyOrderRequest(BaseModel):
    amount: float
    phone: str
    payment_method: str  # "in_person" | "online"
    exchange_name: Optional[str] = None
    network: str
    wallet_address: str
    receipt_url: Optional[str] = None  # الزامی وقتی payment_method == "online"


@app.post("/api/usdt/orders/buy")
async def create_usdt_buy_order(payload: UsdtBuyOrderRequest, user: dict = Depends(_authenticate)):
    if payload.payment_method not in ("in_person", "online"):
        raise HTTPException(status_code=400, detail="روش پرداخت نامعتبر است.")
    if payload.payment_method == "online" and not payload.receipt_url:
        raise HTTPException(status_code=400, detail="برای پرداخت آنلاین، رسید بانکی الزامی است.")
    if not payload.wallet_address or not payload.network:
        raise HTTPException(status_code=400, detail="آدرس ولت و شبکه الزامی است.")
    if not payload.phone or len(payload.phone.strip()) < 7:
        raise HTTPException(status_code=400, detail="شمارهٔ تماس معتبر لازم است.")

    # نرخ همیشه در همان لحظهٔ ثبت سفارش دوباره محاسبه می‌شود؛ چون این یک درخواست
    # فوری و اتمیک است (بر خلاف گفتگوی چندمرحله‌ایِ ربات)، نیازی به مکانیزم انقضای
    # نرخ جداگانه نیست.
    try:
        quote = await usdt_service.get_buy_quote(payload.amount)
    except usdt_service.UsdtAmountError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ نرخ خرید تتر (مینی‌اپ)")
        raise HTTPException(status_code=503, detail=str(exc))

    result = await usdt_order_service.create_buy_order(
        chat_id=user["id"],
        username=user.get("username"),
        full_name=_full_name(user),
        phone=payload.phone.strip(),
        amount=payload.amount,
        quote=quote,
        payment_method=payload.payment_method,
        exchange_name=payload.exchange_name,
        network=payload.network,
        wallet_address=payload.wallet_address,
        receipt_file_id=payload.receipt_url,
        source="miniapp",
    )
    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}


class UsdtSellOrderRequest(BaseModel):
    amount: float
    phone: str
    exchange_name: str
    network: str
    tx_proof: str
    receive_method: str  # "in_person" | "online"
    bank_info: Optional[str] = None  # الزامی وقتی receive_method == "online"


@app.post("/api/usdt/orders/sell")
async def create_usdt_sell_order(payload: UsdtSellOrderRequest, user: dict = Depends(_authenticate)):
    if payload.receive_method not in ("in_person", "online"):
        raise HTTPException(status_code=400, detail="روش دریافت نامعتبر است.")
    if payload.receive_method == "online" and not payload.bank_info:
        raise HTTPException(status_code=400, detail="برای دریافت آنلاین، اطلاعات بانکی الزامی است.")
    if not payload.tx_proof:
        raise HTTPException(status_code=400, detail="اثبات تراکنش (TxID یا رسید) الزامی است.")
    if not payload.exchange_name or not payload.network:
        raise HTTPException(status_code=400, detail="نام صرافی و شبکه الزامی است.")
    if not payload.phone or len(payload.phone.strip()) < 7:
        raise HTTPException(status_code=400, detail="شمارهٔ تماس معتبر لازم است.")

    try:
        quote = await usdt_service.get_sell_quote(payload.amount)
    except usdt_service.UsdtAmountError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("خطا در محاسبهٔ نرخ فروش تتر (مینی‌اپ)")
        raise HTTPException(status_code=503, detail=str(exc))

    result = await usdt_order_service.create_sell_order(
        chat_id=user["id"],
        username=user.get("username"),
        full_name=_full_name(user),
        phone=payload.phone.strip(),
        amount=payload.amount,
        quote=quote,
        exchange_name=payload.exchange_name,
        network=payload.network,
        tx_proof=payload.tx_proof,
        receive_method=payload.receive_method,
        bank_info=payload.bank_info,
        source="miniapp",
    )
    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}


@app.get("/api/usdt/orders/me")
async def get_my_usdt_orders(user: dict = Depends(_authenticate)):
    return db.get_usdt_orders_by_chat_id(user["id"])


@app.get("/api/usdt/stats")
async def get_usdt_stats():
    """آمار عمومی اعتمادساز (تعداد معاملات تکمیل‌شده، میانگین امتیاز) — بدون نیاز به احراز هویت."""
    return db.get_usdt_stats()


class UsdtRatingRequest(BaseModel):
    rating: int
    comment: Optional[str] = None


@app.post("/api/usdt/orders/{order_id}/rate")
async def rate_usdt_order(order_id: int, payload: UsdtRatingRequest, user: dict = Depends(_authenticate)):
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="امتیاز باید بین ۱ تا ۵ باشد.")
    ok = db.set_usdt_order_rating(order_id, user["id"], payload.rating, payload.comment)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="امکان ثبت امتیاز نیست — یا سفارش هنوز تکمیل نشده، یا قبلاً امتیاز ثبت شده.",
        )
    return {"ok": True}


@app.post("/api/usdt/upload-receipt")
async def upload_usdt_receipt(file: UploadFile = File(...), user: dict = Depends(_authenticate)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="فقط فایل تصویری (jpg/png/webp) پذیرفته می‌شود.")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم فایل نباید بیشتر از ۸ مگابایت باشد.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
    filename = f"{user['id']}_{int(datetime.utcnow().timestamp())}.{ext}"
    url = db.upload_usdt_receipt(content, filename, file.content_type)
    if not url:
        raise HTTPException(status_code=503, detail="آپلود رسید ناموفق بود؛ لطفاً دوباره تلاش کنید.")
    return {"url": url}


# ---------------------------------------------------------------------------
# سرو کردن فایل‌های build-شدهٔ مینی‌اپ (webapp/dist) — همیشه در انتهای فایل، بعد
# از تمام routeهای /api/* تا هیچ مسیری را سایه نیندازد.
# ---------------------------------------------------------------------------
_MINIAPP_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp", "dist")
if os.path.isdir(_MINIAPP_DIST):
    app.mount("/miniapp", StaticFiles(directory=_MINIAPP_DIST, html=True), name="miniapp")
else:
    logger.warning("پوشهٔ webapp/dist یافت نشد؛ مینی‌اپ سرو نمی‌شود (فقط API در دسترس است).")
