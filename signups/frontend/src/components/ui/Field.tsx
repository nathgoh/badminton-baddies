import type { HTMLAttributes, ReactNode } from 'react'

interface Props extends HTMLAttributes<HTMLDivElement> {
  label: ReactNode
  htmlFor?: string
  hint?: ReactNode
  error?: ReactNode
}

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ')
}

export default function Field({ label, htmlFor, hint, error, className, children, ...props }: Props) {
  return (
    <div className={cx('space-y-2', className)} {...props}>
      <div className="flex items-center justify-between gap-3">
        <label htmlFor={htmlFor} className="text-sm font-semibold text-ink-950">
          {label}
        </label>
        {hint ? <span className="text-xs text-ink-700">{hint}</span> : null}
      </div>
      {children}
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
    </div>
  )
}
