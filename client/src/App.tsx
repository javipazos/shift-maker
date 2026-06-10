import { SignInButton, UserButton, useAuth } from '@clerk/react'
import { useCallback, useEffect, useState } from 'react'
import './styles/layout.css'
import './styles/grid.css'
import './styles/validation.css'
import './styles/forms.css'
import { createAbsence, createEmployee, createShiftType, deleteAbsence, deleteEmployee, deleteSchedule, deleteShiftType, fetchAllEmployees, fetchAllShiftTypes, fetchRules, generateSchedule, importSchedule, setTokenGetter, updateEmployee, updateRule, updateShiftType } from './api/client'
import type { Employee, Rule, ShiftType } from './api/types'
import { AbsenceForm } from './components/absences/AbsenceForm'
import { EmployeeForm } from './components/config/EmployeeForm'
import { EmployeeList } from './components/config/EmployeeList'
import { ShiftTypeForm } from './components/config/ShiftTypeForm'
import { ShiftTypeList } from './components/config/ShiftTypeList'
import { RuleList } from './components/config/RuleList'
import { AbsenceList } from './components/absences/AbsenceList'
import { MonthSelector } from './components/layout/MonthSelector'
import { TabNav, type Tab } from './components/layout/TabNav'
import { MonthGrid } from './components/schedule/MonthGrid'
import { MetricsPanel } from './components/summary/MetricsPanel'
import { ValidationPanel } from './components/validation/ValidationPanel'
import { useSchedule } from './hooks/useSchedule'
import { useValidation } from './hooks/useValidation'

const clerkEnabled = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function App() {
  if (!clerkEnabled) return <AppContent />
  return <AuthGate />
}

function AuthGate() {
  const { isSignedIn, isLoaded, getToken } = useAuth()

  useEffect(() => {
    if (isSignedIn) setTokenGetter(getToken)
  }, [isSignedIn, getToken])

  if (!isLoaded) return null

  if (!isSignedIn) {
    return (
      <div className="login-screen">
        <h1>Shift Maker</h1>
        <p>Inicia sesión para continuar</p>
        <SignInButton mode="modal">
          <button className="btn-primary">Iniciar sesión</button>
        </SignInButton>
      </div>
    )
  }

  return <AppContent />
}

function AppContent() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [activeTab, setActiveTab] = useState<Tab>('schedule')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null)
  const [allEmployees, setAllEmployees] = useState<Employee[]>([])
  const [editingShiftType, setEditingShiftType] = useState<ShiftType | null>(null)
  const [allShiftTypes, setAllShiftTypes] = useState<ShiftType[]>([])
  const [allRules, setAllRules] = useState<Rule[]>([])
  const [configLoading, setConfigLoading] = useState(false)

  const loadAllEmployees = useCallback(async () => {
    const emps = await fetchAllEmployees()
    setAllEmployees(emps)
  }, [])

  const loadAllShiftTypes = useCallback(async () => {
    const types = await fetchAllShiftTypes()
    setAllShiftTypes(types)
  }, [])

  const loadRules = useCallback(async () => {
    const rules = await fetchRules()
    setAllRules(rules)
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
    if (activeTab === 'config') {
      setConfigLoading(true)
      Promise.all([loadAllEmployees(), loadAllShiftTypes(), loadRules()])
        .finally(() => setConfigLoading(false))
    }
  }, [activeTab, loadAllEmployees, loadAllShiftTypes, loadRules])

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
      const result = await generateSchedule(year, month, fixed.length > 0 ? fixed : undefined)
      if (result.status === 'infeasible') {
        setGenerateError(
          fixed.length > 0
            ? 'No existe ningún horario que cumpla las reglas con esas celdas fijadas. El horario actual no se ha modificado.'
            : 'No existe ningún horario que cumpla todas las reglas activas. Revisa las reglas o las ausencias. El horario actual no se ha modificado.'
        )
        return
      }
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

  async function handleDeleteEmployee(emp: Employee) {
    await deleteEmployee(emp.id)
    await loadAllEmployees()
    await schedule.reload()
  }

  async function handleCreateOrUpdateShiftType(data: Omit<ShiftType, 'id' | 'created_at'>) {
    if (editingShiftType) {
      await updateShiftType(editingShiftType.id, data)
      setEditingShiftType(null)
    } else {
      await createShiftType(data)
    }
    await loadAllShiftTypes()
    await schedule.reload()
  }

  async function handleToggleShiftTypeStatus(st: ShiftType) {
    const newStatus = st.status === 'active' ? 'inactive' : 'active'
    await updateShiftType(st.id, { status: newStatus })
    await loadAllShiftTypes()
    await schedule.reload()
  }

  async function handleDeleteShiftType(st: ShiftType) {
    await deleteShiftType(st.id)
    await loadAllShiftTypes()
    await schedule.reload()
  }

  async function handleToggleRule(rule: Rule) {
    await updateRule(rule.id, { active: !rule.active })
    await loadRules()
  }

  async function handleUpdateRule(ruleId: string, data: Partial<Rule>) {
    await updateRule(ruleId, data)
    await loadRules()
  }

  const [icsMenuOpen, setIcsMenuOpen] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [importWarnings, setImportWarnings] = useState<string[]>([])

  function handleExport() {
    window.open(`/api/schedules/${year}/${month}/export`, '_blank')
  }

  function handleExportIcs(employeeId: number) {
    window.open(`/api/schedules/${year}/${month}/export-ics/${employeeId}`, '_blank')
    setIcsMenuOpen(false)
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setImportError(null)
    setImportWarnings([])

    try {
      const result = await importSchedule(year, month, file)
      if (result.warnings.length > 0) {
        setImportWarnings(result.warnings)
      }
      await schedule.reload()
      await validation.validate()
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Error al importar')
    }
  }

  async function handleClearSchedule() {
    if (!confirm('¿Borrar todo el horario de este mes? Esta acción no se puede deshacer.')) return
    await deleteSchedule(year, month)
    await schedule.reload()
    await validation.validate()
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Shift Maker</h1>
          {clerkEnabled && <UserButton />}
        </div>
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
        <label className="btn-export btn-import-label">
          Importar .xlsx
          <input
            type="file"
            accept=".xlsx"
            onChange={handleImport}
            hidden
          />
        </label>
        {importError && (
          <p className="sidebar-error">{importError}</p>
        )}
        {importWarnings.length > 0 && (
          <details className="import-warnings">
            <summary>{importWarnings.length} aviso{importWarnings.length !== 1 ? 's' : ''}</summary>
            <ul>
              {importWarnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </details>
        )}
        {schedule.schedule && (
          <>
            <button className="btn-export" onClick={handleExport}>
              Exportar .xlsx
            </button>
            <div className="ics-export-group">
              <button
                className="btn-export"
                onClick={() => setIcsMenuOpen(!icsMenuOpen)}
              >
                Exportar calendario
                <span className={`ics-chevron ${icsMenuOpen ? 'ics-chevron-open' : ''}`}>▾</span>
              </button>
              {icsMenuOpen && (
                <ul className="ics-employee-list">
                  {schedule.employees.map(emp => (
                    <li key={emp.id}>
                      <button
                        className="ics-employee-btn"
                        onClick={() => handleExportIcs(emp.id)}
                      >
                        {emp.name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button className="btn-clear-schedule" onClick={handleClearSchedule}>
              Limpiar mes
            </button>
          </>
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
            {configLoading && <p className="loading-hint">Cargando... (la primera vez puede tardar unos segundos)</p>}
            {!configLoading && <>
            <h2 className="config-section-title">Empleados</h2>
            <EmployeeForm
              editing={editingEmployee}
              onSubmit={handleCreateOrUpdateEmployee}
              onCancel={() => setEditingEmployee(null)}
            />
            <EmployeeList
              employees={allEmployees}
              onEdit={setEditingEmployee}
              onToggleStatus={handleToggleEmployeeStatus}
              onDelete={handleDeleteEmployee}
            />
            <h2 className="config-section-title">Horarios</h2>
            <ShiftTypeForm
              editing={editingShiftType}
              onSubmit={handleCreateOrUpdateShiftType}
              onCancel={() => setEditingShiftType(null)}
            />
            <ShiftTypeList
              shiftTypes={allShiftTypes}
              onEdit={setEditingShiftType}
              onToggleStatus={handleToggleShiftTypeStatus}
              onDelete={handleDeleteShiftType}
            />
            <h2 className="config-section-title">Reglas</h2>
            <RuleList
              rules={allRules}
              onToggle={handleToggleRule}
              onUpdate={handleUpdateRule}
            />
            </>}
          </>
        )}
        {activeTab === 'absences' && (
          <>
            {schedule.loading && <p className="loading-hint">Cargando... (la primera vez puede tardar unos segundos)</p>}
            {!schedule.loading && <>
              <AbsenceForm
                employees={schedule.employees}
                onSubmit={handleCreateAbsence}
              />
              <AbsenceList
                absences={schedule.absences}
                employees={schedule.employees}
                onDelete={handleDeleteAbsence}
              />
            </>}
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
