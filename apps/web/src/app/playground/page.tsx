"use client";

import { useState } from "react";
import Link from "next/link";

type Tool = "context" | "generate" | "ask" | "tests" | "workflow";

interface ToolConfig {
  name: string;
  description: string;
  endpoint: string;
  inputs: {
    name: string;
    type: "text" | "textarea" | "select";
    placeholder?: string;
    options?: { value: string; label: string }[];
    required?: boolean;
  }[];
}

const tools: Record<Tool, ToolConfig> = {
  context: {
    name: "Get Stylus Context",
    description: "Search documentation and code examples for relevant context",
    endpoint: "/api/v1/tools/context",
    inputs: [
      {
        name: "query",
        type: "textarea",
        placeholder: "What are you looking for? e.g., 'How to implement ERC20 in Stylus'",
        required: true,
      },
      {
        name: "top_k",
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
    description: "Generate Stylus contract code from a description",
    endpoint: "/api/v1/tools/generate",
    inputs: [
      {
        name: "description",
        type: "textarea",
        placeholder: "Describe the contract you want to generate...",
        required: true,
      },
      {
        name: "context",
        type: "textarea",
        placeholder: "Additional context or requirements (optional)",
      },
    ],
  },
  ask: {
    name: "Ask Stylus",
    description: "Ask questions about Stylus development",
    endpoint: "/api/v1/tools/ask",
    inputs: [
      {
        name: "question",
        type: "textarea",
        placeholder: "What do you want to know about Stylus?",
        required: true,
      },
    ],
  },
  tests: {
    name: "Generate Tests",
    description: "Generate tests for your Stylus contracts",
    endpoint: "/api/v1/tools/tests",
    inputs: [
      {
        name: "code",
        type: "textarea",
        placeholder: "Paste your Stylus contract code here...",
        required: true,
      },
      {
        name: "test_type",
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
    inputs: [
      {
        name: "workflow_type",
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
        setError(`${input.name} is required`);
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
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold text-gray-900">
              ARBuilder
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-gray-600">Playground</span>
          </div>
          <Link
            href="/login"
            className="text-blue-600 hover:text-blue-800"
          >
            Get API Key
          </Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Tool Selector */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-4">Select Tool</h2>
              <div className="space-y-2">
                {(Object.keys(tools) as Tool[]).map((tool) => (
                  <button
                    key={tool}
                    onClick={() => {
                      setSelectedTool(tool);
                      setInputs({});
                      setResult(null);
                      setError(null);
                    }}
                    className={`w-full text-left px-4 py-3 rounded-lg transition ${
                      selectedTool === tool
                        ? "bg-blue-50 border border-blue-200 text-blue-700"
                        : "hover:bg-gray-50 border border-transparent"
                    }`}
                  >
                    <p className="font-medium">{tools[tool].name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      {tools[tool].description}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* API Key Input */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 mt-4">
              <h2 className="font-semibold text-gray-900 mb-4">API Key</h2>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="arb_..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
              <p className="text-xs text-gray-500 mt-2">
                Get your API key from the{" "}
                <Link href="/dashboard/keys" className="text-blue-600">
                  dashboard
                </Link>
              </p>
            </div>
          </div>

          {/* Input Panel */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="font-semibold text-gray-900 mb-4">
                {currentTool.name}
              </h2>

              <div className="space-y-4">
                {currentTool.inputs.map((input) => (
                  <div key={input.name}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {input.name}
                      {input.required && (
                        <span className="text-red-500 ml-1">*</span>
                      )}
                    </label>
                    {input.type === "textarea" ? (
                      <textarea
                        value={inputs[input.name] || ""}
                        onChange={(e) =>
                          handleInputChange(input.name, e.target.value)
                        }
                        placeholder={input.placeholder}
                        rows={4}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      />
                    ) : input.type === "select" ? (
                      <select
                        value={inputs[input.name] || ""}
                        onChange={(e) =>
                          handleInputChange(input.name, e.target.value)
                        }
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
                        onChange={(e) =>
                          handleInputChange(input.name, e.target.value)
                        }
                        placeholder={input.placeholder}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      />
                    )}
                  </div>
                ))}

                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? "Running..." : "Run Tool"}
                </button>
              </div>

              {/* Error */}
              {error && (
                <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                  {error}
                </div>
              )}

              {/* Result */}
              {result && (
                <div className="mt-4">
                  <h3 className="font-medium text-gray-900 mb-2">Result</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm max-h-96 overflow-y-auto">
                    {result}
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
