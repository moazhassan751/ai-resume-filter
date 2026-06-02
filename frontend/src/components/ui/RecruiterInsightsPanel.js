import { GlassCard } from './GlassCard'

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-50">{value}</div>
      {hint && <div className="mt-1 text-sm text-slate-400">{hint}</div>}
    </div>
  )
}

export function RecruiterInsightsPanel({ insights, dashboard }) {
  const summary = insights?.summary || {}
  const funnel = dashboard?.chart_data?.funnel || insights?.hiring_funnel || {}
  const breakdown = dashboard?.chart_data?.score_breakdown || insights?.score_breakdown || {}

  return (
    <GlassCard title="Recruiter Insights" subtitle="Hiring funnel, score breakdown, and operational signals." className="h-full">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Stat label="Avg score" value={summary.average_score ?? '—'} hint="Across recent candidates" />
        <Stat label="Strong matches" value={summary.strong_matches ?? '—'} hint="Score ≥ 85" />
        <Stat label="Screened" value={funnel.screened ?? '—'} hint="Candidates reviewed" />
        <Stat label="Hired" value={funnel.hired ?? '—'} hint="Converted to offers" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {Object.entries(breakdown).map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
            <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label.replaceAll('_', ' ')}</div>
            <div className="mt-2 text-xl font-semibold text-cyan-200">{Math.round((value || 0) * 100)}%</div>
          </div>
        ))}
      </div>
    </GlassCard>
  )
}
