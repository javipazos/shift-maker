import type { ShiftType } from '../../api/types'

interface Props {
  shift: ShiftType | undefined
}

export function ShiftCell({ shift }: Props) {
  if (!shift) {
    return <span className="shift-cell">L</span>
  }

  return (
    <span
      className="shift-cell"
      style={{ color: shift.color }}
      title={`${shift.name} (${shift.start_time} - ${shift.end_time})`}
    >
      {shift.name}
    </span>
  )
}

export function formatShiftLabel(shift: ShiftType): string {
  return `${shift.start_time.replace(':00', '')}-${shift.end_time.replace(':00', '')}`
}
