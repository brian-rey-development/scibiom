from datetime import UTC, timedelta

from scibiom_core.kernel.clock import SystemClock


def test_system_clock_returns_the_current_time_in_utc() -> None:
    clock = SystemClock()

    before = clock.now()
    after = clock.now()

    assert before.utcoffset() == timedelta(0)
    assert before.tzinfo is UTC
    assert before <= after
