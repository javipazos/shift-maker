from app.rules.base import ScheduleContext, Violation
from app.rules.registry import get_all_rules


def validate_schedule(ctx: ScheduleContext) -> list[Violation]:
    """Run all active rules against the schedule, return violations."""
    violations: list[Violation] = []

    for rule in get_all_rules():
        config = rule.get_config(ctx)
        if not config["active"]:
            continue

        rule_violations = rule.validate(ctx)
        violations.extend(rule_violations)

    return violations


def compute_score(violations: list[Violation]) -> float:
    """Score as percentage. Only correctable violations count."""
    correctable = [v for v in violations if v.resolvable]
    if not correctable:
        return 100.0

    # Weight by severity: grave = 3 points, warning = 1 point
    max_penalty = len(correctable) * 3
    actual_penalty = sum(3 if v.severity == "grave" else 1 for v in correctable)

    return max(0.0, round(100.0 * (1 - actual_penalty / max(max_penalty, 1)), 1))
