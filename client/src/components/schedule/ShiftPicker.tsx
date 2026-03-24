import { useEffect, useRef } from 'react'
import type { ShiftType } from '../../api/types'

interface Props {
  shiftTypes: ShiftType[]
  currentShiftTypeId: number | null
  onSelect: (shiftTypeId: number | null) => void
  onClose: () => void
}

export function ShiftPicker({ shiftTypes, currentShiftTypeId, onSelect, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  return (
    <div className="shift-picker" ref={ref}>
      <button
        className={`shift-picker-option ${currentShiftTypeId === null ? 'selected' : ''}`}
        onClick={() => onSelect(null)}
      >
        Libre
      </button>
      {shiftTypes.map(st => (
        <button
          key={st.id}
          className={`shift-picker-option ${currentShiftTypeId === st.id ? 'selected' : ''}`}
          onClick={() => onSelect(st.id)}
        >
          <span className="shift-picker-color" style={{ background: st.color }} />
          {st.name}
        </button>
      ))}
    </div>
  )
}
