"""Shared service package initialization."""

# Install the USDT Mini App API guard before api.py registers its FastAPI routes.
# The guard is additive and only targets the Mini App quote/order endpoints.
from services.usdt_api_guard import install as _install_usdt_api_guard

_install_usdt_api_guard()
