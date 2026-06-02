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
    setLoading(true)
    setProgress(10)
    try {
      const res = await apiFetch('/api/v1/data/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`Upload failed (${res.status})`)
      setProgress(100)
      const payload = await res.json()
      setResult(payload)
      toast(`Uploaded ${payload.filename} successfully`)
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
