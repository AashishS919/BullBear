import { cn } from '../../lib/cn'

const TONES = {
  neutral: 'bg-surface-2 text-ink-2 border-line',
  bull: 'bg-bull-soft text-bull border-transparent',
  bear: 'bg-bear-soft text-bear border-transparent',
  accent: 'bg-accent-soft text-accent border-transparent',
}

// Map common status strings to a tone automatically.
const STATUS_TONE = {
  ACTIVE: 'bull', READY: 'bull', EXECUTED: 'bull',
  SUSPENDED: 'bear', CANCELLED: 'bear', STALE: 'bear',
  PENDING: 'accent', PROCESSING: 'accent',
}

export function Badge({ tone, status, className, children }) {
  const resolved = tone ?? (status ? STATUS_TONE[status] ?? 'neutral' : 'neutral')
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        TONES[resolved],
        className,
      )}
    >
      {children ?? status}
    </span>
  )
}
