import { describe, expect, it } from 'vitest'

import cancelSectionSource from './components/CancelSection.tsx?raw'

describe('CancelSection', () => {
  it('contains the cancel card and toggle hooks in source', () => {
    expect(cancelSectionSource).toContain('data-testid="cancel-card"')
    expect(cancelSectionSource).toContain('data-testid="cancel-toggle"')
  })
})
