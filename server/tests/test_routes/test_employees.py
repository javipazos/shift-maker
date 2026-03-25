def test_list_employees_returns_active_by_default(client):
    response = client.get("/api/employees")
    assert response.status_code == 200

    employees = response.json()
    assert len(employees) == 4
    assert all(e["status"] == "active" for e in employees)


def test_list_employees_with_status_filter(client):
    client.put("/api/employees/1", json={"status": "inactive"})

    active = client.get("/api/employees").json()
    assert len(active) == 3

    all_employees = client.get("/api/employees?status=all").json()
    assert len(all_employees) == 4


def test_create_employee(client):
    response = client.post("/api/employees", json={
        "name": "Lucía Ruiz",
        "hours_per_day": 6.0,
        "max_hours_per_week": 30.0,
        "contract_type": "part_time",
    })
    assert response.status_code == 201

    employee = response.json()
    assert employee["name"] == "Lucía Ruiz"
    assert employee["hours_per_day"] == 6.0
    assert employee["contract_type"] == "part_time"
    assert employee["shift_preference"] == "none"
    assert employee["id"] is not None


def test_create_employee_with_defaults(client):
    response = client.post("/api/employees", json={"name": "Test User"})
    assert response.status_code == 201

    employee = response.json()
    assert employee["hours_per_day"] == 7.5
    assert employee["max_hours_per_week"] == 37.5
    assert employee["contract_type"] == "full_time"
    assert employee["status"] == "active"


def test_create_employee_validates_name_required(client):
    response = client.post("/api/employees", json={})
    assert response.status_code == 422


def test_update_employee(client):
    response = client.put("/api/employees/1", json={
        "name": "Ana García Updated",
        "shift_preference": "morning",
    })
    assert response.status_code == 200

    employee = response.json()
    assert employee["name"] == "Ana García Updated"
    assert employee["shift_preference"] == "morning"
    assert employee["hours_per_day"] == 7.5


def test_update_employee_not_found(client):
    response = client.put("/api/employees/999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_delete_employee_hard_deletes(client):
    response = client.delete("/api/employees/1")
    assert response.status_code == 200

    active = client.get("/api/employees").json()
    assert len(active) == 3
    assert all(e["id"] != 1 for e in active)

    all_employees = client.get("/api/employees?status=all").json()
    assert len(all_employees) == 3


def test_delete_employee_not_found(client):
    response = client.delete("/api/employees/999")
    assert response.status_code == 404
