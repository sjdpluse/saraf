import asyncio
import threading

import pytest

from services import usdt_order_service

SAMPLE_QUOTE = {"usd_rate": 70.5, "fee_percent": 2.0, "total_afn": 719.1, "total_usd": 10.0}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_buy_kwargs(**overrides):
    kwargs = dict(
        chat_id=111,
        username="tester",
        full_name="Test User",
        phone="0700000000",
        amount=10.0,
        quote=SAMPLE_QUOTE,
        payment_method="in_person",
        exchange_name=None,
        network="TRC20",
        wallet_address="TXYZabc123XYZabc123XYZabc123XYZabc",
        source="miniapp",
    )
    kwargs.update(overrides)
    return kwargs


def test_single_order_creation_succeeds(fake_client):
    result = _run(usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key="key-1")))
    assert result["order_id"] == 1
    assert not result.get("duplicate")


def test_same_idempotency_key_returns_same_order_sequential(fake_client):
    r1 = _run(usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key="key-dup")))
    r2 = _run(usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key="key-dup")))
    assert r1["order_id"] == r2["order_id"]
    assert r2.get("duplicate") is True
    # فقط یک سفارش واقعاً در دیتابیس ساخته شده باشد
    assert len(fake_client.rows("usdt_orders")) == 1


def test_different_idempotency_keys_create_different_orders(fake_client):
    r1 = _run(usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key="key-a")))
    r2 = _run(usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key="key-b")))
    assert r1["order_id"] != r2["order_id"]
    assert len(fake_client.rows("usdt_orders")) == 2


def test_no_idempotency_key_bot_flow_still_creates_order(fake_client):
    # جریان قدیمی/بدون کلید هنوز باید کار کند (backward compatibility)
    result = _run(usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key=None, source="bot")))
    assert result["order_id"] == 1


def test_concurrent_identical_requests_produce_exactly_one_order(fake_client):
    """
    سناریوی اصلی درخواست‌شده: ۱۰ درخواست هم‌زمان با یک idempotency-key یکسان ->
    دقیقاً ۱ سفارش در دیتابیس، و همهٔ درخواست‌ها به همان سفارش resolve می‌شوند.

    محدودیت صادقانه: این تست در برابر FakeSupabaseClient (in-memory، با یک قفل
    سراسری که رفتار UNIQUE constraint واقعی Postgres را شبیه‌سازی می‌کند) اجرا
    می‌شود، نه یک Postgres واقعی. semantics قید یکتایی همان چیزی است که در
    migration واقعی تعریف شده (UNIQUE(chat_id, idempotency_key)), اما تضمین
    قفل‌گذاری واقعی سطح ردیف/تراکنش Postgres را تکرار نمی‌کند. تست معادل روی
    Postgres واقعی باید جداگانه در CI/staging اجرا شود.
    """
    n_concurrent = 10
    results = [None] * n_concurrent
    errors = []
    barrier = threading.Barrier(n_concurrent)

    def worker(i):
        try:
            barrier.wait(timeout=5)
            # هر ترد event loop مستقل خودش را می‌سازد (اجرای async در ترد جداگانه)
            loop = asyncio.new_event_loop()
            try:
                results[i] = loop.run_until_complete(
                    usdt_order_service.create_buy_order(**_make_buy_kwargs(idempotency_key="race-key"))
                )
            finally:
                loop.close()
        except Exception as exc:  # pragma: no cover - فقط برای دیباگ تست
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_concurrent)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"خطاهای غیرمنتظره در تردها: {errors}"
    order_ids = {r["order_id"] for r in results if r}
    assert len(results) == n_concurrent, "همهٔ تردها باید پاسخ برگردانند"
    assert order_ids == {1}, f"باید دقیقاً یک سفارش ساخته شود، اما order_id های دیده‌شده: {order_ids}"
    assert len(fake_client.rows("usdt_orders")) == 1, "باید دقیقاً یک ردیف سفارش در دیتابیس باشد"


def test_quote_consumed_only_once_on_successful_order(fake_client):
    from services import quote_service

    quote = quote_service.create_quote(111, "buy", 10.0, SAMPLE_QUOTE)
    result = _run(
        usdt_order_service.create_buy_order(
            **_make_buy_kwargs(idempotency_key="key-q", quote=quote, quote_id=quote["quote_id"])
        )
    )
    assert result["order_id"]
    stored_quote = fake_client.rows("usdt_quotes")[0]
    assert stored_quote["status"] == "consumed"
