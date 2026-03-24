import type { Employee } from '../../api/types'

const CONTRACT_LABELS: Record<string, string> = {
  full_time: 'Completa',
  part_time: 'Parcial',
}

const PREFERENCE_LABELS: Record<string, string> = {
  none: '—',
  morning: 'Mañana',
  afternoon: 'Tarde',
  flexible: 'Flexible',
}

interface Props {
  employees: Employee[]
  onEdit: (employee: Employee) => void
  onToggleStatus: (employee: Employee) => void
}

export function EmployeeList({ employees, onEdit, onToggleStatus }: Props) {
  if (employees.length === 0) {
    return <p className="empty-state">No hay empleados registrados.</p>
  }

  return (
    <table className="absence-table">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Contrato</th>
          <th>Horas/día</th>
          <th>Máx. h/semana</th>
          <th>Preferencia</th>
          <th>Estado</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {employees.map(emp => (
          <tr key={emp.id} className={emp.status === 'inactive' ? 'row-inactive' : ''}>
            <td>{emp.name}</td>
            <td>{CONTRACT_LABELS[emp.contract_type] ?? emp.contract_type}</td>
            <td>{emp.hours_per_day}</td>
            <td>{emp.max_hours_per_week}</td>
            <td>{PREFERENCE_LABELS[emp.shift_preference] ?? emp.shift_preference}</td>
            <td>
              <span className={`status-badge status-${emp.status}`}>
                {emp.status === 'active' ? 'Activo' : 'Inactivo'}
              </span>
            </td>
            <td className="action-buttons">
              <button className="btn-edit" onClick={() => onEdit(emp)}>
                Editar
              </button>
              <button
                className={emp.status === 'active' ? 'btn-delete' : 'btn-activate'}
                onClick={() => onToggleStatus(emp)}
              >
                {emp.status === 'active' ? 'Desactivar' : 'Activar'}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
