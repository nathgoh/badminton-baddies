import type { ButtonHTMLAttributes } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  fullWidth?: boolean
}

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ')
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'border-slate-900 bg-slate-900 text-white hover:bg-slate-800 focus-visible:ring-slate-400',
  secondary:
    'border-slate-300 bg-white text-slate-900 hover:bg-slate-50 focus-visible:ring-slate-300',
  ghost:
    'border-transparent bg-transparent text-slate-700 hover:bg-slate-100 focus-visible:ring-slate-300',
  danger:
    'border-red-600 bg-red-600 text-white hover:bg-red-500 focus-visible:ring-red-300',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3.5 py-2 text-sm',
  md: 'px-4 py-2.5 text-sm',
}

export default function Button({
  className,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  type = 'button',
  ...props
}: Props) {
  return (
    <button
      type={type}
      className={cx(
        'inline-flex items-center justify-center rounded-xl border font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60',
        sizeClasses[size],
        variantClasses[variant],
        fullWidth && 'w-full',
        className,
      )}
      {...props}
    />
  )
}
