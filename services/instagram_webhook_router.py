"""
روتر وبهوک اینستاگرام — در api.py سوار می‌شود (همان پردازهٔ web که روی Railway
اجرا می‌شود، جدا از worker ربات تلگرام).

دو endpoint طبق قرارداد استاندارد وبهوک متا:
  GET  /webhooks/instagram  → handshake اولیه (متا این را فقط یک‌بار موقع ثبت
       Callback URL در داشبورد صدا می‌زند)
  POST /webhooks/instagram  → رویدادهای واقعی (کامنت جدید و...)

نکتهٔ مهم دربارهٔ زمان پاسخ: متا انتظار دارد POST خیلی سریع (چند ثانیه) با
200 OK پاسخ داده شود، وگرنه وبهوک را retry یا در نهایت غیرفعال می‌کند. برای
همین پردازش واقعی (که شامل فراخوانی OpenRouter + چند Graph API call است) در
BackgroundTasks انجام می‌شود — پاسخ 200 فوراً برمی‌گردد و پردازش در پس‌زمینه
ادامه می‌یابد.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from config import INSTAGRAM_WEBHOOK_VERIFY_TOKEN
from services import instagram_automation_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/instagram")
async def verify_instagram_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token and INSTAGRAM_WEBHOOK_VERIFY_TOKEN and token == INSTAGRAM_WEBHOOK_VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")

    logger.warning("درخواست تایید وبهوک اینستاگرام رد شد (verify_token نامعتبر یا mode اشتباه).")
    raise HTTPException(status_code=403, detail="verify token mismatch")


@router.post("/webhooks/instagram")
async def receive_instagram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=None, alias="X-Hub-Signature-256"),
):
    raw_body = await request.body()

    if not instagram_automation_service.verify_webhook_signature(raw_body, x_hub_signature_256):
        logger.warning("امضای وبهوک اینستاگرام نامعتبر بود — درخواست رد شد.")
        raise HTTPException(status_code=403, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        logger.exception("payload وبهوک اینستاگرام قابل‌خواندن نبود (JSON نامعتبر)")
        # با این حال 200 برمی‌گردانیم چون متا برای هر خطای غیر-2xx شروع به
        # retry تهاجمی می‌کند؛ یک payload خراب را فقط لاگ می‌کنیم و رد می‌شویم.
        return JSONResponse({"status": "ignored"})

    # پردازش واقعی در پس‌زمینه — پاسخ فوری 200 برمی‌گردد تا متا این وبهوک را
    # کند/ناموفق تلقی نکند.
    background_tasks.add_task(instagram_automation_service.handle_webhook_payload, payload)
    return JSONResponse({"status": "received"})
