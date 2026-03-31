import type { ComponentPropsWithoutRef, ElementType } from 'react'

type CardTone = 'default' | 'accent' | 'muted'

type Props<T extends ElementType> = {
  as?: T
  tone?: CardTone
  className?: string
} & Omit<ComponentPropsWithoutRef<T>, 'as' | 'className'>

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ')
}

const toneClasses: Record<CardTone, string> = {
  default: 'border-slate-200 bg-white',
  accent: 'border-slate-200 bg-white',
  muted: 'border-slate-200 bg-slate-50',
}

export default function Card<T extends ElementType = 'div'>({
  as,
  className,
  tone = 'default',
  ...props
}: Props<T>) {
  const Component = as ?? 'div'

  return (
    <Component
      className={cx(
        'rounded-3xl border p-5 sm:p-6',
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  )
}
