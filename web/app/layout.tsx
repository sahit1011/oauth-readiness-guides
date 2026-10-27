import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "OAuth Readiness Guides",
  description: "How long and how hard it is to get a provider OAuth app ready for your agent's users",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-20 border-b border-zinc-200/80 bg-white/85 backdrop-blur">
          <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between px-6">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-900 font-mono text-xs font-bold text-white">OA</span>
              <span className="font-semibold tracking-tight text-zinc-900">OAuth Readiness</span>
              <span className="rounded-md border border-zinc-200 px-1.5 py-0.5 text-[11px] font-medium text-zinc-500">Guides</span>
            </Link>
            <nav className="flex items-center gap-6 text-sm text-zinc-600">
              <Link href="/#library" className="hover:text-zinc-900">
                Library
              </Link>
              <Link href="/#catalog" className="hover:text-zinc-900">
                All OAuth apps
              </Link>
              <Link href="/#how-it-works" className="hover:text-zinc-900">
                How it works
              </Link>
              <Link href="/#generate" className="rounded-md bg-zinc-900 px-3 py-1.5 font-medium text-white hover:bg-zinc-700">
                Generate a guide
              </Link>
            </nav>
          </div>
        </header>
        {children}
        <footer className="mt-auto border-t border-zinc-200">
          <div className="mx-auto w-full max-w-7xl px-6 py-6 text-sm text-zinc-500">
            Guides are researched by an agent and checked against their sources. Every statement is labeled tested, sourced, or inferred.
          </div>
        </footer>
      </body>
    </html>
  );
}
