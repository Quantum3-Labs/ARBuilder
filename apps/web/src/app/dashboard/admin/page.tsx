"use client";

import { useEffect, useState, useCallback } from "react";

interface Source {
  id: string;
  url: string;
  sourceType: "documentation" | "github";
  category: string;
  subcategory: string;
  stylusVersion?: string;
  isVersionDeprecated?: boolean;
  status: "active" | "pending" | "error" | "removed";
  chunkCount: number;
  lastScraped?: string;
  lastError?: string;
  errorCount: number;
  createdAt: string;
  updatedAt: string;
}

interface Stats {
  totalSources: number;
  totalChunks: number;
  lastSync?: string;
  byCategory: Record<string, number>;
  byStatus: Record<string, number>;
  byType: Record<string, number>;
  byStylusVersion: Record<string, number>;
  deprecatedCount: number;
}

interface SourcesResponse {
  status: string;
  sources: Source[];
  stats: Stats;
}

export default function AdminPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adminSecret, setAdminSecret] = useState("");
  const [isAuthed, setIsAuthed] = useState(false);

  // View tabs
  const [view, setView] = useState<"sources" | "rateLimits">("sources");

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");

  // Add source form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newCategory, setNewCategory] = useState("stylus");
  const [newSubcategory, setNewSubcategory] = useState("");
  const [addingSource, setAddingSource] = useState(false);

  const fetchSources = useCallback(async () => {
    if (!adminSecret) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (categoryFilter) params.set("category", categoryFilter);
      if (statusFilter) params.set("status", statusFilter);
      if (typeFilter) params.set("type", typeFilter);

      const res = await fetch(`/api/admin/sources?${params.toString()}`, {
        headers: { "X-Admin-Secret": adminSecret },
      });

      if (!res.ok) {
        if (res.status === 401) {
          setIsAuthed(false);
          setError("Invalid admin secret");
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }

      const data = (await res.json()) as SourcesResponse;
      setSources(data.sources);
      setStats(data.stats);
      setIsAuthed(true);
    } catch (err) {
      setError(`Failed to fetch sources: ${err}`);
    } finally {
      setLoading(false);
    }
  }, [adminSecret, categoryFilter, statusFilter, typeFilter]);

  useEffect(() => {
    if (isAuthed) {
      fetchSources();
    }
  }, [isAuthed, fetchSources]);

  const handleAuth = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminSecret) {
      fetchSources();
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl || !newCategory) return;

    setAddingSource(true);
    try {
      const res = await fetch("/api/admin/sources", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Secret": adminSecret,
        },
        body: JSON.stringify({
          url: newUrl,
          category: newCategory,
          subcategory: newSubcategory,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      setNewUrl("");
      setNewSubcategory("");
      setShowAddForm(false);
      fetchSources();
    } catch (err) {
      setError(`Failed to add source: ${err}`);
    } finally {
      setAddingSource(false);
    }
  };

  const handleDeleteSource = async (source: Source) => {
    if (!confirm(`Delete source?\n${source.url}`)) return;

    try {
      const res = await fetch("/api/admin/sources", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Secret": adminSecret,
        },
        body: JSON.stringify({ id: source.id }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      fetchSources();
    } catch (err) {
      setError(`Failed to delete source: ${err}`);
    }
  };

  // Auth form
  if (!isAuthed) {
    return (
      <div className="max-w-md mx-auto mt-20">
        <h1 className="text-2xl font-bold mb-6">Admin Access</h1>
        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin Secret
            </label>
            <input
              type="password"
              value={adminSecret}
              onChange={(e) => setAdminSecret(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter AUTH_SECRET"
            />
          </div>
          {error && (
            <p className="text-red-600 text-sm">{error}</p>
          )}
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Access Admin
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setView("sources")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
            view === "sources"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          RAG Sources
        </button>
        <button
          onClick={() => setView("rateLimits")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
            view === "rateLimits"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Rate Limits
        </button>
      </div>

      {view === "rateLimits" ? (
        <RateLimitsPanel adminSecret={adminSecret} />
      ) : (
      <>
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">RAG Sources</h1>
          <p className="text-gray-600 mt-1">
            Manage documentation and code sources for the knowledge base
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Source
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Sources" value={stats.totalSources} />
          <StatCard label="Total Chunks" value={stats.totalChunks} />
          <StatCard
            label="Active"
            value={stats.byStatus.active || 0}
            color="green"
          />
          <StatCard
            label="Pending"
            value={stats.byStatus.pending || 0}
            color="yellow"
          />
        </div>
      )}

      {/* Add Source Form */}
      {showAddForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Add New Source</h2>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  URL *
                </label>
                <input
                  type="url"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="https://docs.arbitrum.io/..."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category *
                </label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="stylus">Stylus</option>
                  <option value="arbitrum_sdk">Arbitrum SDK</option>
                  <option value="orbit_sdk">Orbit SDK</option>
                  <option value="arbitrum_docs">Arbitrum Docs</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subcategory
                </label>
                <input
                  type="text"
                  value={newSubcategory}
                  onChange={(e) => setNewSubcategory(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="official_docs, examples, etc."
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={addingSource}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {addingSource ? "Adding..." : "Add Source"}
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="text-gray-600 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Category
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Categories</option>
              <option value="stylus">Stylus</option>
              <option value="arbitrum_sdk">Arbitrum SDK</option>
              <option value="orbit_sdk">Orbit SDK</option>
              <option value="arbitrum_docs">Arbitrum Docs</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="pending">Pending</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Type
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="">All Types</option>
              <option value="documentation">Documentation</option>
              <option value="github">GitHub</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={fetchSources}
              className="px-4 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Sources Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : sources.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No sources found. Add some using the button above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Chunks
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sources.map((source) => (
                  <tr key={source.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-sm max-w-xs truncate block"
                        title={source.url}
                      >
                        {truncateUrl(source.url)}
                      </a>
                      <span className="text-xs text-gray-400">{source.id}</span>
                    </td>
                    <td className="px-4 py-3">
                      <TypeBadge type={source.sourceType} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">{source.category}</span>
                      {source.subcategory && (
                        <span className="text-xs text-gray-500 block">
                          {source.subcategory}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={source.status} />
                      {source.lastError && (
                        <span
                          className="text-xs text-red-500 block truncate max-w-[150px]"
                          title={source.lastError}
                        >
                          {source.lastError}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {source.stylusVersion ? (
                        <span
                          className={`text-sm ${source.isVersionDeprecated ? "text-orange-600" : "text-gray-900"}`}
                        >
                          v{source.stylusVersion}
                          {source.isVersionDeprecated && " (deprecated)"}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {source.chunkCount}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDeleteSource(source)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Version Stats */}
      {stats && Object.keys(stats.byStylusVersion).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">By Stylus Version</h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.byStylusVersion)
              .sort((a, b) => b[0].localeCompare(a[0]))
              .map(([version, count]) => (
                <div
                  key={version}
                  className="px-4 py-2 bg-gray-100 rounded-lg text-sm"
                >
                  <span className="font-medium">v{version}</span>
                  <span className="text-gray-500 ml-2">{count} sources</span>
                </div>
              ))}
          </div>
          {stats.deprecatedCount > 0 && (
            <p className="mt-4 text-orange-600 text-sm">
              {stats.deprecatedCount} source(s) use deprecated SDK versions
            </p>
          )}
        </div>
      )}
      </>
      )}
    </div>
  );
}

interface RateLimitKey {
  id: string;
  userId: string;
  userEmail: string | null;
  keyPrefix: string;
  name: string | null;
  tier: string;
  limits: { chat: number; tool: number };
  createdAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
  calls24h: number;
}

function RateLimitsPanel({ adminSecret }: { adminSecret: string }) {
  const [keys, setKeys] = useState<RateLimitKey[]>([]);
  const [tiers, setTiers] = useState<string[]>(["free", "pro", "unlimited"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("");

  const load = useCallback(async () => {
    if (!adminSecret) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/rate-limits", {
        headers: { "X-Admin-Secret": adminSecret },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { tiers: string[]; keys: RateLimitKey[] };
      setKeys(data.keys);
      setTiers(data.tiers);
    } catch (e) {
      setError(`Failed to load: ${e}`);
    } finally {
      setLoading(false);
    }
  }, [adminSecret]);

  useEffect(() => {
    load();
  }, [load]);

  const updateTier = async (keyId: string, tier: string) => {
    setSavingId(keyId);
    try {
      const res = await fetch("/api/admin/rate-limits", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Secret": adminSecret,
        },
        body: JSON.stringify({ keyId, tier }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { limits: { chat: number; tool: number } };
      setKeys((prev) =>
        prev.map((k) => (k.id === keyId ? { ...k, tier, limits: data.limits } : k)),
      );
    } catch (e) {
      setError(`Update failed: ${e}`);
    } finally {
      setSavingId(null);
    }
  };

  const filtered = keys.filter((k) => {
    if (tierFilter && k.tier !== tierFilter) return false;
    if (!filter) return true;
    const f = filter.toLowerCase();
    return (
      (k.userEmail ?? "").toLowerCase().includes(f) ||
      (k.name ?? "").toLowerCase().includes(f) ||
      k.keyPrefix.toLowerCase().includes(f) ||
      k.id.toLowerCase().includes(f)
    );
  });

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rate Limit Tiers</h1>
          <p className="text-gray-600 mt-1 text-sm">
            Per-key daily quotas. Tiers:{" "}
            <span className="font-mono">free</span> = 30 chat / 100 tool,{" "}
            <span className="font-mono">pro</span> = 300 / 1000,{" "}
            <span className="font-mono">unlimited</span> = 10K / 10K. Counters reset at UTC midnight.
          </p>
        </div>
        <button
          onClick={load}
          className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          Refresh
        </button>
      </div>

      <div className="flex gap-2">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by email, name, prefix, or id..."
          className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg"
        />
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"
        >
          <option value="">All tiers</option>
          {tiers.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {error && <div className="bg-red-50 border border-red-100 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
              <tr>
                <th className="px-4 py-2 text-left">User / Key</th>
                <th className="px-4 py-2 text-left">Prefix</th>
                <th className="px-4 py-2 text-left">Tier</th>
                <th className="px-4 py-2 text-right">24h Calls</th>
                <th className="px-4 py-2 text-left">Last Used</th>
                <th className="px-4 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((k) => (
                <tr key={k.id} className="border-t border-gray-100">
                  <td className="px-4 py-2">
                    <div className="font-medium text-gray-900">{k.userEmail || k.userId}</div>
                    <div className="text-xs text-gray-500">{k.name || "(unnamed key)"}</div>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">{k.keyPrefix}…</td>
                  <td className="px-4 py-2">
                    <select
                      value={k.tier}
                      onChange={(e) => updateTier(k.id, e.target.value)}
                      disabled={savingId === k.id || !!k.revokedAt}
                      className="text-xs border border-gray-200 rounded px-2 py-1 bg-white disabled:opacity-50"
                    >
                      {tiers.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-xs">{k.calls24h}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">
                    {k.lastUsedAt ? new Date(k.lastUsedAt).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    {k.revokedAt ? (
                      <span className="text-xs text-red-600">revoked</span>
                    ) : (
                      <span className="text-xs text-green-600">active</span>
                    )}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-400 text-sm">
                    No keys match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  color = "blue",
}: {
  label: string;
  value: number;
  color?: "blue" | "green" | "yellow";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
  };

  return (
    <div className={`rounded-xl p-4 ${colors[color]}`}>
      <div className="text-2xl font-bold">{value.toLocaleString()}</div>
      <div className="text-sm opacity-80">{label}</div>
    </div>
  );
}

function TypeBadge({ type }: { type: "documentation" | "github" }) {
  if (type === "github") {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        <svg className="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
        </svg>
        GitHub
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      Docs
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    pending: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
    removed: "bg-gray-100 text-gray-800",
  };

  return (
    <span
      className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}
    >
      {status}
    </span>
  );
}

function truncateUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.length > 30
      ? parsed.pathname.slice(0, 30) + "..."
      : parsed.pathname;
    return parsed.host + path;
  } catch {
    return url.slice(0, 50) + "...";
  }
}
