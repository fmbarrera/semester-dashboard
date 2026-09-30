from datetime import UTC, date, datetime, time

import pytest

from dashboard import logic
from dashboard.models import Assignment

TODAY = date(2026, 10, 1)


def make(**kw) -> Assignment:
    defaults = dict(id="x", course_id="c", title="t", category="quiz")
    return Assignment(**(defaults | kw))


@pytest.mark.parametrize(
    "offset,expected",
    [
        (-1, logic.OVERDUE),
        (0, logic.DUE_SOON),
        (logic.DUE_SOON_DAYS, logic.DUE_SOON),
        (logic.DUE_SOON_DAYS + 1, logic.THIS_WEEK),
        (logic.THIS_WEEK_DAYS, logic.THIS_WEEK),
        (logic.THIS_WEEK_DAYS + 1, logic.LATER),
    ],
)
def test_urgency_boundaries(offset, expected):
    a = make(due_date=date.fromordinal(TODAY.toordinal() + offset))
    assert logic.urgency(a, TODAY) == expected


def test_undated_item_has_no_date_urgency():
    assert logic.urgency(make(due_date=None, date_tbd=True), TODAY) == logic.NO_DATE


def test_completed_overrides_overdue():
    a = make(due_date=date(2026, 9, 1), completed_at=datetime(2026, 8, 30, tzinfo=UTC))
    assert logic.urgency(a, TODAY) == logic.DONE
    assert logic.status(a) == "completed"


def test_status_tbd_with_approximate_date():
    a = make(due_date=date(2026, 10, 15), date_tbd=True)
    assert logic.status(a) == "tbd"
    # Still gets a real urgency from its approximate date.
    assert logic.urgency(a, TODAY) == logic.LATER


def test_status_upcoming():
    assert logic.status(make(due_date=TODAY)) == "upcoming"


def test_sort_key_orders_by_date_then_time_with_undated_last():
    items = [
        make(id="undated", title="a", due_date=None),
        make(id="noon-untimed", title="b", due_date=TODAY),
        make(id="noon-late", title="c", due_date=TODAY, due_time=time(23, 59)),
        make(id="noon-early", title="d", due_date=TODAY, due_time=time(9, 0)),
        make(id="yesterday", title="e", due_date=date(2026, 9, 30)),
    ]
    ordered = [a.id for a in sorted(items, key=logic.sort_key)]
    assert ordered == ["yesterday", "noon-early", "noon-late", "noon-untimed", "undated"]
