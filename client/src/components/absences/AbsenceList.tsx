import type { Absence, Employee } from '../../api/types'

const TYPE_LABELS: Record<string, string> = {
  vacation: 'Vacaciones',
  sick: 'Baja médica',
  training: 'Formación',
  personal: 'Permiso personal',
  other: 'Otro',
}

interface Props {
  absences: Absence[]
  employees: Employee[]
  onDelete: (id: number) => void
}

export function AbsenceList({ absences, employees, onDelete }: Props) {
  if (absences.length === 0) {
    return <p className="empty-state">No hay ausencias este mes.</p>
  }

  function getEmployeeName(id: number): string {
    return employees.find(e => e.id === id)?.name ?? `ID ${id}`
  }

  return (
    <table className="absence-table">
      <thead>
        <tr>
          <th>Empleado</th>
          <th>Tipo</th>
          <th>Desde</th>
          <th>Hasta</th>
          <th>Cuenta como trabajo</th>
          <th>Notas</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {absences.map(a => (
          <tr key={a.id}>
            <td>{getEmployeeName(a.employee_id)}</td>
            <td>{TYPE_LABELS[a.type] ?? a.type}</td>
            <td>{a.start_date}</td>
            <td>{a.end_date}</td>
            <td>{a.counts_as_work ? 'Sí' : 'No'}</td>
            <td>{a.notes ?? '—'}</td>
            <td>
              <button className="btn-delete" onClick={() => onDelete(a.id)}>Eliminar</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
