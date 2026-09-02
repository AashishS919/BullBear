import { cn } from '../../lib/cn'

const VARIANTS = {
  primary: 'bg-accent text-white hover:opacity-90 active:opacity-80',
  bull: 'bg-bull text-white hover:opacity-90 active:opacity-80',
  bear: 'bg-bear text-white hover:opacity-90 active:opacity-80',
  outline: 'border border-line-2 bg-surface text-ink hover:bg-surface-2',
  ghost: 'text-ink-2 hover:bg-surface-2',
}

const SIZES = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-11 px-5 text-base',
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  type = 'button',
  children,
  ...props
}) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium transition',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40',
        'disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
