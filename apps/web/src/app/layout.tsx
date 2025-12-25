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
  title: {
    default: "ARBuilder - AI-Powered Stylus Development",
    template: "%s | ARBuilder",
  },
  description:
    "Build Arbitrum Stylus smart contracts with AI-powered tools. Generate code, tests, and get instant answers to your development questions.",
  keywords: [
    "Arbitrum",
    "Stylus",
    "Smart Contracts",
    "Rust",
    "Web3",
    "Blockchain",
    "AI",
    "Code Generation",
  ],
  authors: [{ name: "ARBuilder Team" }],
  openGraph: {
    title: "ARBuilder - AI-Powered Stylus Development",
    description:
      "Build Arbitrum Stylus smart contracts with AI-powered tools.",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "ARBuilder - AI-Powered Stylus Development",
    description:
      "Build Arbitrum Stylus smart contracts with AI-powered tools.",
  },
  robots: {
    index: true,
    follow: true,
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
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased min-h-screen bg-white text-gray-900`}
      >
        {children}
      </body>
    </html>
  );
}
