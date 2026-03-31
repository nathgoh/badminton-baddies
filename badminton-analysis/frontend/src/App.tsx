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
        if (cancelled) return;

        startTransition(() => setStatus(nextStatus));

        if (nextStatus.stage === "completed") {
          const nextReport = await fetchReport(stableAnalysisId);
          if (cancelled) return;

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
        if (cancelled) return;

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

  function resetToAnalyze() {
    startTransition(() => {
      setScreen("analyze");
      setAnalysis(null);
      setSetup(null);
      setCourtPoints([]);
      setSelectedPlayer(null);
      setStatus(null);
      setReport(null);
      setError(null);
      setReportTab("coach");
    });
  }

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
    if (!analysis || !setup || !selectedPlayer) return;

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
    if (!bounds || bounds.width === 0 || bounds.height === 0) return;

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
    if (draggingCorner === null) return;
    updateCourtPoint(draggingCorner, event.clientX, event.clientY);
  }

  function stopDragging() {
    setDraggingCorner(null);
  }

  const stageLabels: Screen[] = ["analyze", "setup", "processing", "report"];
  const stageDisplay: Record<Screen, string> = {
    analyze: "Analyze",
    setup: "Setup",
    processing: "Run",
    report: "Report",
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <header className="max-w-4xl mx-auto px-6 pt-10 pb-6">
        <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
          Badminton video intelligence
        </p>
        <h1 className="mt-2 text-4xl sm:text-5xl font-bold tracking-tight text-slate-900">
          Badminton Analysis
        </h1>
        <p className="mt-3 text-base text-slate-500 max-w-2xl leading-relaxed">
          Coach-first review for YouTube match footage with player selection, tactical shot grading,
          and report-ready movement insight.
        </p>
      </header>

      <main className="max-w-5xl mx-auto px-6 pb-16 grid gap-6 lg:grid-cols-[1fr_260px] lg:items-start">
        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          {/* Stage header */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
            <div>
              <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                Workflow
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-800">
                {screen === "analyze" && "Start an analysis"}
                {screen === "setup" && "Confirm the tracked player"}
                {screen === "processing" && "Building the report"}
                {screen === "report" && "Review the report"}
              </h2>
            </div>
            <ol
              className="grid grid-cols-4 gap-2 list-none m-0 p-0"
              aria-label="Analysis stages"
            >
              {stageLabels.map((stage) => (
                <li
                  key={stage}
                  className={`px-3 py-2 rounded-full text-center text-sm border ${
                    screen === stage
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-slate-50 text-slate-400 border-slate-200"
                  }`}
                >
                  {stageDisplay[stage]}
                </li>
              ))}
            </ol>
          </div>

          {/* Error notice */}
          {error ? (
            <div className="mb-4 p-4 rounded-xl bg-red-50 text-red-700 text-sm">{error}</div>
          ) : null}

          {/* Warnings */}
          {status?.warnings.length ? (
            <div className="grid gap-2 mb-4">
              {status.warnings.map((warning) => (
                <div
                  className="p-3 rounded-xl bg-amber-50 text-amber-700 text-sm"
                  key={warning}
                >
                  {warning}
                </div>
              ))}
            </div>
          ) : null}

          {/* Analyze screen */}
          {screen === "analyze" ? (
            <form className="grid gap-5" onSubmit={handleCreateAnalysis}>
              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-700">YouTube link</span>
                <input
                  required
                  type="url"
                  value={youtubeUrl}
                  onChange={(event) => setYoutubeUrl(event.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-700">Match type</span>
                <select
                  value={matchType}
                  onChange={(event) => setMatchType(event.target.value as MatchType)}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {matchTypes.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid sm:grid-cols-2 gap-4">
                <article className="p-4 border border-slate-200 rounded-xl bg-slate-50">
                  <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                    Coach tab priority
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    Summary, strengths, issues, drills, and shot-choice notes lead the experience.
                  </p>
                </article>
                <article className="p-4 border border-slate-200 rounded-xl bg-slate-50">
                  <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                    Analytics tab support
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    Movement, positioning, and shot events remain available as clip-backed evidence.
                  </p>
                </article>
              </div>

              <button
                className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-wait"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? "Preparing setup..." : "Create analysis"}
              </button>
            </form>
          ) : null}

          {/* Setup screen */}
          {screen === "setup" && setup ? (
            <div className="grid gap-5">
              <div className="grid lg:grid-cols-[1.25fr_0.75fr] gap-4">
                <div
                  className="relative min-h-[250px] rounded-2xl border border-slate-200 overflow-hidden bg-slate-100"
                  onPointerCancel={stopDragging}
                  onPointerLeave={stopDragging}
                  onPointerMove={handleFramePointerMove}
                  onPointerUp={stopDragging}
                  ref={frameRef}
                >
                  <img
                    alt="Setup frame"
                    className="block w-full h-full min-h-[250px] object-cover"
                    src={setup.setup_frame_url}
                  />
                  <div className="absolute inset-0">
                    {courtPoints.map((point, index) => (
                      <button
                        aria-label={`Court corner ${index + 1}`}
                        className="absolute w-6 h-6 -ml-3 -mt-3 border-2 border-white rounded-full bg-blue-500 shadow-lg hover:bg-blue-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
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

                <div className="p-4 border border-slate-200 rounded-xl bg-slate-50">
                  <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                    Court setup
                  </p>
                  <p className="mt-2 text-sm text-slate-600">{setup.court.adjustment_hint}</p>
                  <p className="mt-2 text-sm font-medium text-slate-800">
                    Detection confidence: {Math.round(setup.court.confidence * 100)}%
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Drag any court corner to correct the detected geometry.
                  </p>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-3">
                {setup.players.map((player) => (
                  <button
                    key={player.player_id}
                    className={`text-left p-4 border rounded-xl grid gap-2 transition-colors ${
                      selectedPlayer?.player_id === player.player_id
                        ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                    onClick={() => setSelectedPlayer(player)}
                    type="button"
                  >
                    <span className="text-xs font-semibold tracking-widest uppercase text-slate-400">
                      {player.side} side
                    </span>
                    <strong className="text-sm text-slate-800">{player.label}</strong>
                    <span className="text-xs text-slate-500">{player.focus_hint}</span>
                  </button>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  className="py-3 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-sm font-medium text-slate-600 transition-colors"
                  onClick={resetToAnalyze}
                  type="button"
                >
                  Back
                </button>
                <button
                  className="flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-wait"
                  disabled={isSubmitting || !selectedPlayer}
                  onClick={handleRunAnalysis}
                  type="button"
                >
                  {isSubmitting ? "Running analysis..." : "Save setup and run"}
                </button>
              </div>
            </div>
          ) : null}

          {/* Processing screen */}
          {screen === "processing" ? (
            <div className="grid gap-5">
              <div
                className="w-full h-4 rounded-full bg-slate-100 overflow-hidden"
                aria-hidden="true"
              >
                <span
                  className="block h-full rounded-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${status?.progress_percent ?? 0}%` }}
                />
              </div>
              <div className="grid gap-2">
                <strong className="text-lg text-slate-800">
                  {status?.progress_percent ?? 0}%
                </strong>
                <p className="text-sm text-slate-500">
                  {status?.message ??
                    "Generating the seeded coach report, movement metrics, and shot decision timeline."}
                </p>
              </div>
              <button
                className="justify-self-start py-2 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-sm font-medium text-slate-600 transition-colors"
                onClick={() => setScreen("setup")}
                type="button"
              >
                Back to setup
              </button>
            </div>
          ) : null}

          {/* Report screen */}
          {screen === "report" && report ? (
            <div className="grid gap-5">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div
                  className="inline-grid grid-cols-2 gap-1 p-1 rounded-xl bg-slate-100"
                  role="tablist"
                  aria-label="Report tabs"
                >
                  <button
                    aria-selected={reportTab === "coach"}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      reportTab === "coach"
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                    onClick={() => setReportTab("coach")}
                    role="tab"
                    type="button"
                  >
                    Coach View
                  </button>
                  <button
                    aria-selected={reportTab === "analytics"}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      reportTab === "analytics"
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    }`}
                    onClick={() => setReportTab("analytics")}
                    role="tab"
                    type="button"
                  >
                    Analytics View
                  </button>
                </div>
                <button
                  className="py-2 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors"
                  onClick={resetToAnalyze}
                  type="button"
                >
                  Analyze another video
                </button>
              </div>

              {reportTab === "coach" ? (
                <div className="grid sm:grid-cols-2 gap-4">
                  <article className="sm:col-span-2 p-5 border border-blue-100 rounded-xl bg-blue-50">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Summary
                    </p>
                    <p className="mt-2 text-sm text-slate-700 leading-relaxed">
                      {report.coach_view.summary}
                    </p>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Strengths
                    </p>
                    <ul className="mt-2 pl-4 text-sm text-slate-600 list-disc space-y-1">
                      {report.coach_view.strengths.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Priority issues
                    </p>
                    <ul className="mt-2 pl-4 text-sm text-slate-600 list-disc space-y-1">
                      {report.coach_view.priority_issues.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Shot-selection notes
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.coach_view.shot_selection_notes}
                    </p>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Footwork notes
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.coach_view.footwork_notes}
                    </p>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Positioning notes
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.coach_view.positioning_notes}
                    </p>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Confidence notes
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.coach_view.confidence_notes}
                    </p>
                  </article>
                  <article className="sm:col-span-2 p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Recommended drills
                    </p>
                    <ul className="mt-2 pl-4 text-sm text-slate-600 list-disc space-y-1">
                      {report.coach_view.recommended_drills.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                </div>
              ) : null}

              {reportTab === "analytics" ? (
                <div className="grid sm:grid-cols-2 gap-4">
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Mechanics
                    </p>
                    <ul className="mt-2 text-sm text-slate-600 space-y-2">
                      <li>{report.analytics_view.mechanics.stance_note}</li>
                      <li>{report.analytics_view.mechanics.preparation_note}</li>
                      <li>{report.analytics_view.mechanics.balance_note}</li>
                      <li>{report.analytics_view.mechanics.recovery_note}</li>
                      <li>{report.analytics_view.mechanics.stroke_execution_note}</li>
                    </ul>
                  </article>

                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Movement
                    </p>
                    <div className="mt-3 grid grid-cols-2 gap-4">
                      <div>
                        <strong className="text-lg text-slate-800">
                          {report.analytics_view.movement.total_distance_meters.toFixed(1)}m
                        </strong>
                        <span className="block text-xs text-slate-400">Total distance</span>
                      </div>
                      <div>
                        <strong className="text-lg text-slate-800">
                          {report.analytics_view.movement.recovery_score}
                        </strong>
                        <span className="block text-xs text-slate-400">Recovery score</span>
                      </div>
                      <div>
                        <strong className="text-lg text-slate-800">
                          {report.analytics_view.movement.court_coverage_percent}%
                        </strong>
                        <span className="block text-xs text-slate-400">Court coverage</span>
                      </div>
                      <div>
                        <strong className="text-lg text-slate-800">
                          {report.analytics_view.movement.change_of_direction_count}
                        </strong>
                        <span className="block text-xs text-slate-400">Direction changes</span>
                      </div>
                      <div>
                        <strong className="text-lg text-slate-800">
                          {report.analytics_view.movement.burst_count}
                        </strong>
                        <span className="block text-xs text-slate-400">Burst count</span>
                      </div>
                      <div>
                        <strong className="text-lg text-slate-800">
                          {Math.round(
                            report.analytics_view.movement.directional_balance.left * 100,
                          )}{" "}
                          /{" "}
                          {Math.round(
                            report.analytics_view.movement.directional_balance.right * 100,
                          )}
                        </strong>
                        <span className="block text-xs text-slate-400">Left / right balance</span>
                      </div>
                    </div>
                  </article>

                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Positioning
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.analytics_view.positioning.base_position_note}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      {report.analytics_view.positioning.spacing_note}
                    </p>
                    <div className="grid grid-cols-3 gap-2 mt-4">
                      {Object.entries(report.analytics_view.positioning.zone_occupancy).map(
                        ([zone, weight]) => (
                          <div
                            className="p-3 border border-slate-200 rounded-lg bg-slate-50 text-center"
                            key={zone}
                          >
                            <strong className="text-sm text-slate-800">{weight}%</strong>
                            <span className="block text-xs text-slate-400">{zone}</span>
                          </div>
                        ),
                      )}
                    </div>
                    <div className="mt-4">
                      <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                        Heatmap
                      </p>
                      <div className="grid grid-cols-3 gap-2 mt-2">
                        {report.analytics_view.positioning.heatmap.map((cell) => (
                          <article
                            className="p-3 border border-slate-200 rounded-lg bg-blue-50"
                            key={cell.zone}
                          >
                            <strong className="text-xs text-slate-700">{cell.zone}</strong>
                            <span className="block text-sm text-blue-600 font-semibold">
                              {Math.round(cell.weight * 100)}%
                            </span>
                          </article>
                        ))}
                      </div>
                    </div>
                  </article>

                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Shot selection
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.analytics_view.shot_selection.overview}
                    </p>
                    <div className="grid gap-3 mt-4">
                      {report.analytics_view.shot_selection.events.map((event) => (
                        <article
                          className="p-4 border border-slate-200 rounded-xl bg-slate-50"
                          key={`${event.timestamp}-${event.shot_type}`}
                        >
                          <div className="flex flex-col gap-1 mb-2">
                            <strong className="text-sm text-slate-800">
                              {event.timestamp} &middot; {event.shot_type}
                            </strong>
                            <span className="text-xs text-slate-500">
                              Execution {event.execution_score} / Decision {event.decision_score}
                            </span>
                          </div>
                          <p className="inline-block px-2 py-1 rounded-full bg-slate-200 text-xs capitalize mb-2">
                            {event.decision_quality}
                          </p>
                          {event.recommendation ? (
                            <p className="text-sm text-slate-600">{event.recommendation}</p>
                          ) : null}
                          <p className="text-xs font-semibold tracking-widest uppercase text-blue-600 mt-2">
                            Evidence
                          </p>
                          <p className="text-xs text-slate-400 mt-1">{event.evidence}</p>
                        </article>
                      ))}
                    </div>
                  </article>

                  <article className="sm:col-span-2 p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Confidence annotations
                    </p>
                    <div className="grid gap-3 mt-3">
                      {report.confidence_annotations.map((annotation) => (
                        <article
                          className="p-3 border border-slate-200 rounded-lg grid gap-1"
                          key={annotation.field}
                        >
                          <strong className="text-sm text-slate-700">{annotation.field}</strong>
                          <span className="text-xs text-blue-600 font-semibold">
                            {Math.round(annotation.confidence * 100)}% confidence
                          </span>
                          <p className="text-xs text-slate-500">{annotation.reason}</p>
                        </article>
                      ))}
                    </div>
                  </article>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>

        <aside className="grid gap-4">
          <article className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
            <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
              Current tracked player
            </p>
            <strong className="block mt-2 text-sm text-slate-800">
              {selectedPlayer?.label ?? report?.tracked_player_label ?? "Waiting for setup"}
            </strong>
            <span className="block mt-1 text-xs text-slate-400">
              {analysis
                ? formatMatchType(analysis.match_type)
                : "Choose a match type to begin."}
            </span>
          </article>
          <article className="p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
            <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
              AI layer
            </p>
            <strong className="block mt-2 text-sm text-slate-800">
              Typed single-pass placeholder
            </strong>
            <span className="block mt-1 text-xs text-slate-400">
              Structured coach notes can layer on top later without changing the report contract.
            </span>
          </article>
        </aside>
      </main>
    </div>
  );
}

export default App;
