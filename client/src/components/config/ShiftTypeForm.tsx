import { useEffect, useState } from 'react'
import type { ShiftType } from '../../api/types'

type ShiftTypeData = Omit<ShiftType, 'id' | 'created_at'>

interface Props {
  editing: ShiftType | null
  onSubmit: (data: ShiftTypeData) => void
  onCancel: () => void
}

function calcHours(start: string, end: string): number {
  const [sh, sm] = start.split(':').map(Number)
  const [eh, em] = end.split(':').map(Number)
  let diff = (eh * 60 + em) - (sh * 60 + sm)
  if (diff <= 0) diff += 24 * 60
  return Math.round(diff / 30) * 0.5
}

const DEFAULTS: ShiftTypeData = {
  name: '',
  start_time: '07:00',
  end_time: '14:30',
  effective_hours: 7.5,
  priority_order: 1,
  color: '#4CAF50',
  status: 'active',
}

export function ShiftTypeForm({ editing, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<ShiftTypeData>(DEFAULTS)

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

  function updateField<K extends keyof ShiftTypeData>(key: K, value: ShiftTypeData[K]) {
    setForm(prev => {
      const next = { ...prev, [key]: value }
      if (key === 'start_time' || key === 'end_time') {
        next.effective_hours = calcHours(next.start_time, next.end_time)
      }
      return next
    })
  }

  return (
    <form className="config-form" onSubmit={handleSubmit}>
      <h3>{editing ? `Editando: ${editing.name}` : 'Nuevo horario'}</h3>
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
          Color
          <input
            type="color"
            value={form.color}
            onChange={e => updateField('color', e.target.value)}
          />
        </label>
      </div>
      <div className="form-row">
        <label>
          Hora inicio
          <input
            type="time"
            value={form.start_time}
            onChange={e => updateField('start_time', e.target.value)}
            required
          />
        </label>
        <label>
          Hora fin
          <input
            type="time"
            value={form.end_time}
            onChange={e => updateField('end_time', e.target.value)}
            required
          />
        </label>
      </div>
      <div className="form-row">
        <label>
          Horas efectivas
          <input type="text" value={`${form.effective_hours}h`} disabled />
        </label>
        <label>
          Prioridad (orden)
          <input
            type="number"
            min="1"
            max="10"
            value={form.priority_order}
            onChange={e => updateField('priority_order', Number(e.target.value))}
            required
          />
        </label>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn-primary">
          {editing ? 'Guardar cambios' : 'Añadir horario'}
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
