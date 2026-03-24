export interface Employee {
  id: number
  name: string
  hours_per_day: number
  max_hours_per_week: number
  contract_type: 'full_time' | 'part_time'
  shift_preference: 'morning' | 'afternoon' | 'flexible' | 'none'
  preference_strength: 'mandatory' | 'desirable'
  status: 'active' | 'inactive'
  created_at: string
}

export interface ShiftType {
  id: number
  name: string
  start_time: string
  end_time: string
  effective_hours: number
  priority_order: number
  color: string
  status: 'active' | 'inactive'
  created_at: string
}

export interface Assignment {
  date: string
  employee_id: number
  shift_type_id: number | null
}

export interface Schedule {
  id: number
  month: number
  year: number
  status: 'draft' | 'published'
  created_at: string
  updated_at: string
}

export interface ScheduleResponse {
  schedule: Schedule | null
  assignments: Assignment[]
}

export interface Absence {
  id: number
  employee_id: number
  start_date: string
  end_date: string
  type: 'vacation' | 'sick' | 'training' | 'personal' | 'other'
  counts_as_work: boolean
  notes: string | null
  created_at: string
}

export interface Violation {
  rule_id: string
  date: string
  employee_id: number | null
  severity: 'grave' | 'warning'
  resolvable: boolean
  message: string
}

export interface ValidationResult {
  violations: Violation[]
  score: number
  correctable_count: number
  structural_count: number
}

export interface GenerateResult {
  status: string
  assignments: Assignment[]
  violations: Violation[]
  score: number
  solve_time_ms: number
  relaxed_rules: string[]
}
