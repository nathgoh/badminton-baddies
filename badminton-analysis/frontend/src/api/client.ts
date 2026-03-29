import {
  UploadResponse,
  DetectRequest,
  DetectResponse,
  AnalyzeRequest,
  AnalyzeStartResponse,
  AnalysisStatus,
  AnalysisResult,
  BoundingBox,
} from '../types';

const API_BASE = '/api';

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async uploadVideo(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  async detectPersons(request: DetectRequest): Promise<DetectResponse> {
    return this.request<DetectResponse>('/detect', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async startAnalysis(request: AnalyzeRequest): Promise<AnalyzeStartResponse> {
    return this.request<AnalyzeStartResponse>('/analyze', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
    return this.request<AnalysisStatus>(`/analyze/${analysisId}/status`);
  }

  async getAnalysisResults(analysisId: string): Promise<AnalysisResult> {
    return this.request<AnalysisResult>(`/analyze/${analysisId}/results`);
  }

  getVideoUrl(videoId: string, filename: string): string {
    return `${API_BASE}/video/${videoId}/${filename}`;
  }

  getAnnotatedVideoUrl(analysisId: string): string {
    return `${API_BASE}/video/analyses/${analysisId}/annotated_video.mp4`;
  }
}

export const apiClient = new ApiClient();
