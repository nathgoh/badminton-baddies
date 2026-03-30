import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import CancelSection from './components/CancelSection'

describe('CancelSection', () => {
  it('shows a compact trigger when collapsed', () => {
    const markup = renderToStaticMarkup(
      <CancelSection
        token="abc"
        expanded={false}
        onToggle={() => {}}
        onCancelled={() => {}}
      />,
    )

    expect(markup).toContain('Already signed up?')
    expect(markup).toContain('Manage your signup')
    expect(markup).toContain('Open')
    expect(markup).not.toContain('Find signup')
  })

  it('shows the cancel panel when expanded', () => {
    const markup = renderToStaticMarkup(
      <CancelSection
        token="abc"
        expanded
        onToggle={() => {}}
        onCancelled={() => {}}
      />,
    )

    expect(markup).toContain('Email')
    expect(markup).toContain('Find signup')
    expect(markup).not.toContain('Cancellation closes 48 hours before the session')
  })
})
