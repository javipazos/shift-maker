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
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null)
  const [allEmployees, setAllEmployees] = useState<Employee[]>([])

  const loadAllEmployees = useCallback(async () => {
    const emps = await fetchAllEmployees()
    setAllEmployees(emps)
  }, [])

  // Wake up backend on app load to reduce cold start latency
  useEffect(() => {
    const wakeUpBackend = async () => {
      try {
        await fetch('/api/health', { method: 'HEAD' })
      } catch {
        // Silently ignore - this is just a wake-up ping
      }
    }
    wakeUpBackend()
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

  const hasPins = schedule.pinned.size > 0

  const handleGenerate = useCallback(async () => {
    setGenerating(true)
    setGenerateError(null)
    try {
      const fixed = schedule.getPinnedAssignments()
      await generateSchedule(year, month, fixed.length > 0 ? fixed : undefined)
      await schedule.reload()
      await validation.validate()
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : 'Error al generar horario')
    } finally {
      setGenerating(false)
    }
  }, [year, month, schedule.reload, schedule.getPinnedAssignments, validation.validate])

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
          {generating ? 'Generando...' : hasPins ? 'Regenerar (con fijados)' : 'Generar horario'}
        </button>
        {generateError && (
          <p className="sidebar-error">{generateError}</p>
        )}
        {hasPins && (
          <div className="pin-info">
            <span>{schedule.pinned.size} celda{schedule.pinned.size !== 1 ? 's' : ''} fijada{schedule.pinned.size !== 1 ? 's' : ''}</span>
            <button className="btn-clear-pins" onClick={schedule.clearPins}>
              Limpiar
            </button>
          </div>
        )}
        {!hasPins && schedule.schedule && (
          <p className="sidebar-hint">Haz clic en el punto azul de una celda para fijarla antes de regenerar.</p>
        )}
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
            {schedule.loading && <p className="loading-hint">Cargando... (la primera vez puede tardar unos segundos)</p>}
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
                  isPinned={schedule.isPinned}
                  onTogglePin={schedule.togglePin}
                />
                <ValidationPanel
                  violations={validation.violations}
                  score={validation.score}
                  correctableCount={validation.correctableCount}
                  structuralCount={validation.structuralCount}
                  loading={validation.loading}
                  error={validation.error}
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
