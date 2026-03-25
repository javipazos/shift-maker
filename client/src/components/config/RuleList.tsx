import { useState } from 'react'
import type { Rule } from '../../api/types'

const CATEGORY_LABELS: Record<string, string> = {
  rest: 'Descanso',
  coverage: 'Cobertura',
  equity: 'Equidad',
  limits: 'Límites',
}

const PRIORITY_LABELS: Record<string, string> = {
  mandatory: 'Obligatoria',
  desirable: 'Deseable',
}

const RULE_DESCRIPTIONS: Record<string, string> = {
  min_rest_between_shifts: 'Horas mínimas de descanso entre el final de un turno y el inicio del siguiente. Evita que alguien cierre por la tarde y abra por la mañana.',
  max_consecutive_days: 'Límite de días seguidos trabajando sin descanso. Después de este máximo, el empleado debe tener al menos un día libre.',
  min_consecutive_free_days: 'Cuando un empleado tiene días libres, deben ser al menos esta cantidad seguidos. Evita días libres aislados que no permiten descansar de verdad.',
  weekly_rest: 'Días mínimos de descanso por semana (puede ser fracción, ej: 1.5 = un día y medio libre por semana).',
  min_daily_coverage: 'Número mínimo de personas trabajando cada día. Se configura por separado para días de semana y fines de semana.',
  weekend_shift_coverage: 'Los fines de semana deben tener cubiertos los turnos prioritarios (mañana y tarde). Evita que un fin de semana quede sin turno de mañana.',
  min_per_shift_coverage: 'Cada tipo de turno debe tener al menos esta cantidad de personas asignadas. Útil si necesitas que siempre haya alguien en cada turno.',
  priority_shift_coverage: 'Los turnos de mayor prioridad deben cubrirse antes que los de menor prioridad. Si solo hay una persona, va al turno más importante.',
  monthly_free_weekend: 'Cada empleado debe tener al menos este número de fines de semana completamente libres (sábado + domingo) al mes.',
  weekend_distribution: 'Los fines de semana trabajados deben repartirse de forma equitativa entre todos los empleados. Nadie debería trabajar muchos más fines de semana que otro.',
  hours_distribution: 'Las horas totales del mes deben repartirse de forma equitativa entre empleados del mismo tipo de contrato.',
  max_weekly_hours: 'No superar las horas máximas semanales definidas en el perfil de cada empleado (ej: 37.5h para jornada completa).',
  max_daily_hours: 'Ningún empleado puede trabajar más de estas horas en un solo día.',
  requested_days_off: 'Respetar las ausencias registradas (vacaciones, bajas, etc.). Si alguien tiene una ausencia, no se le asigna turno ese día.',
}

const PARAM_LABELS: Record<string, string> = {
  min_hours: 'Horas mínimas',
  max_days: 'Máximo días',
  min_days: 'Mínimo días',
  weekday_min: 'Mín. entre semana',
  weekend_min: 'Mín. fin de semana',
  min_per_shift: 'Mín. por turno',
  min_free_weekends: 'Fines de semana libres',
  max_hours: 'Máximo horas',
}

interface Props {
  rules: Rule[]
  onToggle: (rule: Rule) => void
  onUpdate: (ruleId: string, data: Partial<Rule>) => void
}

export function RuleList({ rules, onToggle, onUpdate }: Props) {
  const grouped = groupByCategory(rules)

  return (
    <div className="rule-list">
      {Object.entries(grouped).map(([category, categoryRules]) => (
        <div key={category} className="rule-category">
          <h4 className="rule-category-title">{CATEGORY_LABELS[category] ?? category}</h4>
          {categoryRules.map(rule => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onToggle={() => onToggle(rule)}
              onUpdate={(data) => onUpdate(rule.id, data)}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

interface RuleCardProps {
  rule: Rule
  onToggle: () => void
  onUpdate: (data: Partial<Rule>) => void
}

function RuleCard({ rule, onToggle, onUpdate }: RuleCardProps) {
  const [editing, setEditing] = useState(false)
  const [weight, setWeight] = useState(rule.weight)
  const [priority, setPriority] = useState(rule.priority)
  const [params, setParams] = useState<Record<string, unknown>>({ ...rule.params })

  function handleSave() {
    onUpdate({ weight, priority, params })
    setEditing(false)
  }

  function handleCancel() {
    setWeight(rule.weight)
    setPriority(rule.priority)
    setParams({ ...rule.params })
    setEditing(false)
  }

  const editableParams = Object.entries(params).filter(
    ([, v]) => typeof v === 'number'
  )

  return (
    <div className={`rule-card ${!rule.active ? 'rule-inactive' : ''}`}>
      <div className="rule-header">
        <label className="rule-toggle">
          <input type="checkbox" checked={rule.active} onChange={onToggle} />
          <span className="rule-name">{rule.name}</span>
        </label>
        <span className={`priority-badge priority-${rule.priority}`}>
          {PRIORITY_LABELS[rule.priority]}
        </span>
      </div>
      {RULE_DESCRIPTIONS[rule.id] && (
        <p className="rule-description">{RULE_DESCRIPTIONS[rule.id]}</p>
      )}

      {rule.active && !editing && (
        <div className="rule-summary">
          <span className="rule-weight">Peso: {rule.weight}/10</span>
          {editableParams.map(([key, val]) => (
            <span key={key} className="rule-param-tag">
              {PARAM_LABELS[key] ?? key}: {String(val)}
            </span>
          ))}
          <button className="btn-edit-small" onClick={() => setEditing(true)}>
            Editar
          </button>
        </div>
      )}

      {rule.active && editing && (
        <div className="rule-edit">
          <div className="rule-edit-row">
            <label>
              Prioridad
              <select
                value={priority}
                onChange={e => setPriority(e.target.value as Rule['priority'])}
              >
                <option value="mandatory">Obligatoria</option>
                <option value="desirable">Deseable</option>
              </select>
            </label>
            <label>
              Peso (1-10)
              <input
                type="number"
                min="1"
                max="10"
                value={weight}
                onChange={e => setWeight(Number(e.target.value))}
              />
            </label>
          </div>
          {editableParams.length > 0 && (
            <div className="rule-edit-row">
              {editableParams.map(([key, val]) => (
                <label key={key}>
                  {PARAM_LABELS[key] ?? key}
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={Number(val)}
                    onChange={e => setParams(p => ({ ...p, [key]: Number(e.target.value) }))}
                  />
                </label>
              ))}
            </div>
          )}
          <div className="form-actions">
            <button className="btn-primary" onClick={handleSave}>Guardar</button>
            <button className="btn-cancel" onClick={handleCancel}>Cancelar</button>
          </div>
        </div>
      )}
    </div>
  )
}

function groupByCategory(rules: Rule[]): Record<string, Rule[]> {
  const grouped: Record<string, Rule[]> = {}
  for (const rule of rules) {
    if (!grouped[rule.category]) grouped[rule.category] = []
    grouped[rule.category].push(rule)
  }
  return grouped
}
