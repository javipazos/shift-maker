export type Tab = 'schedule' | 'config' | 'absences' | 'validation' | 'summary'

const TAB_LABELS: Record<Tab, string> = {
  schedule: 'Horario',
  config: 'Configuración',
  absences: 'Ausencias',
  validation: 'Validación',
  summary: 'Resumen',
}

interface Props {
  active: Tab
  onChange: (tab: Tab) => void
}

export function TabNav({ active, onChange }: Props) {
  return (
    <nav className="tab-nav">
      {(Object.keys(TAB_LABELS) as Tab[]).map(tab => (
        <button
          key={tab}
          className={tab === active ? 'active' : ''}
          onClick={() => onChange(tab)}
        >
          {TAB_LABELS[tab]}
        </button>
      ))}
    </nav>
  )
}
