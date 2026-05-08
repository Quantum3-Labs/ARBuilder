"use client";

import { useState, useEffect, useCallback } from "react";

interface ApiKey {
  id: string;
  keyPrefix: string;
  name: string | null;
  createdAt: string;
  lastUsedAt: string | null;
  rateLimitTier?: string;
  /** Raw JSON string from API; parsed in render. */
  allowedOrigins?: string | null;
}

interface WindowState {
  limit: number;
  remaining: number;
  used: number;
  resetSeconds: number;
}

interface KeyUsage {
  tier: string;
  limits: { perMinute: number; perDay: number };
  chat: { minute: WindowState; day: WindowState };
  tool: { minute: WindowState; day: WindowState };
  recent: { calls24h: number; lastCallAt: string | null; successRate: number | null };
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [usage, setUsage] = useState<Record<string, KeyUsage>>({});
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetch("/api/keys");
      const data = (await res.json()) as { keys?: ApiKey[] };
      setKeys(data.keys || []);
    } catch {
      setError("Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUsage = useCallback(async () => {
    try {
      const res = await fetch("/api/keys/usage");
      if (!res.ok) return;
      const data = (await res.json()) as { usage: Record<string, KeyUsage> };
      setUsage(data.usage || {});
    } catch {
      // Non-fatal — widget just won't render until next poll succeeds.
    }
  }, []);

  useEffect(() => {
    fetchKeys();
    fetchUsage();
    const id = setInterval(fetchUsage, 15_000);
    return () => clearInterval(id);
  }, [fetchKeys, fetchUsage]);

  async function createKey() {
    setCreating(true);
    setError(null);

    try {
      const res = await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName || undefined }),
      });

      if (!res.ok) throw new Error("Failed to create key");

      const data = (await res.json()) as { key: string };
      setNewKey(data.key);
      setNewKeyName("");
      fetchKeys();
      fetchUsage();
    } catch {
      setError("Failed to create API key");
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(id: string) {
    if (!confirm("Are you sure you want to revoke this key? This action cannot be undone.")) return;

    try {
      const res = await fetch(`/api/keys/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to revoke key");
      fetchKeys();
      fetchUsage();
    } catch {
      setError("Failed to revoke API key");
    }
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  async function copyToClipboard() {
    if (newKey) {
      await navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">API Keys</h1>
        <p className="text-gray-600 mt-1">
          Create and manage your API keys for accessing ARBuilder tools
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-100 text-red-700 px-4 py-3 rounded-xl flex items-center gap-3 animate-fade-in">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* New Key Created Modal */}
      {newKey && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl animate-fade-in-up">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-900">
                API Key Created
              </h2>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Copy this key now. You won&apos;t be able to see it again!
            </p>
            <div className="bg-gray-900 text-gray-100 p-4 rounded-xl font-mono text-sm break-all mb-4 relative group">
              {newKey}
              <button
                onClick={copyToClipboard}
                className="absolute top-2 right-2 p-2 bg-gray-800 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-700"
              >
                {copied ? (
                  <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                )}
              </button>
            </div>
            <div className="flex gap-3">
              <button
                onClick={copyToClipboard}
                className="flex-1 bg-blue-600 text-white py-2.5 px-4 rounded-xl font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
              >
                {copied ? (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                    Copy to Clipboard
                  </>
                )}
              </button>
              <button
                onClick={() => setNewKey(null)}
                className="flex-1 bg-gray-100 text-gray-800 py-2.5 px-4 rounded-xl font-medium hover:bg-gray-200 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create New Key */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Create New API Key
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Key name (optional)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
          />
          <button
            onClick={createKey}
            disabled={creating}
            className="bg-blue-600 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 whitespace-nowrap"
          >
            {creating ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Creating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create Key
              </>
            )}
          </button>
        </div>
      </div>

      {/* Keys List */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Your API Keys</h2>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-flex items-center gap-2 text-gray-500">
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Loading...
            </div>
          </div>
        ) : keys.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <p className="text-gray-500">No API keys yet</p>
            <p className="text-sm text-gray-400 mt-1">Create one above to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {keys.map((key, index) => (
              <div
                key={key.id}
                className={`px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-gray-50 transition-colors animate-fade-in stagger-${index + 1}`}
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="font-mono text-sm bg-gray-100 px-3 py-1 rounded-lg text-gray-700">
                      {key.keyPrefix}
                    </code>
                    {key.name && (
                      <span className="text-sm font-medium text-gray-700">{key.name}</span>
                    )}
                    {key.rateLimitTier && (
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          key.rateLimitTier === "unlimited"
                            ? "bg-purple-50 text-purple-700"
                            : key.rateLimitTier === "pro"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-gray-100 text-gray-600"
                        }`}
                        title="Daily rate-limit tier — contact support to upgrade"
                      >
                        {key.rateLimitTier}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
                    <span>Created: {formatDate(key.createdAt)}</span>
                    <span>Last used: {formatDate(key.lastUsedAt)}</span>
                  </div>
                  {usage[key.id] && <UsageWidget u={usage[key.id]} />}
                  <OriginsEditor
                    keyId={key.id}
                    raw={key.allowedOrigins}
                    onSaved={fetchKeys}
                  />
                </div>
                <button
                  onClick={() => revokeKey(key.id)}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors flex-shrink-0 self-start"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UsageWidget({ u }: { u: KeyUsage }) {
  return (
    <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
      <UsageBars label="Chat" cat={u.chat} />
      <UsageBars label="Tool" cat={u.tool} />
      <div className="sm:col-span-2 text-gray-500 mt-1">
        24h: {u.recent.calls24h} call{u.recent.calls24h === 1 ? "" : "s"}
        {u.recent.successRate !== null && (
          <> · {Math.round(u.recent.successRate * 100)}% success</>
        )}
      </div>
    </div>
  );
}

function UsageBars({
  label,
  cat,
}: {
  label: string;
  cat: { minute: WindowState; day: WindowState };
}) {
  return (
    <div className="border border-gray-100 rounded-lg p-2 bg-gray-50">
      <div className="font-medium text-gray-700 mb-1">{label}</div>
      <Bar window="min" used={cat.minute.used} limit={cat.minute.limit} />
      <Bar window="day" used={cat.day.used} limit={cat.day.limit} />
    </div>
  );
}

function Bar({ window: w, used, limit }: { window: "min" | "day"; used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const color = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2 mt-0.5">
      <span className="w-8 text-gray-400">{w === "min" ? "/min" : "/day"}</span>
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 text-right tabular-nums text-gray-600">
        {used} / {limit}
      </span>
    </div>
  );
}

function parseOrigins(raw: string | null | undefined): string[] | null {
  if (raw == null) return null;
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.filter((s) => typeof s === "string") : null;
  } catch {
    return null;
  }
}

function OriginsEditor({
  keyId,
  raw,
  onSaved,
}: {
  keyId: string;
  raw: string | null | undefined;
  onSaved: () => void;
}) {
  const initial = parseOrigins(raw);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState((initial ?? []).join("\n"));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const restricted = initial !== null;
  const origins = initial ?? [];

  async function save(allowedOrigins: string[] | null) {
    setSaving(true);
    setErr(null);
    try {
      const res = await fetch(`/api/keys/${keyId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ allowedOrigins }),
      });
      const data = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      setEditing(false);
      onSaved();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <div className="mt-3 text-xs flex flex-wrap items-center gap-2">
        <span className="font-medium text-gray-600">Allowed origins:</span>
        {!restricted ? (
          <span className="text-gray-500 italic">Unrestricted (server-to-server only)</span>
        ) : origins.length === 0 ? (
          <span className="text-orange-600">Locked — no browser may use this key</span>
        ) : (
          origins.map((o) => (
            <code key={o} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded font-mono">
              {o}
            </code>
          ))
        )}
        <button
          onClick={() => {
            setText((initial ?? []).join("\n"));
            setEditing(true);
          }}
          className="text-blue-600 hover:text-blue-700 underline"
        >
          Edit
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3 text-xs space-y-2">
      <div className="font-medium text-gray-600">Allowed origins (one per line, or `*` for any):</div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        placeholder="https://docs.example.com&#10;https://example.com"
        className="w-full px-2 py-1.5 text-xs font-mono border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
      />
      <p className="text-gray-500">
        Empty list = locked (no browser allowed). Use{" "}
        <button
          type="button"
          onClick={() => save(null)}
          className="underline text-blue-600 hover:text-blue-700"
          disabled={saving}
        >
          unrestricted
        </button>{" "}
        for server-to-server keys (default). CORS allowlist applies only to browser requests; server callers without an Origin header are never blocked.
      </p>
      {err && <p className="text-red-600">{err}</p>}
      <div className="flex gap-2">
        <button
          onClick={() => {
            const list = text
              .split(/\s+/)
              .map((s) => s.trim())
              .filter(Boolean);
            save(list);
          }}
          disabled={saving}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={() => {
            setEditing(false);
            setErr(null);
          }}
          disabled={saving}
          className="px-3 py-1 border border-gray-200 rounded hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
