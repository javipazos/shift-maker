const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

interface Props {
  year: number
  month: number
  onChange: (year: number, month: number) => void
}

export function MonthSelector({ year, month, onChange }: Props) {
  function goBack() {
    if (month === 1) onChange(year - 1, 12)
    else onChange(year, month - 1)
  }

  function goForward() {
    if (month === 12) onChange(year + 1, 1)
    else onChange(year, month + 1)
  }

  return (
    <div className="month-selector">
      <button onClick={goBack}>←</button>
      <span className="current-month">
        {MONTH_NAMES[month - 1]} {year}
      </span>
      <button onClick={goForward}>→</button>
    </div>
  )
}
