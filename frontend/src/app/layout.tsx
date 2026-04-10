import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-ibm-plex-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "RoofLeads AI",
  description: "AI-powered sales intelligence for roofing distributors",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {/* Floating pill nav — Instalily style */}
        <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-5xl">
          <div
            className="flex items-center justify-between px-6 py-3 rounded-2xl border border-accent/30"
            style={{
              background: "linear-gradient(to right, rgba(0,0,0,0.85), rgba(51,51,51,0.85))",
              backdropFilter: "blur(2px)",
              boxShadow: "0px 4px 6px rgba(0,0,0,0.11)",
            }}
          >
            <Link href="/" className="text-white text-sm font-semibold tracking-tight">
              ROOF<span className="font-light">LEADS_</span>
            </Link>

            <div className="flex items-center gap-6">
              <Link
                href="/"
                className="text-gray-300 text-xs font-medium tracking-widest uppercase hover:text-white transition-colors"
                style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
              >
                Dashboard
              </Link>
              <Link
                href="/pipeline"
                className="text-gray-300 text-xs font-medium tracking-widest uppercase hover:text-white transition-colors"
                style={{ fontFamily: "var(--font-ibm-plex-mono)" }}
              >
                Pipeline
              </Link>
              <span className="px-4 py-1.5 text-xs font-medium text-white border border-white/80 rounded-2xl tracking-wide">
                Deploy InstaWorkers
              </span>
            </div>
          </div>
        </nav>

        {/* Spacer for fixed nav */}
        <div className="h-20" />

        <main className="flex-1">{children}</main>

        {/* Footer — dark, seamless with Instalily CTA style */}
        <footer className="bg-[#181818] border-t border-dark-border">
          <div className="mx-auto max-w-5xl px-6 py-12 flex items-center justify-between">
            <div>
              <p className="text-white text-sm font-medium">RoofLeads AI</p>
              <p className="text-gray-400 text-xs mt-1">
                AI-powered sales intelligence for roofing distributors
              </p>
            </div>
            <p className="text-gray-500 text-xs">&copy; 2026</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
