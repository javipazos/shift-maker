from io import BytesIO

from openpyxl import Workbook

from app.services.importer import ImportError, parse_schedule_xlsx


SHIFT_TYPES = [
    {"id": 1, "name": "Mañana", "start_time": "07:00", "end_time": "14:30", "effective_hours": 7.5, "priority_order": 1, "color": "#4A90D9"},
    {"id": 2, "name": "Tarde", "start_time": "14:30", "end_time": "22:00", "effective_hours": 7.5, "priority_order": 2, "color": "#E8A838"},
    {"id": 3, "name": "Media mañana", "start_time": "09:00", "end_time": "13:00", "effective_hours": 4.0, "priority_order": 3, "color": "#7EC87E"},
]

EMPLOYEES = [
    {"id": 1, "name": "Ana García"},
    {"id": 2, "name": "Carlos López"},
]


def _build_xlsx(rows: list[list]) -> BytesIO:
    """Build a real xlsx file from a list of rows."""
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_parse_basic_schedule():
    xlsx = _build_xlsx([
        ["Empleado", 1, 2, 3],
        ["Ana García", "Mañana", "Tarde", "L"],
        ["Carlos López", "L", "Mañana", "Mañana"],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    assert len(result.assignments) == 6
    ana_day1 = next(a for a in result.assignments if a["employee_id"] == 1 and a["date"] == "2026-03-01")
    assert ana_day1["shift_type_id"] == 1

    ana_day3 = next(a for a in result.assignments if a["employee_id"] == 1 and a["date"] == "2026-03-03")
    assert ana_day3["shift_type_id"] is None

    carlos_day2 = next(a for a in result.assignments if a["employee_id"] == 2 and a["date"] == "2026-03-02")
    assert carlos_day2["shift_type_id"] == 1


def test_parse_accepts_time_format():
    """Accept the format produced by the xlsx export (e.g. '07:00-14:30')."""
    xlsx = _build_xlsx([
        ["Empleado", 1, 2],
        ["Ana García", "07:00-14:30", "14:30-22:00"],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    ana_day1 = next(a for a in result.assignments if a["date"] == "2026-03-01")
    assert ana_day1["shift_type_id"] == 1

    ana_day2 = next(a for a in result.assignments if a["date"] == "2026-03-02")
    assert ana_day2["shift_type_id"] == 2


def test_parse_empty_cell_means_free():
    xlsx = _build_xlsx([
        ["Empleado", 1, 2],
        ["Ana García", "Mañana", None],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    ana_day2 = next(a for a in result.assignments if a["date"] == "2026-03-02")
    assert ana_day2["shift_type_id"] is None


def test_parse_warns_on_unknown_employee():
    xlsx = _build_xlsx([
        ["Empleado", 1],
        ["Ana García", "Mañana"],
        ["Desconocido", "Tarde"],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    assert len(result.warnings) == 1
    assert "Desconocido" in result.warnings[0]
    assert len(result.assignments) == 1


def test_parse_warns_on_unknown_shift():
    xlsx = _build_xlsx([
        ["Empleado", 1],
        ["Ana García", "Noche"],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    assert len(result.warnings) == 1
    assert "Noche" in result.warnings[0]
    ana = next(a for a in result.assignments if a["date"] == "2026-03-01")
    assert ana["shift_type_id"] is None


def test_parse_case_insensitive_shift_names():
    xlsx = _build_xlsx([
        ["Empleado", 1],
        ["Ana García", "mañana"],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    ana = next(a for a in result.assignments if a["date"] == "2026-03-01")
    assert ana["shift_type_id"] == 1


def test_parse_skips_header_with_day_names():
    """Handle headers like 'L\\n1' (day name + number) from the export format."""
    xlsx = _build_xlsx([
        ["Empleado", "L\n1", "M\n2"],
        ["Ana García", "Mañana", "Tarde"],
    ])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    assert len(result.assignments) == 2
    ana_day1 = next(a for a in result.assignments if a["date"] == "2026-03-01")
    assert ana_day1["shift_type_id"] == 1


def test_parse_error_on_empty_file():
    xlsx = _build_xlsx([])
    result = parse_schedule_xlsx(xlsx, EMPLOYEES, SHIFT_TYPES, 2026, 3)

    assert len(result.errors) > 0


def test_import_endpoint_creates_schedule(client):
    xlsx = _build_xlsx([
        ["Empleado", 1, 2],
        ["Ana García", "Mañana", "Tarde"],
        ["Carlos López", "Tarde", "Mañana"],
    ])

    response = client.post(
        "/api/schedules/2026/3/import",
        files={"file": ("horario.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["assignments"]) == 4
    assert data["warnings"] == []

    # Verify it was persisted
    get_response = client.get("/api/schedules/2026/3")
    assert get_response.status_code == 200


def test_import_endpoint_overwrites_existing(client):
    """Importing over an existing schedule replaces the assignments."""
    xlsx1 = _build_xlsx([
        ["Empleado", 1],
        ["Ana García", "Mañana"],
    ])
    client.post(
        "/api/schedules/2026/3/import",
        files={"file": ("h.xlsx", xlsx1, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    xlsx2 = _build_xlsx([
        ["Empleado", 1],
        ["Ana García", "Tarde"],
    ])
    response = client.post(
        "/api/schedules/2026/3/import",
        files={"file": ("h.xlsx", xlsx2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    assignments = response.json()["assignments"]
    ana = next(a for a in assignments if a["employee_id"] == 1 and a["date"] == "2026-03-01")
    assert ana["shift_type_id"] == 2
