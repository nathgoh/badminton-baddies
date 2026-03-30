import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { useMobile } from './useMobile'

function Probe() {
  const isMobile = useMobile()
  return <span>{isMobile ? 'mobile' : 'desktop'}</span>
}

describe('useMobile', () => {
  it('returns false in SSR / node environment', () => {
    // window is undefined in vitest node env, so hook returns false
    const markup = renderToStaticMarkup(<Probe />)
    expect(markup).toContain('desktop')
  })
})
