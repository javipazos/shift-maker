import { useCallback, useEffect, useState } from 'react'
import { fetchSchedule, fetchEmployees, fetchShiftTypes, fetchAbsences, createSchedule, saveAssignments } from '../api/client'
import type { Absence, Assignment, Employee, Schedule, ShiftType } from '../api/types'

interface ScheduleState {
  schedule: Schedule | null
  assignments: Assignment[]
  employees: Employee[]
  shiftTypes: ShiftType[]
  absences: Absence[]
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

      setState({
        schedule: scheduleData.schedule,
        assignments: scheduleData.assignments,
        employees,
        shiftTypes,
        absences,
        loading: false,
        saving: false,
        dirty: false,
        error: null,
      })
    } catch (e) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : 'Unknown error',
      }))
    }
  }, [year, month])

  useEffect(() => { load() }, [load])

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

  return { ...state, reload: load, ensureSchedule, updateCell, save }
}
