import React, { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { ChevronDown, LayoutDashboard, LogOut, MessageSquare, ShoppingCart, TrendingUp, Upload, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Toaster, toast } from 'sonner'

import { AuthProvider, useAuth } from '@/context/AuthContext'
import HomePage from '@/pages/HomePage'
import DashboardPage from '@/pages/DashboardPage'
import ForecastPage from '@/pages/ForecastPage'
import ReorderPage from '@/pages/ReorderPage'
import UploadPage from '@/pages/UploadPage'
import api from '@/services/api'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mx-auto max-w-xl rounded-3xl border border-slate-200 bg-white p-10 text-center shadow-lg">
          <h2 className="text-2xl font-semibold text-slate-950">Something went wrong</h2>
          <p className="mt-3 text-sm text-slate-500">Refresh the page to reload this InventAI view.</p>
        </div>
      )
    }
    return this.props.children
  }
}

function ChatAssistant() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [history, setHistory] = useState([])
  const [streaming, setStreaming] = useState(false)

  const suggestions = [
    'What should I reorder this week?',
    'What may sell most next month?',
    'Which items are affected by mandi prices?',
    'What should I stock before Diwali?',
  ]

  const sendMessage = async (message) => {
    const prompt = message || input.trim()
    if (!prompt) return

    const nextHistory = [...history, { role: 'user', content: prompt }, { role: 'assistant', content: '' }]
    setHistory(nextHistory)
    setInput('')
    setStreaming(true)

    try {
      const response = await api.streamChat({
        message: prompt,
        conversation_history: history,
      })
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        parts.forEach((part) => {
          if (!part.startsWith('data: ')) return
          const payload = part.slice(6)
          if (payload === '[DONE]') return
          const parsed = JSON.parse(payload)
          setHistory((current) => {
            const updated = [...current]
            updated[updated.length - 1] = {
              role: 'assistant',
              content: `${updated[updated.length - 1].content}${parsed.content || ''}`,
            }
            return updated
          })
        })
      }
    } catch (error) {
      toast.error(error.message)
    } finally {
      setStreaming(false)
    }
  }

  return (
    <>
      <button className="chat-bubble" onClick={() => setOpen((value) => !value)} aria-label="Open InventAI Assistant">
        <MessageSquare size={18} />
      </button>
      <div className={`chat-drawer ${open ? 'open' : ''}`}>
        <div className="chat-header">
          <div>
            <strong>InventAI Assistant</strong>
            <div className="text-xs text-slate-400">Simple help for stock and sales</div>
          </div>
          <div className="chat-header-actions">
            <button className="chip" onClick={() => setHistory([])}>Clear chat</button>
            <button className="chat-close-button" onClick={() => setOpen(false)} aria-label="Close InventAI Assistant">
              <X size={16} />
            </button>
          </div>
        </div>
        <div className="chat-suggestions">
          {suggestions.map((suggestion) => (
            <button key={suggestion} className="chip" onClick={() => sendMessage(suggestion)}>{suggestion}</button>
          ))}
        </div>
        <div className="chat-history">
          {history.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>
              <ReactMarkdown>{message.content || (streaming && message.role === 'assistant' ? 'Checking your data...' : '')}</ReactMarkdown>
            </div>
          ))}
        </div>
        <div className="chat-composer">
          <input className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about stock, sales, reorder, or festivals" />
          <button className="rounded-full bg-teal-400 px-4 py-3 text-sm font-medium text-slate-950" onClick={() => sendMessage()} disabled={streaming}>Send</button>
        </div>
      </div>
    </>
  )
}

function AppShell() {
  const { user, logout, isAuthenticated } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <nav className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <NavLink to="/dashboard" className="inline-flex items-center gap-2 text-xl font-semibold tracking-[0.26em] uppercase">
            InventAI
          </NavLink>
          <div className="flex flex-wrap items-center gap-2">
            <NavLink to="/dashboard" className={({ isActive }) => `nav-link-tailwind ${isActive ? 'nav-link-tailwind-active' : ''}`}><LayoutDashboard size={16} />Dashboard</NavLink>
            <NavLink to="/reorder" className={({ isActive }) => `nav-link-tailwind ${isActive ? 'nav-link-tailwind-active' : ''}`}><ShoppingCart size={16} />Reorder</NavLink>
            <NavLink to="/forecast" className={({ isActive }) => `nav-link-tailwind ${isActive ? 'nav-link-tailwind-active' : ''}`}><TrendingUp size={16} />Forecast</NavLink>
            <NavLink to="/upload" className={({ isActive }) => `nav-link-tailwind ${isActive ? 'nav-link-tailwind-active' : ''}`}><Upload size={16} />Upload</NavLink>
          </div>
          {isAuthenticated ? (
            <div className="relative">
              <button className="profile-chip" onClick={() => setMenuOpen((value) => !value)}>
                {user?.avatar_url ? <img src={user.avatar_url} alt={user?.name || user?.email} className="avatar" /> : <div className="avatar-fallback">{user?.name?.[0] || user?.email?.[0] || 'I'}</div>}
                <span className="hidden text-sm font-medium text-slate-100 sm:inline">{user?.name || user?.email}</span>
                <ChevronDown size={16} className="text-slate-300" />
              </button>
              {menuOpen ? (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl border border-white/10 bg-slate-900 p-2 shadow-2xl">
                  <div className="border-b border-white/10 px-3 py-3 text-sm text-slate-300">
                    <div className="font-medium text-white">{user?.name || 'InventAI User'}</div>
                    <div className="truncate text-xs">{user?.email}</div>
                  </div>
                  <button className="mt-2 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-white transition hover:bg-white/5" onClick={logout}>
                    <LogOut size={16} />
                    Logout
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <ErrorBoundary>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/reorder" element={<ReorderPage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/upload" element={<UploadPage />} />
          </Routes>
        </ErrorBoundary>
      </main>
      <ChatAssistant />
    </div>
  )
}

function AuthenticatedRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/*" element={<AppShell />} />
    </Routes>
  )
}

function App() {
  return (
    <>
      <Toaster theme="dark" richColors position="top-right" />
      <AuthProvider>
        <AuthenticatedRoutes />
      </AuthProvider>
    </>
  )
}

export default App
