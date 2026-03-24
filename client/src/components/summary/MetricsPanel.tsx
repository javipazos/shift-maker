import { useEffect, useState } from 'react'

interface EmployeeStat {
  employee_id: number
  name: string
  days_worked: number
  total_hours: number
  weekly_avg_hours: number
  max_consecutive_days: number
  free_weekends: number
}

interface SummaryData {
  employees: EmployeeStat[]
}

interface Props {
  year: number
  month: number
  hasSchedule: boolean
}

export function MetricsPanel({ year, month, hasSchedule }: Props) {
  const [data, setData] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!hasSchedule) {
      setData(null)
      return
    }

    setLoading(true)
    fetch(`/api/schedules/${year}/${month}/summary`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setData(d))
      .finally(() => setLoading(false))
  }, [year, month, hasSchedule])

  if (loading) return <p>Cargando resumen...</p>
  if (!data) return <p className="empty-state">No hay horario para mostrar métricas.</p>

  return (
    <div className="metrics-panel">
      <h3>Métricas por empleado</h3>
      <table className="absence-table">
        <thead>
          <tr>
            <th>Empleado</th>
            <th>Días trabajados</th>
            <th>Horas totales</th>
            <th>Horas/semana</th>
            <th>Máx. días consecutivos</th>
            <th>Fines de semana libres</th>
          </tr>
        </thead>
        <tbody>
          {data.employees.map(emp => (
            <tr key={emp.employee_id}>
              <td>{emp.name}</td>
              <td>{emp.days_worked}</td>
              <td>{emp.total_hours}</td>
              <td>{emp.weekly_avg_hours}</td>
              <td>{emp.max_consecutive_days}</td>
              <td>{emp.free_weekends}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
