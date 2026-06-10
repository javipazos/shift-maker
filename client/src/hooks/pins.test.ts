import { describe, expect, it } from 'vitest'
import type { Assignment } from '../api/types'
import { buildPinnedAssignments, pinKey } from './pins'

const assignments: Assignment[] = [
  { date: '2026-03-02', employee_id: 1, shift_type_id: 1 },
  { date: '2026-03-02', employee_id: 2, shift_type_id: 2 },
  { date: '2026-03-03', employee_id: 1, shift_type_id: null },
]

function pins(...cells: Array<{ date: string; employeeId: number }>) {
  return new Map(cells.map(c => [pinKey(c.date, c.employeeId), c]))
}

describe('buildPinnedAssignments', () => {
  it('returns the existing assignment for a pinned cell with a record', () => {
    const result = buildPinnedAssignments(
      pins({ date: '2026-03-02', employeeId: 1 }),
      assignments,
    )

    expect(result).toEqual([
      { date: '2026-03-02', employee_id: 1, shift_type_id: 1 },
    ])
  })

  it('keeps an explicit free day (null shift) for a pinned cell', () => {
    const result = buildPinnedAssignments(
      pins({ date: '2026-03-03', employeeId: 1 }),
      assignments,
    )

    expect(result).toEqual([
      { date: '2026-03-03', employee_id: 1, shift_type_id: null },
    ])
  })

  it('sends a pinned cell without any record as a fixed free day', () => {
    const result = buildPinnedAssignments(
      pins({ date: '2026-03-10', employeeId: 3 }),
      assignments,
    )

    expect(result).toEqual([
      { date: '2026-03-10', employee_id: 3, shift_type_id: null },
    ])
  })

  it('returns one fixed assignment per pinned cell', () => {
    const result = buildPinnedAssignments(
      pins(
        { date: '2026-03-02', employeeId: 2 },
        { date: '2026-03-10', employeeId: 3 },
      ),
      assignments,
    )

    expect(result).toEqual([
      { date: '2026-03-02', employee_id: 2, shift_type_id: 2 },
      { date: '2026-03-10', employee_id: 3, shift_type_id: null },
    ])
  })

  it('returns empty when nothing is pinned', () => {
    expect(buildPinnedAssignments(new Map(), assignments)).toEqual([])
  })
})
