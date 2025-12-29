import Link from "next/link";
import { auth } from "@/auth";

export default async function Home() {
  const session = await auth();

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <h1 className="text-xl font-bold text-gray-900">ARBuilder</h1>
            </div>
            <div className="flex items-center gap-6">
              <Link
                href="/playground"
                className="hidden sm:block text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Playground
              </Link>
              {session?.user ? (
                <Link
                  href="/dashboard"
                  className="bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-all hover:shadow-lg hover:shadow-blue-600/25"
                >
                  Dashboard
                </Link>
              ) : (
                <Link
                  href="/login"
                  className="bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-all hover:shadow-lg hover:shadow-blue-600/25"
                >
                  Get Started
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative py-20 sm:py-28 px-4 overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-gradient-to-bl from-blue-50 via-indigo-50 to-transparent rounded-full blur-3xl opacity-70" />
          <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-purple-50 to-transparent rounded-full blur-3xl opacity-50" />
        </div>

        <div className="max-w-4xl mx-auto text-center animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full text-blue-700 text-sm font-medium mb-6">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            AI-Powered Development
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6 leading-tight">
            Build Arbitrum Stylus
            <br />
            <span className="gradient-text">Contracts with AI</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            ARBuilder provides AI-powered tools to help you write, test, and
            deploy Stylus smart contracts. Connect your IDE and start building
            in minutes.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-medium hover:bg-blue-700 transition-all hover:shadow-xl hover:shadow-blue-600/25 hover:-translate-y-0.5"
            >
              Get Free API Key
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
            <Link
              href="/playground"
              className="inline-flex items-center justify-center gap-2 bg-gray-50 text-gray-700 px-8 py-4 rounded-xl text-lg font-medium border border-gray-200 hover:bg-gray-100 hover:border-gray-300 transition-all"
            >
              Try Playground
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gray-50 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              AI-Powered Development Tools
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Everything you need to build production-ready Stylus contracts
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                ),
                iconBg: "bg-blue-100",
                iconColor: "text-blue-600",
                title: "Code Generation",
                description: "Generate production-ready Stylus contract code from natural language descriptions.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                ),
                iconBg: "bg-emerald-100",
                iconColor: "text-emerald-600",
                title: "Test Generation",
                description: "Automatically generate comprehensive test suites for your Stylus contracts.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                ),
                iconBg: "bg-violet-100",
                iconColor: "text-violet-600",
                title: "Q&A Assistant",
                description: "Get instant answers to your Stylus development questions with context from docs.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                ),
                iconBg: "bg-amber-100",
                iconColor: "text-amber-600",
                title: "Context Search",
                description: "Search through Stylus documentation and code examples with semantic understanding.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                ),
                iconBg: "bg-rose-100",
                iconColor: "text-rose-600",
                title: "Workflow Guides",
                description: "Get step-by-step guides for building, testing, and deploying your contracts.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                ),
                iconBg: "bg-indigo-100",
                iconColor: "text-indigo-600",
                title: "IDE Integration",
                description: "Works with Cursor, Claude Desktop, and any MCP-compatible editor via mcp-remote.",
              },
            ].map((feature, index) => (
              <div
                key={feature.title}
                className={`bg-white p-6 rounded-2xl border border-gray-100 shadow-sm card-hover opacity-0 animate-fade-in stagger-${index + 1}`}
              >
                <div className={`w-12 h-12 ${feature.iconBg} rounded-xl flex items-center justify-center mb-4`}>
                  <svg className={`w-6 h-6 ${feature.iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {feature.icon}
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Quick Start Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Get Started in 3 Steps
            </h2>
            <p className="text-lg text-gray-600">
              From signup to building in under 5 minutes
            </p>
          </div>
          <div className="space-y-8">
            {[
              {
                step: 1,
                title: "Sign up and get your API key",
                description: "Create a free account and generate an API key from your dashboard. No credit card required.",
              },
              {
                step: 2,
                title: "Configure your IDE",
                description: "Add this to your Cursor or Claude Desktop MCP configuration:",
                code: `{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": ["-y", "mcp-remote",
               "https://arbbuilder.whymelabs.com/mcp",
               "--header", "Authorization: Bearer YOUR_API_KEY"]
    }
  }
}`,
              },
              {
                step: 3,
                title: "Start building",
                description: "Ask your AI assistant to help you build Stylus contracts. The tools are automatically available in your IDE.",
              },
            ].map((item) => (
              <div key={item.step} className="flex gap-6 items-start">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold flex-shrink-0 shadow-lg shadow-blue-600/25">
                  {item.step}
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600 mb-4">
                    {item.description}
                  </p>
                  {item.code && (
                    <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-x-auto text-sm shadow-xl">
                      <code>{item.code}</code>
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Free Tier Section */}
      <section className="py-20 bg-gradient-to-br from-blue-600 to-indigo-700 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Free to Start
          </h2>
          <p className="text-xl text-blue-100 mb-10 max-w-2xl mx-auto">
            Our free tier includes everything you need to get started with
            Stylus development.
          </p>
          <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
              {[
                { value: "100", label: "API calls/day" },
                { value: "50", label: "Context searches" },
                { value: "20", label: "Code generations" },
                { value: "30", label: "Q&A queries" },
              ].map((stat) => (
                <div key={stat.label}>
                  <p className="text-4xl font-bold text-white">{stat.value}</p>
                  <p className="text-blue-200 text-sm mt-1">{stat.label}</p>
                </div>
              ))}
            </div>
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-xl font-semibold hover:bg-blue-50 transition-all hover:shadow-xl"
            >
              Get Started Free
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-gray-100 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <span className="text-gray-600">
                ARBuilder - AI-powered Stylus development tools
              </span>
            </div>
            <div className="flex gap-8">
              <a
                href="https://github.com/Quantum3-Labs/ARBuilder"
                className="text-gray-500 hover:text-gray-900 transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
              <Link href="/playground" className="text-gray-500 hover:text-gray-900 transition-colors">
                Playground
              </Link>
              <Link href="/dashboard" className="text-gray-500 hover:text-gray-900 transition-colors">
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
