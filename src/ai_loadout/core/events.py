"""A tiny thread-safe event bus.

Every meaningful thing that happens (a component changing state, an install step
starting/finishing, a warning) is published here. The dashboard subscribes and streams
events to the browser over a WebSocket; the CLI subscribes and prints them. Because the
bus keeps a bounded history, a client that connects late can catch up via ``history()``.
"""

from __future__ import annotations

import itertools
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class EventLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


def _coerce(value: Any) -> Any:
    """Turn enums into their plain values so events serialize cleanly to JSON."""

    if isinstance(value, Enum):
        return value.value
    return value


@dataclass
class Event:
    """A single thing that happened, ready to be sent to a UI as JSON."""

    id: int
    ts: float
    level: str
    message: str
    source: str = "loadout"
    kind: str = "log"  # log | state | progress | notification | step
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "kind": self.kind,
            "data": self.data,
        }


Subscriber = Callable[[Event], None]


class EventBus:
    """Fan-out publish/subscribe with a bounded replay buffer.

    Thread-safe: subscribers may be added/removed from any thread, and publishing from
    a worker thread is expected (installs run off the request thread).
    """

    def __init__(self, history: int = 2000) -> None:
        self._subscribers: list[Subscriber] = []
        self._lock = threading.RLock()
        self._ids = itertools.count(1)
        self._history: deque[Event] = deque(maxlen=history)

    def subscribe(self, callback: Subscriber) -> Callable[[], None]:
        """Register a callback; returns a function that unsubscribes it."""

        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def publish(
        self,
        level: Any = EventLevel.INFO,
        message: str = "",
        source: str = "loadout",
        kind: str = "log",
        **data: Any,
    ) -> Event:
        """Create, record, and broadcast an event. Never raises to callers."""

        with self._lock:
            event = Event(
                id=next(self._ids),
                ts=time.time(),
                level=str(_coerce(level)),
                message=message,
                source=source,
                kind=kind,
                data={k: _coerce(v) for k, v in data.items()},
            )
            self._history.append(event)
            subscribers = list(self._subscribers)

        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                # A misbehaving subscriber must never break the publisher or other subs.
                pass
        return event

    # Convenience wrappers ------------------------------------------------------------
    def info(self, message: str, **kw: Any) -> Event:
        return self.publish(EventLevel.INFO, message, **kw)

    def success(self, message: str, **kw: Any) -> Event:
        return self.publish(EventLevel.SUCCESS, message, **kw)

    def warning(self, message: str, **kw: Any) -> Event:
        return self.publish(EventLevel.WARNING, message, **kw)

    def error(self, message: str, **kw: Any) -> Event:
        return self.publish(EventLevel.ERROR, message, **kw)

    def history(self, since_id: int = 0) -> list[Event]:
        """Return buffered events with ``id`` greater than ``since_id`` (for catch-up)."""

        with self._lock:
            return [event for event in self._history if event.id > since_id]

    def last_id(self) -> int:
        with self._lock:
            return self._history[-1].id if self._history else 0
