from app.rules.base import Rule
from app.rules.coverage import (
    MinPerShiftCoverage,
    PriorityShiftCoverage,
    WeekendShiftCoverage,
)
from app.rules.equity import (
    HoursDistribution,
    MonthlyFreeWeekend,
    WeekendDistribution,
)
from app.rules.limits import MaxDailyHours, RequestedDaysOff
from app.rules.rest import (
    MaxConsecutiveDays,
    MaxWeeklyHours,
    MinConsecutiveFreeDays,
    MinDailyCoverage,
    MinRestBetweenShifts,
    WeeklyRest,
)

_RULES: list[Rule] = [
    # Rest
    MinRestBetweenShifts(),
    MaxConsecutiveDays(),
    MinConsecutiveFreeDays(),
    WeeklyRest(),
    # Coverage
    MinDailyCoverage(),
    WeekendShiftCoverage(),
    MinPerShiftCoverage(),
    PriorityShiftCoverage(),
    # Equity
    MonthlyFreeWeekend(),
    WeekendDistribution(),
    HoursDistribution(),
    # Limits
    MaxWeeklyHours(),
    MaxDailyHours(),
    RequestedDaysOff(),
]

_RULES_BY_ID: dict[str, Rule] = {r.id: r for r in _RULES}


def get_all_rules() -> list[Rule]:
    return list(_RULES)


def get_rule(rule_id: str) -> Rule | None:
    return _RULES_BY_ID.get(rule_id)
