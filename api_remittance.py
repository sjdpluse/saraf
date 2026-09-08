"""Production API entrypoint including international remittance endpoints."""
import keyboards

from api import app
from services import remittance_service
from services.remittance_admin import remittance_keyboard
from services.remittance_api_router import router as remittance_router
from services.remittance_wallet_config import get_wallet, SUPPORTED

# Bridge legacy modules without changing the stablecoin trading paths.
keyboards.admin_remittance_keyboard = remittance_keyboard
remittance_service._deposit_wallet = get_wallet
remittance_service.SUPPORTED_NETWORKS = SUPPORTED

app.include_router(remittance_router)
