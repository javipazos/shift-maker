def test_previous_context_no_previous_schedule(client):
    response = client.get("/api/schedules/2026/3/previous-context")
    assert response.status_code == 200

    data = response.json()
    assert data["assignments"] == []
    assert data["prev_year"] == 2026
    assert data["prev_month"] == 2


def test_previous_context_with_data(client):
    client.post("/api/schedules/2026/2")
    client.put("/api/schedules/2026/2/assignments", json={
        "assignments": [
            {"date": "2026-02-25", "employee_id": 1, "shift_type_id": 1},
            {"date": "2026-02-26", "employee_id": 1, "shift_type_id": 2},
            {"date": "2026-02-27", "employee_id": 2, "shift_type_id": 1},
            {"date": "2026-02-28", "employee_id": 2, "shift_type_id": 1},
            {"date": "2026-02-10", "employee_id": 1, "shift_type_id": 1},
        ]
    })

    response = client.get("/api/schedules/2026/3/previous-context")
    data = response.json()

    # Should only return last 7 days (Feb 22-28), not Feb 10
    dates = {a["date"] for a in data["assignments"]}
    assert "2026-02-10" not in dates
    assert "2026-02-25" in dates
    assert "2026-02-28" in dates


def test_previous_context_january_wraps_to_december(client):
    response = client.get("/api/schedules/2026/1/previous-context")
    data = response.json()
    assert data["prev_year"] == 2025
    assert data["prev_month"] == 12
