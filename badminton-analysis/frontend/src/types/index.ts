export interface BoundingBox {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export interface UploadResponse {
  video_id: string;
  filename: string;
}

export interface DetectRequest {
  video_id: string;
  frame_number?: number;
}

export interface DetectResponse {
  frame_image: string; // base64 encoded
  persons: BoundingBox[];
}

export interface AnalyzeRequest {
  video_id: string;
  person_bbox: BoundingBox;
}

export interface AnalyzeStartResponse {
  analysis_id: string;
  status: string;
}

export interface AnalysisStatus {
  status: 'processing' | 'completed' | 'failed';
  progress?: number;
}

export interface MovementPoint {
  time_sec: number;
  distance: number;
}

export interface AnalysisStats {
  total_distance_meters: number;
  avg_speed_mps: number;
  court_coverage_pct: number;
  estimated_shot_count: number;
  movement_over_time: MovementPoint[];
}

export interface AnalysisResult {
  stats: AnalysisStats;
  annotated_video_url: string;
}
