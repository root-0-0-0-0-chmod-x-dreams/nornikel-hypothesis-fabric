import type {
  GenerateRequest,
  GenerateResponse,
  StreamEvent,
  RoadmapRequest,
  RoadmapResponse,
  FeedbackRequest,
  FeedbackResponse,
  HistoryResponse,
} from "./types";

const BASE = "/api/v1";

function apiUrl(path: string): string {
  return `${BASE}${path}`;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Ошибка API: ${res.status}`);
  }
  return res.json();
}

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(apiUrl(path), window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Ошибка API: ${res.status}`);
  }
  return res.json();
}

export const hypothesesApi = {
  generate(req: GenerateRequest): Promise<GenerateResponse> {
    return post("/hypotheses/generate", req);
  },

  async *generateStream(req: GenerateRequest, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
    const res = await fetch(apiUrl("/hypotheses/generate/stream"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body: JSON.stringify(req),
      signal,
      cache: "no-store",
    });
    if (!res.ok) {
      const err = await res.text().catch(() => "");
      throw new Error(err || `HTTP ${res.status}`);
    }
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        for (const rawLine of block.split("\n")) {
          const line = rawLine.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trimStart();
          if (!data || data === "[DONE]") continue;
          try {
            yield JSON.parse(data) as StreamEvent;
          } catch {
            // skip malformed chunks
          }
        }

        boundary = buffer.indexOf("\n\n");
      }
    }
  },

  getRoadmap(hypothesisId: string, req?: RoadmapRequest): Promise<RoadmapResponse> {
    return post(`/hypotheses/${hypothesisId}/roadmap`, req || {});
  },

  submitFeedback(hypothesisId: string, req: FeedbackRequest): Promise<FeedbackResponse> {
    return post(`/hypotheses/${hypothesisId}/feedback`, req);
  },

  getHistory(params?: { status?: string; limit?: number; offset?: number }): Promise<HistoryResponse> {
    const p: Record<string, string> = {};
    if (params?.status) p.status = params.status;
    if (params?.limit) p.limit = String(params.limit);
    if (params?.offset) p.offset = String(params.offset);
    return get("/history", p);
  },
};
