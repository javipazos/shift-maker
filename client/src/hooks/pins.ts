import type { Assignment } from '../api/types'

export interface PinnedCell {
  date: string
  employeeId: number
}

export function pinKey(date: string, employeeId: number): string {
  return `${date}|${employeeId}`
}

export function buildPinnedAssignments(
  pinned: Map<string, PinnedCell>,
  assignments: Assignment[],
): Assignment[] {
  const fixed: Assignment[] = []

  for (const cell of pinned.values()) {
    const existing = assignments.find(
      a => a.date === cell.date && a.employee_id === cell.employeeId,
    )
    // A pinned cell with no record is an empty cell the user wants kept free
    fixed.push(existing ?? {
      date: cell.date,
      employee_id: cell.employeeId,
      shift_type_id: null,
    })
  }

  return fixed
}
