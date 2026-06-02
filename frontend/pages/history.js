import { useEffect, useState } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'

export default function HistoryPage() {
  const router = useRouter()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!getToken()) { router.push('/login'); return }

    const load = async () => {
      setLoading(true)
      try {
        const res = await apiFetch('/api/v1/data/history?limit=25')
        if (res.ok) {
          const data = await res.json()
          setItems(data.items || [])
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [router])

  return (
    <>
      <Head><title>Candidate History — TalentLens AI</title></Head>
      <main className="min-h-screen">
        <ResponsiveHeader
          title="Candidate History"
          links={[
            { href: '/dashboard', label: 'Dashboard' },
            { href: '/analytics', label: 'Analytics' },
            { href: '/upload', label: 'Upload' },
          ]}
          onLogout={() => { logout(); router.push('/login') }}
        />

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="glass-panel rounded-[2rem] p-6 md:p-8">
            <div className="max-w-2xl">
              <div className="text-xs uppercase tracking-[0.28em] text-cyan-200/80">TalentLens AI</div>
              <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">Recent uploads and ATS scoring history.</h2>
              <p className="mt-3 text-sm leading-7 text-slate-300 sm:text-base">Review the latest candidate files and scan outcomes in a responsive, searchable-ready card grid.</p>
            </div>

            {error && <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div>}

            {loading ? (
              <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-sm text-slate-400">Loading history…</div>
            ) : items.length === 0 ? (
              <div className="mt-6 rounded-2xl border border-dashed border-white/10 bg-white/5 p-8 text-sm text-slate-400">No candidate history yet.</div>
            ) : (
              <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {items.map((item, index) => (
                  <div className="glass-card rounded-3xl p-5" key={`${item.filename || 'item'}-${index}`}>
                    <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">Candidate</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{item.candidate_name || 'Unnamed candidate'}</div>
                    <div className="mt-2 text-sm text-slate-300">File: {item.filename}</div>
                    <div className="mt-2 text-sm text-slate-300">ATS score: {item.ats_score ?? 'N/A'}</div>
                    <div className="mt-2 text-sm text-slate-300">Uploaded by: {item.uploaded_by || 'system'}</div>
                    {item.job_description && <div className="mt-2 text-sm leading-6 text-slate-400">Job: {item.job_description.slice(0, 180)}{item.job_description.length > 180 ? '...' : ''}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  )
}
