from enum import Enum


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ContractType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"


class ShiftPreference(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    FLEXIBLE = "flexible"
    NONE = "none"


class PreferenceStrength(str, Enum):
    MANDATORY = "mandatory"
    DESIRABLE = "desirable"


class ShiftTypeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AbsenceType(str, Enum):
    VACATION = "vacation"
    SICK = "sick"
    TRAINING = "training"
    PERSONAL = "personal"
    OTHER = "other"


class RuleCategory(str, Enum):
    REST = "rest"
    COVERAGE = "coverage"
    EQUITY = "equity"
    LIMITS = "limits"
    CUSTOM = "custom"


class RulePriority(str, Enum):
    MANDATORY = "mandatory"
    DESIRABLE = "desirable"


class ScheduleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ViolationSeverity(str, Enum):
    GRAVE = "grave"
    WARNING = "warning"
