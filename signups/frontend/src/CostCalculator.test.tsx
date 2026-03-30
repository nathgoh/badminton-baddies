import { describe, expect, it } from 'vitest'

import CostCalculatorSource from './components/CostCalculator.tsx?raw'

describe('CostCalculator structure hooks', () => {
  it('includes court and signup link class hooks in the source', () => {
    expect(CostCalculatorSource).toContain('admin-court-list')
    expect(CostCalculatorSource).toContain('admin-court-item')
    expect(CostCalculatorSource).toContain('admin-signup-link-card')
  })

  it('does not include session controls card (moved to AdminSessionDetail)', () => {
    expect(CostCalculatorSource).not.toContain('admin-session-controls-card')
    expect(CostCalculatorSource).not.toContain('handleToggleActive')
    expect(CostCalculatorSource).not.toContain('handleCalculate')
  })
})
