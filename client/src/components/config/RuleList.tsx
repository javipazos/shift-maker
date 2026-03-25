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
