"""Pure status/urgency logic — no database access, so it's easy to test."""

from datetime import date, time

from .models import Assignment

# Urgency buckets, most to least pressing. The list view groups by these.
OVERDUE = "overdue"
DUE_SOON = "due_soon"  # today through DUE_SOON_DAYS
THIS_WEEK = "this_week"  # through THIS_WEEK_DAYS
LATER = "later"
NO_DATE = "no_date"
DONE = "done"

URGENCY_ORDER = (OVERDUE, DUE_SOON, THIS_WEEK, LATER, NO_DATE, DONE)

DUE_SOON_DAYS = 2
THIS_WEEK_DAYS = 7


def status(a: Assignment) -> str:
    if a.completed_at is not None:
        return "completed"
    if a.date_tbd or a.due_date is None:
        return "tbd"
    return "upcoming"


def days_until(a: Assignment, today: date) -> int | None:
    if a.due_date is None:
        return None
    return (a.due_date - today).days


def urgency(a: Assignment, today: date) -> str:
    if a.completed_at is not None:
        return DONE
    days = days_until(a, today)
    if days is None:
        return NO_DATE
    if days < 0:
        return OVERDUE
    if days <= DUE_SOON_DAYS:
        return DUE_SOON
    if days <= THIS_WEEK_DAYS:
        return THIS_WEEK
    return LATER


def sort_key(a: Assignment) -> tuple:
    """Chronological, with undated items last and untimed items at end of day."""
    return (
        a.due_date is None,
        a.due_date or date.max,
        a.due_time is None,
        a.due_time or time.min,
        a.course_id,
        a.title,
    )
