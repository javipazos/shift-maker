import type { Violation } from '../../api/types'
import { ViolationItem } from './ViolationItem'

interface Props {
  violations: Violation[]
  score: number
  correctableCount: number
  structuralCount: number
  loading: boolean
  error?: string | null
}

export function ValidationPanel({ violations, score, correctableCount, structuralCount, loading, error }: Props) {
  const grave = violations.filter(v => v.resolvable && v.severity === 'grave')
  const warnings = violations.filter(v => v.resolvable && v.severity === 'warning')
  const structural = violations.filter(v => !v.resolvable)

  return (
    <div className="validation-panel">
      <div className="validation-header">
        <div className="validation-score">
          <span className={`score-value ${getScoreClass(score)}`}>
            {score}%
          </span>
          <span className="score-label">cumplimiento</span>
        </div>
        <div className="validation-counts">
          {correctableCount > 0 && (
            <span className="count-correctable">
              {correctableCount} corregible{correctableCount !== 1 ? 's' : ''}
            </span>
          )}
          {structuralCount > 0 && (
            <span className="count-structural">
              {structuralCount} estructural{structuralCount !== 1 ? 'es' : ''}
            </span>
          )}
          {violations.length === 0 && !loading && (
            <span className="count-ok">Sin violaciones</span>
          )}
        </div>
        {loading && <span className="validation-loading">Validando...</span>}
        {error && <span className="validation-error">Error: {error}</span>}
      </div>

      {grave.length > 0 && (
        <div className="violation-group">
          <h4 className="violation-group-title violation-grave-title">Faltas graves</h4>
          {grave.map((v, i) => <ViolationItem key={`g-${i}`} violation={v} />)}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="violation-group">
          <h4 className="violation-group-title violation-warning-title">Advertencias</h4>
          {warnings.map((v, i) => <ViolationItem key={`w-${i}`} violation={v} />)}
        </div>
      )}

      {structural.length > 0 && (
        <div className="violation-group">
          <h4 className="violation-group-title violation-structural-title">Limitaciones estructurales</h4>
          {structural.map((v, i) => <ViolationItem key={`s-${i}`} violation={v} />)}
        </div>
      )}
    </div>
  )
}

function getScoreClass(score: number): string {
  if (score >= 90) return 'score-good'
  if (score >= 70) return 'score-ok'
  return 'score-bad'
}
