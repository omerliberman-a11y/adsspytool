import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "adspy",
  description: "Internal ad intelligence dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">
        <header className="border-b border-border bg-panel sticky top-0 z-10">
          <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center gap-6">
            <Link href="/" className="font-mono text-accent font-semibold tracking-tight">
              adspy
            </Link>
            <nav className="flex gap-4 text-sm text-muted">
              <Link href="/" className="hover:text-ink">Winners</Link>
              <Link href="/competitors" className="hover:text-ink">Competitors</Link>
              <Link href="/sources" className="hover:text-ink">Sources</Link>
              <Link href="/playbooks" className="hover:text-ink">Playbooks</Link>
              <Link href="/stats" className="hover:text-ink">Stats</Link>
              <Link href="/queue" className="hover:text-ink">Queue</Link>
            </nav>
            <div className="ml-auto flex items-center gap-2">
              <Link
                href="/scrape"
                className="text-sm px-3 py-1.5 rounded-md bg-accent text-white hover:opacity-90"
              >
                + New scrape
              </Link>
            </div>
          </div>
        </header>
        <main className="max-w-screen-2xl mx-auto px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
