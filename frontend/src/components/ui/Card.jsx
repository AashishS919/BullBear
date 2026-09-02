import { cn } from '../../lib/cn'

export function Card({ className, children, ...props }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-line bg-surface shadow-card',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action, className }) {
  return (
    <div className={cn('flex items-start justify-between gap-3 border-b border-line px-5 py-4', className)}>
      <div>
        <h3 className="text-lg font-semibold leading-tight text-ink">{title}</h3>
        {subtitle && <p className="mt-0.5 text-sm text-ink-3">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function CardBody({ className, children }) {
  return <div className={cn('px-5 py-4', className)}>{children}</div>
}
