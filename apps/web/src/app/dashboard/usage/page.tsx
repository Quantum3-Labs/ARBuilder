"use client";

import { useState, useEffect } from "react";

interface UsageStats {
  totalCalls: number;
  totalTokens: number;
  callsByTool: Record<string, number>;
  dailyUsage: Array<{ date: string; calls: number; tokens: number }>;
}

export default function UsagePage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadStats() {
      setLoading(true);
      try {
        const res = await fetch(`/api/usage?days=${days}`);
        const data = (await res.json()) as UsageStats;
        setStats(data);
      } catch {
        setError("Failed to load usage stats");
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, [days]);


  const toolNames: Record<string, string> = {
    context: "Get Context",
    generate: "Generate Code",
    ask: "Ask Stylus",
    tests: "Generate Tests",
    workflow: "Get Workflow",
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Usage Statistics</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="border border-gray-300 rounded px-3 py-2"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : stats ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Total API Calls
              </h3>
              <p className="text-3xl font-bold text-gray-900">
                {stats.totalCalls.toLocaleString()}
              </p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Total Tokens Used
              </h3>
              <p className="text-3xl font-bold text-gray-900">
                {stats.totalTokens.toLocaleString()}
              </p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Avg Tokens/Call
              </h3>
              <p className="text-3xl font-bold text-gray-900">
                {stats.totalCalls > 0
                  ? Math.round(stats.totalTokens / stats.totalCalls).toLocaleString()
                  : 0}
              </p>
            </div>
          </div>

          {/* Usage by Tool */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Usage by Tool
            </h2>
            {Object.keys(stats.callsByTool).length === 0 ? (
              <p className="text-gray-500">No usage data yet</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(stats.callsByTool)
                  .sort(([, a], [, b]) => b - a)
                  .map(([tool, count]) => (
                    <div key={tool} className="flex items-center gap-4">
                      <div className="w-32 text-sm text-gray-600">
                        {toolNames[tool] || tool}
                      </div>
                      <div className="flex-1 bg-gray-100 rounded-full h-4">
                        <div
                          className="bg-blue-600 rounded-full h-4"
                          style={{
                            width: `${(count / stats.totalCalls) * 100}%`,
                          }}
                        />
                      </div>
                      <div className="w-16 text-right text-sm text-gray-600">
                        {count}
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Daily Usage */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Daily Usage
            </h2>
            {stats.dailyUsage.length === 0 ? (
              <p className="text-gray-500">No usage data yet</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-2 px-3 font-medium text-gray-600">
                        Date
                      </th>
                      <th className="text-right py-2 px-3 font-medium text-gray-600">
                        API Calls
                      </th>
                      <th className="text-right py-2 px-3 font-medium text-gray-600">
                        Tokens
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.dailyUsage.map((day) => (
                      <tr key={day.date} className="border-b border-gray-100">
                        <td className="py-2 px-3 text-gray-900">{day.date}</td>
                        <td className="py-2 px-3 text-right text-gray-600">
                          {day.calls.toLocaleString()}
                        </td>
                        <td className="py-2 px-3 text-right text-gray-600">
                          {day.tokens.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
