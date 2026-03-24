def test_list_absences_empty(client):
    response = client.get("/api/absences")
    assert response.status_code == 200
    assert response.json() == []


def test_create_absence(client):
    response = client.post("/api/absences", json={
        "employee_id": 1,
        "start_date": "2026-03-16",
        "end_date": "2026-03-20",
        "type": "vacation",
    })
    assert response.status_code == 201

    absence = response.json()
    assert absence["employee_id"] == 1
    assert absence["start_date"] == "2026-03-16"
    assert absence["end_date"] == "2026-03-20"
    assert absence["type"] == "vacation"
    assert absence["counts_as_work"] is False
    assert absence["notes"] is None


def test_create_absence_training_counts_as_work(client):
    response = client.post("/api/absences", json={
        "employee_id": 2,
        "start_date": "2026-03-10",
        "end_date": "2026-03-10",
        "type": "training",
        "counts_as_work": True,
        "notes": "SOAD formación",
    })
    assert response.status_code == 201

    absence = response.json()
    assert absence["counts_as_work"] is True
    assert absence["notes"] == "SOAD formación"


def test_create_absence_validates_date_format(client):
    response = client.post("/api/absences", json={
        "employee_id": 1,
        "start_date": "16/03/2026",
        "end_date": "2026-03-20",
        "type": "vacation",
    })
    assert response.status_code == 422


def test_create_absence_validates_employee_exists(client):
    response = client.post("/api/absences", json={
        "employee_id": 999,
        "start_date": "2026-03-16",
        "end_date": "2026-03-20",
        "type": "vacation",
    })
    assert response.status_code == 404


def test_list_absences_filtered_by_month(client):
    client.post("/api/absences", json={
        "employee_id": 1,
        "start_date": "2026-03-16",
        "end_date": "2026-03-20",
        "type": "vacation",
    })
    client.post("/api/absences", json={
        "employee_id": 2,
        "start_date": "2026-04-01",
        "end_date": "2026-04-05",
        "type": "vacation",
    })

    march = client.get("/api/absences?year=2026&month=3").json()
    assert len(march) == 1
    assert march[0]["employee_id"] == 1

    april = client.get("/api/absences?year=2026&month=4").json()
    assert len(april) == 1
    assert april[0]["employee_id"] == 2

    all_absences = client.get("/api/absences").json()
    assert len(all_absences) == 2


def test_update_absence(client):
    client.post("/api/absences", json={
        "employee_id": 1,
        "start_date": "2026-03-16",
        "end_date": "2026-03-20",
        "type": "vacation",
    })

    response = client.put("/api/absences/1", json={
        "end_date": "2026-03-22",
        "notes": "Ampliado",
    })
    assert response.status_code == 200

    absence = response.json()
    assert absence["end_date"] == "2026-03-22"
    assert absence["notes"] == "Ampliado"
    assert absence["start_date"] == "2026-03-16"


def test_update_absence_not_found(client):
    response = client.put("/api/absences/999", json={"notes": "x"})
    assert response.status_code == 404


def test_delete_absence(client):
    client.post("/api/absences", json={
        "employee_id": 1,
        "start_date": "2026-03-16",
        "end_date": "2026-03-20",
        "type": "vacation",
    })

    response = client.delete("/api/absences/1")
    assert response.status_code == 200

    assert client.get("/api/absences").json() == []


def test_delete_absence_not_found(client):
    response = client.delete("/api/absences/999")
    assert response.status_code == 404
