from datetime import timedelta

from .conftest import TODAY


def ids(resp):
    return [a["id"] for a in resp.json()]


def test_list_courses_with_open_counts(client):
    courses = {c["id"]: c for c in client.get("/api/courses").json()}
    assert set(courses) == {"bus101", "eco250", "lang110"}
    assert courses["bus101"]["open_count"] == 4


def test_list_assignments_sorted_with_tbd_last(client):
    items = client.get("/api/assignments").json()
    assert items[0]["id"] == "bus101-quiz1"  # 3 days overdue
    assert items[-1]["id"] == "eco250-final-exam"  # no date
    dated = [a["due_date"] for a in items if a["due_date"]]
    assert dated == sorted(dated)


def test_assignment_shape(client):
    a = client.get("/api/assignments/bus101-case1").json()
    assert a["course_code"] == "BUS 101"
    assert a["due_date"] == str(TODAY + timedelta(days=2))
    assert a["days_until"] == 2
    assert a["urgency"] == "due_soon"
    assert a["status"] == "upcoming"
    assert a["estimate"] == {
        "hours": 2.0,
        "default_hours": 2.0,
        "override_hours": None,
        "source": "default",
    }


def test_unknown_assignment_404(client):
    assert client.get("/api/assignments/nope").status_code == 404
    assert client.patch("/api/assignments/nope", json={"completed": True}).status_code == 404


def test_filter_by_course(client):
    items = client.get("/api/assignments", params={"course_id": "lang110"}).json()
    assert items and all(a["course_id"] == "lang110" for a in items)


def test_within_days_includes_overdue_excludes_undated(client):
    got = ids(client.get("/api/assignments", params={"within_days": 7}))
    assert "bus101-quiz1" in got  # overdue
    assert "eco250-problem-set-1" in got  # +5
    assert "lang110-hw-week2" not in got  # +8
    assert "eco250-final-exam" not in got  # undated


def test_filter_by_status_tbd(client):
    assert ids(client.get("/api/assignments", params={"status": "tbd"})) == [
        "eco250-final-exam"
    ]


def test_complete_and_uncomplete(client):
    r = client.patch("/api/assignments/bus101-quiz1", json={"completed": True})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["urgency"] == "done"
    assert body["completed_at"] is not None

    open_ids = ids(client.get("/api/assignments", params={"status": "open"}))
    assert "bus101-quiz1" not in open_ids
    done_ids = ids(client.get("/api/assignments", params={"status": "completed"}))
    assert done_ids == ["bus101-quiz1"]

    body = client.patch("/api/assignments/bus101-quiz1", json={"completed": False}).json()
    assert body["status"] == "upcoming"
    assert body["urgency"] == "overdue"
    assert body["completed_at"] is None


def test_recompleting_keeps_original_timestamp(client):
    first = client.patch("/api/assignments/bus101-quiz1", json={"completed": True}).json()
    again = client.patch("/api/assignments/bus101-quiz1", json={"completed": True}).json()
    assert again["completed_at"] == first["completed_at"]


def test_uncompleting_tbd_item_stays_tbd(client):
    client.patch("/api/assignments/eco250-final-exam", json={"completed": True})
    body = client.patch("/api/assignments/eco250-final-exam", json={"completed": False}).json()
    assert body["status"] == "tbd"


def test_override_and_clear_estimate(client):
    body = client.patch("/api/assignments/bus101-midterm", json={"override_hours": 6.5}).json()
    assert body["estimate"]["hours"] == 6.5
    assert body["estimate"]["source"] == "user_override"

    # Patching something else leaves the override alone.
    body = client.patch("/api/assignments/bus101-midterm", json={"completed": True}).json()
    assert body["estimate"]["hours"] == 6.5

    body = client.patch("/api/assignments/bus101-midterm", json={"override_hours": None}).json()
    assert body["estimate"] == {
        "hours": 4.0,
        "default_hours": 4.0,
        "override_hours": None,
        "source": "default",
    }


def test_override_must_be_positive(client):
    r = client.patch("/api/assignments/bus101-midterm", json={"override_hours": 0})
    assert r.status_code == 422


def test_estimate_rules(client):
    rules = client.get("/api/estimate-rules").json()
    assert rules["exam"] == 4.0 and len(rules) == 11

