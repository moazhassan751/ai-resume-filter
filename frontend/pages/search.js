import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { GlassCard } from '../src/components/ui/GlassCard'
import { LoadingSkeleton } from '../src/components/ui/LoadingSkeleton'
import { useToast } from '../src/components/ui/ToastProvider'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'

export default function SearchPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState(null)
  
  const categories = [
    'All Categories',
    'HR',
    'Designer',
    'Information Technology',
    'Teacher',
    'Advocate',
    'Business Development',
    'Healthcare',
    'Fitness',
    'Agriculture',
    'Development',
    'Engineering',
    'Finance',
    'Sales',
  ]

  useEffect(() => {
    if (!getToken()) router.push('/login')
  }, [router])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) {
      toast('Please enter a query', 'error')
      return
    }

    setLoading(true)
    setError(null)
    setSearched(true)
    try {
      const payload = {
        query: query,
        top_k: parseInt(topK),
      }
      if (category && category !== 'All Categories') {
        payload.category = category
      }

      const res = await apiFetch('/api/v1/search/semantic', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      if (!res.ok) throw new Error(`Search failed (${res.status})`)
      const data = await res.json()
      setResults(data.results || [])
      toast(`Found ${data.results?.length || 0} matching candidates`)
    } catch (err) {
      setError(err.message)
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const navLinks = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/upload', label: 'Upload' },
    { href: '/ranking', label: 'Ranking' },
    { href: '/rag', label: 'AI Assistant' },
    { href: '/analytics', label: 'Analytics' },
    { href: '/history', label: 'History' },
  ]

  return (
    <>
      <Head>
        <title>Semantic Search — TalentLens AI</title>
      </Head>
      <main className="min-h-screen">
        <ResponsiveHeader
          title="Semantic Search"
          links={navLinks}
          onLogout={handleLogout}
        />

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="glass-panel rounded-[2rem] p-6 md:p-8 mb-6">
            <div className="max-w-3xl">
              <div className="inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-cyan-200">
                Vector Search Engine
              </div>
              <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white sm:text-5xl">
                Find candidates using natural language commands.
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-300 sm:text-base">
                ChromaDB retrieves candidate resumes using cosine-similarity matches. Type descriptive roles like 
                <span className="text-cyan-200"> "React developer with Docker experience"</span> or 
                <span className="text-cyan-200"> "Teacher with MS in Education"</span>.
              </p>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
            <div className="h-fit">
              <GlassCard title="Search Queries" subtitle="Configure matching options.">
                <form onSubmit={handleSearch} className="space-y-4">
                  <div>
                    <label className="mb-2 block text-sm text-slate-300">Recruiter Query</label>
                    <textarea
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="e.g., Python Developer with FastAPI and MongoDB"
                      className="min-h-[120px] w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none placeholder:text-slate-500 text-sm focus:border-cyan-400/50"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm text-slate-300">Top Matches (K)</label>
                      <span className="text-xs font-semibold text-cyan-300">{topK}</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="20"
                      value={topK}
                      onChange={(e) => setTopK(e.target.value)}
                      className="w-full h-1.5 rounded-lg bg-white/10 appearance-none cursor-pointer accent-cyan-300"
                    />
                  </div>

                  <div>
                    <label className="mb-2 block text-sm text-slate-300">Filter Category</label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none text-sm focus:border-cyan-400/50"
                    >
                      {categories.map((cat) => (
                        <option key={cat} value={cat === 'All Categories' ? '' : cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading ? 'Searching...' : 'Search Candidates'}
                  </button>
                </form>
              </GlassCard>
            </div>

            <div>
              <GlassCard title="Search Results" subtitle="Candidates ranked by vector similarity score.">
                {error && (
                  <div className="mb-4 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    {error}
                  </div>
                )}

                {loading ? (
                  <div className="space-y-4">
                    <LoadingSkeleton className="h-[120px] rounded-3xl" />
                    <LoadingSkeleton className="h-[120px] rounded-3xl" />
                    <LoadingSkeleton className="h-[120px] rounded-3xl" />
                  </div>
                ) : results.length > 0 ? (
                  <div className="space-y-4">
                    <AnimatePresence>
                      {results.map((result, idx) => (
                        <motion.div
                          key={result.candidate_id || idx}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: idx * 0.05 }}
                          className="glass-card rounded-3xl p-5 border border-white/5 hover:border-cyan-400/20 transition-all"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-3">
                            <div>
                              <div className="text-[10px] uppercase tracking-wider text-slate-400">Candidate ID</div>
                              <div className="text-sm font-semibold text-slate-200 truncate max-w-[200px]">
                                {result.candidate_id}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {result.category && (
                                <span className="inline-flex items-center rounded-full bg-white/5 border border-white/10 px-2.5 py-0.5 text-xs text-slate-300">
                                  {result.category}
                                </span>
                              )}
                              <span className="inline-flex items-center rounded-full bg-cyan-400/10 border border-cyan-400/20 px-2.5 py-0.5 text-xs font-semibold text-cyan-200">
                                {Math.round((result.score || 0) * 100)}% match
                              </span>
                            </div>
                          </div>

                          <div className="mt-4 grid gap-4">
                            {result.skills && (
                              <div>
                                <div className="text-[10px] uppercase tracking-wider text-slate-400">Skills</div>
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {result.skills.split(',').map((skill, sIdx) => (
                                    <span key={sIdx} className="inline-flex items-center rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-slate-300 border border-white/5">
                                      {skill.trim()}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            <div>
                              <div className="text-[10px] uppercase tracking-wider text-slate-400">Match Explanation</div>
                              <p className="mt-1 text-xs text-slate-300 leading-relaxed">
                                {result.explanation}
                              </p>
                            </div>

                            <div>
                              <details className="group cursor-pointer">
                                <summary className="flex items-center justify-between text-[10px] text-slate-400 hover:text-slate-300 select-none">
                                  <span>Resume Preview Snippet</span>
                                  <span className="text-[9px] uppercase tracking-widest text-slate-500 group-open:rotate-180 transition-transform">▼</span>
                                </summary>
                                <p className="mt-2 max-h-[150px] overflow-auto whitespace-pre-wrap rounded-xl border border-white/5 bg-slate-950/40 p-3 text-xs leading-relaxed text-slate-400 font-mono">
                                  {result.preview}
                                </p>
                              </details>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                ) : searched ? (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-sm text-slate-400 text-center">
                    No matching candidates found for this query.
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-sm text-slate-400 text-center">
                    Run a query to view matching candidates.
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
