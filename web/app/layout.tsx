import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Trading Bot Dashboard',
  description: 'Real-time monitoring and control for MES futures trading bot',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen">
          <nav className="bg-slate-900 border-b border-slate-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h1 className="text-xl font-bold">Trading Bot</h1>
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded">
                  V2 Engine
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <a href="/" className="text-slate-300 hover:text-white">Dashboard</a>
                <a href="/journal" className="text-slate-300 hover:text-white">Journal</a>
                <a href="/signals" className="text-slate-300 hover:text-white">Signals</a>
                <a href="/settings" className="text-slate-300 hover:text-white">Settings</a>
              </div>
            </div>
          </nav>
          <main className="p-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
