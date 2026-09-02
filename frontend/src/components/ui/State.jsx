import { Loader2, AlertTriangle, Inbox } from 'lucide-react'

export function Loader({ label = 'Loading...', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-2 py-12 text-ink-3 ${className}`}>
      <Loader2 className="animate-spin" size={18} />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function FullScreenLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-paper">
      <Loader label="Loading BullBear..." />
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <AlertTriangle className="text-bear" size={24} />
      <p className="text-sm text-ink-2">{error?.message || 'Something went wrong.'}</p>
      {onRetry && (
        <button onClick={onRetry} className="text-sm font-medium text-accent hover:underline">
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message = 'Nothing to show yet.' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-ink-3">
      <Inbox size={22} />
      <p className="text-sm">{message}</p>
    </div>
  )
}
