import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const ACCENT = '#10b981'
const MUTED  = '#374151'

const METRIC_LABELS = {
  accuracy:  'Accuracy',
  precision: 'Precision',
  recall:    'Recall',
  f1_score:  'F1 Score',
  f1_macro:  'F1 Macro',
}

export default function PerformanceChart({ metrics }) {
  if (!metrics) {
    return (
      <div style={{ color: '#6b7280', textAlign: 'center', padding: '60px 0', fontSize: 14 }}>
        No metrics loaded yet — train a model first.
      </div>
    )
  }

  const scalar = Object.entries(metrics)
    .filter(([k, v]) => typeof v === 'number' && METRIC_LABELS[k])
    .map(([k, v]) => ({ name: METRIC_LABELS[k] || k, value: parseFloat((v * 100).toFixed(1)) }))

  if (scalar.length === 0) return null

  return (
    <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
      {/* Bar chart */}
      <div style={{ flex: '1 1 340px' }}>
        <p style={{ color: '#9ca3af', fontSize: 12, marginBottom: 8, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Metric Breakdown
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={scalar} barSize={28}>
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 8 }}
              labelStyle={{ color: '#f9fafb' }}
              formatter={(v) => [`${v}%`, '']}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {scalar.map((_, i) => (
                <Cell key={i} fill={i === 0 ? ACCENT : MUTED} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Radar chart */}
      {scalar.length >= 3 && (
        <div style={{ flex: '1 1 280px' }}>
          <p style={{ color: '#9ca3af', fontSize: 12, marginBottom: 8, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Model Radar
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={scalar}>
              <PolarGrid stroke="#1f2937" />
              <PolarAngleAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar dataKey="value" stroke={ACCENT} fill={ACCENT} fillOpacity={0.25} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}