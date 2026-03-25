import { useState } from 'react'
import type { Employee } from '../../api/types'

const ABSENCE_TYPES = [
  { value: 'vacation', label: 'Vacaciones' },
  { value: 'sick', label: 'Baja médica' },
  { value: 'training', label: 'Formación' },
  { value: 'personal', label: 'Permiso personal' },
  { value: 'other', label: 'Otro' },
] as const

interface Props {
  employees: Employee[]
  onSubmit: (data: {
    employee_id: number
    start_date: string
    end_date: string
    type: string
    counts_as_work: boolean
    notes: string | null
  }) => void
}

export function AbsenceForm({ employees, onSubmit }: Props) {
  const [employeeId, setEmployeeId] = useState(employees[0]?.id ?? 0)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [type, setType] = useState<string>('vacation')
  const [countsAsWork, setCountsAsWork] = useState(false)
  const [notes, setNotes] = useState('')

  const dateError = startDate && endDate && startDate > endDate
    ? 'La fecha de inicio debe ser anterior o igual a la de fin'
    : ''

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!startDate || !endDate || !employeeId || dateError) return

    onSubmit({
      employee_id: employeeId,
      start_date: startDate,
      end_date: endDate,
      type,
      counts_as_work: countsAsWork,
      notes: notes || null,
    })

    setStartDate('')
    setEndDate('')
    setNotes('')
  }

  return (
    <form className="absence-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <label>
          Empleado
          <select value={employeeId} onChange={e => setEmployeeId(Number(e.target.value))}>
            {employees.map(emp => (
              <option key={emp.id} value={emp.id}>{emp.name}</option>
            ))}
          </select>
        </label>
        <label>
          Tipo
          <select value={type} onChange={e => setType(e.target.value)}>
            {ABSENCE_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="form-row">
        <label>
          Desde
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} required />
        </label>
        <label>
          Hasta
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} required />
        </label>
      </div>
      <div className="form-row">
        <label className="checkbox-label">
          <input type="checkbox" checked={countsAsWork} onChange={e => setCountsAsWork(e.target.checked)} />
          Cuenta como jornada laboral
        </label>
      </div>
      <div className="form-row">
        <label>
          Notas
          <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Opcional" />
        </label>
      </div>
      {dateError && <p className="form-error">{dateError}</p>}
      <button type="submit" className="btn-primary" disabled={!!dateError}>Añadir ausencia</button>
    </form>
  )
}
