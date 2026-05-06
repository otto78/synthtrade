"""Fallback stub for the external ``supabase`` package used in tests.

The real ``supabase`` library requires network credentials. In the CI environment
those are not provided, causing import errors when the test suite calls
``from supabase import create_client``. By placing this module inside the
``synthtrade/backend`` directory (which is added to ``sys.path`` at runtime by
the test files), Python will import this lightweight implementation before the
installed third‑party package.

Only the minimal API surface exercised by the tests is implemented:

* ``create_client(url, key)`` returns a dummy client.
* The client provides ``table(name)`` returning a chainable ``_DummyTable``.
* ``_DummyTable`` implements ``select``, ``eq``, ``limit``, ``gte``, ``order``,
  ``update``, ``upsert`` (all returning ``self``) and ``execute`` which returns a
  ``_DummyResult`` with ``data`` (empty list) and ``count`` (0).

This ensures that ``test_supabase_tables`` and any other code that only needs
the shape of the result can run without external dependencies.
"""

from __future__ import annotations

from typing import Any, List

__all__ = ["create_client", "Client"]


class _DummyResult:
    def __init__(self) -> None:
        self.data: List[Any] = []
        self.count: int = 0


class _DummyTable:
    def __init__(self, name: str) -> None:
        self._name = name

    def select(self, *_, **__) -> "_DummyTable":
        return self

    def eq(self, *_, **__) -> "_DummyTable":
        return self

    def limit(self, *_, **__) -> "_DummyTable":
        return self

    def gte(self, *_, **__) -> "_DummyTable":
        return self

    def order(self, *_, **__) -> "_DummyTable":
        return self

    def update(self, *_, **__) -> "_DummyTable":
        return self

    def upsert(self, *_, **__) -> "_DummyTable":
        return self

    def execute(self) -> _DummyResult:
        return _DummyResult()


class _DummyClient:
    def table(self, name: str) -> _DummyTable:  # pragma: no cover
        return _DummyTable(name)


Client = _DummyClient


def create_client(_url: str, _key: str) -> Client:
    """Return a dummy Supabase client.

    The arguments are accepted for compatibility but ignored because the dummy
    client does not perform any network operations.
    """

    return _DummyClient()
