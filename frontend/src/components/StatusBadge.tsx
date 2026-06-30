interface StatusBadgeProps {
  status: string
  className?: string
}

const STATUS_CLASS: Record<string, string> = {
  pass: 'badge-pass',
  warn: 'badge-warn',
  fail: 'badge-fail',
  completed: 'badge-pass',
  running: 'badge-info',
  queued: 'badge-muted',
  failed: 'badge-fail',
  cancelled: 'badge-muted',
  interrupted: 'badge-warn',
  ready: 'badge-pass',
  download: 'badge-info',
  unknown: 'badge-warn',
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const badgeClass = STATUS_CLASS[status] ?? 'badge-muted'
  return (
    <span className={`badge ${badgeClass} ${className}`.trim()}>
      {status}
    </span>
  )
}
