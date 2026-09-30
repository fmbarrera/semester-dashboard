"""API request/response shapes (separate from the DB tables in models.py)."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field


class CourseRead(BaseModel):
    id: str
    code: str
    name: str
    professor: str | None
    weight_scheme: str
    total_points: float | None
    schedule: str | None
    notes: str | None
    open_count: int


class EstimateRead(BaseModel):
    hours: float
    default_hours: float
    override_hours: float | None
    source: str  # "default" | "user_override"


class AssignmentRead(BaseModel):
    id: str
    course_id: str
    course_code: str
    title: str
    category: str
    due_date: date | None
    due_time: time | None
    date_tbd: bool
    weight_value: float | None
    weight_unit: str | None
    is_team: bool
    notes: str | None
    completed_at: datetime | None
    status: str  # "upcoming" | "completed" | "tbd"
    urgency: str  # see logic.URGENCY_ORDER
    days_until: int | None
    estimate: EstimateRead


class AssignmentUpdate(BaseModel):
    """PATCH body. Omit a field to leave it alone.

    Sending `override_hours: null` explicitly clears the override and
    reverts to the category default.
    """

    completed: bool | None = None
    override_hours: float | None = Field(default=None, gt=0, le=200)
