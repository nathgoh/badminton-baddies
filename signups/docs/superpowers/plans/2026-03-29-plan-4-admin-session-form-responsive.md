# Admin Session Form Responsive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the admin session court-entry form stack vertically on narrow screens while preserving the current horizontal layout on wider screens.

**Architecture:** Keep the change local to `AdminSessionList.tsx`. Introduce a viewport-width-driven layout switch for court rows and reuse the existing form state and submission flow unchanged. Verify with a production build after the patch.

**Tech Stack:** React 18, TypeScript, Vite

---

### Task 1: Responsive court-entry layout

**Files:**
- Modify: `signups/frontend/src/pages/AdminSessionList.tsx`

- [ ] **Step 1: Write the failing responsive behavior expectation**

The current court-entry row uses:

```tsx
gridTemplateColumns: 'minmax(180px, 2fr) repeat(4, minmax(110px, 1fr)) auto'
```

This forces a wide single-row layout even on narrow screens. The required behavior is:

- use the existing multi-column layout on wide screens
- switch to a stacked single-column layout on narrow screens
- keep field order unchanged

- [ ] **Step 2: Add viewport-width state and effect**

Add state and an effect near the top of the component:

```tsx
  const [isNarrow, setIsNarrow] = useState(() => window.innerWidth < 900)

  useEffect(() => {
    function handleResize() {
      setIsNarrow(window.innerWidth < 900)
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
```

- [ ] **Step 3: Switch the court row grid based on `isNarrow`**

Replace the inline grid definition for each court row with:

```tsx
              style={{
                display: 'grid',
                gridTemplateColumns: isNarrow
                  ? '1fr'
                  : 'minmax(180px, 2fr) repeat(4, minmax(110px, 1fr)) auto',
                gap: 8,
                marginBottom: 8,
                alignItems: 'stretch',
              }}
```

- [ ] **Step 4: Make the remove button fit both layouts**

Update the remove button styles to:

```tsx
                style={{
                  padding: '6px 8px',
                  background: 'white',
                  border: '1px solid #ffcdd2',
                  borderRadius: 4,
                  color: '#c62828',
                  cursor: 'pointer',
                  alignSelf: isNarrow ? 'start' : 'stretch',
                  justifySelf: isNarrow ? 'start' : 'stretch',
                }}
```

- [ ] **Step 5: Run build to verify the patch**

Run:

```bash
cd signups/frontend
npm run build
```

Expected:

- TypeScript passes
- Vite build succeeds
- output is written to `signups/backend/dist/`

