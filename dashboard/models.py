"""Database tables (see PRD.md §8).

Assignment status is *derived*, not stored: an assignment is "completed"
if it has a completed_at timestamp, otherwise "tbd" if its date is
unpublished/approximate, otherwise "upcoming". Storing completion and
TBD-ness separately means un-completing an item can never lose the fact
that its date was a guess.
"""

from datetime import date, datetime, time

from sqlmodel import Field, SQLModel

CATEGORIES = (
    "quiz",
    "exam",
    "project",
    "paper",
    "case",
    "presentation",
    "homework",
    "problem_set",
    "discussion_post",
    "reflection",
    "other",
)
WEIGHT_UNITS = ("points", "percent")
WEIGHT_SCHEMES = ("points", "percent")


class Course(SQLModel, table=True):
    id: str = Field(primary_key=True)
    code: str
    name: str
    professor: str | None = None
    weight_scheme: str
    total_points: float | None = None
    schedule: str | None = None
    notes: str | None = None


class Assignment(SQLModel, table=True):
    id: str = Field(primary_key=True)
    course_id: str = Field(foreign_key="course.id", index=True)
    title: str
    category: str
    due_date: date | None = Field(default=None, index=True)
    due_time: time | None = None
    weight_value: float | None = None
    weight_unit: str | None = None
    is_team: bool = False
    # True when the professor hasn't published a firm date. The item may
    # still carry an approximate due_date (e.g. "by mid-October").
    date_tbd: bool = False
    completed_at: datetime | None = None
    notes: str | None = None


class TimeEstimate(SQLModel, table=True):
    assignment_id: str = Field(primary_key=True, foreign_key="assignment.id")
    category_default_hours: float
    override_hours: float | None = None

    @property
    def effective_hours(self) -> float:
        if self.override_hours is not None:
            return self.override_hours
        return self.category_default_hours

    @property
    def source(self) -> str:
        return "user_override" if self.override_hours is not None else "default"


class EstimateRule(SQLModel, table=True):
    category: str = Field(primary_key=True)
    default_hours: float
