import { cn } from '../../lib/cn'

/**
 * Connection-status pill for the realtime market stream.
 * status: 'live' | 'connecting' | 'offline'
 */
const LABEL = { live: 'Live', connecting: 'Connecting', offline: 'Reconnecting' }

export function LiveStatus({ status = 'offline', className }) {
  const live = status === 'live'
  const connecting = status === 'connecting'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        live ? 'bg-bull-soft text-bull' : 'bg-surface-2 text-ink-3',
        className,
      )}
    >
      <span
        className={cn(
          'inline-block h-2 w-2 rounded-full',
          live ? 'bg-bull' : connecting ? 'bg-accent' : 'bg-ink-3',
          (live || connecting) && 'animate-pulse',
        )}
      />
      {LABEL[status] || LABEL.offline}
    </span>
  )
}
