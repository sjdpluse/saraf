"""
یک پیاده‌سازی in-memory بسیار ساده از رابط supabase-py (فقط زیرمجموعه‌ای که این
پروژه استفاده می‌کند: table().select/insert/update().eq/is_/limit().execute()).

⚠️ این یک جایگزین کامل برای PostgreSQL/PostgREST واقعی نیست — قیدهای پیچیده‌تر
(مثلاً CHECK constraint روی state machine، یا trigger های واقعی دیتابیس) اینجا
شبیه‌سازی نشده‌اند مگر آنچه صریحاً پیاده شده (قید یکتایی chat_id+idempotency_key
روی usdt_orders، که مستقیماً معادل UNIQUE INDEX واقعی موجود در migration است).
هدف این فیک، تست‌کردن منطق سرویس (idempotency، Quote lifecycle، audit) با
سرعت بالا و بدون نیاز به دیتابیس زنده است؛ تست همزمانی واقعی روی Postgres واقعی
باید جداگانه در محیط CI/staging با دیتابیس واقعی اجرا شود (به گزارش نهایی مراجعه
کنید).
"""
from __future__ import annotations

import threading
from itertools import count


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeTable:
    _id_counters: dict[str, "count"] = {}

    def __init__(self, store: dict, lock: threading.Lock, name: str):
        self._store = store
        self._lock = lock
        self._name = name
        self._filters: list[tuple] = []
        self._insert_payload = None
        self._update_payload = None
        self._limit_n = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self._filters.append(("eq", field, value))
        return self

    def is_(self, field, value):
        self._filters.append(("is", field, value))
        return self

    def limit(self, n):
        self._limit_n = n
        return self

    def order(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def _match(self, row):
        for kind, field, value in self._filters:
            if kind == "eq":
                if row.get(field) != value:
                    return False
            elif kind == "is" and value == "null":
                if row.get(field) is not None:
                    return False
        return True

    def _next_id(self, table_rows):
        return (max((r["id"] for r in table_rows), default=0)) + 1

    def execute(self):
        with self._lock:
            rows = self._store.setdefault(self._name, [])
            if self._insert_payload is not None:
                row = dict(self._insert_payload)
                if self._name == "usdt_orders" and row.get("idempotency_key"):
                    for existing in rows:
                        if (
                            existing.get("chat_id") == row.get("chat_id")
                            and existing.get("idempotency_key") == row.get("idempotency_key")
                        ):
                            raise RuntimeError(
                                "duplicate key value violates unique constraint "
                                '"usdt_orders_chat_id_idempotency_key_key"'
                            )
                if self._name == "usdt_quotes" and "id" not in row:
                    pass  # id assigned below
                row.setdefault("status", row.get("status", "pending"))
                row["id"] = self._next_id(rows)
                rows.append(row)
                return FakeResult([dict(row)])

            if self._update_payload is not None:
                matched = [r for r in rows if self._match(r)]
                for r in matched:
                    r.update(self._update_payload)
                return FakeResult([dict(r) for r in matched])

            matched = [r for r in rows if self._match(r)]
            if self._limit_n:
                matched = matched[: self._limit_n]
            return FakeResult([dict(r) for r in matched])


class FakeStorage:
    def from_(self, _bucket):
        return self

    def upload(self, *_args, **_kwargs):
        return {}

    def get_public_url(self, filename):
        return f"https://fake-storage.local/public/{filename}"

    def create_signed_url(self, path, _expires_in):
        return {"signedURL": f"https://fake-storage.local/signed/{path}"}


class FakeSupabaseClient:
    """یک singleton per-test — هر تست یک نمونهٔ تازه می‌سازد تا state بین تست‌ها
    نشتی نکند."""

    def __init__(self):
        self._store: dict[str, list] = {}
        self._lock = threading.Lock()
        self.storage = FakeStorage()

    def table(self, name: str) -> FakeTable:
        return FakeTable(self._store, self._lock, name)

    # کمکی برای assertion های تست
    def rows(self, table_name: str) -> list[dict]:
        return list(self._store.get(table_name, []))
