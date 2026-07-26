from ai_loadout.core.lifecycle import (
    BUSY_STATES,
    ComponentState,
    Health,
    TrustLevel,
    state_to_health,
)


def test_enum_str_is_clean_value():
    assert str(ComponentState.HEALTHY) == "healthy"
    assert str(Health.GREEN) == "green"
    assert str(TrustLevel.EXPERT) == "expert"


def test_state_to_health_mapping():
    assert state_to_health(ComponentState.HEALTHY) == Health.GREEN
    assert state_to_health(ComponentState.VERIFIED) == Health.GREEN
    assert state_to_health(ComponentState.NEEDS_UPDATE) == Health.YELLOW
    assert state_to_health(ComponentState.FAILED) == Health.RED
    assert state_to_health(ComponentState.MISSING) == Health.GRAY
    assert state_to_health(ComponentState.UNKNOWN) == Health.GRAY


def test_busy_states_map_to_yellow():
    for state in BUSY_STATES:
        assert state_to_health(state) == Health.YELLOW
