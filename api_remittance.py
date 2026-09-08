"""Production API entrypoint including international remittance endpoints."""
import keyboards

from api import app
from services.remittance_admin import remittance_keyboard
from services.remittance_api_router import router as remittance_router
from services.remittance_v2 import install as install_remittance_v2

# Bridge legacy modules without changing the stablecoin trading paths.
keyboards.admin_remittance_keyboard = remittance_keyboard
install_remittance_v2()

app.include_router(remittance_router)
