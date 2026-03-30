import { describe, expect, it } from 'vitest'
import MainSource from './main.tsx?raw'

// Temporary migration coverage: verify the frontend entry points at Tailwind CSS.
describe('frontend styling entry wiring', () => {
  it('imports the Tailwind entry stylesheet', () => {
    expect(MainSource).toMatch(/["']\.\/tailwind\.css["']/)
    expect(MainSource).not.toMatch(/["']\.\/styles\.css["']/)
  })
})
