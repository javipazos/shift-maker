import type { Violation } from '../../api/types'

interface Props {
  violation: Violation
}

export function ViolationItem({ violation }: Props) {
  const icon = getIcon(violation)
  const className = getClassName(violation)

  return (
    <div className={`violation-item ${className}`}>
      <span className="violation-icon">{icon}</span>
      <span className="violation-message">{violation.message}</span>
    </div>
  )
}

function getIcon(v: Violation): string {
  if (!v.resolvable) return 'ℹ'
  return v.severity === 'grave' ? '✗' : '⚠'
}

function getClassName(v: Violation): string {
  if (!v.resolvable) return 'violation-structural'
  return v.severity === 'grave' ? 'violation-grave' : 'violation-warning'
}
