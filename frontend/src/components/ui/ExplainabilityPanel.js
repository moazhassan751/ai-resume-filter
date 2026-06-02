import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { apiFetch } from '../../lib/auth'
import { useToast } from './ToastProvider'
import { GlassCard } from './GlassCard'
import {
  ATSRadarChart,
  SkillGapChart,
  ScoreBreakdownChart,
} from './AnalyticsCharts'

function MetricPill({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</div>
      <div className="mt-1 text-lg font-semibold text-slate-50">{value}</div>
    </div>
  )
}

export function ExplainabilityPanel() {
  const { toast } = useToast()
  const [resumeText, setResumeText] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const radarData = useMemo(() => {
    if (!result) return []
    return [
      { name: 'Confidence', value: Math.round((result.prediction_confidence || 0) * 100) },
      { name: 'Semantic', value: Math.round((result.semantic_overlap || 0) * 100) },
      { name: 'TF-IDF', value: Math.min(100, result.top_tfidf_features?.length ? 100 : 10) },
      { name: 'SHAP', value: Math.min(100, result.shap_explanations?.length ? 100 : 10) },
      { name: 'Coverage', value: Math.min(100, (result.matched_terms?.length || 0) * 8) },
    ]
  }, [result])

  const skillGapData = useMemo(() => (result?.skill_gaps || []).slice(0, 8).map((name, index) => ({ name, value: 100 - index * 10 })), [result])
  const scoreBreakdownData = useMemo(() => {
    if (!result) return []
    return [
      { name: 'Confidence', value: Math.round((result.prediction_confidence || 0) * 100) },
      { name: 'Coverage', value: Math.round((result.semantic_overlap || 0) * 100) },
      { name: 'Keyword Fit', value: Math.min(100, (result.top_keywords?.length || 0) * 12) },
    ]
  }, [result])

  const analyze = async () => {
    if (!resumeText.trim()) return toast('Paste resume text first', 'error')
    setLoading(true)
    try {
      const res = await apiFetch('/api/v1/analytics/explain', {
        method: 'POST',
        body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription }),
      })
      if (!res.ok) throw new Error(`Explainability failed (${res.status})`)
      setResult(await res.json())
      toast('Explainability analysis complete')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassCard title="Explainable AI" subtitle="Paste a resume and job description to inspect model signals, top TF-IDF features, and SHAP-style contributions." className="h-full">
      <div className="grid gap-4 lg:grid-cols-[1.2fr_.8fr]">
        <div className="space-y-4">
          <textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste resume text here..."
            className="min-h-[160px] w-full rounded-2xl border border-white/10 bg-slate-950/70 p-4 text-sm text-slate-100 outline-none placeholder:text-slate-500"
          />
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste job description here..."
            className="min-h-[130px] w-full rounded-2xl border border-white/10 bg-slate-950/70 p-4 text-sm text-slate-100 outline-none placeholder:text-slate-500"
          />
          <button onClick={analyze} disabled={loading} className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60">
            {loading ? 'Analyzing…' : 'Run explanation'}
          </button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <MetricPill label="Confidence" value={result ? `${Math.round((result.prediction_confidence || 0) * 100)}%` : '—'} />
            <MetricPill label="Semantic overlap" value={result ? `${Math.round((result.semantic_overlap || 0) * 100)}%` : '—'} />
          </div>
          <MetricPill label="Top keywords" value={result?.top_keywords?.slice(0, 3)?.join(', ') || '—'} />
          <MetricPill label="Skill gaps" value={result?.skill_gaps?.slice(0, 3)?.join(', ') || '—'} />
        </div>
      </div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-6 grid gap-5 lg:grid-cols-2">
          <GlassCard title="ATS Radar" subtitle="Confidence, semantic fit, TF-IDF richness, SHAP coverage." className="glass-card">
            <ATSRadarChart data={radarData} />
          </GlassCard>
          <GlassCard title="Skill Gaps" subtitle="Missing terms inferred from the job description." className="glass-card">
            <SkillGapChart gaps={result.skill_gaps || []} />
          </GlassCard>
          <GlassCard title="Ranking Score Breakdown" subtitle="Composite view of explainability signals." className="glass-card lg:col-span-2">
            <ScoreBreakdownChart data={scoreBreakdownData} />
          </GlassCard>
        </motion.div>
      )}

      {result && (
        <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(result.top_tfidf_features || []).slice(0, 6).map((feature) => (
            <div key={feature.feature} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{feature.feature}</div>
              <div className="mt-2 text-lg font-semibold text-slate-50">{feature.importance}</div>
              <div className="mt-1 text-xs text-slate-400">Resume {feature.resume_frequency} · Job {feature.job_frequency}</div>
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  )
}
