def test_list_rules(client):
    response = client.get("/api/rules")
    assert response.status_code == 200

    rules = response.json()
    assert len(rules) == 14

    rule_ids = {r["id"] for r in rules}
    assert "min_rest_between_shifts" in rule_ids
    assert "max_consecutive_days" in rule_ids


def test_list_rules_have_correct_structure(client):
    rules = client.get("/api/rules").json()
    rule = next(r for r in rules if r["id"] == "min_rest_between_shifts")

    assert rule["name"] == "Descanso mínimo entre jornadas"
    assert rule["category"] == "rest"
    assert rule["priority"] == "mandatory"
    assert rule["weight"] == 10
    assert rule["params"] == {"min_hours": 12}
    assert rule["active"] is True


def test_update_rule_priority(client):
    response = client.put("/api/rules/min_rest_between_shifts", json={
        "priority": "desirable",
    })
    assert response.status_code == 200

    rule = response.json()
    assert rule["priority"] == "desirable"
    assert rule["weight"] == 10


def test_update_rule_params(client):
    response = client.put("/api/rules/min_rest_between_shifts", json={
        "params": {"min_hours": 10},
    })
    assert response.status_code == 200

    rule = response.json()
    assert rule["params"] == {"min_hours": 10}


def test_update_rule_active(client):
    response = client.put("/api/rules/min_rest_between_shifts", json={
        "active": False,
    })
    assert response.status_code == 200

    rule = response.json()
    assert rule["active"] is False


def test_update_rule_weight_validates_range(client):
    response = client.put("/api/rules/min_rest_between_shifts", json={
        "weight": 11,
    })
    assert response.status_code == 422

    response = client.put("/api/rules/min_rest_between_shifts", json={
        "weight": 0,
    })
    assert response.status_code == 422


def test_update_rule_not_found(client):
    response = client.put("/api/rules/nonexistent_rule", json={
        "priority": "desirable",
    })
    assert response.status_code == 404
