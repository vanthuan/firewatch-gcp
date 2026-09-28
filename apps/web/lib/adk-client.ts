// apps/web/lib/adk-client.ts
import { GoogleAuth } from "google-auth-library";
const auth = new GoogleAuth({ scopes: ["https://www.googleapis.com/auth/cloud-platform"] });
const base = (engine: string) =>
  `https://us-east1-aiplatform.googleapis.com/v1/${engine}`;   // engine = projects/../locations/us-east1/reasoningEngines/ID

// ADK session as returned by async_create_session
export interface AdkSession {
  id: string;
  app_name: string;
  user_id: string;
  state: Record<string, unknown>;
  last_update_time?: number;
}

interface QueryResponse<T> {
  output: T;
}

export async function createSession(engine: string, userId: string, state: Record<string, unknown>) {
  const client = await auth.getClient();
  const res = await client.request<QueryResponse<AdkSession>>({
    url: `${base(engine)}:query`, method: "POST",
    data: { class_method: "async_create_session", input: { user_id: userId, state } },
  });
  return res.data.output;                    // res.data.output.id is the session id
}

export async function streamQuery(engine: string, userId: string, sessionId: string, message: unknown) {
  const token = await (await auth.getClient()).getAccessToken();
  return fetch(`${base(engine)}:streamQuery?alt=sse`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token.token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ class_method: "async_stream_query", input: { user_id: userId, session_id: sessionId, message } }),
  });                                         // stream of ADK events; the route handler re-emits them as SSE
}