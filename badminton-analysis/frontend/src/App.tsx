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
  HeatmapCell,
  MatchType,
  PlayerCandidate,
  ShotSelectionEvent,
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

/** Parse "MM:SS" timestamp to total seconds. */
function parseTimestamp(ts: string): number {
  const parts = ts.split(":");
  if (parts.length === 2) return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
  if (parts.length === 3)
    return parseInt(parts[0], 10) * 3600 + parseInt(parts[1], 10) * 60 + parseInt(parts[2], 10);
  return 0;
}

/** Build a YouTube URL that starts at the given "MM:SS" timestamp. */
function youtubeTimestampUrl(baseUrl: string, timestamp: string): string {
  const seconds = parseTimestamp(timestamp);
  const url = new URL(baseUrl);
  url.searchParams.set("t", String(seconds));
  return url.toString();
}

/** Map heatmap zone name (e.g. "front-left") to a grid position. */
const ZONE_GRID: Record<string, [number, number]> = {
  "front-left": [0, 0],
  "front-centre": [0, 1],
  "front-right": [0, 2],
  "mid-left": [1, 0],
  "mid-centre": [1, 1],
  "mid-right": [1, 2],
  "rear-left": [2, 0],
  "rear-centre": [2, 1],
  "rear-right": [2, 2],
};

/** Color intensity from weight (0-1). Returns a blue shade. */
function heatColor(weight: number): string {
  const w = Math.max(0, Math.min(1, weight));
  if (w < 0.05) return "rgb(241 245 249)"; // slate-100
  // Interpolate from light blue to dark blue
  const r = Math.round(219 - 180 * w);
  const g = Math.round(234 - 150 * w);
  const b = Math.round(254 - 30 * w);
  return `rgb(${r} ${g} ${b})`;
}

function CourtHeatmap({ cells }: { cells: HeatmapCell[] }) {
  const grid: (HeatmapCell | null)[][] = [
    [null, null, null],
    [null, null, null],
    [null, null, null],
  ];
  const maxWeight = Math.max(...cells.map((c) => c.weight), 0.01);
  for (const cell of cells) {
    const pos = ZONE_GRID[cell.zone];
    if (pos) grid[pos[0]][pos[1]] = cell;
  }

  return (
    <div className="mt-2">
      {/* Court outline */}
      <div className="relative border-2 border-slate-400 rounded-lg overflow-hidden">
        {/* Net line */}
        <div className="absolute left-0 right-0 top-1/3 border-t-2 border-dashed border-slate-300 pointer-events-none" />
        <div className="grid grid-rows-3">
          {grid.map((row, ri) => (
            <div className="grid grid-cols-3" key={ri}>
              {row.map((cell, ci) => {
                const normalized = cell ? cell.weight / maxWeight : 0;
                const pct = cell ? Math.round(cell.weight * 100) : 0;
                const zoneName = cell?.zone ?? "";
                return (
                  <div
                    key={ci}
                    className="flex flex-col items-center justify-center aspect-[4/3] border border-slate-200/50 transition-colors"
                    style={{ backgroundColor: heatColor(normalized) }}
                  >
                    <span className="text-lg font-bold text-slate-800">{pct}%</span>
                    <span className="text-[10px] text-slate-500 capitalize">
                      {zoneName.replace("-", " ")}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      {/* Legend */}
      <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
        <span>Low</span>
        <div className="flex-1 h-2 rounded-full bg-gradient-to-r from-slate-100 via-blue-200 to-blue-600" />
        <span>High</span>
      </div>
    </div>
  );
}

function ShotEventCard({
  event,
  youtubeUrl,
}: {
  event: ShotSelectionEvent;
  youtubeUrl: string;
}) {
  const qualityColor =
    event.decision_quality === "strong"
      ? "bg-green-100 text-green-700"
      : event.decision_quality === "poor"
        ? "bg-red-100 text-red-700"
        : "bg-slate-200 text-slate-600";

  return (
    <article className="p-4 border border-slate-200 rounded-xl bg-slate-50">
      <div className="flex flex-col gap-1 mb-2">
        <div className="flex items-center gap-2">
          <a
            href={youtubeTimestampUrl(youtubeUrl, event.timestamp)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-800 hover:underline"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M10 15l5.19-3L10 9v6m11.56-7.83c.13.47.22 1.1.28 1.9.07.8.1 1.49.1 2.09L22 12c0 2.19-.16 3.8-.44 4.83-.25.9-.83 1.48-1.73 1.73-.47.13-1.33.22-2.65.28-1.3.07-2.49.1-3.59.1L12 19c-4.19 0-6.8-.16-7.83-.44-.9-.25-1.48-.83-1.73-1.73-.13-.47-.22-1.1-.28-1.9-.07-.8-.1-1.49-.1-2.09L2 12c0-2.19.16-3.8.44-4.83.25-.9.83-1.48 1.73-1.73.47-.13 1.33-.22 2.65-.28 1.3-.07 2.49-.1 3.59-.1L12 5c4.19 0 6.8.16 7.83.44.9.25 1.48.83 1.73 1.73z" />
            </svg>
            {event.timestamp}
          </a>
          <span className="text-sm text-slate-800 font-medium">{event.shot_type}</span>
        </div>
        <span className="text-xs text-slate-500">
          Execution {event.execution_score} / Decision {event.decision_score}
        </span>
      </div>
      <p className={`inline-block px-2 py-1 rounded-full text-xs capitalize mb-2 ${qualityColor}`}>
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
  );
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
                    {/* Player bounding box overlays */}
                    {setup.players.map((player) =>
                      player.bounding_box ? (
                        <button
                          aria-label={player.label}
                          key={player.player_id}
                          className={`absolute border-2 rounded-md transition-all cursor-pointer ${
                            selectedPlayer?.player_id === player.player_id
                              ? "border-blue-500 bg-blue-500/20 shadow-[0_0_12px_rgba(59,130,246,0.5)]"
                              : "border-white/70 bg-white/10 hover:border-blue-400 hover:bg-blue-400/15"
                          }`}
                          onClick={() => setSelectedPlayer(player)}
                          style={
                            {
                              left: `${player.bounding_box.x * 100}%`,
                              top: `${player.bounding_box.y * 100}%`,
                              width: `${player.bounding_box.width * 100}%`,
                              height: `${player.bounding_box.height * 100}%`,
                            } satisfies CSSProperties
                          }
                          type="button"
                        >
                          <span
                            className={`absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-0.5 rounded text-xs font-semibold ${
                              selectedPlayer?.player_id === player.player_id
                                ? "bg-blue-500 text-white"
                                : "bg-black/60 text-white"
                            }`}
                          >
                            {player.label}
                          </span>
                        </button>
                      ) : null,
                    )}

                    {/* Court corner handles */}
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
                  <article className="p-4 border border-slate-200 rounded-xl bg-slate-50">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      AI provenance
                    </p>
                    <p className="mt-2 text-sm text-slate-700">
                      {report.llm_provider && report.llm_model
                        ? `${report.llm_provider} · ${report.llm_model}`
                        : "Deterministic fallback coaching"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {report.generation_mode === "ai"
                        ? "Structured coaching came from the configured LLM provider."
                        : "The service fell back to deterministic coaching after the AI path failed or was disabled."}
                    </p>
                  </article>
                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      AI rationale
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.ai_rationale?.summary ??
                        "No separate AI rationale was returned for this report."}
                    </p>
                    {report.ai_rationale?.evidence_highlights.length ? (
                      <ul className="mt-3 pl-4 text-sm text-slate-600 list-disc space-y-1">
                        {report.ai_rationale.evidence_highlights.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : null}
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
                  <article className="sm:col-span-2 p-4 border border-slate-200 rounded-xl bg-slate-50">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Evidence summary
                    </p>
                    <div className="mt-3 grid sm:grid-cols-3 gap-3 text-sm text-slate-600">
                      <p>{report.analysis_evidence.movement_summary}</p>
                      <p>{report.analysis_evidence.mechanics_summary}</p>
                      <p>{report.analysis_evidence.shot_selection_summary}</p>
                    </div>
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
                        Court heatmap
                      </p>
                      <CourtHeatmap cells={report.analytics_view.positioning.heatmap} />
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
                        <ShotEventCard
                          key={`${event.timestamp}-${event.shot_type}`}
                          event={event}
                          youtubeUrl={youtubeUrl}
                        />
                      ))}
                    </div>
                  </article>

                  <article className="p-4 border border-slate-200 rounded-xl">
                    <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                      Shuttle evidence
                    </p>
                    <p className="mt-2 text-sm text-slate-600">
                      {report.analysis_evidence.shuttle.summary}
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      {report.analysis_evidence.shuttle.uncertainty_note}
                    </p>
                    <div className="mt-4">
                      <p className="text-xs font-semibold tracking-widest uppercase text-blue-600">
                        Shuttle heatmap
                      </p>
                      <CourtHeatmap cells={report.analytics_view.shuttle.heatmap} />
                    </div>
                    <div className="grid gap-3 mt-4">
                      {report.analysis_evidence.shuttle.pressure_windows.map((window) => (
                        <article
                          className="p-3 border border-slate-200 rounded-lg bg-slate-50"
                          key={`${window.label}-${window.start_timestamp}-${window.end_timestamp}`}
                        >
                          <strong className="text-sm text-slate-700">{window.label}</strong>
                          <span className="block mt-1 text-xs text-blue-600 font-semibold">
                            {window.start_timestamp} - {window.end_timestamp}
                          </span>
                          <p className="mt-1 text-xs text-slate-500">{window.summary}</p>
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
              {report?.llm_model
                ? `${report.llm_provider} · ${report.llm_model}`
                : "Deterministic fallback"}
            </strong>
            <span className="block mt-1 text-xs text-slate-400">
              {report
                ? report.generation_mode === "ai"
                  ? "Coach feedback came from the configured AI provider with structured evidence."
                  : "Coach feedback fell back to deterministic logic while preserving the expanded evidence contract."
                : "Provider-backed coaching is configurable without changing the frontend contract."}
            </span>
          </article>
        </aside>
      </main>
    </div>
  );
}

export default App;
