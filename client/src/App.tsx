import { useCallback, useEffect, useState } from 'react'
import './styles/layout.css'
import './styles/grid.css'
import './styles/validation.css'
import './styles/forms.css'
import { createAbsence, createEmployee, deleteAbsence, fetchAllEmployees, generateSchedule, updateEmployee } from './api/client'
import type { Employee } from './api/types'
import { AbsenceForm } from './components/absences/AbsenceForm'
import { EmployeeForm } from './components/config/EmployeeForm'
import { EmployeeList } from './components/config/EmployeeList'
import { AbsenceList } from './components/absences/AbsenceList'
import { MonthSelector } from './components/layout/MonthSelector'
import { TabNav, type Tab } from './components/layout/TabNav'
import { MonthGrid } from './components/schedule/MonthGrid'
import { MetricsPanel } from './components/summary/MetricsPanel'
import { ValidationPanel } from './components/validation/ValidationPanel'
import { useSchedule } from './hooks/useSchedule'
import { useValidation } from './hooks/useValidation'

function App() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [activeTab, setActiveTab] = useState<Tab>('schedule')
  const [generating, setGenerating] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null)
  const [allEmployees, setAllEmployees] = useState<Employee[]>([])

  const loadAllEmployees = useCallback(async () => {
    const emps = await fetchAllEmployees()
    setAllEmployees(emps)
  }, [])

  useEffect(() => {
    if (activeTab === 'config') loadAllEmployees()
  }, [activeTab, loadAllEmployees])

  const schedule = useSchedule(year, month)
  const validation = useValidation(year, month, !!schedule.schedule, schedule.dirty)

  function handleMonthChange(y: number, m: number) {
    setYear(y)
    setMonth(m)
  }

  const handleGenerate = useCallback(async () => {
    setGenerating(true)
    try {
      await generateSchedule(year, month)
      await schedule.reload()
      await validation.validate()
    } finally {
      setGenerating(false)
    }
  }, [year, month, schedule.reload, validation.validate])

  async function handleCreateAbsence(data: Parameters<typeof createAbsence>[0]) {
    await createAbsence(data)
    await schedule.reload()
  }

  async function handleDeleteAbsence(id: number) {
    await deleteAbsence(id)
    await schedule.reload()
  }

  async function handleCreateOrUpdateEmployee(data: Omit<Employee, 'id' | 'created_at'>) {
    if (editingEmployee) {
      await updateEmployee(editingEmployee.id, data)
      setEditingEmployee(null)
    } else {
      await createEmployee(data)
    }
    await loadAllEmployees()
    await schedule.reload()
  }

  async function handleToggleEmployeeStatus(emp: Employee) {
    const newStatus = emp.status === 'active' ? 'inactive' : 'active'
    await updateEmployee(emp.id, { status: newStatus })
    await loadAllEmployees()
    await schedule.reload()
  }

  function handleExport() {
    window.open(`/api/schedules/${year}/${month}/export`, '_blank')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Shift Maker</h1>
        <MonthSelector year={year} month={month} onChange={handleMonthChange} />
        <button
          className="btn-generate"
          onClick={handleGenerate}
          disabled={generating || schedule.loading}
        >
          {generating ? 'Generando...' : 'Generar horario'}
        </button>
        {schedule.schedule && (
          <button className="btn-export" onClick={handleExport}>
            Exportar .xlsx
          </button>
        )}
      </aside>
      <main className="main-content">
        <TabNav active={activeTab} onChange={setActiveTab} />
        {activeTab === 'schedule' && (
          <>
            {schedule.loading && <p>Cargando...</p>}
            {schedule.error && <p style={{ color: 'var(--color-error)' }}>Error: {schedule.error}</p>}
            {!schedule.loading && !schedule.error && (
              <>
                {schedule.dirty && (
                  <div className="save-bar">
                    <button
                      className="btn-save"
                      onClick={schedule.save}
                      disabled={schedule.saving}
                    >
                      {schedule.saving ? 'Guardando...' : 'Guardar'}
                    </button>
                    <span className="status">Hay cambios sin guardar</span>
                  </div>
                )}
                <MonthGrid
                  year={year}
                  month={month}
                  employees={schedule.employees}
                  shiftTypes={schedule.shiftTypes}
                  assignments={schedule.assignments}
                  absences={schedule.absences}
                  violations={validation.violations}
                  onCellChange={schedule.updateCell}
                />
                <ValidationPanel
                  violations={validation.violations}
                  score={validation.score}
                  correctableCount={validation.correctableCount}
                  structuralCount={validation.structuralCount}
                  loading={validation.loading}
                />
              </>
            )}
          </>
        )}
        {activeTab === 'config' && (
          <>
            <EmployeeForm
              editing={editingEmployee}
              onSubmit={handleCreateOrUpdateEmployee}
              onCancel={() => setEditingEmployee(null)}
            />
            <EmployeeList
              employees={allEmployees}
              onEdit={setEditingEmployee}
              onToggleStatus={handleToggleEmployeeStatus}
            />
          </>
        )}
        {activeTab === 'absences' && (
          <>
            <AbsenceForm
              employees={schedule.employees}
              onSubmit={handleCreateAbsence}
            />
            <AbsenceList
              absences={schedule.absences}
              employees={schedule.employees}
              onDelete={handleDeleteAbsence}
            />
          </>
        )}
        {activeTab === 'validation' && (
          <ValidationPanel
            violations={validation.violations}
            score={validation.score}
            correctableCount={validation.correctableCount}
            structuralCount={validation.structuralCount}
            loading={validation.loading}
          />
        )}
        {activeTab === 'summary' && (
          <MetricsPanel
            year={year}
            month={month}
            hasSchedule={!!schedule.schedule}
          />
        )}
      </main>
    </div>
  )
}

export default App
