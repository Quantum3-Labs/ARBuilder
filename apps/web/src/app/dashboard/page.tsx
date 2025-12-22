import { auth } from "@/auth";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await auth();

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Welcome, {session?.user?.name || "Developer"}
      </h1>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">API Keys</h3>
          <p className="text-3xl font-bold text-gray-900">-</p>
          <Link
            href="/dashboard/keys"
            className="text-sm text-blue-600 hover:text-blue-800 mt-2 inline-block"
          >
            Manage keys →
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            API Calls (30d)
          </h3>
          <p className="text-3xl font-bold text-gray-900">-</p>
          <Link
            href="/dashboard/usage"
            className="text-sm text-blue-600 hover:text-blue-800 mt-2 inline-block"
          >
            View usage →
          </Link>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Tokens Used (30d)
          </h3>
          <p className="text-3xl font-bold text-gray-900">-</p>
          <span className="text-sm text-gray-500 mt-2 inline-block">
            LLM tokens consumed
          </span>
        </div>
      </div>

      {/* Quick Start */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Start</h2>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              1
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Create an API Key</h3>
              <p className="text-gray-600 text-sm">
                Go to{" "}
                <Link href="/dashboard/keys" className="text-blue-600">
                  API Keys
                </Link>{" "}
                and create a new key.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              2
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Configure Your IDE</h3>
              <p className="text-gray-600 text-sm">
                Add the following to your Cursor/Claude Desktop config:
              </p>
              <pre className="mt-2 bg-gray-100 p-3 rounded text-sm overflow-x-auto">
{`{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://arbbuilder.pages.dev/mcp",
               "--header", "Authorization: Bearer YOUR_API_KEY"]
    }
  }
}`}
              </pre>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold">
              3
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Start Building</h3>
              <p className="text-gray-600 text-sm">
                Ask your AI assistant to help you build Stylus contracts!
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tools Overview */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Available Tools
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-gray-100 rounded p-4">
            <h3 className="font-medium text-gray-900">get_stylus_context</h3>
            <p className="text-sm text-gray-600">
              Search documentation and code examples
            </p>
          </div>
          <div className="border border-gray-100 rounded p-4">
            <h3 className="font-medium text-gray-900">generate_stylus_code</h3>
            <p className="text-sm text-gray-600">
              Generate Stylus contract code
            </p>
          </div>
          <div className="border border-gray-100 rounded p-4">
            <h3 className="font-medium text-gray-900">ask_stylus</h3>
            <p className="text-sm text-gray-600">
              Answer questions about Stylus development
            </p>
          </div>
          <div className="border border-gray-100 rounded p-4">
            <h3 className="font-medium text-gray-900">generate_tests</h3>
            <p className="text-sm text-gray-600">
              Generate tests for your contracts
            </p>
          </div>
          <div className="border border-gray-100 rounded p-4">
            <h3 className="font-medium text-gray-900">get_workflow</h3>
            <p className="text-sm text-gray-600">
              Get build, deploy, and test workflows
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
