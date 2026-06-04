import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { GlassCard } from '../src/components/ui/GlassCard'
import { LoadingSkeleton } from '../src/components/ui/LoadingSkeleton'
import { UploadDropzone } from '../src/components/ui/UploadDropzone'
import { useToast } from '../src/components/ui/ToastProvider'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'

export default function UploadPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [candidateName, setCandidateName] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [agentResult, setAgentResult] = useState(null)
  const [agentLoading, setAgentLoading] = useState(false)
  const [agentError, setAgentError] = useState(null)

  useEffect(() => {
    if (!getToken()) router.push('/login')
  }, [router])

  useEffect(() => {
    if (!loading) return undefined
    const timer = window.setInterval(() => {
      setProgress((current) => Math.min(current + 11, 92))
    }, 180)
    return () => window.clearInterval(timer)
  }, [loading])

  const triggerAgentAnalysis = async (resumeText) => {
    if (!resumeText) return
    setAgentLoading(true)
    setAgentError(null)
    setAgentResult(null)
    try {
      const res = await apiFetch('/api/v1/agents/analyze', {
        method: 'POST',
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jobDescription || '',
          candidate_name: candidateName || undefined,
        }),
      })
      if (!res.ok) throw new Error(`Agent analysis failed (${res.status})`)
      const data = await res.json()
      setAgentResult(data)
      toast('Multi-Agent Evaluation completed successfully')
    } catch (err) {
      setAgentError(err.message)
      toast(err.message, 'error')
    } finally {
      setAgentLoading(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Choose a PDF, DOCX, image, or text file first.')
      toast('Choose a file first', 'error')
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('candidate_name', candidateName)
    formData.append('job_description', jobDescription)

    setError(null)
    setAgentResult(null)
    setAgentError(null)
    setLoading(true)
    setProgress(10)
    try {
      const res = await apiFetch('/api/v1/data/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`Upload failed (${res.status})`)
      setProgress(100)
      const payload = await res.json()
      setResult(payload)
      toast(`Uploaded ${payload.filename} successfully`)
      if (payload.preview) {
        triggerAgentAnalysis(payload.preview)
      }
    } catch (err) {
      setError(err.message)
      toast(err.message, 'error')
    } finally {
      window.setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, 300)
    }
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <>
      <Head><title>Upload — TalentLens AI</title></Head>
      <main className="min-h-screen">
        <ResponsiveHeader
          title="Upload Intelligence"
          links={[
            { href: '/dashboard', label: 'Dashboard' },
            { href: '/analytics', label: 'Analytics' },
            { href: '/history', label: 'History' },
          ]}
          onLogout={handleLogout}
        />

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="glass-panel rounded-[2rem] p-6 md:p-8">
            <div className="grid gap-8 lg:grid-cols-[1.05fr_.95fr]">
              <div>
                <div className="inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-cyan-200">OCR + document intelligence</div>
                <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white sm:text-5xl">Drop a resume and get extracted text, ATS signals, and indexing.</h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">Supports scanned PDFs, PNG/JPG resumes, OCR fallback, and semantic indexing with progress feedback.</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="glass-card rounded-3xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">Formats</div><div className="mt-2 text-lg font-semibold text-white">PDF, DOCX, PNG</div></div>
                <div className="glass-card rounded-3xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">OCR</div><div className="mt-2 text-lg font-semibold text-white">Fallback enabled</div></div>
                <div className="glass-card rounded-3xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">Output</div><div className="mt-2 text-lg font-semibold text-white">ATS + semantic</div></div>
              </div>
            </div>
          </div>

          {error && <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div>}

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_.95fr]">
            <GlassCard title="Upload Resume" subtitle="Use drag-and-drop or pick a file from your device.">
              <form onSubmit={submit} className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm text-slate-300">Candidate name</label>
                  <input value={candidateName} onChange={(e) => setCandidateName(e.target.value)} placeholder="Jane Doe" className="w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none placeholder:text-slate-500" />
                </div>

                <div>
                  <label className="mb-2 block text-sm text-slate-300">Job description</label>
                  <textarea value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Paste the role requirements here if you want ATS scoring." className="min-h-[150px] w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none placeholder:text-slate-500" />
                </div>

                <UploadDropzone file={file} setFile={setFile} hint="Drop PDFs, DOCX files, or image resumes here" />

                <button type="submit" disabled={loading} className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60">
                  {loading ? 'Uploading…' : 'Upload and analyze'}
                </button>

                {loading && (
                  <div>
                    <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.22em] text-slate-400">
                      <span>Processing</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-emerald-300 transition-all" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                )}
              </form>
            </GlassCard>

            <GlassCard title="Analysis Result" subtitle="OCR confidence, ATS score, and extracted text preview.">
              {result ? (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="glass-card rounded-2xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">ATS score</div><div className="mt-1 text-3xl font-semibold text-emerald-200">{result.ats ? result.ats.score : '—'}</div></div>
                    <div className="glass-card rounded-2xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">Confidence</div><div className="mt-1 text-3xl font-semibold text-cyan-200">{Math.round((result.extraction_confidence || 0) * 100)}%</div></div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="glass-card rounded-2xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">OCR used</div><div className="mt-2 text-base text-white">{result.ocr_used ? 'Yes' : 'No'}</div></div>
                    <div className="glass-card rounded-2xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">Pages processed</div><div className="mt-2 text-base text-white">{result.pages_processed ?? '—'}</div></div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="glass-card rounded-2xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">File</div><div className="mt-2 text-sm text-white">{result.filename}</div></div>
                    <div className="glass-card rounded-2xl p-4"><div className="text-xs uppercase tracking-[0.22em] text-slate-400">Semantic indexed</div><div className="mt-2 text-sm text-white">{result.semantic_indexed ? 'Indexed' : 'Skipped'}</div></div>
                  </div>

                  <div className="glass-card rounded-2xl p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Extracted preview</div>
                    <p className="mt-3 max-h-[340px] overflow-auto whitespace-pre-wrap text-sm leading-7 text-slate-200">{result.preview}</p>
                  </div>

                  <div className="grid gap-3 text-sm text-slate-300 sm:grid-cols-2">
                    {result.ats?.prediction && <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><span className="text-slate-400">Predicted category:</span> <span className="text-white">{result.ats.prediction}</span></div>}
                    {result.ats?.matched_keywords?.length > 0 && <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><span className="text-slate-400">Matched keywords:</span> <span className="text-white">{result.ats.matched_keywords.join(', ')}</span></div>}
                    {result.ats?.missing_keywords?.length > 0 && <div className="rounded-2xl border border-white/10 bg-white/5 p-4"><span className="text-slate-400">Missing keywords:</span> <span className="text-white">{result.ats.missing_keywords.join(', ')}</span></div>}
                  </div>

                  {/* Multi-Agent AI Evaluation Panel */}
                  <div className="border-t border-white/10 pt-4 mt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h4 className="text-base font-semibold text-white">Multi-Agent AI Evaluation</h4>
                        <p className="text-xs text-slate-400">CrewAI pipelines (Summary, Skill Gap, Bias Detection)</p>
                      </div>
                      {result && !agentLoading && (
                        <button
                          onClick={() => triggerAgentAnalysis(result.preview)}
                          type="button"
                          className="rounded-full bg-cyan-950 border border-cyan-400/30 hover:border-cyan-400 px-3 py-1.5 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-900"
                        >
                          {agentResult ? 'Re-run Evaluation' : 'Run Evaluation'}
                        </button>
                      )}
                    </div>

                    {agentLoading && (
                      <div className="space-y-3 rounded-2xl border border-cyan-500/20 bg-cyan-950/20 p-4 animate-pulse">
                        <div className="flex items-center justify-between">
                          <div className="h-4 w-32 rounded bg-slate-700" />
                          <div className="h-5 w-20 rounded-full bg-slate-700" />
                        </div>
                        <div className="h-3 w-3/4 rounded bg-slate-700" />
                        <div className="h-3 w-1/2 rounded bg-slate-700" />
                        <div className="text-xs text-cyan-300 mt-2">Running CrewAI pipelines (Resume Analyzer, Skill Gap Specialist, Bias Detection Agent)...</div>
                      </div>
                    )}

                    {agentError && (
                      <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-4">
                        <div className="text-sm text-rose-200">Error: {agentError}</div>
                        <button
                          onClick={() => triggerAgentAnalysis(result.preview)}
                          type="button"
                          className="mt-2 text-xs font-semibold text-cyan-300 underline hover:text-cyan-200"
                        >
                          Retry Analysis
                        </button>
                      </div>
                    )}

                    {agentResult && (
                      <div className="space-y-4 rounded-2xl border border-white/10 bg-slate-900/40 p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recommendation</span>
                          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                            agentResult.hiring_recommendation?.toLowerCase().includes('strong')
                              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                              : agentResult.hiring_recommendation?.toLowerCase().includes('review')
                              ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                              : 'bg-slate-500/10 text-slate-300 border-slate-500/30'
                          }`}>
                            {agentResult.hiring_recommendation}
                          </span>
                        </div>

                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Agent Summary</span>
                          <p className="mt-1 text-sm text-slate-200 leading-relaxed">{agentResult.resume_summary}</p>
                        </div>

                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Skill Gaps Identified</span>
                          {agentResult.skill_gaps?.length > 0 ? (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {agentResult.skill_gaps.map((skill, idx) => (
                                <span key={idx} className="inline-flex items-center rounded-md bg-yellow-500/10 px-2 py-1 text-xs font-medium text-yellow-300 border border-yellow-500/20">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="mt-1 text-xs text-slate-400">No skill gaps identified</p>
                          )}
                        </div>

                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Linguistic Bias & Fairness Check</span>
                          {agentResult.bias_flags?.length > 0 ? (
                            <div className="mt-2 space-y-1">
                              {agentResult.bias_flags.map((flag, idx) => (
                                <div key={idx} className="flex items-start gap-1.5 rounded-lg border border-red-500/20 bg-red-500/5 px-2.5 py-1.5 text-xs text-red-200">
                                  <span className="text-red-400 font-bold">⚠</span>
                                  <span>{flag}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="mt-1.5 flex items-center gap-1.5 text-xs text-emerald-400">
                              <span className="font-semibold">✓</span>
                              <span>No linguistic bias detected</span>
                            </div>
                          )}
                        </div>

                        {agentResult.crew_output?.diagnostics && (
                          <div className="border-t border-white/5 pt-3 mt-3">
                            <details className="group cursor-pointer">
                              <summary className="flex items-center justify-between text-xs text-slate-400 hover:text-slate-300 select-none">
                                <span>Agent Execution Diagnostics</span>
                                <span className="text-[10px] uppercase tracking-widest text-slate-500 group-open:rotate-180 transition-transform">▼</span>
                              </summary>
                              <div className="mt-2 space-y-2 text-xs text-slate-300 bg-slate-950/40 p-2.5 rounded-xl border border-white/5">
                                <div className="flex justify-between">
                                  <span>Pipeline Mode:</span>
                                  <span className="font-semibold text-cyan-300 uppercase">{agentResult.mode}</span>
                                </div>
                                <div className="space-y-1.5">
                                  {agentResult.crew_output.diagnostics.agents?.map((agentInfo, idx) => (
                                    <div key={idx} className="flex flex-col gap-0.5 border-b border-white/5 pb-1 last:border-0 last:pb-0">
                                      <div className="flex justify-between">
                                        <span className="font-medium text-slate-200">{agentInfo.agent}</span>
                                        <span className={`px-1.5 py-0.2 rounded text-[10px] uppercase ${
                                          agentInfo.status === 'success' || agentInfo.status === 'completed'
                                            ? 'bg-emerald-500/10 text-emerald-400'
                                            : 'bg-rose-500/10 text-rose-400'
                                        }`}>
                                          {agentInfo.status}
                                        </span>
                                      </div>
                                      <div className="flex justify-between text-[10px] text-slate-500">
                                        <span>Latency: {agentInfo.latency_seconds ? `${agentInfo.latency_seconds.toFixed(2)}s` : '—'}</span>
                                        <span>Schema Valid: {agentInfo.schema_valid ? 'Yes' : 'No'}</span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </details>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ) : loading ? (
                <LoadingSkeleton className="h-[540px] rounded-3xl" />
              ) : (
                <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-sm text-slate-400">Upload a file to see parsing results, OCR confidence, and ATS analysis here.</div>
              )}
            </GlassCard>
          </div>
        </section>
      </main>
    </>
  )
}
