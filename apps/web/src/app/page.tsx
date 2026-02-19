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
              <Link
                href="/transparency"
                className="hidden sm:block text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Transparency
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
            Build on Arbitrum
            <br />
            <span className="gradient-text">with AI-Powered Tools</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            ARBuilder provides AI-powered tools for Stylus smart contracts,
            cross-chain bridging, full-stack dApp generation, and L1/L2/L3
            messaging. Connect your IDE and start building in minutes.
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
          {/* Stylus Tools */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-full text-blue-700 text-sm font-medium mb-4">
              Stylus Development
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Smart Contract Tools
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Build production-ready Stylus contracts with AI assistance
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
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

          {/* Bridging & SDK Tools */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-50 rounded-full text-purple-700 text-sm font-medium mb-4">
              Arbitrum SDK
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Cross-Chain Bridging Tools
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Generate TypeScript code for ETH/ERC20 bridging and cross-chain messaging
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                ),
                iconBg: "bg-purple-100",
                iconColor: "text-purple-600",
                title: "ETH Bridging",
                description: "Generate code for ETH deposits and withdrawals between L1 and L2.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                ),
                iconBg: "bg-pink-100",
                iconColor: "text-pink-600",
                title: "ERC20 Bridging",
                description: "Bridge ERC20 tokens with automatic approval and gateway handling.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                ),
                iconBg: "bg-cyan-100",
                iconColor: "text-cyan-600",
                title: "Cross-Chain Messaging",
                description: "L1→L2 retryable tickets and L2→L1 messages via ArbSys.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                ),
                iconBg: "bg-orange-100",
                iconColor: "text-orange-600",
                title: "L1 → L3 Bridging",
                description: "Bridge assets directly from L1 to Orbit L3 chains.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                ),
                iconBg: "bg-teal-100",
                iconColor: "text-teal-600",
                title: "Message Status",
                description: "Track retryable ticket redemption and L2→L1 message confirmation.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                ),
                iconBg: "bg-lime-100",
                iconColor: "text-lime-600",
                title: "Bridging Q&A",
                description: "Get answers about bridging patterns, timing, and best practices.",
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

          {/* Full dApp Builder Tools */}
          <div className="text-center mb-12 mt-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 rounded-full text-emerald-700 text-sm font-medium mb-4">
              Full dApp Builder
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Complete dApp Scaffolding
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Generate entire dApp stacks from a single prompt — contracts, APIs, frontends, indexers, and oracles
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                ),
                iconBg: "bg-emerald-100",
                iconColor: "text-emerald-600",
                title: "Backend Generation",
                description: "Generate NestJS or Express backends with Web3 integration, viem, and contract interaction.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                ),
                iconBg: "bg-green-100",
                iconColor: "text-green-600",
                title: "Frontend Generation",
                description: "Build Next.js + wagmi + RainbowKit frontends with DaisyUI components.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                ),
                iconBg: "bg-teal-100",
                iconColor: "text-teal-600",
                title: "Indexer Generation",
                description: "Create The Graph subgraphs for indexing ERC20, ERC721, DeFi, and custom events.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                ),
                iconBg: "bg-lime-100",
                iconColor: "text-lime-600",
                title: "Oracle Integration",
                description: "Integrate Chainlink Price Feeds, VRF, Automation, and Functions.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                ),
                iconBg: "bg-emerald-100",
                iconColor: "text-emerald-600",
                title: "Full Orchestration",
                description: "Scaffold complete dApps with monorepo structure, all components wired together.",
              },
              {
                icon: (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                ),
                iconBg: "bg-green-100",
                iconColor: "text-green-600",
                title: "ABI Auto-Extraction",
                description: "Contract ABI parsed from Stylus Rust code and injected into all components.",
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
               "https://arbuilder.app/mcp",
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
                ARBuilder - AI-powered Arbitrum development tools
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
              <Link href="/transparency" className="text-gray-500 hover:text-gray-900 transition-colors">
                Transparency
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
