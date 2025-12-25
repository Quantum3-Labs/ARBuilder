"use client";

import { useState } from "react";
import Link from "next/link";

type Tool = "context" | "generate" | "ask" | "tests" | "workflow";

interface ToolConfig {
  name: string;
  description: string;
  endpoint: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  inputs: {
    name: string;
    label: string;
    type: "text" | "textarea" | "select";
    placeholder?: string;
    options?: { value: string; label: string }[];
    required?: boolean;
  }[];
}

const tools: Record<Tool, ToolConfig> = {
  context: {
    name: "Get Stylus Context",
    description: "Search documentation and code examples",
    endpoint: "/api/v1/tools/context",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    ),
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
    inputs: [
      {
        name: "query",
        label: "Search Query",
        type: "textarea",
        placeholder: "What are you looking for? e.g., 'How to implement ERC20 in Stylus'",
        required: true,
      },
      {
        name: "top_k",
        label: "Number of Results",
        type: "select",
        options: [
          { value: "5", label: "5 results" },
          { value: "10", label: "10 results" },
          { value: "20", label: "20 results" },
        ],
      },
    ],
  },
  generate: {
    name: "Generate Stylus Code",
    description: "Generate contract code from description",
    endpoint: "/api/v1/tools/generate",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    ),
    iconBg: "bg-emerald-100",
    iconColor: "text-emerald-600",
    inputs: [
      {
        name: "description",
        label: "Contract Description",
        type: "textarea",
        placeholder: "Describe the contract you want to generate...",
        required: true,
      },
      {
        name: "context",
        label: "Additional Context",
        type: "textarea",
        placeholder: "Additional context or requirements (optional)",
      },
    ],
  },
  ask: {
    name: "Ask Stylus",
    description: "Ask questions about Stylus development",
    endpoint: "/api/v1/tools/ask",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    iconBg: "bg-violet-100",
    iconColor: "text-violet-600",
    inputs: [
      {
        name: "question",
        label: "Your Question",
        type: "textarea",
        placeholder: "What do you want to know about Stylus?",
        required: true,
      },
    ],
  },
  tests: {
    name: "Generate Tests",
    description: "Generate tests for your contracts",
    endpoint: "/api/v1/tools/tests",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    iconBg: "bg-amber-100",
    iconColor: "text-amber-600",
    inputs: [
      {
        name: "code",
        label: "Contract Code",
        type: "textarea",
        placeholder: "Paste your Stylus contract code here...",
        required: true,
      },
      {
        name: "test_type",
        label: "Test Type",
        type: "select",
        options: [
          { value: "unit", label: "Unit Tests" },
          { value: "integration", label: "Integration Tests" },
          { value: "both", label: "Both" },
        ],
      },
    ],
  },
  workflow: {
    name: "Get Workflow",
    description: "Get step-by-step workflow guides",
    endpoint: "/api/v1/tools/workflow",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    ),
    iconBg: "bg-rose-100",
    iconColor: "text-rose-600",
    inputs: [
      {
        name: "workflow_type",
        label: "Workflow Type",
        type: "select",
        options: [
          { value: "build", label: "Build" },
          { value: "test", label: "Test" },
          { value: "deploy", label: "Deploy" },
          { value: "verify", label: "Verify" },
        ],
        required: true,
      },
      {
        name: "network",
        label: "Network",
        type: "select",
        options: [
          { value: "arbitrum_sepolia", label: "Arbitrum Sepolia (Testnet)" },
          { value: "arbitrum_one", label: "Arbitrum One (Mainnet)" },
        ],
      },
    ],
  },
};

export default function PlaygroundPage() {
  const [selectedTool, setSelectedTool] = useState<Tool>("context");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentTool = tools[selectedTool];

  function handleInputChange(name: string, value: string) {
    setInputs((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit() {
    if (!apiKey) {
      setError("Please enter your API key");
      return;
    }

    // Check required fields
    for (const input of currentTool.inputs) {
      if (input.required && !inputs[input.name]) {
        setError(`${input.label} is required`);
        return;
      }
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(currentTool.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify(inputs),
      });

      const data = (await res.json()) as { error?: string; [key: string]: unknown };

      if (!res.ok) {
        throw new Error(data.error || "Request failed");
      }

      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <span className="text-xl font-bold text-gray-900 hidden sm:block">ARBuilder</span>
            </Link>
            <span className="text-gray-300 hidden sm:block">/</span>
            <span className="text-gray-600 font-medium">Playground</span>
          </div>
          <Link
            href="/login"
            className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            Get API Key
          </Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            {/* Tool Selector */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <h2 className="font-semibold text-gray-900 mb-4 px-2">Select Tool</h2>
              <div className="space-y-1">
                {(Object.keys(tools) as Tool[]).map((tool) => (
                  <button
                    key={tool}
                    onClick={() => {
                      setSelectedTool(tool);
                      setInputs({});
                      setResult(null);
                      setError(null);
                    }}
                    className={`w-full text-left px-4 py-3 rounded-xl transition-all ${
                      selectedTool === tool
                        ? "bg-blue-50 border-2 border-blue-200"
                        : "hover:bg-gray-50 border-2 border-transparent"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-9 h-9 ${tools[tool].iconBg} rounded-lg flex items-center justify-center flex-shrink-0`}>
                        <svg className={`w-5 h-5 ${tools[tool].iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          {tools[tool].icon}
                        </svg>
                      </div>
                      <div>
                        <p className={`font-medium ${selectedTool === tool ? "text-blue-700" : "text-gray-900"}`}>
                          {tools[tool].name}
                        </p>
                        <p className="text-sm text-gray-500 mt-0.5">
                          {tools[tool].description}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* API Key Input */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <h2 className="font-semibold text-gray-900 mb-4 px-2">API Key</h2>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="arb_..."
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
              <p className="text-xs text-gray-500 mt-3 px-2">
                Get your API key from the{" "}
                <Link href="/dashboard/keys" className="text-blue-600 hover:text-blue-700">
                  dashboard
                </Link>
              </p>
            </div>
          </div>

          {/* Main Panel */}
          <div className="lg:col-span-8">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              {/* Tool Header */}
              <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-3">
                <div className={`w-10 h-10 ${currentTool.iconBg} rounded-xl flex items-center justify-center`}>
                  <svg className={`w-5 h-5 ${currentTool.iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {currentTool.icon}
                  </svg>
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900">{currentTool.name}</h2>
                  <p className="text-sm text-gray-500">{currentTool.description}</p>
                </div>
              </div>

              {/* Inputs */}
              <div className="p-6 space-y-5">
                {currentTool.inputs.map((input) => (
                  <div key={input.name}>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {input.label}
                      {input.required && (
                        <span className="text-red-500 ml-1">*</span>
                      )}
                    </label>
                    {input.type === "textarea" ? (
                      <textarea
                        value={inputs[input.name] || ""}
                        onChange={(e) => handleInputChange(input.name, e.target.value)}
                        placeholder={input.placeholder}
                        rows={4}
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none"
                      />
                    ) : input.type === "select" ? (
                      <select
                        value={inputs[input.name] || ""}
                        onChange={(e) => handleInputChange(input.name, e.target.value)}
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all bg-white"
                      >
                        <option value="">Select...</option>
                        {input.options?.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={inputs[input.name] || ""}
                        onChange={(e) => handleInputChange(input.name, e.target.value)}
                        placeholder={input.placeholder}
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      />
                    )}
                  </div>
                ))}

                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white py-3.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 hover:shadow-lg hover:shadow-blue-600/25"
                >
                  {loading ? (
                    <>
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Running...
                    </>
                  ) : (
                    <>
                      Run Tool
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    </>
                  )}
                </button>
              </div>

              {/* Error */}
              {error && (
                <div className="mx-6 mb-6 bg-red-50 border border-red-100 text-red-700 px-4 py-3 rounded-xl flex items-center gap-2 animate-fade-in">
                  <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {error}
                </div>
              )}

              {/* Result */}
              {result && (
                <div className="border-t border-gray-100 p-6 animate-fade-in">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-900">Result</h3>
                    <button
                      onClick={() => navigator.clipboard.writeText(result)}
                      className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1.5 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-x-auto text-sm max-h-96 overflow-y-auto shadow-lg">
                    <code>{result}</code>
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
