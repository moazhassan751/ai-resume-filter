import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import Head from 'next/head'
import { useRouter } from 'next/router'
import { apiFetch, getToken, logout } from '../src/lib/auth'
import { GlassCard } from '../src/components/ui/GlassCard'
import { LoadingSkeleton } from '../src/components/ui/LoadingSkeleton'
import { ExplainabilityPanel } from '../src/components/ui/ExplainabilityPanel'
import { RecruiterInsightsPanel } from '../src/components/ui/RecruiterInsightsPanel'
import { ResponsiveHeader } from '../src/components/ui/ResponsiveHeader'
import { ScoreBreakdownChart } from '../src/components/ui/AnalyticsCharts'

function StatCard({ label, value, hint }) {
  return (
    <div className="glass-card rounded-3xl p-5">
      <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-white">{value}</div>
      {hint && <div className="mt-1 text-sm text-slate-400">{hint}</div>}
    </div>
  )
}

export default function AnalyticsPage() {
  const router = useRouter()
  const [metrics, setMetrics] = useState(null)
  const [report, setReport] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [taskId, setTaskId] = useState(null)
  const [taskState, setTaskState] = useState(null)

  useEffect(() => {
    if (!getToken()) {
      router.push('/login')
      return
    }

    const load = async () => {
      setLoading(true)
      try {
        const [metricsRes, reportRes, dashboardRes] = await Promise.all([
          apiFetch('/api/v1/model/metrics'),
          apiFetch('/api/v1/model/report'),
          apiFetch('/api/v1/analytics/dashboard'),
        ])

        if (metricsRes.ok) setMetrics(await metricsRes.json())
        if (reportRes.ok) setReport(await reportRes.json())
        if (dashboardRes.ok) setDashboard(await dashboardRes.json())
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [router])

  useEffect(() => {
    if (!taskId) return undefined

    const poll = async () => {
      try {
        const res = await apiFetch(`/api/v1/model/train-status/${taskId}`)
        if (res.ok) setTaskState(await res.json())
      } catch (err) {
        setTaskState({ status: 'error', error: err.message })
      }
    }

    poll()
    const id = setInterval(poll, 4000)
    return () => clearInterval(id)
  }, [taskId])

  const matrix = report?.confusion_matrix || []
  const labels = useMemo(() => report?.labels || [], [report])
  const reportRows = useMemo(() => {
    const data = report?.classification_report || {}
    return labels.map((label) => ({
      label,
      precision: data[label]?.precision,
      recall: data[label]?.recall,
      f1: data[label]?.f1-score,
      support: data[label]?.support,
    }))
  }, [report, labels])

  const startTraining = async () => {
    try {
      const res = await apiFetch('/api/v1/model/train-async', { method: 'POST' })
      if (res.ok) {
        const payload = await res.json()
        setTaskId(payload.task_id)
        setTaskState({ status: payload.status })
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const breakdownData = dashboard?.chart_data?.score_breakdown
    ? Object.entries(dashboard.chart_data.score_breakdown).map(([name, value]) => ({ name, value: Math.round((value || 0) * 100) }))
    : []

  return (
    <>
      <Head><title>Analytics — TalentLens AI</title></Head>
      <main className="min-h-screen">
        <ResponsiveHeader
          title="Analytics Control Center"
          links={[
            { href: '/dashboard', label: 'Dashboard' },
            { href: '/upload', label: 'Upload' },
            { href: '/history', label: 'History' },
          ]}
          onLogout={handleLogout}
        />

        <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Accuracy" value={metrics?.accuracy ? `${(metrics.accuracy * 100).toFixed(1)}%` : '—'} hint="Most recent saved metrics" />
            <StatCard label="F1 Macro" value={metrics?.f1_macro ? `${(metrics.f1_macro * 100).toFixed(1)}%` : '—'} hint="Balanced across classes" />
            <StatCard label="Evaluation Samples" value={report?.samples?.toLocaleString?.() || '—'} hint="Holdout set size" />
            <StatCard label="Training Status" value={taskState?.status || 'idle'} hint={taskId ? `Task ${taskId.slice(0, 8)}…` : 'Trigger a new run'} />
          </div>

          {error && <div className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div>}

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <GlassCard title="Model Performance" subtitle="Saved metrics and chart summary." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">Model metrics are available via the dashboard and classified report endpoints.</div>}
            </GlassCard>
            <GlassCard title="Score Breakdown" subtitle="ATS, semantic, skill, experience, and education signals." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : breakdownData.length ? <ScoreBreakdownChart data={breakdownData} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">No score breakdown values yet.</div>}
            </GlassCard>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <GlassCard title="Async Training" subtitle="Dispatch a model training job against the current dataset." className="h-full">
              <p className="text-sm text-slate-300">Trigger a Celery run and monitor progress from this panel.</p>
              <button onClick={startTraining} className="mt-4 rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-200">Start training run</button>
              {taskId && <p className="mt-4 text-sm text-slate-400">Task ID: {taskId}</p>}
              {taskState?.result && <pre className="mt-4 overflow-auto rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-xs text-slate-200">{JSON.stringify(taskState.result, null, 2)}</pre>}
            </GlassCard>

            <GlassCard title="Recruiter Insights" subtitle="Operational funnel and score balance." className="h-full">
              {loading ? <LoadingSkeleton className="h-[280px] rounded-3xl" /> : dashboard ? <RecruiterInsightsPanel insights={dashboard?.recruiter_insights || {}} dashboard={dashboard} /> : <div className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-6 text-sm text-slate-400">Recruiter insights will populate after data is available.</div>}
            </GlassCard>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <GlassCard title="Confusion Matrix" subtitle="Actual vs predicted classes." className="h-full xl:col-span-2">
              {loading ? <LoadingSkeleton className="h-[240px] rounded-3xl" /> : matrix.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-slate-400">
                        <th className="px-3 py-3">Actual / Predicted</th>
                        {labels.map((label) => <th key={label} className="px-3 py-3">{label}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {matrix.map((row, index) => (
                        <tr key={labels[index] || index} className="border-b border-white/5">
                          <th className="px-3 py-3 font-medium text-slate-300">{labels[index]}</th>
                          {row.map((value, colIndex) => <td key={colIndex} className="px-3 py-3 text-slate-100">{value}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="text-sm text-slate-400">No confusion matrix available yet.</div>}
            </GlassCard>

            <GlassCard title="Classification Report" subtitle="Precision, recall, and F1 per class." className="h-full xl:col-span-2">
              {loading ? <LoadingSkeleton className="h-[240px] rounded-3xl" /> : reportRows.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-slate-400">
                        <th className="px-3 py-3">Label</th>
                        <th className="px-3 py-3">Precision</th>
                        <th className="px-3 py-3">Recall</th>
                        <th className="px-3 py-3">F1</th>
                        <th className="px-3 py-3">Support</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportRows.map((row) => (
                        <tr key={row.label} className="border-b border-white/5">
                          <td className="px-3 py-3 text-slate-100">{row.label}</td>
                          <td className="px-3 py-3 text-slate-300">{row.precision?.toFixed?.(3) ?? '—'}</td>
                          <td className="px-3 py-3 text-slate-300">{row.recall?.toFixed?.(3) ?? '—'}</td>
                          <td className="px-3 py-3 text-slate-300">{row.f1?.toFixed?.(3) ?? '—'}</td>
                          <td className="px-3 py-3 text-slate-300">{row.support ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="text-sm text-slate-400">No classification report available yet.</div>}
            </GlassCard>
          </div>

          <div className="mt-6">
            <ExplainabilityPanel />
          </div>
        </section>
      </main>
    </>
  )
}
