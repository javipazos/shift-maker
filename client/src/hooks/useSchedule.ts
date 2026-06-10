import { useCallback, useEffect, useState } from 'react'
import { fetchSchedule, fetchEmployees, fetchShiftTypes, fetchAbsences, createSchedule, saveAssignments } from '../api/client'
import type { Absence, Assignment, Employee, Schedule, ShiftType } from '../api/types'
import { buildPinnedAssignments, pinKey, type PinnedCell } from './pins'

interface ScheduleState {
  schedule: Schedule | null
  assignments: Assignment[]
  employees: Employee[]
  shiftTypes: ShiftType[]
  absences: Absence[]
  pinned: Map<string, PinnedCell>
  loading: boolean
  saving: boolean
  dirty: boolean
  error: string | null
}

export function useSchedule(year: number, month: number) {
  const [state, setState] = useState<ScheduleState>({
    schedule: null,
    assignments: [],
    employees: [],
    shiftTypes: [],
    absences: [],
    pinned: new Map(),
    loading: true,
    saving: false,
    dirty: false,
    error: null,
  })

  const load = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      const [scheduleData, employees, shiftTypes, absences] = await Promise.all([
        fetchSchedule(year, month),
        fetchEmployees(),
        fetchShiftTypes(),
        fetchAbsences(year, month),
      ])

      // Pins survive reloads (regenerate, absences, saves) on purpose:
      // the user clears them explicitly or by changing month
      setState(prev => ({
        schedule: scheduleData.schedule,
        assignments: scheduleData.assignments,
        employees,
        shiftTypes,
        absences,
        pinned: prev.pinned,
        loading: false,
        saving: false,
        dirty: false,
        error: null,
      }))
    } catch (e) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : 'Unknown error',
      }))
    }
  }, [year, month])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    setState(prev => ({ ...prev, pinned: new Map() }))
  }, [year, month])

  const ensureSchedule = useCallback(async () => {
    if (!state.schedule) {
      await createSchedule(year, month)
      await load()
    }
  }, [state.schedule, year, month, load])

  const updateCell = useCallback((date: string, employeeId: number, shiftTypeId: number | null) => {
    setState(prev => {
      const filtered = prev.assignments.filter(
        a => !(a.date === date && a.employee_id === employeeId)
      )
      const updated = [...filtered, { date, employee_id: employeeId, shift_type_id: shiftTypeId }]
      return { ...prev, assignments: updated, dirty: true }
    })
  }, [])

  const togglePin = useCallback((date: string, employeeId: number) => {
    setState(prev => {
      const key = pinKey(date, employeeId)
      const next = new Map(prev.pinned)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.set(key, { date, employeeId })
      }
      return { ...prev, pinned: next }
    })
  }, [])

  const clearPins = useCallback(() => {
    setState(prev => ({ ...prev, pinned: new Map() }))
  }, [])

  const isPinned = useCallback((date: string, employeeId: number): boolean => {
    return state.pinned.has(pinKey(date, employeeId))
  }, [state.pinned])

  const getPinnedAssignments = useCallback((): Assignment[] => {
    return buildPinnedAssignments(state.pinned, state.assignments)
  }, [state.assignments, state.pinned])

  const save = useCallback(async () => {
    if (!state.dirty) return

    setState(prev => ({ ...prev, saving: true, error: null }))
    try {
      if (!state.schedule) {
        await createSchedule(year, month)
      }
      await saveAssignments(year, month, state.assignments)
      setState(prev => ({ ...prev, saving: false, dirty: false }))
      await load()
    } catch (e) {
      setState(prev => ({
        ...prev,
        saving: false,
        error: e instanceof Error ? e.message : 'Save failed',
      }))
    }
  }, [state.dirty, state.schedule, state.assignments, year, month, load])

  return {
    ...state,
    reload: load,
    ensureSchedule,
    updateCell,
    save,
    togglePin,
    clearPins,
    isPinned,
    getPinnedAssignments,
  }
}
