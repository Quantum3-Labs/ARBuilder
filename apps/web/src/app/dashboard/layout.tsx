"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface User {
  id: string;
  email: string;
  name?: string | null;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    async function checkSession() {
      try {
        const res = await fetch("/api/auth/session");
        const data = (await res.json()) as { user: User | null; refreshed?: boolean };

        if (!data.user) {
          router.push("/login");
          return;
        }

        setUser(data.user);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }

    checkSession();

    // Refresh session every 10 minutes to keep tokens fresh
    const refreshInterval = setInterval(checkSession, 10 * 60 * 1000);

    return () => clearInterval(refreshInterval);
  }, [router]);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.push("/login");
    } catch {
      setSigningOut(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="inline-flex items-center gap-2 text-gray-500">
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading...
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-8">
              <Link href="/" className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">AR</span>
                </div>
                <span className="text-xl font-bold text-gray-900 hidden sm:block">
                  ARBuilder
                </span>
              </Link>
              <nav className="hidden md:flex gap-1">
                <NavLink href="/dashboard">Overview</NavLink>
                <NavLink href="/dashboard/keys">API Keys</NavLink>
                <NavLink href="/dashboard/usage">Usage</NavLink>
                <NavLink href="/playground">Playground</NavLink>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <span className="hidden sm:block text-sm text-gray-600 max-w-[200px] truncate">
                {user.email}
              </span>
              <button
                onClick={handleSignOut}
                disabled={signingOut}
                className="text-sm text-gray-500 hover:text-gray-900 font-medium transition-colors px-3 py-2 rounded-lg hover:bg-gray-100 disabled:opacity-50"
              >
                {signingOut ? "Signing out..." : "Sign out"}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-gray-100">
          <div className="px-4 py-2 flex gap-1 overflow-x-auto">
            <MobileNavLink href="/dashboard">Overview</MobileNavLink>
            <MobileNavLink href="/dashboard/keys">API Keys</MobileNavLink>
            <MobileNavLink href="/dashboard/usage">Usage</MobileNavLink>
            <MobileNavLink href="/playground">Playground</MobileNavLink>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="animate-fade-in">{children}</div>
      </main>
    </div>
  );
}

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="text-gray-600 hover:text-gray-900 hover:bg-gray-50 px-4 py-2 rounded-lg font-medium transition-colors"
    >
      {children}
    </Link>
  );
}

function MobileNavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="text-gray-600 hover:text-gray-900 px-3 py-1.5 text-sm font-medium whitespace-nowrap rounded-lg hover:bg-gray-100 transition-colors"
    >
      {children}
    </Link>
  );
}
