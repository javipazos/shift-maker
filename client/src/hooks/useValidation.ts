import { useCallback, useEffect, useRef, useState } from 'react'
import { validateSchedule } from '../api/client'
import type { Violation } from '../api/types'

interface ValidationState {
  violations: Violation[]
  score: number
  correctableCount: number
  structuralCount: number
  loading: boolean
  error: string | null
}

const EMPTY: ValidationState = {
  violations: [],
  score: 100,
  correctableCount: 0,
  structuralCount: 0,
  loading: false,
  error: null,
}

export function useValidation(
  year: number,
  month: number,
  hasSchedule: boolean,
  dirty: boolean,
) {
  const [state, setState] = useState<ValidationState>(EMPTY)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const validate = useCallback(async () => {
    if (!hasSchedule) return

    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      const result = await validateSchedule(year, month)
      setState({
        violations: result.violations,
        score: result.score,
        correctableCount: result.correctable_count,
        structuralCount: result.structural_count,
        loading: false,
        error: null,
      })
    } catch (e) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : 'Error al validar',
      }))
    }
  }, [year, month, hasSchedule])

  // Validate after save (when dirty goes from true to false)
  const prevDirtyRef = useRef(dirty)
  useEffect(() => {
    if (prevDirtyRef.current && !dirty) {
      validate()
    }
    prevDirtyRef.current = dirty
  }, [dirty, validate])

  // Initial validation on mount/month change
  useEffect(() => {
    if (hasSchedule) {
      validate()
    } else {
      setState(EMPTY)
    }
  }, [year, month, hasSchedule, validate])

  return { ...state, validate }
}

export function getViolationsForCell(
  violations: Violation[],
  date: string,
  employeeId: number,
): Violation[] {
  return violations.filter(v =>
    v.date === date && (v.employee_id === employeeId || v.employee_id === null)
  )
}
