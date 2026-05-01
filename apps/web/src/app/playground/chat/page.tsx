"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";

interface SessionUser {
  id: string;
  email: string;
  name?: string | null;
}

interface ApiKey {
  id: string;
  keyPrefix: string;
  name: string | null;
  createdAt: string;
  lastUsedAt: string | null;
}

type AuthMode = "session" | "apikey";

interface ToolCallView {
  id: string;
  name: string;
  arguments: string;
}

interface ChatMessageView {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  reasoningOpen?: boolean;
  toolCalls: ToolCallView[];
  streaming?: boolean;
}

export default function ChatPlaygroundPage() {
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auth state mirrors /playground/page.tsx for consistency.
  const [sessionUser, setSessionUser] = useState<SessionUser | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [userKeys, setUserKeys] = useState<ApiKey[]>([]);
  const [authMode, setAuthMode] = useState<AuthMode>("session");
  const [apiKey, setApiKey] = useState("");
  const [selectedKeyId, setSelectedKeyId] = useState<string>("manual");

  useEffect(() => {
    async function init() {
      try {
        const res = await fetch("/api/auth/session");
        const data = (await res.json()) as { user: SessionUser | null };
        if (data.user) {
          setSessionUser(data.user);
          setAuthMode("session");
          const keysRes = await fetch("/api/keys");
          if (keysRes.ok) {
            const keysData = (await keysRes.json()) as { keys: ApiKey[] };
            const keys = keysData.keys || [];
            setUserKeys(keys);
            if (keys.length > 0) setSelectedKeyId(keys[0].id);
          }
        } else {
          setAuthMode("apikey");
        }
      } catch {
        setAuthMode("apikey");
      } finally {
        setSessionLoading(false);
      }
    }
    init();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    if (!input.trim() || streaming) return;
    setError(null);

    const userMsg: ChatMessageView = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      toolCalls: [],
    };
    const assistantMsg: ChatMessageView = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      reasoning: "",
      toolCalls: [],
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authMode === "apikey" && apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    // Build OpenAI-shape messages from history (drop view-only fields).
    const wireMessages = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch("/api/v1/chat/completions", {
        method: "POST",
        headers,
        credentials: "include",
        signal: controller.signal,
        body: JSON.stringify({
          model: "arbbuilder-chat",
          messages: wireMessages,
          stream: true,
        }),
      });

      if (!res.ok || !res.body) {
        const errBody = (await res.json().catch(() => ({ error: { message: `HTTP ${res.status}` } }))) as { error?: { message: string } };
        throw new Error(errBody.error?.message || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const toolCallAcc: Map<number, ToolCallView> = new Map();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let frameEnd: number;
        while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, frameEnd);
          buffer = buffer.slice(frameEnd + 2);
          for (const line of frame.split("\n")) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data:")) continue;
            const data = trimmed.slice(5).trim();
            if (data === "[DONE]") continue;
            let chunk: {
              error?: { message: string };
              choices?: Array<{
                delta?: {
                  content?: string;
                  reasoning_content?: string;
                  tool_calls?: Array<{
                    index: number;
                    id?: string;
                    function?: { name?: string; arguments?: string };
                  }>;
                };
              }>;
            };
            try {
              chunk = JSON.parse(data);
            } catch {
              continue;
            }

            if (chunk.error) {
              throw new Error(chunk.error.message);
            }

            const delta = chunk.choices?.[0]?.delta;
            if (!delta) continue;

            if (delta.reasoning_content) {
              const r = delta.reasoning_content;
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = { ...last, reasoning: (last.reasoning ?? "") + r };
                return copy;
              });
            }
            if (delta.content) {
              const c = delta.content;
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = { ...last, content: last.content + c };
                return copy;
              });
            }
            if (delta.tool_calls) {
              for (const tc of delta.tool_calls) {
                const existing = toolCallAcc.get(tc.index) ?? {
                  id: tc.id ?? `call_${tc.index}`,
                  name: "",
                  arguments: "",
                };
                if (tc.function?.name) existing.name = tc.function.name;
                if (tc.function?.arguments) existing.arguments += tc.function.arguments;
                if (tc.id) existing.id = tc.id;
                toolCallAcc.set(tc.index, existing);
              }
              const calls = Array.from(toolCallAcc.values());
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], toolCalls: calls };
                return copy;
              });
            }
          }
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        // user cancelled — keep partial state
      } else {
        setError((e as Error).message);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && last.role === "assistant") {
          copy[copy.length - 1] = { ...last, streaming: false };
        }
        return copy;
      });
    }
  }, [input, streaming, messages, authMode, apiKey]);

  function stop() {
    abortRef.current?.abort();
  }

  function clearConversation() {
    if (streaming) return;
    setMessages([]);
    setError(null);
  }

  function toggleReasoning(id: string) {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, reasoningOpen: !m.reasoningOpen } : m)),
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <span className="text-xl font-bold text-gray-900 hidden sm:block">ARBuilder</span>
            </Link>
            <span className="text-gray-300 hidden sm:block">/</span>
            <span className="text-gray-600 font-medium">Playground · Chat</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/playground" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg">
              Tools view
            </Link>
            {sessionLoading ? null : sessionUser ? (
              <span className="text-sm text-gray-500 hidden sm:block">{sessionUser.email}</span>
            ) : (
              <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">Sign In</Link>
            )}
          </div>
        </div>
      </header>

      {/* Auth strip when no session */}
      {!sessionLoading && !sessionUser && (
        <div className="bg-amber-50 border-b border-amber-100 px-4 py-2 text-center">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Paste arb_... API key to continue"
            className="text-sm border border-amber-200 rounded-lg px-3 py-1 w-80 max-w-full"
          />
        </div>
      )}
      {!sessionLoading && sessionUser && (
        <div className="bg-white border-b border-gray-100 px-4 py-2 flex items-center gap-2 justify-end max-w-5xl mx-auto w-full flex-wrap">
          <span className="text-xs text-gray-500">Auth:</span>
          <button
            onClick={() => setAuthMode("session")}
            className={`text-xs px-2 py-1 rounded ${authMode === "session" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >Session</button>
          <button
            onClick={() => setAuthMode("apikey")}
            className={`text-xs px-2 py-1 rounded ${authMode === "apikey" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >API Key</button>
          {authMode === "apikey" && userKeys.length > 0 && (
            <>
              <select
                value={selectedKeyId}
                onChange={(e) => {
                  setSelectedKeyId(e.target.value);
                  if (e.target.value !== "manual") setApiKey("");
                }}
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white"
              >
                {userKeys.map((k) => (
                  <option key={k.id} value={k.id}>{k.name || k.keyPrefix}</option>
                ))}
                <option value="manual">Enter key manually...</option>
              </select>
              {selectedKeyId === "manual" ? (
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="arb_..."
                  className="text-xs border border-gray-200 rounded px-2 py-1 w-48"
                />
              ) : (
                <span className="text-xs text-gray-400">(uses session — key shown for tracking)</span>
              )}
            </>
          )}
          {authMode === "apikey" && userKeys.length === 0 && (
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="arb_..."
              className="text-xs border border-gray-200 rounded px-2 py-1 w-48"
            />
          )}
        </div>
      )}

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6 flex flex-col gap-4">
        <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-2" style={{ minHeight: "60vh" }}>
          {messages.length === 0 && (
            <div className="text-center text-gray-400 py-20">
              <p className="text-lg">Ask anything about Stylus, Arbitrum SDK, or Orbit chains.</p>
              <p className="text-sm mt-2">The assistant has 14 tools at its disposal and will call them automatically.</p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-3xl rounded-2xl px-4 py-3 ${m.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-gray-100 shadow-sm"}`}>
                {m.role === "assistant" && m.reasoning && (
                  <button
                    onClick={() => toggleReasoning(m.id)}
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-2"
                  >
                    <span>{m.reasoningOpen ? "▾" : "▸"}</span>
                    Thinking ({m.reasoning.length} chars)
                  </button>
                )}
                {m.role === "assistant" && m.reasoningOpen && m.reasoning && (
                  <pre className="text-xs text-gray-500 whitespace-pre-wrap mb-3 bg-gray-50 rounded-lg p-2 border border-gray-100">
                    {m.reasoning}
                  </pre>
                )}
                {m.toolCalls.length > 0 && (
                  <div className="space-y-1 mb-2">
                    {m.toolCalls.map((tc) => (
                      <div key={tc.id} className="text-xs font-mono bg-gray-50 border border-gray-200 rounded px-2 py-1">
                        🔧 <span className="text-blue-700">{tc.name || "(pending)"}</span>
                        <span className="text-gray-500"> ({tc.arguments.length > 80 ? tc.arguments.slice(0, 80) + "…" : tc.arguments})</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="whitespace-pre-wrap text-sm">{m.content || (m.streaming ? "…" : "")}</div>
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-100 text-red-700 px-4 py-2 rounded-xl text-sm">
            {error}
          </div>
        )}

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-3 flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={streaming}
            placeholder="Ask about Stylus, bridging, or Orbit chains..."
            rows={2}
            className="flex-1 resize-none border-0 focus:ring-0 outline-none text-sm py-2 px-3"
          />
          <div className="flex flex-col gap-2">
            <button
              onClick={clearConversation}
              disabled={streaming || messages.length === 0}
              className="px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Clear
            </button>
            {streaming ? (
              <button
                onClick={stop}
                className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600"
              >
                Stop
              </button>
            ) : (
              <button
                onClick={send}
                disabled={!input.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Send
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
