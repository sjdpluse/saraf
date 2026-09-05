"""Shared service package initialization."""

# Install Mini App extensions before api.py instantiates/registers FastAPI routes.
from services.stablecoin_api_extension import install as _install_stablecoin_api_extension
from services.usdt_api_guard import install as _install_usdt_api_guard
from services.reviews_api_extension import install as _install_reviews_api_extension

_install_stablecoin_api_extension()
_install_usdt_api_guard()
_install_reviews_api_extension()
