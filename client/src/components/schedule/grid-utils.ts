import type { Assignment, ShiftType } from '../../api/types'

const DAY_NAMES = ['D', 'L', 'M', 'X', 'J', 'V', 'S']

export interface DayInfo {
  date: string
  dayOfMonth: number
  dayOfWeek: string
  isWeekend: boolean
}

export function getDaysInMonth(year: number, month: number): DayInfo[] {
  const days: DayInfo[] = []
  const daysCount = new Date(year, month, 0).getDate()

  for (let d = 1; d <= daysCount; d++) {
    const date = new Date(year, month - 1, d)
    const dow = date.getDay()
    days.push({
      date: `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`,
      dayOfMonth: d,
      dayOfWeek: DAY_NAMES[dow],
      isWeekend: dow === 0 || dow === 6,
    })
  }

  return days
}

export function getAssignment(
  assignments: Assignment[],
  date: string,
  employeeId: number,
): Assignment | undefined {
  return assignments.find(a => a.date === date && a.employee_id === employeeId)
}

export function getShiftType(
  shiftTypes: ShiftType[],
  shiftTypeId: number | null,
): ShiftType | undefined {
  if (shiftTypeId === null) return undefined
  return shiftTypes.find(st => st.id === shiftTypeId)
}

export function getCoverageForDay(assignments: Assignment[], date: string): number {
  return assignments.filter(a => a.date === date && a.shift_type_id !== null).length
}
