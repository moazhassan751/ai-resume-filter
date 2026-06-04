import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { GlassCard } from '../src/components/ui/GlassCard'
import { LoadingSkeleton } from '../src/components/ui/LoadingSkeleton'
import { ExplainabilityPanel } from '../src/components/ui/ExplainabilityPanel'
import { RecruiterInsightsPanel } from '../src/components/ui/RecruiterInsightsPanel'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'
import {
  ATSRadarChart,
  CategoryDistributionChart,
  HiringFunnelChart,
  SemanticSimilarityChart,
  ScoreBreakdownChart,
} from '../src/components/ui/AnalyticsCharts'

function StatCard({ label, value, hint, accent = 'text-cyan-200' }) {
  return (
    <div className="glass-card rounded-3xl p-5">
      <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{label}</div>
      <div className={`mt-2 text-3xl font-semibold ${accent}`}>{value}</div>
      {hint && <div className="mt-1 text-sm text-slate-400">{hint}</div>}
    </div>
  )
}

export default function Dashboard() {
  const router = useRouter()
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!getToken()) {
      router.push('/login')
      return
    }

    const load = async () => {
      setLoading(true)
      try {
        const res = await apiFetch('/api/v1/analytics/dashboard')
        if (!res.ok) throw new Error(`Analytics unavailable (${res.status})`)
        setDashboard(await res.json())
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [router])

  const recruiter = dashboard?.recruiter_insights || {}
  const chartData = dashboard?.chart_data || {}

  const summaryCards = [
    { label: 'Accuracy', value: dashboard?.model_metrics?.accuracy ? `${(dashboard.model_metrics.accuracy * 100).toFixed(1)}%` : '—', hint: 'Saved model metrics' },
    { label: 'Samples', value: dashboard?.model_metrics?.samples?.toLocaleString?.() || '—', hint: 'Evaluation records' },
    { label: 'Strong matches', value: recruiter?.summary?.strong_matches ?? '—', hint: 'Recruiter-ready candidates' },
    { label: 'Average score', value: recruiter?.summary?.average_score ?? '—', hint: 'Recent candidate pool' },
  ]

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <>
      <Head><title>Dashboard — TalentLens AI</title></Head>
      <main className="min-h-screen">
        <ResponsiveHeader
          title="Recruitment Intelligence Dashboard"
          links={[
            { href: '/dashboard', label: 'Dashboard' },
            { href: '/upload', label: 'Upload' },
            { href: '/search', label: 'Search' },
            { href: '/ranking', label: 'Ranking' },
            { href: '/rag', label: 'AI Assistant' },
            { href: '/analytics', label: 'Analytics' },
            { href: '/history', label: 'History' },
          ]}
          onLogout={handleLogout}
        />

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="bg-grid glass-panel overflow-hidden rounded-[2rem] border-white/10 p-6 md:p-8">
            <div className="grid gap-8 lg:grid-cols-[1.2fr_.8fr] lg:items-end">
              <div>
                <div className="inline-flex rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-emerald-200">Explainable ranking, OCR intelligence, and analytics</div>
                <h2 className="mt-5 max-w-3xl text-3xl font-semibold tracking-tight text-white sm:text-5xl">Modern AI SaaS dashboard for recruiters.</h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                  Track model quality, recruiter funnel health, semantic alignment, and feature explanations with responsive visual analytics.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {summaryCards.map((card) => <StatCard key={card.label} {...card} />)}
              </div>
            </div>
          </div>

          {error && <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div>}

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <GlassCard title="Recruiter Insights" subtitle="Operational funnel and score breakdown." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : (dashboard ? <RecruiterInsightsPanel insights={recruiter} dashboard={dashboard} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">No recruiter insights yet. Upload resumes to populate the dashboard.</div>)}
            </GlassCard>

            <GlassCard title="ATS Radar" subtitle="Semantic fit, keyword coverage, and scoring emphasis." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : Object.keys(chartData.score_breakdown || {}).length > 0 ? <ATSRadarChart data={Object.entries(chartData.score_breakdown || {}).map(([name, value]) => ({ name, value: Math.round((value || 0) * 100) }))} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">Radar data appears after model metrics are available.</div>}
            </GlassCard>

            <GlassCard title="Hiring Funnel" subtitle="Screening throughput and conversion health." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : (chartData.funnel?.length ? <HiringFunnelChart data={chartData.funnel || []} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">No funnel data yet. The chart will populate after candidate activity is recorded.</div>)}
            </GlassCard>

            <GlassCard title="Category Distribution" subtitle="Model labels across the evaluation set." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : (chartData.category_distribution?.length ? <CategoryDistributionChart data={chartData.category_distribution || []} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">Category distribution will appear once classification samples are loaded.</div>)}
            </GlassCard>

            <GlassCard title="Semantic Similarity" subtitle="Recent recruiter pool similarity pattern." className="h-full xl:col-span-2">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : (chartData.semantic_similarity?.length ? <SemanticSimilarityChart data={chartData.semantic_similarity || []} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">Semantic trend data is empty for this dataset.</div>)}
            </GlassCard>

            <GlassCard title="Score Breakdown" subtitle="Composite signal balance across the stack." className="h-full xl:col-span-2">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : Object.keys(chartData.score_breakdown || {}).length > 0 ? <ScoreBreakdownChart data={Object.entries(chartData.score_breakdown || {}).map(([name, value]) => ({ name, value: Math.round((value || 0) * 100) }))} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">Score breakdown values appear here once the analytics endpoint returns data.</div>}
            </GlassCard>
          </div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
            <ExplainabilityPanel />
          </motion.div>
        </section>
      </main>
    </>
  )
}