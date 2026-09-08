"""Production API entrypoint including international remittance endpoints."""
from api import app
from services.remittance_api_router import router as remittance_router

app.include_router(remittance_router)
