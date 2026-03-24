import { useEffect, useState } from 'react'
import type { Employee } from '../../api/types'

const CONTRACT_TYPES = [
  { value: 'full_time', label: 'Jornada completa' },
  { value: 'part_time', label: 'Media jornada' },
] as const

const SHIFT_PREFERENCES = [
  { value: 'none', label: 'Sin preferencia' },
  { value: 'morning', label: 'Mañana' },
  { value: 'afternoon', label: 'Tarde' },
  { value: 'flexible', label: 'Flexible' },
] as const

const PREFERENCE_STRENGTHS = [
  { value: 'desirable', label: 'Deseable' },
  { value: 'mandatory', label: 'Obligatorio' },
] as const

type EmployeeData = Omit<Employee, 'id' | 'created_at'>

interface Props {
  editing: Employee | null
  onSubmit: (data: EmployeeData) => void
  onCancel: () => void
}

const DEFAULTS: EmployeeData = {
  name: '',
  hours_per_day: 7.5,
  max_hours_per_week: 37.5,
  contract_type: 'full_time',
  shift_preference: 'none',
  preference_strength: 'desirable',
  status: 'active',
}

export function EmployeeForm({ editing, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<EmployeeData>(DEFAULTS)

  useEffect(() => {
    if (editing) {
      const { id: _, created_at: __, ...data } = editing
      setForm(data)
    } else {
      setForm(DEFAULTS)
    }
  }, [editing])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) return
    onSubmit(form)
    if (!editing) setForm(DEFAULTS)
  }

  function updateField<K extends keyof EmployeeData>(key: K, value: EmployeeData[K]) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  return (
    <form className="config-form" onSubmit={handleSubmit}>
      <h3>{editing ? `Editando: ${editing.name}` : 'Nuevo empleado'}</h3>
      <div className="form-row">
        <label>
          Nombre
          <input
            type="text"
            value={form.name}
            onChange={e => updateField('name', e.target.value)}
            required
          />
        </label>
        <label>
          Tipo de contrato
          <select
            value={form.contract_type}
            onChange={e => updateField('contract_type', e.target.value as EmployeeData['contract_type'])}
          >
            {CONTRACT_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="form-row">
        <label>
          Horas/día
          <input
            type="number"
            step="0.5"
            min="1"
            max="12"
            value={form.hours_per_day}
            onChange={e => updateField('hours_per_day', Number(e.target.value))}
            required
          />
        </label>
        <label>
          Máx. horas/semana
          <input
            type="number"
            step="0.5"
            min="1"
            max="60"
            value={form.max_hours_per_week}
            onChange={e => updateField('max_hours_per_week', Number(e.target.value))}
            required
          />
        </label>
      </div>
      <div className="form-row">
        <label>
          Preferencia de turno
          <select
            value={form.shift_preference}
            onChange={e => updateField('shift_preference', e.target.value as EmployeeData['shift_preference'])}
          >
            {SHIFT_PREFERENCES.map(p => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </label>
        <label>
          Fuerza de preferencia
          <select
            value={form.preference_strength}
            onChange={e => updateField('preference_strength', e.target.value as EmployeeData['preference_strength'])}
          >
            {PREFERENCE_STRENGTHS.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn-primary">
          {editing ? 'Guardar cambios' : 'Añadir empleado'}
        </button>
        {editing && (
          <button type="button" className="btn-cancel" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
