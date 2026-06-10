from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from ortools.sat.python import cp_model


@dataclass
class Violation:
    rule_id: str
    date: str
    employee_id: int | None
    severity: Literal["grave", "warning"]
    resolvable: bool
    message: str


@dataclass
class ScheduleContext:
    """All data needed to validate or solve a schedule."""

    year: int
    month: int
    employees: list[dict]
    shift_types: list[dict]
    absences: list[dict]
    assignments: list[dict]
    rules_config: dict[str, dict]
    prev_assignments: list[dict] = field(default_factory=list)


@dataclass
class SolverVars:
    """Variables for the CP-SAT model."""

    # x[employee_id][date][shift_type_id] = BoolVar
    shifts: dict[int, dict[str, dict[int, Any]]]
    # works[employee_id][date] = BoolVar (1 if employee works any shift)
    works: dict[int, dict[str, Any]]
    dates: list[str]
    employee_ids: list[int]
    shift_type_ids: list[int]
    # Extended range including previous month context (for rest rules)
    context_dates: list[str] = field(default_factory=list)
    # rule_id -> violation indicators for relaxed desirable rules,
    # penalized in the objective by the rule's weight
    penalties: dict[str, list[Any]] = field(default_factory=dict)


class Rule(ABC):
    id: str
    name: str
    category: str
    default_priority: Literal["mandatory", "desirable"]
    default_weight: int
    default_params: dict = field(default_factory=dict)

    def get_config(self, ctx: ScheduleContext) -> dict:
        """Get merged config: defaults overridden by user settings."""
        user_config = ctx.rules_config.get(self.id, {})
        priority = user_config.get("priority", self.default_priority)
        weight = user_config.get("weight", self.default_weight)
        params = {**self.default_params, **user_config.get("params", {})}
        active = user_config.get("active", True)
        return {
            "priority": priority,
            "weight": weight,
            "params": params,
            "active": active,
        }

    @abstractmethod
    def validate(self, ctx: ScheduleContext) -> list[Violation]:
        """Check schedule for violations of this rule."""

    @abstractmethod
    def add_constraints(
        self, model: cp_model.CpModel, vars: SolverVars, ctx: ScheduleContext
    ) -> None:
        """Add CP-SAT constraints for this rule."""

    def make_enforcer(
        self, model: cp_model.CpModel, vars: SolverVars, ctx: ScheduleContext
    ) -> Callable[[Any], None]:
        """Mandatory rules stay hard; desirable rules become relaxable at a
        weighted penalty so an impossible preference never blocks the solve."""
        if self.get_config(ctx)["priority"] == "mandatory":
            return _keep_hard

        def relax_at_cost(constraint: Any) -> None:
            violation = _new_violation_var(model, vars, self.id)
            constraint.OnlyEnforceIf(violation.Not())

        return relax_at_cost


def _keep_hard(constraint: Any) -> None:
    """model.Add() already applied the constraint unconditionally."""


def _new_violation_var(
    model: cp_model.CpModel, vars: SolverVars, rule_id: str
) -> Any:
    violations = vars.penalties.setdefault(rule_id, [])
    var = model.NewBoolVar(f"viol_{rule_id}_{len(violations)}")
    violations.append(var)
    return var
