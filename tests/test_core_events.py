from ai_loadout.core.events import Event, EventBus, EventLevel


def test_publish_returns_event_with_incrementing_ids():
    bus = EventBus()
    a = bus.publish(EventLevel.INFO, "first")
    b = bus.publish(EventLevel.WARNING, "second")
    assert isinstance(a, Event)
    assert b.id == a.id + 1
    assert a.level == "info"
    assert b.level == "warning"


def test_enum_values_are_coerced_in_data():
    bus = EventBus()
    ev = bus.publish(EventLevel.SUCCESS, "done", kind="state", level_echo=EventLevel.ERROR)
    # both the top-level level and enum values inside data serialize to plain strings
    assert ev.level == "success"
    assert ev.data["level_echo"] == "error"
    assert ev.to_dict()["message"] == "done"


def test_subscribe_receives_events_and_unsubscribe_works():
    bus = EventBus()
    seen = []
    unsub = bus.subscribe(seen.append)
    bus.info("hello")
    assert len(seen) == 1 and seen[0].message == "hello"
    unsub()
    bus.info("after")
    assert len(seen) == 1  # no new events after unsubscribe


def test_history_catch_up_by_since_id():
    bus = EventBus()
    bus.info("a")
    marker = bus.last_id()
    bus.info("b")
    bus.info("c")
    recent = bus.history(since_id=marker)
    assert [e.message for e in recent] == ["b", "c"]


def test_bad_subscriber_does_not_break_bus():
    bus = EventBus()

    def boom(_):
        raise RuntimeError("subscriber blew up")

    good = []
    bus.subscribe(boom)
    bus.subscribe(good.append)
    bus.info("still delivered")
    assert good and good[0].message == "still delivered"
