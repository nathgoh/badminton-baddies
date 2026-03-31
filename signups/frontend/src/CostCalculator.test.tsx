import { describe, expect, it } from 'vitest'

import CostCalculatorSource from './components/CostCalculator.tsx?raw'

describe('CostCalculator structure hooks', () => {
  it('includes explicit test ids for court and signup link sections', () => {
    expect(CostCalculatorSource).toMatch(/data-testid\s*=\s*["']court-list["']/)
    expect(CostCalculatorSource).toMatch(/data-testid\s*=\s*["']court-item["']/)
    expect(CostCalculatorSource).toMatch(/data-testid\s*=\s*["']signup-link-card["']/)
  })

  it('does not include session controls card (moved to AdminSessionDetail)', () => {
    expect(CostCalculatorSource).not.toContain('handleToggleActive')
    expect(CostCalculatorSource).not.toContain('handleCalculate')
  })
})
