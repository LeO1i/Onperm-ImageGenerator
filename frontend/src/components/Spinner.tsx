interface SpinnerProps {
  label?: string
  small?: boolean
}

export function Spinner({ label, small }: SpinnerProps) {
  return (
    <div className={`spinner-wrap ${small ? 'spinner-wrap-sm' : ''}`}>
      <div className="spinner" aria-hidden />
      {label && <span>{label}</span>}
    </div>
  )
}
