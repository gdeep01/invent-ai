import React from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { TurbulentFlow } from '@/components/ui/turbulent-flow'

export function HeroSection() {
  const [scrolled, setScrolled] = React.useState(false)
  const { user, isAuthenticated } = useAuth()

  React.useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 12)
    }

    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })

    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <section className="relative min-h-screen overflow-hidden bg-black text-white">
      <header className="fixed inset-x-0 top-0 z-50">
        <nav
          className={cn(
            'mx-auto flex max-w-7xl items-center justify-between px-6 py-5 transition-all duration-300 lg:px-12',
            scrolled && 'bg-black/30 backdrop-blur-md'
          )}
        >
          <Link to="/" className="text-xl font-bold tracking-tight text-white">
            InventAI
          </Link>
          {!isAuthenticated ? (
            <Button asChild variant="outline" size="sm" className="rounded-full border-white/30 bg-white/0 px-4 text-white hover:bg-white/10">
              <Link to="/upload">Get Started</Link>
            </Button>
          ) : (
            <div className="flex items-center gap-3">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name || user.email}
                  className="h-9 w-9 rounded-full border border-white/10 object-cover"
                />
              ) : (
                <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-white">
                  {(user?.name || user?.email || 'I').slice(0, 1).toUpperCase()}
                </div>
              )}
              <Button asChild size="sm" className="rounded-full bg-teal-400 px-4 text-slate-950 hover:bg-teal-300">
                <Link to="/dashboard">Dashboard</Link>
              </Button>
            </div>
          )}
        </nav>
      </header>

      <TurbulentFlow>
        <div className="relative z-10 flex min-h-screen items-center">
          <div className="mx-auto w-full max-w-7xl px-6 pt-24 lg:px-12">
            <div className="max-w-4xl">
              <div className="inline-flex rounded-full border border-teal-400/30 bg-teal-400/10 px-3 py-1 text-xs text-teal-300">
                Now with Gemini AI
              </div>
              <h1 className="mt-8 text-5xl font-black leading-none tracking-tight text-white sm:text-6xl md:text-7xl">
                <span className="block">Inventory</span>
                <span className="block italic text-teal-400">Intelligence</span>
                <span className="block">Reimagined.</span>
              </h1>
              <p className="mt-6 max-w-md text-base text-white/60 md:text-lg">
                ARIMA forecasting, live mandi prices, and AI chat - built for Indian retail teams.
              </p>
              <div className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <Button asChild size="lg" className="rounded-full bg-teal-400 px-8 py-3 text-base font-semibold text-gray-950 hover:bg-teal-300">
                  <Link to="/upload">Get Started</Link>
                </Button>
                <a
                  href="#how-it-works"
                  className="text-sm text-white/70 underline underline-offset-4 transition hover:text-white"
                >
                  See how it works
                </a>
              </div>
              <div className="mt-16 flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.28em] text-white/40 sm:gap-4">
                <span>ARIMA Forecasting</span>
                <span className="text-white/20">&middot;</span>
                <span>Live Mandi Prices</span>
                <span className="text-white/20">&middot;</span>
                <span>AI Chat Assistant</span>
              </div>
            </div>
          </div>
        </div>
      </TurbulentFlow>
    </section>
  )
}
