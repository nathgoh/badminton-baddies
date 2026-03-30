import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";


function queueFetchResponses(
  responses: Array<{
    body: unknown;
    status?: number;
  }>,
) {
  const fetchMock = vi.fn();

  for (const response of responses) {
    const status = response.status ?? 200;
    fetchMock.mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      json: async () => response.body,
    } as Response);
  }

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}


const setupResponse = {
  analysis_id: "analysis-123",
  setup_frame_url: "data:image/svg+xml;base64,PHN2Zy8+",
  players: [
    {
      player_id: "player-1",
      label: "Player 1",
      side: "near",
      focus_hint: "Recommended tracking candidate",
    },
    {
      player_id: "player-2",
      label: "Player 2",
      side: "far",
      focus_hint: "Detected court player",
    },
  ],
  court: {
    confidence: 0.78,
    adjustment_hint: "Drag the corners if the tramlines look off.",
    points: [
      { x: 0.14, y: 0.12 },
      { x: 0.86, y: 0.12 },
      { x: 0.92, y: 0.9 },
      { x: 0.08, y: 0.9 },
    ],
  },
};

const completedReport = {
  analysis_id: "analysis-123",
  match_type: "mixed_doubles",
  tracked_player_label: "Player 1",
  coach_view: {
    summary: "Player 1 sustains pressure well, but late recoveries still leak attacking quality.",
    strengths: ["Finds playable positions after most attacking shots."],
    priority_issues: ["Recovery rotation lands too central under pressure."],
    shot_selection_notes: "Attack the next shuttle only after regaining balance.",
    footwork_notes: "The first recovery step is late after deep forehand exits.",
    positioning_notes: "Partner spacing holds shape until the rear-court reset drifts central.",
    confidence_notes: "This MVP report is evidence-backed but still generated from mocked CV data.",
    recommended_drills: ["Four-corner recovery with split-step resets."],
  },
  analytics_view: {
    mechanics: {
      stance_note: "Split-step timing is consistent enough to stay neutral before contact.",
      preparation_note: "Preparation is early on forehand interceptions.",
      balance_note: "Balance drops after stretched forehand recoveries.",
      recovery_note: "Recovery shape degrades after deep forehand movements.",
      stroke_execution_note: "Attacking strokes hold quality until balance drops late in the rally.",
    },
    movement: {
      total_distance_meters: 54.2,
      recovery_score: 74,
      court_coverage_percent: 81,
      change_of_direction_count: 28,
      burst_count: 8,
      directional_balance: { left: 0.51, right: 0.49 },
    },
    positioning: {
      base_position_note: "Recovery rotation is a beat late after forehand pressure.",
      zone_occupancy: { front: 29, mid: 36, rear: 35 },
      heatmap: [
        { zone: "front-left", weight: 0.12 },
        { zone: "mid-centre", weight: 0.22 },
        { zone: "rear-right", weight: 0.06 },
      ],
      spacing_note: "Partner spacing holds shape well, but the rear-court recovery drifts central.",
    },
    shot_selection: {
      overview: "Shot decisions are strongest when the feet arrive early.",
      events: [
        {
          timestamp: "00:12",
          shot_type: "smash",
          execution_score: 82,
          decision_score: 61,
          decision_quality: "neutral",
          recommendation: "A steep drop would likely have been higher percentage here.",
          evidence: "Balance and opponent depth favored a softer attacking option.",
        },
      ],
    },
  },
  confidence_annotations: [
    {
      field: "analytics.movement.recovery_score",
      confidence: 0.74,
      reason: "Mocked movement analysis uses a limited rally sample.",
    },
  ],
  generated_at: "2026-03-30T20:00:00Z",
};

async function flushMicrotasks() {
  await Promise.resolve();
  await Promise.resolve();
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test("renders the analysis workspace heading", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: /badminton analysis/i })).toBeInTheDocument();
  expect(screen.getByText(/youtube link/i)).toBeInTheDocument();
});

test("renders the setup frame and waits for explicit player selection before running", async () => {
  queueFetchResponses([
    {
      status: 201,
      body: {
        analysis_id: "analysis-123",
        youtube_url: "https://www.youtube.com/watch?v=badminton-demo",
        match_type: "mixed_doubles",
        selection_required: true,
        stage: "setup_required",
        created_at: "2026-03-30T20:00:00Z",
      },
    },
    { body: setupResponse },
  ]);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("img", { name: /setup frame/i })).toBeInTheDocument();
  });

  expect(screen.getByText(/drag the corners/i)).toBeInTheDocument();
  expect(screen.getAllByLabelText(/court corner/i)).toHaveLength(4);
  expect(screen.getByRole("button", { name: /save setup and run/i })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: /player 1/i }));

  expect(screen.getByRole("button", { name: /save setup and run/i })).toBeEnabled();
});

test("polls status, shows warnings, and returns to setup when the analysis fails", async () => {
  queueFetchResponses([
    {
      status: 201,
      body: {
        analysis_id: "analysis-123",
        youtube_url: "https://www.youtube.com/watch?v=badminton-demo",
        match_type: "mixed_doubles",
        selection_required: true,
        stage: "setup_required",
        created_at: "2026-03-30T20:00:00Z",
      },
    },
    { body: setupResponse },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "ready_to_run",
        message: "Player selection saved. Analysis is ready to run.",
      },
    },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "analyzing",
        message: "Analysis started. Poll status for progress updates.",
      },
    },
    {
      body: {
        analysis_id: "analysis-123",
        stage: "analyzing",
        progress_percent: 62,
        message: "Tracking the selected player and scoring movement patterns.",
        warnings: ["Coach feedback fallback applied after coach engine unavailable."],
        error_details: null,
      },
    },
    {
      body: {
        analysis_id: "analysis-123",
        stage: "failed",
        progress_percent: 100,
        message: "Analysis failed. Review the error details and return to setup.",
        warnings: ["Coach feedback fallback applied after coach engine unavailable."],
        error_details: "pipeline exploded for mixed_doubles",
      },
    },
  ]);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });

  vi.useFakeTimers();
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
    await flushMicrotasks();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
    await flushMicrotasks();
  });

  expect(screen.getByText(/62%/i)).toBeInTheDocument();
  expect(screen.getByText(/coach feedback fallback applied/i)).toBeInTheDocument();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
    await flushMicrotasks();
  });

  expect(screen.getByText(/pipeline exploded for mixed_doubles/i)).toBeInTheDocument();
  expect(screen.getByText(/confirm the tracked player/i)).toBeInTheDocument();
});

test("renders the expanded coach and analytics report sections from the revised schema", async () => {
  queueFetchResponses([
    {
      status: 201,
      body: {
        analysis_id: "analysis-123",
        youtube_url: "https://www.youtube.com/watch?v=badminton-demo",
        match_type: "mixed_doubles",
        selection_required: true,
        stage: "setup_required",
        created_at: "2026-03-30T20:00:00Z",
      },
    },
    { body: setupResponse },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "ready_to_run",
        message: "Player selection saved. Analysis is ready to run.",
      },
    },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "analyzing",
        message: "Analysis started. Poll status for progress updates.",
      },
    },
    {
      body: {
        analysis_id: "analysis-123",
        stage: "analyzing",
        progress_percent: 62,
        message: "Tracking the selected player and scoring movement patterns.",
        warnings: [],
        error_details: null,
      },
    },
    {
      body: {
        analysis_id: "analysis-123",
        stage: "completed",
        progress_percent: 100,
        message: "Report generated successfully.",
        warnings: [],
        error_details: null,
      },
    },
    { body: completedReport },
  ]);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });

  vi.useFakeTimers();
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
    await flushMicrotasks();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
    await flushMicrotasks();
  });

  expect(screen.getByText(/62%/i)).toBeInTheDocument();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
    await flushMicrotasks();
  });

  expect(screen.getByText(/late recoveries still leak attacking quality/i)).toBeInTheDocument();
  expect(screen.getByText(/shot-selection notes/i)).toBeInTheDocument();
  expect(screen.getByText(/footwork notes/i)).toBeInTheDocument();
  expect(screen.getByText(/positioning notes/i)).toBeInTheDocument();
  expect(screen.getByText(/confidence notes/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /analytics view/i }));

  expect(screen.getByText(/mechanics/i)).toBeInTheDocument();
  expect(screen.getByText(/burst count/i)).toBeInTheDocument();
  expect(screen.getByText(/heatmap/i)).toBeInTheDocument();
  expect(screen.getByText(/front-left/i)).toBeInTheDocument();
  expect(screen.getByText(/evidence/i)).toBeInTheDocument();
});
