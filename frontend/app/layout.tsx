import type { Metadata } from "next";
import "./globals.css";
import AuthControls from '@/components/AuthControls';
import Navigation from '@/components/Navigation';

export const metadata: Metadata = {
  title: "Stock Option Analyzer Pro",
  description: "AI Stock Option Analyzer with Real-time Finnhub Data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <body className="bg-background text-text">
        <header className="sticky top-0 z-100 bg-surface border-b border-border">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="text-lg font-bold bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">
              ⚡ Stock Option Analyzer
            </div>
            <div id="userBar" className="flex gap-3">
              <AuthControls />
            </div>
          </div>
          <Navigation />
        </header>

        <main className="container-page">{children}</main>
      </body>
    </html>
  );
}


