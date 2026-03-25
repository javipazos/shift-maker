import type { ShiftType } from '../../api/types'

interface Props {
  shiftTypes: ShiftType[]
  onEdit: (shiftType: ShiftType) => void
  onToggleStatus: (shiftType: ShiftType) => void
  onDelete: (shiftType: ShiftType) => void
}

export function ShiftTypeList({ shiftTypes, onEdit, onToggleStatus, onDelete }: Props) {
  if (shiftTypes.length === 0) {
    return <p className="empty-state">No hay horarios registrados.</p>
  }

  return (
    <table className="absence-table">
      <thead>
        <tr>
          <th>Color</th>
          <th>Nombre</th>
          <th>Inicio</th>
          <th>Fin</th>
          <th>Horas</th>
          <th>Prioridad</th>
          <th>Estado</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {shiftTypes.map(st => (
          <tr key={st.id} className={st.status === 'inactive' ? 'row-inactive' : ''}>
            <td>
              <span
                className="color-swatch"
                style={{ backgroundColor: st.color }}
              />
            </td>
            <td>{st.name}</td>
            <td>{st.start_time}</td>
            <td>{st.end_time}</td>
            <td>{st.effective_hours}</td>
            <td>{st.priority_order}</td>
            <td>
              <span className={`status-badge status-${st.status}`}>
                {st.status === 'active' ? 'Activo' : 'Inactivo'}
              </span>
            </td>
            <td className="action-buttons">
              <button className="btn-edit" onClick={() => onEdit(st)}>
                Editar
              </button>
              <button
                className={st.status === 'active' ? 'btn-delete' : 'btn-activate'}
                onClick={() => onToggleStatus(st)}
              >
                {st.status === 'active' ? 'Desactivar' : 'Activar'}
              </button>
              <button
                className="btn-destroy"
                onClick={() => {
                  if (confirm(`¿Eliminar "${st.name}" permanentemente?`)) onDelete(st)
                }}
              >
                Borrar
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
