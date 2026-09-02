import { cn } from '../../lib/cn'

export function Field({ label, htmlFor, hint, error, required, children }) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={htmlFor} className="block text-sm font-medium text-ink-2">
          {label}
          {required && <span className="ml-0.5 text-bear">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-bear">{error}</p>
      ) : (
        hint && <p className="text-xs text-ink-3">{hint}</p>
      )}
    </div>
  )
}

export function Input({ className, mono, invalid, ...props }) {
  return (
    <input
      className={cn(
        'h-10 w-full rounded-md border bg-surface px-3 text-sm text-ink',
        'placeholder:text-ink-3 focus:outline-none focus-visible:ring-2',
        invalid
          ? 'border-bear focus-visible:ring-bear/30'
          : 'border-line-2 focus-visible:ring-accent/30',
        mono && 'font-mono tabular-nums',
        className,
      )}
      {...props}
    />
  )
}

export function Range({ className, ...props }) {
  return (
    <input
      type="range"
      className={cn(
        'h-1.5 w-full cursor-pointer appearance-none rounded-full bg-line-2 accent-accent',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/30',
        className,
      )}
      {...props}
    />
  )
}

export function Select({ className, invalid, children, ...props }) {
  return (
    <select
      className={cn(
        'h-10 w-full rounded-md border bg-surface px-3 text-sm text-ink',
        'focus:outline-none focus-visible:ring-2',
        invalid ? 'border-bear focus-visible:ring-bear/30' : 'border-line-2 focus-visible:ring-accent/30',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  )
}
