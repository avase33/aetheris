"""Event bus abstraction.

``InMemoryBus`` is a dependency-free async pub/sub used for local dev and tests.
``RedisBus`` / ``KafkaBus`` adapters (guarded imports) plug the same interface
into real brokers for production.
"""

from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from collections import deque
from typing import Awaitable, Callable

from .models import Event

Handler = Callable[[Event], Awaitable[None] | None]


def _topic_matches(pattern: str, topic: str) -> bool:
    if pattern in ("*", topic):
        return True
    # prefix wildcard: "vision.*" matches "vision.alert"
    return pattern.endswith(".*") and topic.startswith(pattern[:-1])


class EventBus(ABC):
    @abstractmethod
    async def publish(self, event: Event) -> None: ...

    @abstractmethod
    def subscribe(self, topic: str, handler: Handler) -> None: ...

    async def start(self) -> None:  # pragma: no cover - default
        pass

    async def close(self) -> None:  # pragma: no cover - default
        pass


class InMemoryBus(EventBus):
    def __init__(self, history_size: int = 500):
        self._subs: list[tuple[str, Handler]] = []
        self.history: deque[Event] = deque(maxlen=history_size)

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._subs.append((topic, handler))

    async def publish(self, event: Event) -> None:
        self.history.append(event)
        for pattern, handler in list(self._subs):
            if _topic_matches(pattern, event.topic):
                result = handler(event)
                if inspect.isawaitable(result):
                    await result

    def recent(self, topic: str | None = None, limit: int = 50) -> list[Event]:
        items = [e for e in self.history if topic is None or _topic_matches(topic, e.topic)]
        return items[-limit:]


class RedisBus(EventBus):  # pragma: no cover - needs redis
    def __init__(self, url: str):
        try:
            import redis.asyncio as redis
        except ImportError as exc:
            raise RuntimeError("pip install 'aetheris[redis]' to use RedisBus") from exc
        self._redis = redis.from_url(url)
        self._pubsub = self._redis.pubsub()
        self._handlers: dict[str, list[Handler]] = {}
        self._task: asyncio.Task | None = None

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def start(self) -> None:
        import json
        await self._pubsub.subscribe(*self._handlers.keys())

        async def _loop():
            async for msg in self._pubsub.listen():
                if msg.get("type") != "message":
                    continue
                data = json.loads(msg["data"])
                event = Event(topic=msg["channel"].decode(), payload=data.get("payload", {}),
                              source=data.get("source", "redis"))
                for h in self._handlers.get(event.topic, []):
                    res = h(event)
                    if inspect.isawaitable(res):
                        await res

        self._task = asyncio.create_task(_loop())

    async def publish(self, event: Event) -> None:
        import json
        await self._redis.publish(event.topic, json.dumps(event.to_dict()))


def get_bus(backend: str = "memory", **kwargs) -> EventBus:
    backend = (backend or "memory").lower()
    if backend == "memory":
        return InMemoryBus()
    if backend == "redis":
        return RedisBus(kwargs.get("url", "redis://localhost:6379"))
    raise ValueError(f"unknown bus backend: {backend!r}")
