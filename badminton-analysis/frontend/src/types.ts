export type MatchType =
  | "mens_singles"
  | "womens_singles"
  | "mens_doubles"
  | "womens_doubles"
  | "mixed_doubles";

export type AnalysisStage =
  | "setup_required"
  | "ready_to_run"
  | "analyzing"
  | "completed"
  | "failed";

export interface CourtPoint {
  x: number;
  y: number;
}

export interface CourtModel {
  confidence: number;
  points: CourtPoint[];
  adjustment_hint: string;
}

export interface DetectionBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PlayerCandidate {
  player_id: string;
  label: string;
  side: "near" | "far";
  focus_hint: string;
  detection_id?: string | null;
  bounding_box?: DetectionBox | null;
}

export interface AnalysisCreatePayload {
  youtube_url: string;
  match_type: MatchType;
}

export interface AnalysisCreateResponse {
  analysis_id: string;
  youtube_url: string;
  match_type: MatchType;
  selection_required: boolean;
  stage: AnalysisStage;
  created_at: string;
}

export interface AnalysisSetupResponse {
  analysis_id: string;
  setup_frame_url: string;
  players: PlayerCandidate[];
  court: CourtModel;
}

export interface AnalysisSelectionInput {
  player_id: string;
  court_points: CourtPoint[];
}

export interface AnalysisActionResponse {
  analysis_id: string;
  stage: AnalysisStage;
  message: string;
}

export interface AnalysisStatusResponse {
  analysis_id: string;
  stage: AnalysisStage;
  progress_percent: number;
  message: string;
  warnings: string[];
  error_details: string | null;
  pipeline_stage?: string | null;
  frame_index?: number | null;
  total_frames?: number | null;
}

export interface FrameEvent {
  analysis_id: string;
  pipeline_stage: string;
  frame_index: number;
  total_frames: number;
  progress_percent: number;
  message: string;
  frame_jpeg_base64: string | null;
}

export interface CoachView {
  summary: string;
  strengths: string[];
  priority_issues: string[];
  shot_selection_notes: string;
  footwork_notes: string;
  positioning_notes: string;
  confidence_notes: string;
  recommended_drills: string[];
}

export interface MechanicsMetrics {
  stance_note: string;
  preparation_note: string;
  balance_note: string;
  recovery_note: string;
  stroke_execution_note: string;
}

export interface MovementMetrics {
  total_distance_meters: number;
  recovery_score: number;
  court_coverage_percent: number;
  change_of_direction_count: number;
  burst_count: number;
  directional_balance: Record<string, number>;
}

export interface HeatmapCell {
  zone: string;
  weight: number;
}

export interface PositioningMetrics {
  base_position_note: string;
  zone_occupancy: Record<string, number>;
  heatmap: HeatmapCell[];
  spacing_note: string;
}

export interface ShotSelectionEvent {
  timestamp: string;
  shot_type: string;
  execution_score: number;
  decision_score: number;
  decision_quality: "strong" | "neutral" | "poor";
  recommendation: string;
  evidence: string;
  clip_start_seconds: number;
  clip_end_seconds: number;
  rendered_clip_url?: string | null;
  rendered_clip_media_type?: string | null;
}

export interface ShotSelectionMetrics {
  overview: string;
  events: ShotSelectionEvent[];
}

export interface ShuttleSample {
  timestamp_seconds: number;
  x: number;
  y: number;
  confidence: number;
  source: "inferred" | "observed";
}

export interface PressureWindow {
  label: string;
  start_timestamp: string;
  end_timestamp: string;
  summary: string;
  clip_start_seconds?: number | null;
  clip_end_seconds?: number | null;
  rendered_clip_url?: string | null;
  rendered_clip_media_type?: string | null;
}

export interface ReportClipSelection {
  title: string;
  startSeconds: number;
  endSeconds: number;
  assetLabel: string;
  renderedClipUrl?: string | null;
  renderedClipMediaType?: string | null;
}

export interface ShuttleMetrics {
  summary: string;
  uncertainty_note: string;
  samples: ShuttleSample[];
  pressure_windows: PressureWindow[];
  heatmap: HeatmapCell[];
}

export interface AnalyticsView {
  mechanics: MechanicsMetrics;
  movement: MovementMetrics;
  positioning: PositioningMetrics;
  shot_selection: ShotSelectionMetrics;
  shuttle: ShuttleMetrics;
}

export interface ConfidenceAnnotation {
  field: string;
  confidence: number;
  reason: string;
}

export interface AIRationale {
  summary: string;
  evidence_highlights: string[];
}

export interface AnalysisEvidence {
  shuttle: ShuttleMetrics;
  movement_summary: string;
  mechanics_summary: string;
  shot_selection_summary: string;
}

export interface AnalysisReport {
  analysis_id: string;
  match_type: MatchType;
  tracked_player_label: string;
  coach_view: CoachView;
  analytics_view: AnalyticsView;
  confidence_annotations: ConfidenceAnnotation[];
  llm_provider: string | null;
  llm_model: string | null;
  generation_mode: "ai" | "fallback";
  analysis_evidence: AnalysisEvidence;
  ai_rationale: AIRationale | null;
  generated_at: string;
}
