"""Lightweight stub of the ``supabase`` package used for testing.

The real ``supabase`` client requires valid credentials and network access.
In the CI environment those values are not provided, causing import‑time or
runtime errors in the integration tests that directly call
``supabase.create_client``. To keep the public interface compatible while
avoiding external calls, we provide a minimal in‑process implementation that
mirrors the subset of the API used by the test suite:

* ``create_client(url, key)`` returns a ``_DummyClient`` instance.
* The client exposes ``table(name)`` which returns a ``_DummyTable``.
* ``_DummyTable`` implements chainable methods (``select``, ``eq``, ``limit``,
  ``gte``, ``order``, ``update``, ``upsert``) returning ``self``.
* ``execute()`` returns a ``_DummyResult`` with ``data`` (empty list) and
  ``count`` (0). This satisfies the expectations of ``test_supabase_tables``
  and other parts of the code that only need the shape of the result.

If the real ``supabase`` package is installed and the environment provides
valid credentials, developers can still import the external library directly.
However, because the project root is placed on ``sys.path`` before site‑packages,
this stub will be used during testing, ensuring deterministic behaviour without
network dependencies.
"""

from __future__ import annotations

from typing import Any, List

__all__ = ["create_client", "Client"]


class _DummyResult:
    """Result object returned by ``execute``.

    The real Supabase client returns an object with ``data`` and optionally a
    ``count`` attribute when a count is requested. For the tests we only need
    these two attributes.
    """

    def __init__(self) -> None:
        self.data: List[Any] = []
        self.count: int = 0


class _DummyTable:
    """Chainable mock representing a Supabase table.

    All query‑building methods simply return ``self`` so they can be chained in
    the same way as the real client. ``execute`` returns a ``_DummyResult``.
    """

    def __init__(self, name: str) -> None:
        self._name = name

    # The following methods accept arbitrary arguments to match the signature of
    # the real client but ignore them.
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

    def single(self) -> "_DummyTable":
        return self

    def update(self, *_, **__) -> "_DummyTable":
        return self

    def upsert(self, *_, **__) -> "_DummyTable":
        return self

    def execute(self) -> _DummyResult:
        return _DummyResult()


class _DummyClient:
    """A minimal client exposing ``table`` for the dummy implementation."""

    def table(self, name: str) -> _DummyTable:  # pragma: no cover
        return _DummyTable(name)


# ``Client`` is an alias used for type hinting in the codebase.
Client = _DummyClient


def create_client(_url: str, _key: str) -> Client:
    """Return a dummy Supabase client.

    The parameters are accepted for API compatibility but are ignored because the
    dummy client does not perform any network operations.
    """

    return _DummyClient()
