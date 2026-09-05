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
import re
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends, Form, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.api_errors import ApiError
from config import (
    BOT_TOKEN,
    TRACKED_CURRENCIES,
    GOLD_KARATS,
    USDT_IDENTITY_VERIFICATION_THRESHOLD_USD,
    BANK_NAME,
    BANK_ACCOUNT_HOLDER,
    BANK_ACCOUNT_NUMBER,
)
from services import (
    currency_service,
    converter_service,
    gold_service,
    rate_engine,
    spread_service,
    usdt_service,
    usdt_order_service,
    webapp_auth,
    kyc_service,
    usdt_api_guard,
    wallet_validator,
    rate_limiter,
    audit_service,
    api_errors,
)
from services import supabase_service as db
from services.instagram_webhook_router import router as instagram_webhook_router

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

# وبهوک اینستاگرام (کامنت جدید → دایرکت خودکار کلمهٔ کلیدی + پاسخ AI عمومی) —
# services/instagram_webhook_router.py را ببینید. مسیرش /webhooks/instagram است.
app.include_router(instagram_webhook_router)


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    """
    لاگ observability سبک (spec §14 «Observability»): method/path/status/duration
    برای هر درخواست، به‌اضافهٔ یک request_id کوتاه برای ردیابی در لاگ‌ها.

    ⚠️ عمداً چیزی که سطح این middleware می‌بیند محدود است — نه بدنهٔ درخواست، نه
    هدرها (که ممکن است X-Telegram-Init-Data حاوی امضای معتبر کاربر باشد)، و نه
    پاسخ. بنابراین هیچ payment_info/wallet_address/KYC data/token ای از این
    مسیر امکان لو رفتن به لاگ را ندارد؛ فقط شکل درخواست (نه محتوای آن) ثبت می‌شود.
    """
    request_id = uuid.uuid4().hex[:12]
    start = time.monotonic()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        status = response.status_code if response is not None else 500
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id, request.method, request.url.path, status, duration_ms,
        )
        if response is not None:
            response.headers["X-Request-Id"] = request_id

# پاسخ خطای استاندارد (§16) — success/error در کنار detail قدیمی، بدون شکستن
# فرانت‌اند فعلی.
api_errors.register(app)


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
    """Liveness/Readiness ساده (spec §29): وضعیت اپلیکیشن همیشه گزارش می‌شود؛
    دسترسی واقعی به دیتابیس هم جداگانه چک می‌شود تا یک readiness واقعی باشد نه
    صرفاً «پردازه بالاست». اگر دیتابیس در دسترس نباشد، هنوز 200 برمی‌گردد (چون
    endpoint های عمومی نرخ ارز/طلا به Supabase وابسته نیستند) اما status را
    'degraded' گزارش می‌کند تا مانیتورینگ متوجه شود."""
    db_ok = True
    db_error = None
    try:
        db.get_client().table("usdt_quotes").select("id").limit(1).execute()
    except Exception as exc:  # noqa: BLE001 — health check باید هر خطایی را ببلعد
        db_ok = False
        db_error = str(exc)[:200]
        logger.warning("Health check: دیتابیس در دسترس نیست: %s", db_error)

    return {
        "status": "ok" if db_ok else "degraded",
        "time": datetime.utcnow().isoformat(),
        "checks": {
            "application": "ok",
            "database": "ok" if db_ok else "unavailable",
        },
    }


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


_SAFE_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}
_ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp", "pdf"}


def _validate_own_receipt_reference(raw: Optional[str], chat_id: int) -> str:
    """
    قبل از این تغییر، receipt_url مستقیماً از کلاینت گرفته و بدون هیچ اعتبارسنجی
    به‌عنوان receipt_file_id سفارش ذخیره می‌شد — یعنی هر رشتهٔ دلخواهی (نه لزوماً
    خروجی واقعی /api/usdt/upload-receipt) پذیرفته می‌شد.

    این تابع تضمین می‌کند مقدار ارسالی واقعاً به فایلی اشاره دارد که همین کاربر
    (بر اساس chat_id احرازشده، نه ادعای کلاینت) از طریق endpoint آپلود رسید ما
    ساخته — چون نام فایل با قرارداد ثابت `{chat_id}_{timestamp}.{ext}` ساخته
    می‌شود و در signed URL برگشتی به‌صورت یک segment مسیر ظاهر می‌شود. این یک
    راه‌حل سبک است (بدون تغییر قرارداد API یا فرانت‌اند)، نه یک مکانیزم کامل
    توکن-محور؛ اما جلوی ارسال یک URL کاملاً دلخواه/خارجی یا رسید یک کاربر دیگر
    را می‌گیرد.
    """
    if not raw or len(raw) > 2048:
        raise HTTPException(status_code=400, detail="لینک رسید نامعتبر است.")
    pattern = re.compile(rf"(^|/){re.escape(str(chat_id))}_\d+\.(jpg|jpeg|png|webp|pdf)(\?|$)")
    if not pattern.search(raw):
        raise HTTPException(
            status_code=400,
            detail="لینک رسید باید نتیجهٔ آپلود واقعی شما از همین حساب باشد؛ لطفاً دوباره رسید را آپلود کنید.",
        )
    return raw


def _safe_ext(filename: Optional[str], content_type: Optional[str]) -> str:
    """پسوند فایل را به‌جای اعتماد مستقیم به filename ارسالی کلاینت (که می‌تواند
    حاوی `/` یا `..` باشد و در کلید Storage تزریق شود)، از یک allow-list استخراج
    می‌کند — اولویت با content_type واقعی است، filename فقط یک راهنمای کمکی است
    که هرگز مستقیماً در نام فایل نهایی استفاده نمی‌شود."""
    if content_type in _SAFE_EXT_BY_CONTENT_TYPE:
        return _SAFE_EXT_BY_CONTENT_TYPE[content_type]
    if filename and "." in filename:
        candidate = filename.rsplit(".", 1)[-1].lower()
        if candidate in _ALLOWED_EXTS:
            return candidate
    return "jpg"


def _full_name(user: dict) -> Optional[str]:
    name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip()
    return name or None


# ---------------------------------------------------------------------------
# پروفایل و احراز هویت (KYC)
# ---------------------------------------------------------------------------
@app.get("/api/usdt/profile")
async def get_my_profile(user: dict = Depends(_authenticate)):
    """
    وضعیت پروفایل کاربر برای مینی‌اپ — دو سطح جدا:
      - has_basic_profile: نام/نام‌خانوادگی/شماره تماس؛ برای هر سفارشی لازم است.
      - has_identity_verification: مدرک هویتی + سلفی؛ فقط برای سفارش‌های
        بالای USDT_IDENTITY_VERIFICATION_THRESHOLD_USD لازم است.
    """
    profile = db.get_user_profile(user["id"])
    return {
        "has_basic_profile": db.has_basic_profile(user["id"]),
        "has_identity_verification": db.has_identity_verification(user["id"]),
        "identity_verification_threshold_usd": USDT_IDENTITY_VERIFICATION_THRESHOLD_USD,
        "profile": profile,
    }


@app.post("/api/usdt/profile")
async def submit_basic_profile(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    user: dict = Depends(_authenticate),
):
    """
    مرحلهٔ اول و اجباری تکمیل پروفایل — فقط نام، نام‌خانوادگی، شمارهٔ تماس.
    نه اطلاعات پرداخت لازم است، نه مدرک هویتی؛ آن‌ها مرحلهٔ دوم و جداگانه‌اند
    (POST /api/usdt/kyc) که فقط برای سفارش‌های بزرگ‌تر از آستانه لازم می‌شود.
    """
    rate_limiter.enforce("kyc_upload", request, identity=str(user["id"]))
    first_name, last_name, phone = first_name.strip(), last_name.strip(), phone.strip()
    if len(first_name) < 2 or len(last_name) < 2:
        raise HTTPException(status_code=400, detail="نام و نام خانوادگی معتبر لازم است.")
    if len(phone) < 7:
        raise HTTPException(status_code=400, detail="شمارهٔ تماس معتبر لازم است.")

    try:
        await kyc_service.save_basic_profile(chat_id=user["id"], first_name=first_name, last_name=last_name, phone=phone)
    except Exception:
        raise HTTPException(status_code=503, detail="ثبت پروفایل ناموفق بود؛ لطفاً دوباره تلاش کنید.")

    audit_service.record(action="basic_profile_saved", entity="user_profile", entity_id=user["id"], actor=user["id"])
    return {"ok": True}


@app.post("/api/usdt/kyc")
async def submit_identity_verification(
    request: Request,
    payment_info: Optional[str] = Form(None),
    id_document: UploadFile = File(...),
    selfie: UploadFile = File(...),
    user: dict = Depends(_authenticate),
):
    """
    مرحلهٔ دوم (اختیاری تا وقتی مبلغ سفارش کاربر از آستانه بیشتر شود): مدرک
    هویتی + سلفی. اطلاعات پرداخت عمداً اختیاری است — کاربر می‌تواند بعداً موقع
    ثبت سفارش وارد کند.
    """
    rate_limiter.enforce("kyc_upload", request, identity=str(user["id"]))
    if not db.has_basic_profile(user["id"]):
        raise HTTPException(status_code=400, detail="ابتدا باید اطلاعات پایهٔ پروفایل را تکمیل کنید.")
    if payment_info is not None and len(payment_info.strip()) > 0 and len(payment_info.strip()) < 4:
        raise HTTPException(status_code=400, detail="اطلاعات پرداخت وارد‌شده معتبر نیست.")

    for f, label in ((id_document, "مدرک هویتی"), (selfie, "سلفی")):
        if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=400, detail=f"{label} باید یک فایل تصویری (jpg/png/webp) باشد.")

    id_doc_bytes = await id_document.read()
    selfie_bytes = await selfie.read()
    if len(id_doc_bytes) > 8 * 1024 * 1024 or len(selfie_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم هر فایل نباید بیشتر از ۸ مگابایت باشد.")

    id_doc_ext = _safe_ext(id_document.filename, id_document.content_type)
    selfie_ext = _safe_ext(selfie.filename, selfie.content_type)

    ok = await kyc_service.submit_identity_verification(
        chat_id=user["id"],
        payment_info=(payment_info or "").strip() or None,
        id_doc_bytes=id_doc_bytes,
        id_doc_ext=id_doc_ext,
        id_doc_content_type=id_document.content_type,
        selfie_bytes=selfie_bytes,
        selfie_ext=selfie_ext,
        selfie_content_type=selfie.content_type,
    )
    if not ok:
        raise HTTPException(status_code=503, detail="ثبت مدارک احراز هویت ناموفق بود؛ لطفاً دوباره تلاش کنید.")
    audit_service.record(
        action="kyc_docs_uploaded", entity="user_profile", entity_id=user["id"], actor=user["id"],
        after={"id_doc_ext": id_doc_ext, "selfie_ext": selfie_ext},
    )
    return {"ok": True}


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
    in_person_code: Optional[str] = None
    payment_method: str  # "in_person" | "online"
    exchange_name: Optional[str] = None
    network: str
    wallet_address: str
    receipt_url: Optional[str] = None  # الزامی وقتی payment_method == "online"


@app.post("/api/usdt/orders/buy")
async def create_usdt_buy_order(payload: UsdtBuyOrderRequest, user: dict = Depends(_authenticate)):
    if not db.has_basic_profile(user["id"]):
        raise HTTPException(status_code=403, detail="ابتدا باید پروفایل خود را تکمیل کنید.")
    if payload.amount > USDT_IDENTITY_VERIFICATION_THRESHOLD_USD and not db.has_identity_verification(user["id"]):
        raise ApiError(
            status_code=403,
            code="IDENTITY_VERIFICATION_REQUIRED",
            message=f"برای معاملات بالای {USDT_IDENTITY_VERIFICATION_THRESHOLD_USD:g} دالر، ابتدا باید احراز هویت تکمیل شود.",
        )
    if payload.payment_method not in ("in_person", "online"):
        raise HTTPException(status_code=400, detail="روش پرداخت نامعتبر است.")
    if payload.payment_method == "in_person" and (not payload.in_person_code or not payload.in_person_code.isdigit() or len(payload.in_person_code) != 4):
        raise HTTPException(status_code=400, detail="کد ۴ رقمی مراجعهٔ حضوری نامعتبر است.")
    if payload.payment_method == "online" and not payload.receipt_url:
        raise HTTPException(status_code=400, detail="برای پرداخت آنلاین، رسید بانکی الزامی است.")
    if payload.payment_method == "online":
        _validate_own_receipt_reference(payload.receipt_url, user["id"])
    if not payload.wallet_address or not payload.network:
        raise HTTPException(status_code=400, detail="آدرس ولت و شبکه الزامی است.")
    try:
        wallet_validator.validate_wallet_address(payload.network, payload.wallet_address)
    except wallet_validator.WalletValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    profile = db.get_user_profile(user["id"])
    phone = profile.get("phone") if profile else None

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
        phone=phone,
        amount=payload.amount,
        quote=quote,
        payment_method=payload.payment_method,
        exchange_name=payload.exchange_name,
        network=payload.network,
        wallet_address=payload.wallet_address,
        receipt_file_id=payload.receipt_url,
        source="miniapp",
        idempotency_key=(usdt_api_guard.get_order_context() or {}).get("key"),
        quote_id=quote.get("quote_id"),
        in_person_code=payload.in_person_code,
    )
    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}


class UsdtSellOrderRequest(BaseModel):
    amount: float
    in_person_code: Optional[str] = None
    exchange_name: str
    network: str
    tx_proof: str
    receive_method: str  # "in_person" | "online"
    bank_info: Optional[str] = None  # الزامی وقتی receive_method == "online"


@app.post("/api/usdt/orders/sell")
async def create_usdt_sell_order(payload: UsdtSellOrderRequest, user: dict = Depends(_authenticate)):
    if not db.has_basic_profile(user["id"]):
        raise HTTPException(status_code=403, detail="ابتدا باید پروفایل خود را تکمیل کنید.")
    if payload.amount > USDT_IDENTITY_VERIFICATION_THRESHOLD_USD and not db.has_identity_verification(user["id"]):
        raise ApiError(
            status_code=403,
            code="IDENTITY_VERIFICATION_REQUIRED",
            message=f"برای معاملات بالای {USDT_IDENTITY_VERIFICATION_THRESHOLD_USD:g} دالر، ابتدا باید احراز هویت تکمیل شود.",
        )
    if payload.receive_method not in ("in_person", "online"):
        raise HTTPException(status_code=400, detail="روش دریافت نامعتبر است.")
    if payload.receive_method == "in_person" and (not payload.in_person_code or not payload.in_person_code.isdigit() or len(payload.in_person_code) != 4):
        raise HTTPException(status_code=400, detail="کد ۴ رقمی مراجعهٔ حضوری نامعتبر است.")
    if payload.receive_method == "online" and not payload.bank_info:
        raise HTTPException(status_code=400, detail="برای دریافت آنلاین، اطلاعات بانکی الزامی است.")
    if not payload.tx_proof:
        raise HTTPException(status_code=400, detail="اثبات تراکنش (TxID یا رسید) الزامی است.")
    if not payload.exchange_name or not payload.network:
        raise HTTPException(status_code=400, detail="نام صرافی و شبکه الزامی است.")
    try:
        wallet_validator.validate_network(payload.network, [])
    except wallet_validator.WalletValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    profile = db.get_user_profile(user["id"])
    phone = profile.get("phone") if profile else None

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
        phone=phone,
        amount=payload.amount,
        quote=quote,
        exchange_name=payload.exchange_name,
        network=payload.network,
        tx_proof=payload.tx_proof,
        receive_method=payload.receive_method,
        bank_info=payload.bank_info,
        source="miniapp",
        idempotency_key=(usdt_api_guard.get_order_context() or {}).get("key"),
        quote_id=quote.get("quote_id"),
        in_person_code=payload.in_person_code,
    )
    return {"order_id": result["order_id"], "order_code": result["order_code"], "quote": quote}


@app.get("/api/usdt/orders/me")
async def get_my_usdt_orders(user: dict = Depends(_authenticate)):
    return db.get_usdt_orders_by_chat_id(user["id"])


@app.get("/api/usdt/stats")
async def get_usdt_stats():
    """آمار عمومی اعتمادساز (تعداد معاملات تکمیل‌شده، میانگین امتیاز) — بدون نیاز به احراز هویت."""
    return db.get_usdt_stats()


@app.get("/api/usdt/payment-info")
async def get_usdt_payment_info():
    """
    اطلاعات حساب بانکی برای پرداخت آنلاین خرید تتر — بدون نیاز به احراز هویت
    (همان اطلاعاتی که ربات چت هم به هر کاربری نشان می‌دهد، پس چیز حساسی
    نیست). منبع واحد config.py است — قبلاً مینی‌اپ نسخهٔ جدا و hardcode‌شدهٔ
    خودش را داشت که با تغییر متغیرهای محیطی هماهنگ نمی‌شد.
    """
    return {
        "bank_name": BANK_NAME,
        "bank_account_holder": BANK_ACCOUNT_HOLDER,
        "bank_account_number": BANK_ACCOUNT_NUMBER,
    }


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
async def upload_usdt_receipt(request: Request, file: UploadFile = File(...), user: dict = Depends(_authenticate)):
    rate_limiter.enforce("receipt_upload", request, identity=str(user["id"]))
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="فقط فایل تصویری (jpg/png/webp) پذیرفته می‌شود.")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم فایل نباید بیشتر از ۸ مگابایت باشد.")

    ext = _safe_ext(file.filename, file.content_type)
    filename = f"{user['id']}_{int(datetime.utcnow().timestamp())}.{ext}"
    url = db.upload_usdt_receipt(content, filename, file.content_type)
    if not url:
        raise HTTPException(status_code=503, detail="آپلود رسید ناموفق بود؛ لطفاً دوباره تلاش کنید.")
    audit_service.record(action="receipt_uploaded", entity="usdt_receipt", entity_id=filename, actor=user["id"])
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
