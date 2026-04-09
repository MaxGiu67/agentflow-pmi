import { describe, it, expect } from 'vitest'

describe('deal-detail components exist', () => {
  it('DealHeader exports default', async () => {
    const mod = await import('../DealHeader')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealClientCard exports default', async () => {
    const mod = await import('../DealClientCard')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealDetailsCard exports default', async () => {
    const mod = await import('../DealDetailsCard')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealOrderCard exports default', async () => {
    const mod = await import('../DealOrderCard')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealActivities exports default', async () => {
    const mod = await import('../DealActivities')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealDocuments exports default', async () => {
    const mod = await import('../DealDocuments')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealResources exports default', async () => {
    const mod = await import('../DealResources')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealPortalWorkflow exports default', async () => {
    const mod = await import('../DealPortalWorkflow')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })

  it('DealProgress exports default', async () => {
    const mod = await import('../DealProgress')
    expect(mod.default).toBeDefined()
    expect(typeof mod.default).toBe('function')
  })
})
