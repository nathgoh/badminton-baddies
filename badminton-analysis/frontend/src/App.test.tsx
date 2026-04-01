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

class MockEventSource {
  static instances: MockEventSource[] = [];

  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readonly url: string;
  closed = false;
  private readonly listeners = new Map<string, Array<(event: Event) => void>>();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    const callback =
      typeof listener === "function" ? listener : (event: Event) => listener.handleEvent(event);
    const current = this.listeners.get(type) ?? [];
    current.push(callback);
    this.listeners.set(type, current);
  }

  close() {
    this.closed = true;
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  emitDone() {
    for (const listener of this.listeners.get("done") ?? []) {
      listener(new Event("done"));
    }
  }

  emitError() {
    this.onerror?.(new Event("error"));
  }

  static latest(): MockEventSource {
    const instance = MockEventSource.instances.at(-1);
    if (!instance) {
      throw new Error("No EventSource instance created.");
    }
    return instance;
  }

  static reset() {
    MockEventSource.instances = [];
  }
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
          clip_start_seconds: 9,
          clip_end_seconds: 15,
          rendered_clip_url: "/api/analyses/analysis-123/clips/shot-00-12-smash",
          rendered_clip_media_type: "video/mp4",
        },
      ],
    },
    shuttle: {
      summary: "Gaussian-smoothed shuttle occupancy leaned most heavily toward the front centre.",
      uncertainty_note:
        "Shuttle positions are inferred from shot context and tracked-player movement.",
      samples: [{ timestamp_seconds: 12, x: 0.51, y: 0.24, confidence: 0.62, source: "inferred" }],
      pressure_windows: [
        {
          label: "Forecourt pressure",
          start_timestamp: "00:10",
          end_timestamp: "00:18",
          summary: "Repeated forecourt interceptions kept pressure on the opponent.",
          clip_start_seconds: 8,
          clip_end_seconds: 20,
          rendered_clip_url: "/api/analyses/analysis-123/clips/pressure-1-00-10-00-18-forecourt-pressure",
          rendered_clip_media_type: "video/mp4",
        },
      ],
      heatmap: [
        { zone: "front-left", weight: 0.12 },
        { zone: "front-centre", weight: 0.34 },
        { zone: "mid-centre", weight: 0.21 },
      ],
    },
  },
  llm_provider: "gemini",
  llm_model: "gemini-3.1-flash-lite-preview",
  generation_mode: "ai",
  analysis_evidence: {
    movement_summary: "Tracked distance 54.2m with recovery score 74.",
    mechanics_summary: "Recovery shape degrades after deep forehand movements.",
    shot_selection_summary: "Shot decisions are strongest when the feet arrive early.",
    shuttle: {
      summary: "Birdie pressure stayed front-court heavy.",
      uncertainty_note: "Shuttle path was inferred from sampled events.",
      samples: [{ timestamp_seconds: 12, x: 0.51, y: 0.24, confidence: 0.62, source: "inferred" }],
      pressure_windows: [
        {
          label: "Forecourt pressure",
          start_timestamp: "00:10",
          end_timestamp: "00:18",
          summary: "Repeated forecourt interceptions kept pressure on the opponent.",
          clip_start_seconds: 8,
          clip_end_seconds: 20,
          rendered_clip_url: "/api/analyses/analysis-123/clips/pressure-1-00-10-00-18-forecourt-pressure",
          rendered_clip_media_type: "video/mp4",
        },
      ],
      heatmap: [{ zone: "front-centre", weight: 0.34 }],
    },
  },
  ai_rationale: {
    summary: "The model weighted shuttle pressure and recovery timing most heavily.",
    evidence_highlights: ["Forecourt pressure repeated in three shuttle windows."],
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
  MockEventSource.reset();
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

test("falls back to polling, shows warnings, and returns to setup when the feed errors", async () => {
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
        message: "Analysis started. Connect to the feed for live updates.",
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
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

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

  const source = MockEventSource.latest();
  expect(source.url).toBe("/api/analyses/analysis-123/feed");

  await act(async () => {
    source.emitError();
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

test("streams live frame updates and renders the expanded coach and analytics report sections", async () => {
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
        message: "Analysis started. Connect to the feed for live updates.",
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
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
    await flushMicrotasks();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
    await flushMicrotasks();
  });

  await waitFor(() => {
    expect(MockEventSource.instances).toHaveLength(1);
  });

  await act(async () => {
    MockEventSource.latest().emitMessage({
      analysis_id: "analysis-123",
      pipeline_stage: "tracking",
      frame_index: 1,
      total_frames: 12,
      progress_percent: 62,
      message: "Tracking: frame 1/12",
      frame_jpeg_base64: "ZmFrZS1qcGVn",
    });
    await flushMicrotasks();
  });

  expect(screen.getByText(/62%/i)).toBeInTheDocument();
  expect(screen.getByText(/player tracking/i)).toBeInTheDocument();
  expect(screen.getByText("1/12")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: /analysis frame/i })).toHaveAttribute(
    "src",
    expect.stringContaining("data:image/jpeg;base64,ZmFrZS1qcGVn"),
  );

  await act(async () => {
    MockEventSource.latest().emitDone();
    await flushMicrotasks();
  });

  expect(screen.getByText(/late recoveries still leak attacking quality/i)).toBeInTheDocument();
  expect(screen.getByText(/shot-selection notes/i)).toBeInTheDocument();
  expect(screen.getByText(/footwork notes/i)).toBeInTheDocument();
  expect(screen.getByText(/positioning notes/i)).toBeInTheDocument();
  expect(screen.getByText(/confidence notes/i)).toBeInTheDocument();
  expect(screen.getAllByText(/gemini-3.1-flash-lite-preview/i).length).toBeGreaterThan(0);
  expect(
    screen.getByText(/the model weighted shuttle pressure and recovery timing most heavily/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/forecourt pressure repeated in three shuttle windows/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /analytics view/i }));

  expect(screen.getByText(/mechanics/i)).toBeInTheDocument();
  expect(screen.getByText(/burst count/i)).toBeInTheDocument();
  expect(screen.getByText(/court heatmap/i)).toBeInTheDocument();
  expect(screen.getByText(/shuttle heatmap/i)).toBeInTheDocument();
  expect(screen.getAllByText(/front left/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/shuttle evidence/i)).toBeInTheDocument();
  expect(screen.getByText(/birdie pressure stayed front-court heavy/i)).toBeInTheDocument();
  expect(screen.getByText(/shuttle path was inferred from sampled events/i)).toBeInTheDocument();
});

test("prefers an annotated report clip when the backend provides one", async () => {
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
        message: "Analysis started. Connect to the feed for live updates.",
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
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
    await flushMicrotasks();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
    await flushMicrotasks();
  });

  await act(async () => {
    MockEventSource.latest().emitDone();
    await flushMicrotasks();
  });

  fireEvent.click(screen.getByRole("tab", { name: /analytics view/i }));
  fireEvent.click(screen.getByRole("button", { name: /load clip for 00:12 smash/i }));

  const video = screen.getByTitle(/annotated report clip/i);
  expect(video).toHaveAttribute("src", "/api/analyses/analysis-123/clips/shot-00-12-smash");
  expect(screen.getByText(/annotated clip • 00:12 smash • 9s-15s/i)).toBeInTheDocument();
});

test("falls back to the shared YouTube clip player when no rendered clip exists", async () => {
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
        message: "Analysis started. Connect to the feed for live updates.",
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
    {
      body: {
        ...completedReport,
        analytics_view: {
          ...completedReport.analytics_view,
          shot_selection: {
            ...completedReport.analytics_view.shot_selection,
            events: [
              {
                ...completedReport.analytics_view.shot_selection.events[0],
                rendered_clip_url: null,
                rendered_clip_media_type: null,
              },
            ],
          },
        },
      },
    },
  ]);
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
    await flushMicrotasks();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
    await flushMicrotasks();
  });

  await act(async () => {
    MockEventSource.latest().emitDone();
    await flushMicrotasks();
  });

  fireEvent.click(screen.getByRole("tab", { name: /analytics view/i }));
  fireEvent.click(screen.getByRole("button", { name: /load clip for 00:12 smash/i }));

  const iframe = screen.getByTitle(/report clip player/i);
  expect(iframe).toHaveAttribute("src", expect.stringContaining("/embed/badminton-demo"));
  expect(iframe).toHaveAttribute("src", expect.stringContaining("start=9"));
  expect(iframe).toHaveAttribute("src", expect.stringContaining("end=15"));
  expect(screen.getByText(/youtube fallback • 00:12 smash • 9s-15s/i)).toBeInTheDocument();
});

test("analyze another video button resets to the analyze screen", async () => {
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
        message: "Player selection saved.",
      },
    },
    {
      status: 202,
      body: {
        analysis_id: "analysis-123",
        stage: "analyzing",
        message: "Analysis started. Connect to the feed for live updates.",
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
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /create analysis/i }));

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /player 1/i })).toBeInTheDocument();
  });

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /player 1/i }));
    await flushMicrotasks();
  });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /save setup and run/i }));
    await flushMicrotasks();
  });

  await act(async () => {
    MockEventSource.latest().emitDone();
    await flushMicrotasks();
  });

  expect(screen.getByText(/late recoveries still leak attacking quality/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /analyze another video/i }));

  expect(screen.getByRole("heading", { name: /start an analysis/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /create analysis/i })).toBeInTheDocument();
});
