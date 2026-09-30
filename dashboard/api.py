"""FastAPI app: JSON API under /api (the HTML frontend will live at /)."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, select

from . import logic
from .models import Assignment, Course, EstimateRule, TimeEstimate
from .schemas import AssignmentRead, AssignmentUpdate, CourseRead, EstimateRead
from .seed import is_seeded, load_seed


def create_app(
    engine: Engine,
    seed_dir: Path,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            if not is_seeded(session):
                load_seed(session, seed_dir, today())
        yield

    app = FastAPI(title="Semester Dashboard", lifespan=lifespan)
    app.state.engine = engine
    app.state.today = today
    register_routes(app)
    return app


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


def get_today(request: Request) -> date:
    return request.app.state.today()


SessionDep = Annotated[Session, Depends(get_session)]
TodayDep = Annotated[date, Depends(get_today)]


def to_read(a: Assignment, course: Course, est: TimeEstimate, today: date) -> AssignmentRead:
    return AssignmentRead(
        **a.model_dump(),
        course_code=course.code,
        status=logic.status(a),
        urgency=logic.urgency(a, today),
        days_until=logic.days_until(a, today),
        estimate=EstimateRead(
            hours=est.effective_hours,
            default_hours=est.category_default_hours,
            override_hours=est.override_hours,
            source=est.source,
        ),
    )


def register_routes(app: FastAPI) -> None:
    @app.get("/api/courses", response_model=list[CourseRead])
    def list_courses(session: SessionDep):
        courses = session.exec(select(Course).order_by(Course.code)).all()
        open_ids = session.exec(
            select(Assignment.course_id).where(Assignment.completed_at.is_(None))
        ).all()
        return [
            CourseRead(**c.model_dump(), open_count=open_ids.count(c.id)) for c in courses
        ]

    @app.get("/api/assignments", response_model=list[AssignmentRead])
    def list_assignments(
        session: SessionDep,
        today: TodayDep,
        course_id: str | None = None,
        status: Literal["upcoming", "completed", "tbd", "open"] | None = Query(
            default=None,
            description='"open" means anything not completed (upcoming + tbd).',
        ),
        within_days: int | None = Query(
            default=None,
            ge=0,
            description="Only items due on or before today + N days. "
            "Overdue items are included; undated items are excluded.",
        ),
    ):
        stmt = select(Assignment, Course, TimeEstimate).join(Course).join(TimeEstimate)
        if course_id is not None:
            stmt = stmt.where(Assignment.course_id == course_id)
        if within_days is not None:
            stmt = stmt.where(Assignment.due_date <= today + timedelta(days=within_days))
        rows = session.exec(stmt).all()

        if status == "open":
            rows = [r for r in rows if logic.status(r[0]) != "completed"]
        elif status is not None:
            rows = [r for r in rows if logic.status(r[0]) == status]
        rows.sort(key=lambda r: logic.sort_key(r[0]))
        return [to_read(a, c, e, today) for a, c, e in rows]

    def fetch_one(session: Session, assignment_id: str):
        row = session.exec(
            select(Assignment, Course, TimeEstimate)
            .join(Course)
            .join(TimeEstimate)
            .where(Assignment.id == assignment_id)
        ).first()
        if row is None:
            raise HTTPException(404, f"No assignment with id {assignment_id!r}")
        return row

    @app.get("/api/assignments/{assignment_id}", response_model=AssignmentRead)
    def get_assignment(assignment_id: str, session: SessionDep, today: TodayDep):
        return to_read(*fetch_one(session, assignment_id), today)

    @app.patch("/api/assignments/{assignment_id}", response_model=AssignmentRead)
    def update_assignment(
        assignment_id: str, body: AssignmentUpdate, session: SessionDep, today: TodayDep
    ):
        a, c, est = fetch_one(session, assignment_id)
        if body.completed is not None:
            # Keep the original timestamp if it's re-marked complete.
            if body.completed and a.completed_at is None:
                a.completed_at = datetime.now(UTC)
            elif not body.completed:
                a.completed_at = None
        if "override_hours" in body.model_fields_set:
            est.override_hours = body.override_hours
        session.add_all([a, est])
        session.commit()
        session.refresh(a)
        session.refresh(est)
        return to_read(a, c, est, today)

    @app.get("/api/estimate-rules", response_model=dict[str, float])
    def list_estimate_rules(session: SessionDep):
        return {r.category: r.default_hours for r in session.exec(select(EstimateRule))}
