"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";

interface PublicSource {
  id: string;
  url: string;
  sourceType: "documentation" | "github";
  category: string;
  subcategory: string;
  stylusVersion?: string;
  chunkCount: number;
  lastUpdated: string;
}

interface PublicStats {
  totalSources: number;
  totalChunks: number;
  lastSync?: string;
  byCategory: Record<string, number>;
  byType: Record<string, number>;
  byStylusVersion: Record<string, number>;
}

interface SourcesResponse {
  status: string;
  sources: PublicSource[];
  stats: PublicStats;
}

// Stylus template
interface StylusTemplate {
  type: "stylus";
  name: string;
  description: string;
  contractType: string;
  sdkVersion: string;
  features: string[];
  files?: {
    libRs: string;
    cargoToml: string;
    mainRs: string;
  };
}

// SDK template
interface SdkTemplate {
  type: "sdk";
  name: string;
  description: string;
  category: string;
  subcategory: string;
  sdkVersion: string;
  dependencies: Record<string, string>;
  envVars: string[];
  notes: string[];
  code?: string;
}

type Template = StylusTemplate | SdkTemplate;

interface TemplatesResponse {
  status: string;
  templates: Template[];
  count: number;
  stats: {
    stylus: number;
    sdk: number;
  };
}

type TabType = "sources" | "templates";
type TemplateFilterType = "all" | "stylus" | "sdk";

export default function TransparencyPage() {
  const [activeTab, setActiveTab] = useState<TabType>("sources");

  // Sources state
  const [sources, setSources] = useState<PublicSource[]>([]);
  const [stats, setStats] = useState<PublicStats | null>(null);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  // Templates state
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateStats, setTemplateStats] = useState<{ stylus: number; sdk: number } | null>(null);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null);
  const [activeFile, setActiveFile] = useState<string>("libRs");
  const [templateFilter, setTemplateFilter] = useState<TemplateFilterType>("all");

  // Filters for sources
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");

  // Fetch sources
  useEffect(() => {
    async function fetchSources() {
      setSourcesLoading(true);
      setSourcesError(null);

      try {
        const params = new URLSearchParams();
        if (categoryFilter) params.set("category", categoryFilter);
        if (typeFilter) params.set("type", typeFilter);

        const res = await fetch(`/api/public/sources?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = (await res.json()) as SourcesResponse;
        setSources(data.sources);
        setStats(data.stats);
      } catch (err) {
        setSourcesError(`Failed to load sources: ${err}`);
      } finally {
        setSourcesLoading(false);
      }
    }

    fetchSources();
  }, [categoryFilter, typeFilter]);

  // Fetch templates
  useEffect(() => {
    async function fetchTemplates() {
      setTemplatesLoading(true);
      setTemplatesError(null);

      try {
        const params = new URLSearchParams({ code: "true" });
        if (templateFilter !== "all") {
          params.set("type", templateFilter);
        }

        const res = await fetch(`/api/public/templates?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = (await res.json()) as TemplatesResponse;
        setTemplates(data.templates);
        setTemplateStats(data.stats);
      } catch (err) {
        setTemplatesError(`Failed to load templates: ${err}`);
      } finally {
        setTemplatesLoading(false);
      }
    }

    fetchTemplates();
  }, [templateFilter]);

  // Filter displayed templates
  const filteredTemplates = templates.filter((t) => {
    if (templateFilter === "all") return true;
    return t.type === templateFilter;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <span className="text-xl font-bold text-gray-900">ARBuilder</span>
            </Link>
            <nav className="flex items-center gap-4">
              <Link
                href="/playground"
                className="text-sm text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Playground
              </Link>
              <Link
                href="/"
                className="text-sm text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Home
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Page header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Transparency</h1>
          <p className="text-gray-600 mt-2 max-w-2xl mx-auto">
            View the documentation and code sources that power ARBuilder&apos;s knowledge base,
            along with the verified code templates available for generation.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex justify-center">
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1">
            <button
              onClick={() => setActiveTab("sources")}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "sources"
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Ingested Sources
            </button>
            <button
              onClick={() => setActiveTab("templates")}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "templates"
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Code Templates
            </button>
          </div>
        </div>

        {/* Sources Tab */}
        {activeTab === "sources" && (
          <div className="space-y-6">
            {/* Stats */}
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Active Sources" value={stats.totalSources} />
                <StatCard label="Total Chunks" value={stats.totalChunks} />
                <StatCard
                  label="Documentation"
                  value={stats.byType.documentation || 0}
                  color="blue"
                />
                <StatCard
                  label="GitHub Repos"
                  value={stats.byType.github || 0}
                  color="gray"
                />
              </div>
            )}

            {/* Filters */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex flex-wrap gap-4 items-end">
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
                {stats && stats.lastSync && (
                  <div className="ml-auto text-xs text-gray-500">
                    Last synced: {new Date(stats.lastSync).toLocaleDateString()}
                  </div>
                )}
              </div>
            </div>

            {/* Error */}
            {sourcesError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                {sourcesError}
              </div>
            )}

            {/* Sources Table */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {sourcesLoading ? (
                <div className="p-8 text-center text-gray-500">
                  <LoadingSpinner />
                  Loading sources...
                </div>
              ) : sources.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  No active sources found.
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
                          Version
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Chunks
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
                          </td>
                          <td className="px-4 py-3">
                            <TypeBadge type={source.sourceType} />
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm text-gray-900">
                              {formatCategory(source.category)}
                            </span>
                            {source.subcategory && (
                              <span className="text-xs text-gray-500 block">
                                {source.subcategory}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {source.stylusVersion ? (
                              <span className="text-sm text-gray-900">
                                v{source.stylusVersion}
                              </span>
                            ) : (
                              <span className="text-gray-400 text-sm">-</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {source.chunkCount.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Version Distribution */}
            {stats && Object.keys(stats.byStylusVersion).length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-lg font-semibold mb-4">By Stylus SDK Version</h2>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(stats.byStylusVersion)
                    .sort((a, b) => b[0].localeCompare(a[0]))
                    .map(([version, count]) => (
                      <div
                        key={version}
                        className="px-4 py-2 bg-gray-100 rounded-lg text-sm"
                      >
                        <span className="font-medium">v{version}</span>
                        <span className="text-gray-500 ml-2">
                          {count} source{count !== 1 ? "s" : ""}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Templates Tab */}
        {activeTab === "templates" && (
          <div className="space-y-6">
            {/* Templates Overview */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold mb-2">Code Templates</h2>
              <p className="text-gray-600 text-sm mb-4">
                Verified templates for Stylus smart contracts (Rust) and Arbitrum SDK
                bridging/messaging (TypeScript).
              </p>
              <div className="flex gap-3">
                {templateStats && (
                  <>
                    <div className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-medium">
                      {templateStats.stylus} Stylus Templates
                    </div>
                    <div className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-medium">
                      {templateStats.sdk} SDK Templates
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Template Filter */}
            <div className="flex justify-center">
              <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1">
                <button
                  onClick={() => setTemplateFilter("all")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    templateFilter === "all"
                      ? "bg-gray-900 text-white"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setTemplateFilter("stylus")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    templateFilter === "stylus"
                      ? "bg-orange-600 text-white"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  Stylus (Rust)
                </button>
                <button
                  onClick={() => setTemplateFilter("sdk")}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    templateFilter === "sdk"
                      ? "bg-purple-600 text-white"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  SDK (TypeScript)
                </button>
              </div>
            </div>

            {/* Error */}
            {templatesError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                {templatesError}
              </div>
            )}

            {/* Templates List */}
            {templatesLoading ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
                <LoadingSpinner />
                Loading templates...
              </div>
            ) : (
              <div className="space-y-4">
                {filteredTemplates.map((template) => (
                  <TemplateCard
                    key={template.name}
                    template={template}
                    expanded={expandedTemplate === template.name}
                    onToggle={() =>
                      setExpandedTemplate(
                        expandedTemplate === template.name ? null : template.name
                      )
                    }
                    activeFile={activeFile}
                    onFileChange={setActiveFile}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Footer Info */}
        <div className="text-center text-sm text-gray-500 pt-8 pb-4">
          <p>
            All data sources are carefully curated to ensure accuracy and relevance
            for Arbitrum development.
          </p>
          <p className="mt-1">
            Questions?{" "}
            <a
              href="https://github.com/Quantum3-Labs/ARBuilder/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Open an issue on GitHub
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}

// Template Card Component
function TemplateCard({
  template,
  expanded,
  onToggle,
  activeFile,
  onFileChange,
}: {
  template: Template;
  expanded: boolean;
  onToggle: () => void;
  activeFile: string;
  onFileChange: (file: string) => void;
}) {
  const isStylusTemplate = template.type === "stylus";
  const stylusTemplate = template as StylusTemplate;
  const sdkTemplate = template as SdkTemplate;

  const bgGradient = isStylusTemplate
    ? "from-orange-500 to-red-600"
    : "from-purple-500 to-indigo-600";

  const typeBadgeColor = isStylusTemplate
    ? "bg-orange-100 text-orange-700"
    : "bg-purple-100 text-purple-700";

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Template Header */}
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div
            className={`w-10 h-10 bg-gradient-to-br ${bgGradient} rounded-lg flex items-center justify-center`}
          >
            {isStylusTemplate ? (
              <TemplateTypeIcon type={stylusTemplate.contractType} />
            ) : (
              <SdkCategoryIcon category={sdkTemplate.category} />
            )}
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">{template.name}</h3>
            <p className="text-sm text-gray-600">{template.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-1 rounded text-xs font-medium ${typeBadgeColor}`}>
            {isStylusTemplate ? stylusTemplate.contractType : sdkTemplate.subcategory}
          </span>
          <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
            v{template.sdkVersion}
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-200">
          {/* Features/Notes */}
          <div className="px-6 py-4 bg-gray-50">
            <div className="flex flex-wrap gap-2">
              {isStylusTemplate
                ? stylusTemplate.features.map((feature) => (
                    <span
                      key={feature}
                      className="px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-600"
                    >
                      {feature}
                    </span>
                  ))
                : sdkTemplate.notes.map((note, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-600"
                    >
                      {note}
                    </span>
                  ))}
            </div>

            {/* SDK-specific: Dependencies and Env Vars */}
            {!isStylusTemplate && (
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
                <div>
                  <span className="font-medium">Dependencies:</span>{" "}
                  {Object.entries(sdkTemplate.dependencies)
                    .map(([k, v]) => `${k}@${v}`)
                    .join(", ")}
                </div>
                <div>
                  <span className="font-medium">Env vars:</span>{" "}
                  {sdkTemplate.envVars.join(", ")}
                </div>
              </div>
            )}
          </div>

          {/* File Tabs / Code */}
          <div className="border-t border-gray-200">
            {isStylusTemplate && stylusTemplate.files ? (
              <>
                <div className="flex border-b border-gray-200">
                  {(["libRs", "cargoToml", "mainRs"] as const).map((file) => (
                    <button
                      key={file}
                      onClick={() => onFileChange(file)}
                      className={`px-4 py-2 text-sm font-medium transition-colors ${
                        activeFile === file
                          ? "border-b-2 border-orange-600 text-orange-600"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                    >
                      {file === "libRs"
                        ? "src/lib.rs"
                        : file === "cargoToml"
                        ? "Cargo.toml"
                        : "src/main.rs"}
                    </button>
                  ))}
                </div>
                <CodeBlock
                  code={
                    stylusTemplate.files[activeFile as keyof typeof stylusTemplate.files]
                  }
                  language="rust"
                />
              </>
            ) : !isStylusTemplate && sdkTemplate.code ? (
              <CodeBlock code={sdkTemplate.code} language="typescript" />
            ) : (
              <div className="p-4 text-gray-500 text-sm">No code available</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  return (
    <div className="relative">
      <button
        onClick={() => navigator.clipboard.writeText(code)}
        className="absolute top-2 right-2 px-3 py-1 bg-gray-700 text-white text-xs rounded hover:bg-gray-600 transition-colors z-10"
      >
        Copy
      </button>
      <pre className="p-4 bg-gray-900 text-gray-100 text-sm overflow-x-auto max-h-96">
        <code className={`language-${language}`}>{code}</code>
      </pre>
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
  color?: "blue" | "green" | "yellow" | "gray";
}) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    gray: "bg-gray-100 text-gray-700",
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
      <svg
        className="w-3 h-3 mr-1"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      Docs
    </span>
  );
}

function TemplateTypeIcon({ type }: { type: string }) {
  const icons: Record<string, ReactNode> = {
    token: (
      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    utility: (
      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    defi: (
      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
  };

  return icons[type] || icons.utility;
}

function SdkCategoryIcon({ category }: { category: string }) {
  if (category === "bridging") {
    return (
      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    );
  }
  // messaging
  return (
    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 text-blue-600 mx-auto mb-2"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

function truncateUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path =
      parsed.pathname.length > 40
        ? parsed.pathname.slice(0, 40) + "..."
        : parsed.pathname;
    return parsed.host + path;
  } catch {
    return url.slice(0, 60) + "...";
  }
}

function formatCategory(category: string): string {
  const labels: Record<string, string> = {
    stylus: "Stylus",
    arbitrum_sdk: "Arbitrum SDK",
    orbit_sdk: "Orbit SDK",
    arbitrum_docs: "Arbitrum Docs",
  };
  return labels[category] || category;
}
