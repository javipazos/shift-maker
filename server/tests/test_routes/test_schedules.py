def test_get_schedule_returns_empty_when_none(client):
    response = client.get("/api/schedules/2026/3")
    assert response.status_code == 200

    data = response.json()
    assert data["schedule"] is None
    assert data["assignments"] == []


def test_create_schedule(client):
    response = client.post("/api/schedules/2026/3")
    assert response.status_code == 201

    schedule = response.json()
    assert schedule["year"] == 2026
    assert schedule["month"] == 3
    assert schedule["status"] == "draft"


def test_create_schedule_is_idempotent(client):
    first = client.post("/api/schedules/2026/3").json()
    second = client.post("/api/schedules/2026/3").json()
    assert first["id"] == second["id"]


def test_update_assignments_bulk(client):
    client.post("/api/schedules/2026/3")

    response = client.put("/api/schedules/2026/3/assignments", json={
        "assignments": [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-02", "employee_id": 2, "shift_type_id": 2},
            {"date": "2026-03-03", "employee_id": 1, "shift_type_id": None},
        ]
    })
    assert response.status_code == 200

    assignments = response.json()["assignments"]
    assert len(assignments) == 3


def test_update_assignments_replaces_all(client):
    client.post("/api/schedules/2026/3")

    client.put("/api/schedules/2026/3/assignments", json={
        "assignments": [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-03-02", "employee_id": 2, "shift_type_id": 2},
        ]
    })

    client.put("/api/schedules/2026/3/assignments", json={
        "assignments": [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 2},
        ]
    })

    data = client.get("/api/schedules/2026/3").json()
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["shift_type_id"] == 2


def test_update_assignments_schedule_not_found(client):
    response = client.put("/api/schedules/2026/3/assignments", json={
        "assignments": []
    })
    assert response.status_code == 404


def test_get_schedule_with_assignments(client):
    client.post("/api/schedules/2026/3")
    client.put("/api/schedules/2026/3/assignments", json={
        "assignments": [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
    })

    data = client.get("/api/schedules/2026/3").json()
    assert data["schedule"]["year"] == 2026
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["employee_id"] == 1


def test_update_schedule_status(client):
    client.post("/api/schedules/2026/3")

    response = client.put("/api/schedules/2026/3/status", json={
        "status": "published"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_generate_with_fixed_assignments(client):
    response = client.post("/api/schedules/2026/3/generate", json={
        "fixed_assignments": [
            {"date": "2026-03-05", "employee_id": 1, "shift_type_id": None},
            {"date": "2026-03-05", "employee_id": 2, "shift_type_id": 1},
        ]
    })
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("optimal", "feasible")

    ana_5 = next(a for a in data["assignments"] if a["employee_id"] == 1 and a["date"] == "2026-03-05")
    assert ana_5["shift_type_id"] is None

    carlos_5 = next(a for a in data["assignments"] if a["employee_id"] == 2 and a["date"] == "2026-03-05")
    assert carlos_5["shift_type_id"] == 1


def test_generate_without_fixed_assignments(client):
    response = client.post("/api/schedules/2026/3/generate")
    assert response.status_code == 200
    assert response.json()["status"] in ("optimal", "feasible")


def test_generate_infeasible_reports_status_and_keeps_assignments(client):
    client.post("/api/schedules/2026/3")
    client.put("/api/schedules/2026/3/assignments", json={
        "assignments": [
            {"date": "2026-03-02", "employee_id": 1, "shift_type_id": 1},
        ]
    })

    client.put("/api/rules/min_daily_coverage", json={
        "params": {"weekday_min": 10, "weekend_min": 10}
    })

    response = client.post("/api/schedules/2026/3/generate")
    assert response.status_code == 200
    assert response.json()["status"] == "infeasible"

    data = client.get("/api/schedules/2026/3").json()
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["shift_type_id"] == 1


def test_generate_relaxes_rule_demoted_to_desirable(client):
    client.put("/api/rules/min_daily_coverage", json={
        "priority": "desirable",
        "params": {"weekday_min": 10, "weekend_min": 10},
    })

    response = client.post("/api/schedules/2026/3/generate")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ("optimal", "feasible")
    assert "min_daily_coverage" in data["relaxed_rules"]


def test_delete_schedule(client):
    client.post("/api/schedules/2026/3")
    response = client.delete("/api/schedules/2026/3")
    assert response.status_code == 200

    data = client.get("/api/schedules/2026/3").json()
    assert data["schedule"] is None
    assert data["assignments"] == []


def test_delete_schedule_not_found(client):
    response = client.delete("/api/schedules/2099/1")
    assert response.status_code == 404
