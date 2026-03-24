import { useState } from 'react'
import type { Absence, Assignment, Employee, ShiftType, Violation } from '../../api/types'
import { getViolationsForCell } from '../../hooks/useValidation'
import { getDaysInMonth, getAssignment, getShiftType, getCoverageForDay } from './grid-utils'
import { ShiftCell } from './ShiftCell'
import { ShiftPicker } from './ShiftPicker'

interface Props {
  year: number
  month: number
  employees: Employee[]
  shiftTypes: ShiftType[]
  assignments: Assignment[]
  absences?: Absence[]
  violations?: Violation[]
  onCellChange?: (date: string, employeeId: number, shiftTypeId: number | null) => void
}

export function MonthGrid({ year, month, employees, shiftTypes, assignments, absences = [], violations = [], onCellChange }: Props) {
  const days = getDaysInMonth(year, month)
  const [editingCell, setEditingCell] = useState<string | null>(null)

  function handleCellClick(date: string, employeeId: number) {
    if (!onCellChange) return
    const key = `${date}-${employeeId}`
    setEditingCell(prev => prev === key ? null : key)
  }

  function handleSelect(date: string, employeeId: number, shiftTypeId: number | null) {
    onCellChange?.(date, employeeId, shiftTypeId)
    setEditingCell(null)
  }

  return (
    <div className="schedule-grid">
      <table className="schedule-table">
        <thead>
          <tr>
            <th className="employee-header">Empleado</th>
            {days.map(day => (
              <th key={day.date} className={day.isWeekend ? 'weekend' : ''}>
                <div className="day-header-dow">{day.dayOfWeek}</div>
                <div className="day-header-num">{day.dayOfMonth}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {employees.map(emp => (
            <tr key={emp.id}>
              <td className="employee-name">{emp.name}</td>
              {days.map(day => {
                const assignment = getAssignment(assignments, day.date, emp.id)
                const shiftTypeId = assignment?.shift_type_id ?? null
                const shift = getShiftType(shiftTypes, shiftTypeId)
                const cellKey = `${day.date}-${emp.id}`
                const isEditing = editingCell === cellKey
                const cellViolations = getViolationsForCell(violations, day.date, emp.id)
                const violationClass = getViolationCellClass(cellViolations)
                const isAbsent = isEmployeeAbsent(absences, day.date, emp.id)

                return (
                  <td
                    key={day.date}
                    className={`${day.isWeekend ? 'weekend' : ''} ${!shift ? 'day-off' : ''} ${onCellChange && !isAbsent ? 'editable' : ''} ${violationClass} ${isAbsent ? 'has-absence' : ''}`}
                    onClick={() => !isAbsent && handleCellClick(day.date, emp.id)}
                    title={isAbsent ? 'Ausencia' : cellViolations.map(v => v.message).join('\n') || undefined}
                  >
                    <ShiftCell shift={shift} />
                    {isEditing && (
                      <ShiftPicker
                        shiftTypes={shiftTypes}
                        currentShiftTypeId={shiftTypeId}
                        onSelect={(id) => handleSelect(day.date, emp.id, id)}
                        onClose={() => setEditingCell(null)}
                      />
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
          <tr className="coverage-row">
            <td className="employee-name">Cobertura</td>
            {days.map(day => {
              const count = getCoverageForDay(assignments, day.date)
              return (
                <td key={day.date} className={count === 0 ? 'coverage-low' : ''}>
                  {count || '—'}
                </td>
              )
            })}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function isEmployeeAbsent(absences: Absence[], date: string, employeeId: number): boolean {
  return absences.some(a =>
    a.employee_id === employeeId && a.start_date <= date && a.end_date >= date
  )
}

function getViolationCellClass(violations: Violation[]): string {
  if (violations.length === 0) return ''
  const hasGrave = violations.some(v => v.resolvable && v.severity === 'grave')
  if (hasGrave) return 'has-grave-violation'
  const hasWarning = violations.some(v => v.resolvable && v.severity === 'warning')
  if (hasWarning) return 'has-warning-violation'
  return 'has-structural-violation'
}
