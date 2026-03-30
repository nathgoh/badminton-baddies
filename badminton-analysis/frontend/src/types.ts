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

export interface PlayerCandidate {
  player_id: string;
  label: string;
  side: "near" | "far";
  focus_hint: string;
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
}

export interface ShotSelectionMetrics {
  overview: string;
  events: ShotSelectionEvent[];
}

export interface AnalyticsView {
  mechanics: MechanicsMetrics;
  movement: MovementMetrics;
  positioning: PositioningMetrics;
  shot_selection: ShotSelectionMetrics;
}

export interface ConfidenceAnnotation {
  field: string;
  confidence: number;
  reason: string;
}

export interface AnalysisReport {
  analysis_id: string;
  match_type: MatchType;
  tracked_player_label: string;
  coach_view: CoachView;
  analytics_view: AnalyticsView;
  confidence_annotations: ConfidenceAnnotation[];
  generated_at: string;
}
