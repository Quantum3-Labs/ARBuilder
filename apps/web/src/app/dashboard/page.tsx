import { auth } from "@/auth";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await auth();

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          Welcome back
          {session?.user?.name ? `, ${session.user.name}` : ""}
        </h1>
        <p className="text-gray-600 mt-1">
          Manage your API keys and monitor usage
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        <StatCard
          title="API Keys"
          value="-"
          linkText="Manage keys"
          linkHref="/dashboard/keys"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          }
          iconBg="bg-blue-100"
          iconColor="text-blue-600"
        />
        <StatCard
          title="API Calls (30d)"
          value="-"
          linkText="View usage"
          linkHref="/dashboard/usage"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
          iconBg="bg-emerald-100"
          iconColor="text-emerald-600"
        />
        <StatCard
          title="Tokens Used (30d)"
          value="-"
          subtitle="LLM tokens consumed"
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          }
          iconBg="bg-violet-100"
          iconColor="text-violet-600"
        />
      </div>

      {/* Quick Start */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Quick Start</h2>
        </div>
        <div className="p-6">
          <div className="space-y-6">
            <QuickStartStep
              step={1}
              title="Create an API Key"
              description={
                <>
                  Go to{" "}
                  <Link href="/dashboard/keys" className="text-blue-600 hover:text-blue-700 font-medium">
                    API Keys
                  </Link>{" "}
                  and create a new key.
                </>
              }
            />
            <QuickStartStep
              step={2}
              title="Configure Your IDE"
              description="Add the following to your Cursor/Claude Desktop config:"
              code={`{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://arbbuilder.whymelabs.com/mcp",
               "--header", "Authorization: Bearer YOUR_API_KEY"]
    }
  }
}`}
            />
            <QuickStartStep
              step={3}
              title="Start Building"
              description="Ask your AI assistant to help you build Stylus contracts!"
            />
          </div>
        </div>
      </div>

      {/* Tools Overview */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Available Tools</h2>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <ToolCard
              name="get_stylus_context"
              description="Search documentation and code examples"
            />
            <ToolCard
              name="generate_stylus_code"
              description="Generate Stylus contract code"
            />
            <ToolCard
              name="ask_stylus"
              description="Answer questions about Stylus development"
            />
            <ToolCard
              name="generate_tests"
              description="Generate tests for your contracts"
            />
            <ToolCard
              name="get_workflow"
              description="Get build, deploy, and test workflows"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  linkText,
  linkHref,
  subtitle,
  icon,
  iconBg,
  iconColor,
}: {
  title: string;
  value: string;
  linkText?: string;
  linkHref?: string;
  subtitle?: string;
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
      <p className="text-3xl font-bold text-gray-900 mb-2">{value}</p>
      {linkText && linkHref && (
        <Link
          href={linkHref}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1 group"
        >
          {linkText}
          <svg className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      )}
      {subtitle && <span className="text-sm text-gray-500">{subtitle}</span>}
    </div>
  );
}

function QuickStartStep({
  step,
  title,
  description,
  code,
}: {
  step: number;
  title: string;
  description: React.ReactNode;
  code?: string;
}) {
  return (
    <div className="flex gap-4">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-semibold text-sm flex-shrink-0 shadow-md shadow-blue-600/20">
        {step}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <p className="text-gray-600 text-sm mt-1">{description}</p>
        {code && (
          <pre className="mt-3 bg-gray-900 text-gray-100 p-4 rounded-xl text-sm overflow-x-auto shadow-lg">
            <code>{code}</code>
          </pre>
        )}
      </div>
    </div>
  );
}

function ToolCard({ name, description }: { name: string; description: string }) {
  return (
    <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-gray-50 transition-colors">
      <h3 className="font-mono text-sm font-medium text-gray-900">{name}</h3>
      <p className="text-sm text-gray-600 mt-1">{description}</p>
    </div>
  );
}
