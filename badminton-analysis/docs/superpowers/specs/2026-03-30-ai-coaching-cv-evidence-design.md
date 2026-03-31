# AI Coaching And CV Evidence Design

## Summary

Replace the deterministic placeholder coaching layer with a provider-agnostic LLM coaching engine
that consumes structured badminton evidence assembled from the CV pipeline and existing heuristics.
Default the runtime to Google's Flash-tier Gemini model for latency and cost, but keep the backend
configuration generic so the same contract can target Gemini Pro or other LLM providers later.

The report contract should expand now, not later. The backend will expose shuttle and AI evidence
explicitly, and the frontend will render those details alongside the existing coach and analytics
views.

## Goals

- Replace canned coach feedback with structured LLM-generated badminton coaching.
- Make the LLM provider and model configurable without changing service code.
- Expand the report schema to expose provider/model provenance and AI rationale.
- Add shuttle or birdie evidence derived from CV outputs and lightweight inference.
- Preserve graceful fallback to deterministic coaching when the AI path fails.
- Surface the new AI and shuttle evidence in the existing frontend report flow.

## Non-Goals

- Full frame-accurate shuttle tracking across an entire match.
- Multimodal video uploads directly into an LLM.
- User-facing controls for selecting provider or model in the frontend.
- Persisting reports or analyses beyond the current in-memory store.

## Current Constraints

- The existing CV path provides setup detection, player tracking, and pose summaries, but not
  reliable shuttle detection on every frame.
- The current service already has a coaching abstraction (`CoachFeedbackEngine`) and fallback path.
- The frontend already expects a two-tab report and mirrors backend response types directly.

## Architecture

### 1. Evidence Builder

Add a backend evidence-building layer that assembles the report payload the LLM will use. This
layer should accept the current `AnalysisRecord`, `AnalyticsView`, tracking summary, and pose
summary and produce a structured evidence object with:

- movement evidence from tracked player samples
- positioning evidence from zone occupancy and heatmaps
- mechanics evidence from pose summaries
- shot-selection evidence from scored shot events
- shuttle evidence from inferred or sampled birdie positions, smoothed into meaningful summaries
- confidence and uncertainty notes explaining what was observed vs. inferred

The service remains the orchestrator, but it should stop embedding prompt construction or evidence
formatting inline.

### 2. Provider-Agnostic LLM Coaching Engine

Replace the current narrow `PydanticAICoachFeedbackEngine` shape with a provider-agnostic adapter
that still satisfies the existing coaching interface. The backend should accept a generic config:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- provider-specific API keys such as `GEMINI_API_KEY`, `OPENAI_API_KEY`, and
  `ANTHROPIC_API_KEY`

The default config should be:

- provider: `gemini`
- model: `gemini-3-flash-preview`

The provider adapter should validate structured output into typed Pydantic models before returning
it to the service. Invalid output or provider errors must trigger the existing deterministic
fallback path.

### 3. Shuttle And Birdie Evidence

The first shuttle implementation should be honest about what it is: inferred evidence, not a claim
of full frame-accurate tracking. The backend should add a shuttle-analysis slice that can work from
today's available data and can be replaced by richer CV later.

First-pass shuttle evidence should include:

- sampled shuttle points or inferred contact windows
- Gaussian-smoothed court occupancy or density summaries
- trajectory trend summaries such as front-court pressure, rear-court resets, and cross-court
  pressure
- attack or defense pressure windows derived from shuttle movement context
- uncertainty notes when the shuttle evidence is inferred instead of directly observed

This should be represented as structured analytics, not only prose.

### 4. Frontend Integration

Keep the existing `coach` and `analytics` tab structure, but expand both tabs to show the new
evidence:

- provider and model provenance
- AI rationale and evidence summaries
- shuttle or birdie analytics and uncertainty
- confidence annotations tied to the expanded backend fields

The UI should remain readable on mobile and desktop. The current report should not turn into a raw
JSON dump; the evidence must be rendered as compact cards, summaries, and visual court cues.

## Data Model Changes

### Report Provenance

`AnalysisReport` should grow fields that explain how the report was generated:

- `llm_provider: str | None`
- `llm_model: str | None`
- `generation_mode: Literal["ai", "fallback"]`
- `analysis_evidence: AnalysisEvidence`
- `ai_rationale: AIRationale | None`

### Expanded Analytics

`AnalyticsView` should grow a `shuttle` section. The first-pass shuttle model should support:

- inferred samples or windows
- court-zone occupancy summaries
- pressure annotations
- uncertainty notes

### Evidence Models

Add typed evidence models rather than shoving everything into freeform strings. Likely models:

- `AnalysisEvidence`
- `ShuttleMetrics`
- `ShuttleSample` or `ShuttleWindow`
- `PressureWindow`
- `AIRationale`

Exact names can shift during implementation, but the shape should stay:

- machine-readable evidence for the LLM
- machine-readable evidence for the frontend
- human-readable summaries alongside the structured fields

## Prompt And Output Strategy

The LLM should receive:

- match type
- tracked player identity
- expanded analytics
- structured evidence bundle
- confidence annotations
- explicit instructions to stay evidence-backed and avoid unsupported claims

The model should return a typed coaching object plus rationale fields, not freeform markdown. The
service should validate this output before assembling the final report.

## Failure Handling

If the provider is unavailable, misconfigured, times out, or returns invalid schema:

- append a warning to the analysis status or report
- fall back to deterministic coaching
- still return a complete report
- record `generation_mode="fallback"`
- preserve the expanded analytics and evidence even when coaching text falls back

## Backend Implementation Direction

- Keep `AnalysisService` as the orchestrator.
- Move provider selection and SDK calls behind a provider registry or adapter factory.
- Move prompt construction out of the service and into the LLM layer.
- Move evidence construction out of the coaching engine and into a dedicated builder.
- Keep deterministic fallback logic in the service so resilience remains centralized.

## Frontend Implementation Direction

- Expand `types.ts` to mirror the new report schema.
- Render report provenance and AI rationale in the coach tab.
- Render shuttle evidence, pressure windows, and confidence cues in the analytics tab.
- Preserve current navigation and polling behavior.
- Add tests that prove the new sections appear and degrade gracefully when the backend reports
  fallback mode.

## Testing Strategy

### Backend

- Add unit or API tests for provider config parsing and default Gemini Flash selection.
- Add tests proving provider adapters receive the expanded evidence payload.
- Add tests for report schema expansion and serialization.
- Add tests for fallback mode when the provider raises or returns invalid structured output.
- Add tests for shuttle evidence generation from available CV context.

### Frontend

- Add tests for provider and model provenance rendering.
- Add tests for AI rationale and evidence sections.
- Add tests for shuttle analytics rendering and uncertainty notes.
- Add tests for fallback rendering when `generation_mode` is `fallback`.

## Recommended Delivery Slice

1. Expand the backend models for evidence, shuttle analytics, and provenance.
2. Add an evidence builder and wire it into `AnalysisService`.
3. Add a provider-agnostic LLM engine with Gemini Flash as the default config.
4. Keep deterministic fallback intact.
5. Update frontend types and report rendering for the new schema.
6. Add backend and frontend tests for the new paths.

## Acceptance Criteria

- A completed analysis can return AI-authored coaching using a configurable provider and model.
- The default backend path uses Gemini Flash-tier configuration.
- Swapping to a different provider or model does not require touching service code.
- Reports expose shuttle evidence, confidence notes, and AI provenance explicitly.
- The frontend visibly renders the new evidence and provenance.
- Provider failure still returns a valid fallback report with warnings.
