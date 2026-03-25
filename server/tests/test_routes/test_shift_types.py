def test_list_shift_types_returns_active(client):
    response = client.get("/api/shift-types")
    assert response.status_code == 200

    shift_types = response.json()
    assert len(shift_types) == 3
    assert shift_types[0]["name"] == "Mañana"
    assert shift_types[0]["priority_order"] == 1


def test_list_shift_types_with_status_filter(client):
    client.put("/api/shift-types/1", json={"status": "inactive"})

    active = client.get("/api/shift-types").json()
    assert len(active) == 2

    all_types = client.get("/api/shift-types?status=all").json()
    assert len(all_types) == 3


def test_create_shift_type(client):
    response = client.post("/api/shift-types", json={
        "name": "Noche",
        "start_time": "22:00",
        "end_time": "06:00",
        "effective_hours": 8.0,
        "priority_order": 4,
        "color": "#9B59B6",
    })
    assert response.status_code == 201

    st = response.json()
    assert st["name"] == "Noche"
    assert st["start_time"] == "22:00"
    assert st["priority_order"] == 4
    assert st["color"] == "#9B59B6"


def test_create_shift_type_validates_time_format(client):
    response = client.post("/api/shift-types", json={
        "name": "Bad",
        "start_time": "9am",
        "end_time": "14:30",
        "effective_hours": 5.0,
        "priority_order": 1,
    })
    assert response.status_code == 422


def test_create_shift_type_validates_priority_positive(client):
    response = client.post("/api/shift-types", json={
        "name": "Bad",
        "start_time": "09:00",
        "end_time": "14:30",
        "effective_hours": 5.0,
        "priority_order": 0,
    })
    assert response.status_code == 422


def test_update_shift_type(client):
    response = client.put("/api/shift-types/1", json={
        "name": "Mañana temprana",
        "start_time": "06:00",
    })
    assert response.status_code == 200

    st = response.json()
    assert st["name"] == "Mañana temprana"
    assert st["start_time"] == "06:00"
    assert st["end_time"] == "14:30"


def test_update_shift_type_not_found(client):
    response = client.put("/api/shift-types/999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_delete_shift_type_hard_deletes(client):
    response = client.delete("/api/shift-types/1")
    assert response.status_code == 200

    all_types = client.get("/api/shift-types?status=all").json()
    assert len(all_types) == 2


def test_delete_shift_type_not_found(client):
    response = client.delete("/api/shift-types/999")
    assert response.status_code == 404
