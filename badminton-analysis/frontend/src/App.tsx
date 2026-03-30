import {
  CSSProperties,
  FormEvent,
  PointerEvent,
  startTransition,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  createAnalysis,
  fetchReport,
  fetchSetup,
  fetchStatus,
  runAnalysis,
  saveSelection,
} from "./api";
import type {
  AnalysisCreateResponse,
  AnalysisReport,
  AnalysisSetupResponse,
  AnalysisStatusResponse,
  CourtPoint,
  MatchType,
  PlayerCandidate,
} from "./types";

const matchTypes: Array<{ value: MatchType; label: string }> = [
  { value: "mixed_doubles", label: "Mixed doubles" },
  { value: "womens_doubles", label: "Women's doubles" },
  { value: "mens_doubles", label: "Men's doubles" },
  { value: "mens_singles", label: "Men's singles" },
  { value: "womens_singles", label: "Women's singles" },
];

type Screen = "analyze" | "setup" | "processing" | "report";
type ReportTab = "coach" | "analytics";

function clamp(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function formatMatchType(matchType: MatchType): string {
  return matchType.replaceAll("_", " ");
}

function App() {
  const [screen, setScreen] = useState<Screen>("analyze");
  const [reportTab, setReportTab] = useState<ReportTab>("coach");
  const [youtubeUrl, setYoutubeUrl] = useState("https://www.youtube.com/watch?v=badminton-demo");
  const [matchType, setMatchType] = useState<MatchType>("mixed_doubles");
  const [analysis, setAnalysis] = useState<AnalysisCreateResponse | null>(null);
  const [setup, setSetup] = useState<AnalysisSetupResponse | null>(null);
  const [courtPoints, setCourtPoints] = useState<CourtPoint[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerCandidate | null>(null);
  const [status, setStatus] = useState<AnalysisStatusResponse | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [draggingCorner, setDraggingCorner] = useState<number | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const analysisId = analysis?.analysis_id;
    if (screen !== "processing" || analysisId === undefined) {
      return;
    }
    const stableAnalysisId: string = analysisId;

    let cancelled = false;
    let timeoutId: number | undefined;

    async function pollStatus() {
      try {
        const nextStatus = await fetchStatus(stableAnalysisId);
        if (cancelled) {
          return;
        }

        startTransition(() => setStatus(nextStatus));

        if (nextStatus.stage === "completed") {
          const nextReport = await fetchReport(stableAnalysisId);
          if (cancelled) {
            return;
          }

          startTransition(() => {
            setReport(nextReport);
            setScreen("report");
          });
          return;
        }

        if (nextStatus.stage === "failed") {
          startTransition(() => {
            setError(nextStatus.error_details ?? "Analysis failed. Review the setup and try again.");
            setScreen("setup");
          });
          return;
        }

        timeoutId = window.setTimeout(() => {
          void pollStatus();
        }, 2000);
      } catch (pollError) {
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setError(
            pollError instanceof Error
              ? pollError.message
              : "Unable to poll the analysis status. Review the setup and try again.",
          );
          setScreen("setup");
        });
      }
    }

    void pollStatus();

    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [analysis, screen]);

  async function handleCreateAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const created = await createAnalysis({
        youtube_url: youtubeUrl,
        match_type: matchType,
      });
      const nextSetup = await fetchSetup(created.analysis_id);

      startTransition(() => {
        setAnalysis(created);
        setSetup(nextSetup);
        setCourtPoints(nextSetup.court.points);
        setSelectedPlayer(null);
        setStatus(null);
        setReport(null);
        setReportTab("coach");
        setScreen("setup");
      });
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : "Unable to create analysis. Check the backend connection and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRunAnalysis() {
    if (!analysis || !setup || !selectedPlayer) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await saveSelection(analysis.analysis_id, {
        player_id: selectedPlayer.player_id,
        court_points: courtPoints,
      });
      const nextRunState = await runAnalysis(analysis.analysis_id);

      startTransition(() => {
        setStatus({
          analysis_id: analysis.analysis_id,
          stage: nextRunState.stage,
          progress_percent: 0,
          message: nextRunState.message,
          warnings: [],
          error_details: null,
        });
        setScreen("processing");
      });
    } catch (runError) {
      startTransition(() => {
        setError(
          runError instanceof Error
            ? runError.message
            : "Unable to complete the analysis run. Try again after reviewing the setup.",
        );
        setScreen("setup");
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateCourtPoint(index: number, clientX: number, clientY: number) {
    const bounds = frameRef.current?.getBoundingClientRect();
    if (!bounds || bounds.width === 0 || bounds.height === 0) {
      return;
    }

    const nextPoint = {
      x: clamp((clientX - bounds.left) / bounds.width),
      y: clamp((clientY - bounds.top) / bounds.height),
    };

    setCourtPoints((currentPoints) =>
      currentPoints.map((point, currentIndex) => (currentIndex === index ? nextPoint : point)),
    );
  }

  function handleCourtCornerPointerDown(index: number) {
    return (event: PointerEvent<HTMLButtonElement>) => {
      event.preventDefault();
      setDraggingCorner(index);
      updateCourtPoint(index, event.clientX, event.clientY);
    };
  }

  function handleFramePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (draggingCorner === null) {
      return;
    }

    updateCourtPoint(draggingCorner, event.clientX, event.clientY);
  }

  function stopDragging() {
    setDraggingCorner(null);
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="hero">
        <p className="eyebrow">Badminton video intelligence</p>
        <h1>Badminton Analysis</h1>
        <p className="hero-copy">
          Coach-first review for YouTube match footage with player selection, tactical shot
          grading, and report-ready movement insight.
        </p>
      </header>

      <main className="workspace">
        <section className="stage-card">
          <div className="stage-header">
            <div>
              <p className="label">Workflow</p>
              <h2>
                {screen === "analyze" && "Start an analysis"}
                {screen === "setup" && "Confirm the tracked player"}
                {screen === "processing" && "Building the report"}
                {screen === "report" && "Review the report"}
              </h2>
            </div>
            <ol className="stage-rail" aria-label="Analysis stages">
              <li data-active={screen === "analyze"}>Analyze</li>
              <li data-active={screen === "setup"}>Setup</li>
              <li data-active={screen === "processing"}>Run</li>
              <li data-active={screen === "report"}>Report</li>
            </ol>
          </div>

          {error ? <div className="notice error">{error}</div> : null}

          {status?.warnings.length ? (
            <div className="stack warning-stack">
              {status.warnings.map((warning) => (
                <div className="notice warning" key={warning}>
                  {warning}
                </div>
              ))}
            </div>
          ) : null}

          {screen === "analyze" ? (
            <form className="stack" onSubmit={handleCreateAnalysis}>
              <label className="field">
                <span>YouTube link</span>
                <input
                  required
                  type="url"
                  value={youtubeUrl}
                  onChange={(event) => setYoutubeUrl(event.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                />
              </label>

              <label className="field">
                <span>Match type</span>
                <select
                  value={matchType}
                  onChange={(event) => setMatchType(event.target.value as MatchType)}
                >
                  {matchTypes.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="support-grid">
                <article className="support-card">
                  <p className="label">Coach tab priority</p>
                  <p>Summary, strengths, issues, drills, and shot-choice notes lead the experience.</p>
                </article>
                <article className="support-card">
                  <p className="label">Analytics tab support</p>
                  <p>Movement, positioning, and shot events remain available as clip-backed evidence.</p>
                </article>
              </div>

              <button className="primary-button" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Preparing setup..." : "Create analysis"}
              </button>
            </form>
          ) : null}

          {screen === "setup" && setup ? (
            <div className="stack">
              <div className="setup-preview">
                <div
                  className="frame"
                  onPointerCancel={stopDragging}
                  onPointerLeave={stopDragging}
                  onPointerMove={handleFramePointerMove}
                  onPointerUp={stopDragging}
                  ref={frameRef}
                >
                  <img
                    alt="Setup frame"
                    className="setup-image"
                    src={setup.setup_frame_url}
                  />
                  <div className="court-overlay">
                    {courtPoints.map((point, index) => (
                      <button
                        aria-label={`Court corner ${index + 1}`}
                        className="court-handle"
                        key={`${point.x}-${point.y}-${index}`}
                        onPointerDown={handleCourtCornerPointerDown(index)}
                        style={
                          {
                            left: `${point.x * 100}%`,
                            top: `${point.y * 100}%`,
                          } satisfies CSSProperties
                        }
                        type="button"
                      />
                    ))}
                  </div>
                </div>

                <div className="support-card">
                  <p className="label">Court setup</p>
                  <p>{setup.court.adjustment_hint}</p>
                  <p className="metric">
                    Detection confidence: {Math.round(setup.court.confidence * 100)}%
                  </p>
                  <p className="muted">Drag any court corner to correct the detected geometry.</p>
                </div>
              </div>

              <div className="player-grid">
                {setup.players.map((player) => (
                  <button
                    key={player.player_id}
                    className="player-card"
                    data-selected={selectedPlayer?.player_id === player.player_id}
                    onClick={() => setSelectedPlayer(player)}
                    type="button"
                  >
                    <span className="label">{player.side} side</span>
                    <strong>{player.label}</strong>
                    <span>{player.focus_hint}</span>
                  </button>
                ))}
              </div>

              <button
                className="primary-button"
                disabled={isSubmitting || !selectedPlayer}
                onClick={handleRunAnalysis}
                type="button"
              >
                {isSubmitting ? "Running analysis..." : "Save setup and run"}
              </button>
            </div>
          ) : null}

          {screen === "processing" ? (
            <div className="stack">
              <div className="progress-bar" aria-hidden="true">
                <span style={{ width: `${status?.progress_percent ?? 0}%` }} />
              </div>
              <div className="progress-meta">
                <strong>{status?.progress_percent ?? 0}%</strong>
                <p className="processing-copy">
                  {status?.message ??
                    "Generating the seeded coach report, movement metrics, and shot decision timeline."}
                </p>
              </div>
            </div>
          ) : null}

          {screen === "report" && report ? (
            <div className="stack">
              <div className="tab-bar" role="tablist" aria-label="Report tabs">
                <button
                  aria-selected={reportTab === "coach"}
                  className="tab"
                  onClick={() => setReportTab("coach")}
                  role="tab"
                  type="button"
                >
                  Coach View
                </button>
                <button
                  aria-selected={reportTab === "analytics"}
                  className="tab"
                  onClick={() => setReportTab("analytics")}
                  role="tab"
                  type="button"
                >
                  Analytics View
                </button>
              </div>

              {reportTab === "coach" ? (
                <div className="report-grid">
                  <article className="report-card feature-card">
                    <p className="label">Summary</p>
                    <p>{report.coach_view.summary}</p>
                  </article>
                  <article className="report-card">
                    <p className="label">Strengths</p>
                    <ul>
                      {report.coach_view.strengths.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                  <article className="report-card">
                    <p className="label">Priority issues</p>
                    <ul>
                      {report.coach_view.priority_issues.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                  <article className="report-card">
                    <p className="label">Shot-selection notes</p>
                    <p>{report.coach_view.shot_selection_notes}</p>
                  </article>
                  <article className="report-card">
                    <p className="label">Footwork notes</p>
                    <p>{report.coach_view.footwork_notes}</p>
                  </article>
                  <article className="report-card">
                    <p className="label">Positioning notes</p>
                    <p>{report.coach_view.positioning_notes}</p>
                  </article>
                  <article className="report-card">
                    <p className="label">Confidence notes</p>
                    <p>{report.coach_view.confidence_notes}</p>
                  </article>
                  <article className="report-card">
                    <p className="label">Recommended drills</p>
                    <ul>
                      {report.coach_view.recommended_drills.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                </div>
              ) : null}

              {reportTab === "analytics" ? (
                <div className="report-grid">
                  <article className="report-card">
                    <p className="label">Mechanics</p>
                    <ul>
                      <li>{report.analytics_view.mechanics.stance_note}</li>
                      <li>{report.analytics_view.mechanics.preparation_note}</li>
                      <li>{report.analytics_view.mechanics.balance_note}</li>
                      <li>{report.analytics_view.mechanics.recovery_note}</li>
                      <li>{report.analytics_view.mechanics.stroke_execution_note}</li>
                    </ul>
                  </article>

                  <article className="report-card">
                    <p className="label">Movement</p>
                    <div className="metric-grid">
                      <div>
                        <strong>{report.analytics_view.movement.total_distance_meters.toFixed(1)}m</strong>
                        <span>Total distance</span>
                      </div>
                      <div>
                        <strong>{report.analytics_view.movement.recovery_score}</strong>
                        <span>Recovery score</span>
                      </div>
                      <div>
                        <strong>{report.analytics_view.movement.court_coverage_percent}%</strong>
                        <span>Court coverage</span>
                      </div>
                      <div>
                        <strong>{report.analytics_view.movement.change_of_direction_count}</strong>
                        <span>Direction changes</span>
                      </div>
                      <div>
                        <strong>{report.analytics_view.movement.burst_count}</strong>
                        <span>Burst count</span>
                      </div>
                      <div>
                        <strong>
                          {Math.round(report.analytics_view.movement.directional_balance.left * 100)} /{" "}
                          {Math.round(report.analytics_view.movement.directional_balance.right * 100)}
                        </strong>
                        <span>Left / right balance</span>
                      </div>
                    </div>
                  </article>

                  <article className="report-card">
                    <p className="label">Positioning</p>
                    <p>{report.analytics_view.positioning.base_position_note}</p>
                    <p>{report.analytics_view.positioning.spacing_note}</p>
                    <div className="zone-grid">
                      {Object.entries(report.analytics_view.positioning.zone_occupancy).map(
                        ([zone, weight]) => (
                          <div className="zone-pill" key={zone}>
                            <strong>{weight}%</strong>
                            <span>{zone}</span>
                          </div>
                        ),
                      )}
                    </div>
                    <div className="heatmap-card">
                      <p className="label">Heatmap</p>
                      <div className="heatmap-grid">
                        {report.analytics_view.positioning.heatmap.map((cell) => (
                          <article className="heatmap-cell" key={cell.zone}>
                            <strong>{cell.zone}</strong>
                            <span>{Math.round(cell.weight * 100)}%</span>
                          </article>
                        ))}
                      </div>
                    </div>
                  </article>

                  <article className="report-card">
                    <p className="label">Shot selection</p>
                    <p>{report.analytics_view.shot_selection.overview}</p>
                    <div className="event-stack">
                      {report.analytics_view.shot_selection.events.map((event) => (
                        <article className="event-card" key={`${event.timestamp}-${event.shot_type}`}>
                          <div className="event-heading">
                            <strong>
                              {event.timestamp} · {event.shot_type}
                            </strong>
                            <span>
                              Execution {event.execution_score} / Decision {event.decision_score}
                            </span>
                          </div>
                          <p className="event-chip">{event.decision_quality}</p>
                          {event.recommendation ? <p>{event.recommendation}</p> : null}
                          <p className="label">Evidence</p>
                          <p className="muted">{event.evidence}</p>
                        </article>
                      ))}
                    </div>
                  </article>

                  <article className="report-card">
                    <p className="label">Confidence annotations</p>
                    <div className="annotation-stack">
                      {report.confidence_annotations.map((annotation) => (
                        <article className="annotation-card" key={annotation.field}>
                          <strong>{annotation.field}</strong>
                          <span>{Math.round(annotation.confidence * 100)}% confidence</span>
                          <p>{annotation.reason}</p>
                        </article>
                      ))}
                    </div>
                  </article>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>

        <aside className="insight-rail">
          <article className="rail-card">
            <p className="label">Current tracked player</p>
            <strong>{selectedPlayer?.label ?? report?.tracked_player_label ?? "Waiting for setup"}</strong>
            <span>{analysis ? formatMatchType(analysis.match_type) : "Choose a match type to begin."}</span>
          </article>
          <article className="rail-card">
            <p className="label">AI layer</p>
            <strong>Typed single-pass placeholder</strong>
            <span>
              Structured coach notes can layer on top later without changing the report contract.
            </span>
          </article>
        </aside>
      </main>
    </div>
  );
}

export default App;
