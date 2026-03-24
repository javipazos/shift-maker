def test_summary_endpoint(client):
    client.post("/api/schedules/2026/3")
    client.put("/api/schedules/2026/3/assignments", json={
        "assignments": [
            {"date": f"2026-03-{d:02d}", "employee_id": 1, "shift_type_id": 1}
            for d in range(2, 7)
        ]
    })

    response = client.get("/api/schedules/2026/3/summary")
    assert response.status_code == 200

    data = response.json()
    assert len(data["employees"]) == 4

    ana = next(e for e in data["employees"] if e["name"] == "Ana García")
    assert ana["days_worked"] == 5
    assert ana["total_hours"] == 37.5
    assert ana["max_consecutive_days"] == 5

    assert len(data["coverage"]) == 31


def test_summary_not_found(client):
    response = client.get("/api/schedules/2026/3/summary")
    assert response.status_code == 404
