"""Production API entrypoint including international remittance endpoints."""
import keyboards

from api import app
from services.remittance_admin import remittance_keyboard
from services.remittance_api_router import router as remittance_router

# remittance_service sends admin notifications through the shared keyboard module.
keyboards.admin_remittance_keyboard = remittance_keyboard

app.include_router(remittance_router)
