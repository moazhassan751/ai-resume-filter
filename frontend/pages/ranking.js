import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { GlassCard } from '../src/components/ui/GlassCard'
import { LoadingSkeleton } from '../src/components/ui/LoadingSkeleton'
import { useToast } from '../src/components/ui/ToastProvider'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'

export default function RankingPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [jobDescription, setJobDescription] = useState('')
  const [historyItems, setHistoryItems] = useState([])
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [historyLoading, setHistoryLoading] = useState(true)
  const [rankingLoading, setRankingLoading] = useState(false)
  const [rankedResults, setRankedResults] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!getToken()) {
      router.push('/login')
      return
    }

    const loadHistory = async () => {
      setHistoryLoading(true)
      try {
        const res = await apiFetch('/api/v1/data/history?limit=20')
        if (res.ok) {
          const data = await res.json()
          setHistoryItems(data.items || [])
        }
      } catch (err) {
        toast('Failed to load history items', 'error')
      } finally {
        setHistoryLoading(false)
      }
    }

    loadHistory()
  }, [router])

  const toggleSelect = (id) => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleRank = async (e) => {
    e.preventDefault()
    if (!jobDescription.trim()) {
      toast('Please enter a job description', 'error')
      return
    }
    if (selectedIds.size === 0) {
      toast('Please select at least one candidate to rank', 'error')
      return
    }

    setRankingLoading(true)
    setError(null)
    setRankedResults([])
    try {
      // Fetch full candidate texts (including extracted_text) for each selected candidate
      const candidatesToRank = []
      for (const id of selectedIds) {
        const detailRes = await apiFetch(`/api/v1/data/history/${id}`)
        if (!detailRes.ok) throw new Error(`Failed to load details for candidate ${id}`)
        const detail = await detailRes.json()
        
        candidatesToRank.push({
          candidate_id: detail.candidate_id,
          text: detail.extracted_text || '',
          metadata: {
            name: detail.candidate_name || 'Unnamed candidate',
            skills: detail.skills || '',
            experience_years: parseFloat(detail.experience_years || 0),
          }
        })
      }

      const res = await apiFetch('/api/v1/ranking/rank-candidates', {
        method: 'POST',
        body: JSON.stringify({
          job_description: jobDescription,
          candidates: candidatesToRank,
        })
      })

      if (!res.ok) throw new Error(`Ranking failed (${res.status})`)
      const data = await res.json()
      setRankedResults(data.results || [])
      toast('Ranking completed successfully')
    } catch (err) {
      setError(err.message)
      toast(err.message, 'error')
    } finally {
      setRankingLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const navLinks = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/upload', label: 'Upload' },
    { href: '/search', label: 'Search' },
    { href: '/rag', label: 'AI Assistant' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/history', label: 'History' },
  ]

  return (
    <>
      <Head>
        <title>Candidate Ranking — TalentLens AI</title>
      </Head>
      <main className="min-h-screen">
        <ResponsiveHeader
          title="Candidate Ranking Engine"
          links={navLinks}
          onLogout={handleLogout}
        />

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="glass-panel rounded-[2rem] p-6 md:p-8 mb-6">
            <div className="max-w-3xl">
              <div className="inline-flex rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-emerald-200">
                Multi-Candidate Comparison
              </div>
              <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white sm:text-5xl">
                Rank multiple candidates side-by-side.
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-300 sm:text-base">
                Select parsed candidates from the history list, paste a job description, and let our multi-signal algorithm rank them based on semantic, ATS keyword, skills, and experience overlap.
              </p>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr] lg:grid-cols-[1fr_1fr]">
            <div className="space-y-6">
              <GlassCard title="1. Configure Ranking" subtitle="Paste JD and select candidates.">
                <form onSubmit={handleRank} className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm text-slate-300">Job Description</label>
                    <textarea
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Paste the target job description here..."
                      className="min-h-[160px] w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none placeholder:text-slate-500 text-sm focus:border-cyan-400/50"
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-sm text-slate-300">
                      Select Candidates to Compare ({selectedIds.size} selected)
                    </label>

                    {historyLoading ? (
                      <LoadingSkeleton className="h-[150px] rounded-3xl" />
                    ) : historyItems.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-4 text-xs text-slate-400 text-center">
                        No candidates in history. Upload resumes first.
                      </div>
                    ) : (
                      <div className="max-h-[260px] overflow-y-auto space-y-2 border border-white/5 rounded-2xl p-3 bg-slate-950/30">
                        {historyItems.map((item) => {
                          const isSelected = selectedIds.has(item.candidate_id)
                          return (
                            <div
                              key={item.candidate_id}
                              onClick={() => toggleSelect(item.candidate_id)}
                              className={`flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all ${
                                isSelected
                                  ? 'bg-cyan-400/10 border-cyan-400/30'
                                  : 'bg-white/5 border-white/5 hover:bg-white/10'
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <div className={`w-4 h-4 rounded-md border flex items-center justify-center transition-all ${
                                  isSelected ? 'bg-cyan-300 border-cyan-300 text-slate-900 font-bold text-xs' : 'border-white/20'
                                }`}>
                                  {isSelected && '✓'}
                                </div>
                                <div>
                                  <div className="text-sm font-semibold text-slate-100">
                                    {item.candidate_name || 'Unnamed candidate'}
                                  </div>
                                  <div className="text-[10px] text-slate-400">
                                    {item.filename} {item.ats_score ? `(ATS: ${item.ats_score})` : ''}
                                  </div>
                                </div>
                              </div>
                              {item.category && (
                                <span className="text-[10px] bg-white/5 border border-white/10 rounded px-2 py-0.5 text-slate-300">
                                  {item.category}
                                </span>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={rankingLoading || selectedIds.size === 0}
                    className="w-full rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {rankingLoading ? 'Processing & Ranking...' : `Compare & Rank Selected (${selectedIds.size})`}
                  </button>
                </form>
              </GlassCard>
            </div>

            <div>
              <GlassCard title="2. Ranked Match Results" subtitle="Candidates ordered by composite fitness score.">
                {error && (
                  <div className="mb-4 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    {error}
                  </div>
                )}

                {rankingLoading ? (
                  <div className="space-y-4">
                    <LoadingSkeleton className="h-[120px] rounded-3xl animate-pulse" />
                    <LoadingSkeleton className="h-[120px] rounded-3xl animate-pulse" />
                  </div>
                ) : rankedResults.length > 0 ? (
                  <div className="space-y-4">
                    <AnimatePresence>
                      {rankedResults.map((result, idx) => {
                        const rec = result.recommendation?.toLowerCase() || ''
                        const badgeColor = rec.includes('strong')
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : rec.includes('good')
                          ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                          : rec.includes('consider')
                          ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                          : 'bg-rose-500/10 text-rose-300 border-rose-500/30'

                        return (
                          <motion.div
                            key={result.candidate_id || idx}
                            initial={{ opacity: 0, scale: 0.98 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: idx * 0.05 }}
                            className="glass-card rounded-3xl p-5 border border-white/5 hover:border-cyan-400/20 transition-all"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-3">
                              <div className="flex items-center gap-2">
                                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-cyan-400/20 text-xs font-bold text-cyan-300">
                                  #{idx + 1}
                                </span>
                                <div>
                                  <div className="text-base font-semibold text-slate-100">
                                    {result.candidate_name || 'Unnamed candidate'}
                                  </div>
                                  <div className="text-[10px] text-slate-400 truncate max-w-[150px]">
                                    ID: {result.candidate_id}
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${badgeColor}`}>
                                  {result.recommendation}
                                </span>
                                <span className="text-xl font-bold text-cyan-200">
                                  {result.score}
                                </span>
                              </div>
                            </div>

                            <div className="mt-4 space-y-4">
                              {result.strengths?.length > 0 && (
                                <div>
                                  <div className="text-[10px] uppercase tracking-wider text-slate-400">Strengths / Skills</div>
                                  <div className="mt-1 flex flex-wrap gap-1">
                                    {result.strengths.map((str, sIdx) => (
                                      <span key={sIdx} className="inline-flex items-center rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-300 border border-emerald-500/20">
                                        {str}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {result.missing_skills?.length > 0 && (
                                <div>
                                  <div className="text-[10px] uppercase tracking-wider text-slate-400">Missing Required Skills</div>
                                  <div className="mt-1 flex flex-wrap gap-1">
                                    {result.missing_skills.map((skill, sIdx) => (
                                      <span key={sIdx} className="inline-flex items-center rounded-md bg-rose-500/10 px-2 py-0.5 text-[11px] text-rose-300 border border-rose-500/20">
                                        {skill}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {result.details?.component_scores && (
                                <div className="border-t border-white/5 pt-3">
                                  <details className="group cursor-pointer">
                                    <summary className="flex items-center justify-between text-[10px] text-slate-400 hover:text-slate-300 select-none">
                                      <span>Component Score Breakdown</span>
                                      <span className="text-[9px] uppercase tracking-widest text-slate-500 group-open:rotate-180 transition-transform">▼</span>
                                    </summary>
                                    <div className="mt-2 grid grid-cols-2 gap-2 rounded-xl border border-white/5 bg-slate-950/40 p-3 text-[11px] text-slate-300">
                                      {Object.entries(result.details.component_scores).map(([name, scoreVal]) => (
                                        <div key={name} className="flex justify-between border-b border-white/5 pb-1 last:border-0 last:pb-0">
                                          <span className="capitalize">{name}:</span>
                                          <span className="font-semibold text-cyan-300">{Math.round((scoreVal || 0) * 100)}%</span>
                                        </div>
                                      ))}
                                    </div>
                                  </details>
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )
                      })}
                    </AnimatePresence>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-sm text-slate-400 text-center">
                    Select candidates and paste a job description, then click compare to see the ranked candidates.
                  </div>
                )}
              </GlassCard>
            </div>
          </div>
        </section>
      </main>
    </>
  )
}
