"""
لایهٔ دقت مالی — تمام محاسبات پولی باید از این ماژول عبور کنند، نه از float خام.

طبق SARAF 2.0 Spec §13:
  - محاسبات پایتون: Decimal
  - ستون‌های PostgreSQL: NUMERIC
  - گرد کردن (rounding) فقط در «مرز» مناسب انجام شود (یعنی درست قبل از نمایش/ذخیره،
    نه در میانهٔ محاسبات زنجیره‌ای).

خروجی توابع quantize_* همیشه Decimal است. تبدیل به float فقط در مرز JSON/UI انجام
می‌شود (float64 برای مقادیر افغانی/تتر در این مقیاس خطای معناداری تولید نمی‌کند،
چون گرد کردن قبلاً با Decimal انجام شده)؛ ذخیره‌سازی در ستون NUMERIC دیتابیس نیز
همان مقدار quantize‌شده را می‌گیرد.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union

Numeric = Union[int, float, str, Decimal]

# دقت‌های استاندارد این پروژه
AFN_QUANT = Decimal("0.1")      # افغانی با یک رقم اعشار
USD_QUANT = Decimal("0.01")     # دالر/تتر با دو رقم اعشار
RATE_QUANT = Decimal("0.0001")  # نرخ ارز با چهار رقم اعشار
PERCENT_QUANT = Decimal("0.01")  # درصد کارمزد با دو رقم اعشار


class MoneyError(ValueError):
    """ورودی مالی نامعتبر (خالی، غیرعددی، یا منفیِ غیرمنتظره)."""


def D(value: Numeric) -> Decimal:
    """هر مقدار عددی (float/int/str/Decimal) را با عبور از str به Decimal امن تبدیل
    می‌کند. تبدیل مستقیم float->Decimal ممنوع است چون خطای باینری float را هم وارد
    می‌کند (مثلاً Decimal(0.1) != Decimal('0.1'))."""
    if value is None:
        raise MoneyError("مقدار مالی نمی‌تواند خالی باشد.")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(f"مقدار مالی نامعتبر است: {value!r}") from exc


def quantize(value: Numeric, quant: Decimal = AFN_QUANT) -> Decimal:
    return D(value).quantize(quant, rounding=ROUND_HALF_UP)


def quantize_afn(value: Numeric) -> Decimal:
    return quantize(value, AFN_QUANT)


def quantize_usd(value: Numeric) -> Decimal:
    return quantize(value, USD_QUANT)


def quantize_rate(value: Numeric) -> Decimal:
    return quantize(value, RATE_QUANT)


def quantize_percent(value: Numeric) -> Decimal:
    return quantize(value, PERCENT_QUANT)


def to_float(value: Decimal) -> float:
    """فقط در مرز خروجی (JSON/UI) استفاده شود — هرگز در میانهٔ زنجیرهٔ محاسبات."""
    return float(value)


def money_equal(a: Numeric, b: Numeric, tolerance: Decimal = Decimal("0.0000001")) -> bool:
    """مقایسهٔ امن دو مقدار مالی — برای اعتبارسنجی «مقدار درخواستی == مقدار Quote»
    به‌جای مقایسهٔ مستقیم float که با خطای گرد کردن دچار false-negative می‌شود."""
    return abs(D(a) - D(b)) <= tolerance
