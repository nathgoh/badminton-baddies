import { describe, expect, it } from 'vitest'
import ViteConfigSource from '../vite.config.ts?raw'

// Temporary migration coverage: verify Vite is wired for Tailwind before component work.
describe('vite Tailwind integration wiring', () => {
  it('registers the Tailwind Vite plugin', () => {
    expect(ViteConfigSource).toMatch(/@tailwindcss\/vite/)
    expect(ViteConfigSource).toMatch(/tailwindcss\s*\(\s*\)/)
  })
})
