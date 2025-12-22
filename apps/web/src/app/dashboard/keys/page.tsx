"use client";

import { useState, useEffect } from "react";

interface ApiKey {
  id: string;
  keyPrefix: string;
  name: string | null;
  createdAt: string;
  lastUsedAt: string | null;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchKeys();
  }, []);

  async function fetchKeys() {
    try {
      const res = await fetch("/api/keys");
      const data = (await res.json()) as { keys?: ApiKey[] };
      setKeys(data.keys || []);
    } catch {
      setError("Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }

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
    } catch {
      setError("Failed to create API key");
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(id: string) {
    if (!confirm("Are you sure you want to revoke this key?")) return;

    try {
      const res = await fetch(`/api/keys/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to revoke key");
      fetchKeys();
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

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* New Key Created Modal */}
      {newKey && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              API Key Created
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Copy this key now. You won&apos;t be able to see it again!
            </p>
            <div className="bg-gray-100 p-3 rounded font-mono text-sm break-all mb-4">
              {newKey}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(newKey);
                }}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700"
              >
                Copy to Clipboard
              </button>
              <button
                onClick={() => setNewKey(null)}
                className="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded hover:bg-gray-300"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create New Key */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Create New API Key
        </h2>
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Key name (optional)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="flex-1 border border-gray-300 rounded px-3 py-2"
          />
          <button
            onClick={createKey}
            disabled={creating}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create Key"}
          </button>
        </div>
      </div>

      {/* Keys List */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Your API Keys</h2>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : keys.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No API keys yet. Create one above to get started.
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {keys.map((key) => (
              <div
                key={key.id}
                className="px-6 py-4 flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-3">
                    <code className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                      {key.keyPrefix}
                    </code>
                    {key.name && (
                      <span className="text-sm text-gray-600">{key.name}</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Created: {formatDate(key.createdAt)} • Last used:{" "}
                    {formatDate(key.lastUsedAt)}
                  </div>
                </div>
                <button
                  onClick={() => revokeKey(key.id)}
                  className="text-red-600 hover:text-red-800 text-sm"
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
