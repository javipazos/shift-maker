from pydantic import BaseModel, Field

from app.types import (
    AbsenceType,
    ContractType,
    EmployeeStatus,
    PreferenceStrength,
    RuleCategory,
    RulePriority,
    ScheduleStatus,
    ShiftPreference,
    ShiftTypeStatus,
    ViolationSeverity,
)


# --- Employees ---


class EmployeeCreate(BaseModel):
    name: str
    hours_per_day: float = 7.5
    max_hours_per_week: float = 37.5
    contract_type: ContractType = ContractType.FULL_TIME
    shift_preference: ShiftPreference = ShiftPreference.NONE
    preference_strength: PreferenceStrength = PreferenceStrength.DESIRABLE
    status: EmployeeStatus = EmployeeStatus.ACTIVE


class EmployeeUpdate(BaseModel):
    name: str | None = None
    hours_per_day: float | None = None
    max_hours_per_week: float | None = None
    contract_type: ContractType | None = None
    shift_preference: ShiftPreference | None = None
    preference_strength: PreferenceStrength | None = None
    status: EmployeeStatus | None = None


class Employee(BaseModel):
    id: int
    name: str
    hours_per_day: float
    max_hours_per_week: float
    contract_type: ContractType
    shift_preference: ShiftPreference
    preference_strength: PreferenceStrength
    status: EmployeeStatus
    created_at: str


# --- Shift Types ---


class ShiftTypeCreate(BaseModel):
    name: str
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    effective_hours: float
    priority_order: int = Field(ge=1)
    color: str = "#4A90D9"
    status: ShiftTypeStatus = ShiftTypeStatus.ACTIVE


class ShiftTypeUpdate(BaseModel):
    name: str | None = None
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    effective_hours: float | None = None
    priority_order: int | None = Field(default=None, ge=1)
    color: str | None = None
    status: ShiftTypeStatus | None = None


class ShiftType(BaseModel):
    id: int
    name: str
    start_time: str
    end_time: str
    effective_hours: float
    priority_order: int
    color: str
    status: ShiftTypeStatus
    created_at: str


# --- Absences ---


class AbsenceCreate(BaseModel):
    employee_id: int
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    type: AbsenceType
    counts_as_work: bool = False
    notes: str | None = None


class AbsenceUpdate(BaseModel):
    start_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    type: AbsenceType | None = None
    counts_as_work: bool | None = None
    notes: str | None = None


class Absence(BaseModel):
    id: int
    employee_id: int
    start_date: str
    end_date: str
    type: AbsenceType
    counts_as_work: bool
    notes: str | None
    created_at: str


# --- Rules ---


class RuleUpdate(BaseModel):
    priority: RulePriority | None = None
    weight: int | None = Field(default=None, ge=1, le=10)
    params: dict | None = None
    active: bool | None = None


class Rule(BaseModel):
    id: str
    name: str
    category: RuleCategory
    priority: RulePriority
    weight: int
    params: dict
    active: bool


# --- Schedules ---


class Schedule(BaseModel):
    id: int
    month: int
    year: int
    status: ScheduleStatus
    created_at: str
    updated_at: str


class Assignment(BaseModel):
    date: str
    employee_id: int
    shift_type_id: int | None = None


class AssignmentsBulkUpdate(BaseModel):
    assignments: list[Assignment]


class ScheduleStatusUpdate(BaseModel):
    status: ScheduleStatus


# --- Validation ---


class Violation(BaseModel):
    rule_id: str
    date: str
    employee_id: int | None = None
    severity: ViolationSeverity
    resolvable: bool
    message: str


class ValidationResult(BaseModel):
    violations: list[Violation]
    score: float
    correctable_count: int
    structural_count: int


# --- Solver ---


class SolverResult(BaseModel):
    status: str
    assignments: list[Assignment]
    violations: list[Violation]
    score: float
    solve_time_ms: float
    relaxed_rules: list[str] = []
