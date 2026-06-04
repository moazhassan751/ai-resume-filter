import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { GlassCard } from '../src/components/ui/GlassCard'
import { LoadingSkeleton } from '../src/components/ui/LoadingSkeleton'
import { useToast } from '../src/components/ui/ToastProvider'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'

export default function RagPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [inputQuery, setInputQuery] = useState('')
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      summary: 'Hello! I am your AI Recruiter Assistant. I search through all candidate resumes in ChromaDB and synthesize matching profiles. Try asking me a question like "Which candidates have React and Docker experience?" or "Who is best suited for an AI Research role?"',
    }
  ])
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (!getToken()) router.push('/login')
  }, [router])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!inputQuery.trim()) return

    const queryText = inputQuery.trim()
    setInputQuery('')
    setErrorMsg(null)

    // Add user message
    const userMsgId = `user-${Date.now()}`
    setMessages((prev) => [...prev, { id: userMsgId, role: 'user', text: queryText }])
    setLoading(true)

    try {
      const res = await apiFetch('/api/v1/rag/analyze', {
        method: 'POST',
        body: JSON.stringify({
          job_description: queryText,
          top_k: 5,
        })
      })

      if (!res.ok) throw new Error(`Assistant query failed (${res.status})`)
      const data = await res.json()

      // Add assistant response message
      const assistantMsgId = `assistant-${Date.now()}`
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: 'assistant',
          summary: data.summary,
          rankedCandidates: data.ranked_candidates || [],
          recommendedHires: data.recommended_hires || [],
          skillGaps: data.skill_gaps || [],
          diagnostics: data.diagnostics || null,
        }
      ])
      toast('AI Assistant responded')
    } catch (err) {
      toast(err.message, 'error')
      // Add error message to chat
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          summary: `Sorry, I encountered an error: ${err.message}. Please try again later.`,
          isError: true,
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const [errorMsg, setErrorMsg] = useState(null)

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const navLinks = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/upload', label: 'Upload' },
    { href: '/search', label: 'Search' },
    { href: '/ranking', label: 'Ranking' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/history', label: 'History' },
  ]

  return (
    <>
      <Head>
        <title>Recruiter Assistant — TalentLens AI</title>
      </Head>
      <main className="min-h-screen flex flex-col h-screen bg-[#050912]">
        <ResponsiveHeader
          title="AI Recruiter Assistant"
          links={navLinks}
          onLogout={handleLogout}
        />

        <section className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col overflow-hidden">
          <div className="glass-panel rounded-[2rem] p-4 mb-4 flex-shrink-0">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cyan-200">
                Retrieval-Augmented Generation (RAG)
              </span>
              <p className="text-xs text-slate-300">
                Active context window contains all resumes stored in ChromaDB vector index.
              </p>
            </div>
          </div>

          <div className="flex-1 glass-card rounded-[2rem] border border-white/5 p-4 md:p-6 flex flex-col overflow-hidden bg-slate-950/20">
            <div className="flex-1 overflow-y-auto space-y-6 pr-2 mb-4 scrollbar-thin">
              <AnimatePresence initial={false}>
                {messages.map((msg) => {
                  const isUser = msg.role === 'user'
                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex gap-3 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
                    >
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                        isUser ? 'bg-cyan-300 text-slate-900' : msg.isError ? 'bg-rose-500/20 border border-rose-500/30 text-rose-300' : 'bg-emerald-400/20 border border-emerald-400/30 text-emerald-300'
                      }`}>
                        {isUser ? 'U' : 'AI'}
                      </div>

                      <div className={`rounded-3xl p-4 md:p-5 border ${
                        isUser 
                          ? 'bg-cyan-950/25 border-cyan-400/20 text-slate-100'
                          : msg.isError
                          ? 'bg-rose-950/20 border-rose-500/20 text-rose-100'
                          : 'bg-white/5 border-white/5 text-slate-200'
                      }`}>
                        {isUser ? (
                          <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                        ) : (
                          <div className="space-y-4">
                            <p className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
                              {msg.summary}
                            </p>

                            {/* Recommended Hires Section */}
                            {msg.recommendedHires?.length > 0 && (
                              <div className="border-t border-white/5 pt-3">
                                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                                  Recommended Candidates
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  {msg.recommendedHires.map((hire, hIdx) => (
                                    <span key={hIdx} className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-300 border border-emerald-500/20">
                                      ★ {hire}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Ranked Candidates Detail Grid */}
                            {msg.rankedCandidates?.length > 0 && (
                              <div className="border-t border-white/5 pt-3">
                                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                                  Retrieved Match Scores
                                </div>
                                <div className="grid gap-2">
                                  {msg.rankedCandidates.map((candidate, cIdx) => (
                                    <div key={cIdx} className="bg-slate-950/40 border border-white/5 rounded-xl p-3 text-xs">
                                      <div className="flex justify-between items-center mb-1.5">
                                        <span className="font-semibold text-slate-200">ID: {candidate.candidate_id}</span>
                                        <span className="font-bold text-cyan-300">{Math.round(candidate.score)}% fit</span>
                                      </div>
                                      
                                      {candidate.reasons?.length > 0 && (
                                        <div className="text-[11px] text-slate-400 mt-1 pl-2 border-l border-white/10">
                                          {candidate.reasons.join(', ')}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Skill Gaps identified */}
                            {msg.skillGaps?.length > 0 && (
                              <div className="border-t border-white/5 pt-3">
                                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">
                                  Skills Gaps Found
                                </div>
                                <div className="space-y-1">
                                  {msg.skillGaps.map((gap, gIdx) => (
                                    <div key={gIdx} className="flex justify-between items-center bg-white/5 rounded px-2 py-1 text-[11px]">
                                      <span className="text-yellow-200">{gap.skill}</span>
                                      {gap.missing_from?.length > 0 && (
                                        <span className="text-[10px] text-slate-500">Missing from: {gap.missing_from.join(', ')}</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Diagnostics Dropdown */}
                            {msg.diagnostics && (
                              <div className="border-t border-white/5 pt-3">
                                <details className="group cursor-pointer">
                                  <summary className="flex items-center justify-between text-[9px] text-slate-500 hover:text-slate-400 select-none">
                                    <span>Retrieval Diagnostics</span>
                                    <span className="text-[8px] uppercase tracking-widest text-slate-600 group-open:rotate-180 transition-transform">▼</span>
                                  </summary>
                                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] text-slate-500 font-mono bg-slate-950/60 p-2.5 rounded-xl border border-white/5">
                                    <div>Retrieved in: {msg.diagnostics.retrieval_ms?.toFixed(1)}ms</div>
                                    <div>AI Response in: {msg.diagnostics.ai_ms?.toFixed(1)}ms</div>
                                    <div>Total Duration: {msg.diagnostics.total_ms?.toFixed(1)}ms</div>
                                    <div>Model: {msg.diagnostics.used_model || 'Local Model'}</div>
                                  </div>
                                </details>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )
                })}
              </AnimatePresence>

              {loading && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 max-w-[85%]">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs bg-emerald-400/20 border border-emerald-400/30 text-emerald-300 animate-pulse">
                    AI
                  </div>
                  <div className="rounded-3xl p-4 bg-white/5 border border-white/5 text-slate-400 text-sm flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    <span>AI Assistant is compiling context and ranking matches...</span>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSend} className="mt-auto pt-4 border-t border-white/5 flex gap-3">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask about candidate experience, missing skills, or match summaries..."
                className="flex-1 rounded-full border border-white/10 bg-slate-950/60 px-5 py-3 text-slate-100 outline-none text-sm placeholder:text-slate-500 focus:border-cyan-400/50"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !inputQuery.trim()}
                className="rounded-full bg-cyan-300 hover:bg-cyan-200 px-6 py-3 text-sm font-semibold text-slate-950 transition disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
              >
                Send
              </button>
            </form>
          </div>
        </section>
      </main>
    </>
  )
}
