import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://arbuilder.app"),
  title: {
    default: "ARBuilder - Accelerate Smart Contract Development on Arbitrum",
    template: "%s | ARBuilder",
  },
  description:
    "Ship smart contracts and dApps faster with 19 AI-powered MCP tools for Arbitrum. Stylus contracts, cross-chain bridging, full-stack scaffolding, and Orbit L3 deployment — inside Cursor, Claude Code, and VS Code.",
  keywords: [
    "Arbitrum",
    "Stylus",
    "Smart Contracts",
    "Rust",
    "Web3",
    "Blockchain",
    "AI",
    "Code Generation",
    "MCP",
    "Model Context Protocol",
    "Orbit",
    "L3",
    "Cross-Chain",
    "Bridging",
    "dApp",
    "Cursor",
    "Claude Code",
    "WASM",
  ],
  authors: [{ name: "Quantum3 Labs" }],
  openGraph: {
    title: "ARBuilder - Accelerate Smart Contract Development on Arbitrum",
    description:
      "Ship smart contracts and dApps faster with 19 AI-powered MCP tools. Stylus contracts, bridging, full-stack scaffolding, and Orbit L3 deployment. Free to start.",
    type: "website",
    locale: "en_US",
    url: "https://arbuilder.app",
    siteName: "ARBuilder",
  },
  twitter: {
    card: "summary_large_image",
    title: "ARBuilder - Accelerate Smart Contract Development on Arbitrum",
    description:
      "Ship smart contracts and dApps faster with 19 AI-powered MCP tools. Stylus contracts, bridging, full-stack scaffolding, and Orbit L3 deployment.",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
  alternates: {
    canonical: "https://arbuilder.app",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#2563eb",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "ARBuilder",
              description:
                "Accelerate smart contract and dApp development on Arbitrum. 19 AI-powered MCP tools for Stylus contracts, cross-chain bridging, full-stack scaffolding, and Orbit L3 chain deployment.",
              url: "https://arbuilder.app",
              applicationCategory: "DeveloperApplication",
              operatingSystem: "Cross-platform",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "USD",
              },
              author: {
                "@type": "Organization",
                name: "Quantum3 Labs",
                url: "https://github.com/Quantum3-Labs",
              },
            }),
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased min-h-screen bg-white text-gray-900`}
      >
        {children}
      </body>
    </html>
  );
}
