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

  const toolColors: Record<string, string> = {
    context: "bg-blue-500",
    generate: "bg-emerald-500",
    ask: "bg-violet-500",
    tests: "bg-amber-500",
    workflow: "bg-rose-500",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Usage Statistics</h1>
          <p className="text-gray-600 mt-1">
            Monitor your API usage and token consumption
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all w-full sm:w-auto"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-100 text-red-700 px-4 py-3 rounded-xl flex items-center gap-3 animate-fade-in">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center">
          <div className="inline-flex items-center gap-2 text-gray-500">
            <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Loading usage data...
          </div>
        </div>
      ) : stats ? (
        <div className="space-y-6 animate-fade-in">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            <StatCard
              title="Total API Calls"
              value={stats.totalCalls.toLocaleString()}
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              }
              iconBg="bg-blue-100"
              iconColor="text-blue-600"
            />
            <StatCard
              title="Total Tokens Used"
              value={stats.totalTokens.toLocaleString()}
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              }
              iconBg="bg-emerald-100"
              iconColor="text-emerald-600"
            />
            <StatCard
              title="Avg Tokens/Call"
              value={
                stats.totalCalls > 0
                  ? Math.round(stats.totalTokens / stats.totalCalls).toLocaleString()
                  : "0"
              }
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
              }
              iconBg="bg-violet-100"
              iconColor="text-violet-600"
            />
          </div>

          {/* Usage by Tool */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">Usage by Tool</h2>
            </div>
            <div className="p-6">
              {Object.keys(stats.callsByTool).length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <p className="text-gray-500">No usage data yet</p>
                  <p className="text-sm text-gray-400 mt-1">Start using the API to see statistics</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(stats.callsByTool)
                    .sort(([, a], [, b]) => b - a)
                    .map(([tool, count]) => (
                      <div key={tool} className="flex items-center gap-4">
                        <div className="w-28 sm:w-36 text-sm text-gray-700 font-medium truncate">
                          {toolNames[tool] || tool}
                        </div>
                        <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                          <div
                            className={`${toolColors[tool] || "bg-blue-500"} rounded-full h-3 transition-all duration-500`}
                            style={{
                              width: `${(count / stats.totalCalls) * 100}%`,
                            }}
                          />
                        </div>
                        <div className="w-16 text-right text-sm font-medium text-gray-900">
                          {count}
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>

          {/* Daily Usage */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">Daily Usage</h2>
            </div>
            {stats.dailyUsage.length === 0 ? (
              <div className="p-6 text-center py-8">
                <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <p className="text-gray-500">No daily usage data yet</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="text-left py-3 px-6 font-semibold text-gray-700">
                        Date
                      </th>
                      <th className="text-right py-3 px-6 font-semibold text-gray-700">
                        API Calls
                      </th>
                      <th className="text-right py-3 px-6 font-semibold text-gray-700">
                        Tokens
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {stats.dailyUsage.map((day) => (
                      <tr key={day.date} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3 px-6 text-gray-900 font-medium">{day.date}</td>
                        <td className="py-3 px-6 text-right text-gray-600">
                          {day.calls.toLocaleString()}
                        </td>
                        <td className="py-3 px-6 text-right text-gray-600">
                          {day.tokens.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  iconBg,
  iconColor,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 card-hover">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 ${iconBg} rounded-xl flex items-center justify-center ${iconColor}`}>
          {icon}
        </div>
      </div>
      <h3 className="text-sm font-medium text-gray-500 mb-1">{title}</h3>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
