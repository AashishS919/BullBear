import { cn } from '../../lib/cn'

export function Table({ className, children }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn('w-full border-collapse text-sm', className)}>{children}</table>
    </div>
  )
}

export function THead({ children }) {
  return (
    <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-3">
      {children}
    </thead>
  )
}

export function TH({ className, align = 'left', children }) {
  return (
    <th
      className={cn(
        'px-4 py-2.5 font-medium',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function TBody({ children }) {
  return <tbody className="divide-y divide-line">{children}</tbody>
}

export function TR({ className, children, ...props }) {
  return (
    <tr className={cn('transition hover:bg-surface-2/60', className)} {...props}>
      {children}
    </tr>
  )
}

export function TD({ className, align = 'left', mono, children }) {
  return (
    <td
      className={cn(
        'px-4 py-3 text-ink',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        mono && 'font-mono tabular-nums',
        className,
      )}
    >
      {children}
    </td>
  )
}
