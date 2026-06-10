import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Assignment } from '../api/types'

vi.mock('../api/client', () => ({
  fetchSchedule: vi.fn(),
  fetchEmployees: vi.fn(),
  fetchShiftTypes: vi.fn(),
  fetchAbsences: vi.fn(),
  createSchedule: vi.fn(),
  saveAssignments: vi.fn(),
}))

import { fetchAbsences, fetchEmployees, fetchSchedule, fetchShiftTypes } from '../api/client'
import { useSchedule } from './useSchedule'

const serverAssignments: Assignment[] = [
  { date: '2026-03-02', employee_id: 1, shift_type_id: 1 },
]

beforeEach(() => {
  vi.mocked(fetchSchedule).mockResolvedValue({
    schedule: {
      id: 1, month: 3, year: 2026, status: 'draft',
      created_at: '', updated_at: '',
    },
    assignments: serverAssignments,
  })
  vi.mocked(fetchEmployees).mockResolvedValue([])
  vi.mocked(fetchShiftTypes).mockResolvedValue([])
  vi.mocked(fetchAbsences).mockResolvedValue([])
})

describe('useSchedule pins', () => {
  it('keeps pins after a reload so regenerating still respects them', async () => {
    const { result } = renderHook(() => useSchedule(2026, 3))
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => result.current.togglePin('2026-03-02', 1))
    expect(result.current.isPinned('2026-03-02', 1)).toBe(true)

    await act(() => result.current.reload())

    expect(result.current.isPinned('2026-03-02', 1)).toBe(true)
    expect(result.current.getPinnedAssignments()).toEqual([
      { date: '2026-03-02', employee_id: 1, shift_type_id: 1 },
    ])
  })

  it('clears pins when the month changes', async () => {
    const { result, rerender } = renderHook(
      ({ year, month }) => useSchedule(year, month),
      { initialProps: { year: 2026, month: 3 } },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => result.current.togglePin('2026-03-02', 1))
    expect(result.current.pinned.size).toBe(1)

    rerender({ year: 2026, month: 4 })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.pinned.size).toBe(0)
  })

  it('includes a pinned empty cell as a fixed free day', async () => {
    const { result } = renderHook(() => useSchedule(2026, 3))
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => result.current.togglePin('2026-03-15', 2))

    expect(result.current.getPinnedAssignments()).toEqual([
      { date: '2026-03-15', employee_id: 2, shift_type_id: null },
    ])
  })

  it('unpins a cell when toggled twice', async () => {
    const { result } = renderHook(() => useSchedule(2026, 3))
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => result.current.togglePin('2026-03-02', 1))
    act(() => result.current.togglePin('2026-03-02', 1))

    expect(result.current.isPinned('2026-03-02', 1)).toBe(false)
    expect(result.current.getPinnedAssignments()).toEqual([])
  })

  it('clearPins removes all pins', async () => {
    const { result } = renderHook(() => useSchedule(2026, 3))
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => result.current.togglePin('2026-03-02', 1))
    act(() => result.current.togglePin('2026-03-05', 2))
    act(() => result.current.clearPins())

    expect(result.current.pinned.size).toBe(0)
  })
})
