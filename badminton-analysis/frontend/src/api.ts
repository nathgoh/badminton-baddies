import type {
  AnalysisActionResponse,
  AnalysisCreatePayload,
  AnalysisCreateResponse,
  AnalysisReport,
  AnalysisSelectionInput,
  AnalysisSetupResponse,
  AnalysisStatusResponse,
  FrameEvent,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
        detail = payload.detail[0].msg;
      }
    } catch {
      // Ignore JSON parsing errors and keep the generic message.
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function createAnalysis(payload: AnalysisCreatePayload): Promise<AnalysisCreateResponse> {
  return request("/api/analyses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchSetup(analysisId: string): Promise<AnalysisSetupResponse> {
  return request(`/api/analyses/${analysisId}/setup`);
}

export function saveSelection(
  analysisId: string,
  payload: AnalysisSelectionInput,
): Promise<AnalysisActionResponse> {
  return request(`/api/analyses/${analysisId}/selection`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runAnalysis(analysisId: string): Promise<AnalysisActionResponse> {
  return request(`/api/analyses/${analysisId}/run`, {
    method: "POST",
  });
}

export function fetchStatus(analysisId: string): Promise<AnalysisStatusResponse> {
  return request(`/api/analyses/${analysisId}/status`);
}

export function fetchReport(analysisId: string): Promise<AnalysisReport> {
  return request(`/api/analyses/${analysisId}/report`);
}

export function subscribeToFeed(
  analysisId: string,
  onFrame: (event: FrameEvent) => void,
  onDone: () => void,
  onError: (error: Event) => void,
): () => void {
  const source = new EventSource(`/api/analyses/${analysisId}/feed`);

  source.onmessage = (message) => {
    onFrame(JSON.parse(message.data) as FrameEvent);
  };

  source.addEventListener("done", () => {
    source.close();
    onDone();
  });

  source.onerror = (error) => {
    source.close();
    onError(error);
  };

  return () => source.close();
}
