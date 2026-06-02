import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar,
  XAxis, YAxis, LineChart, Line, CartesianGrid, AreaChart, Area,
} from 'recharts'

const COLORS = ['#10b981', '#38bdf8', '#f59e0b', '#a78bfa', '#f472b6', '#22c55e']

export function ATSRadarChart({ data }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
        <Radar dataKey="value" stroke="#22c55e" fill="#22c55e" fillOpacity={0.18} />
      </RadarChart>
    </ResponsiveContainer>
  )
}

export function SkillGapChart({ gaps = [] }) {
  if (!gaps.length) return null
  const data = gaps.map((item, index) => ({ name: item, value: Math.max(20, 100 - index * 8) }))
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
        <XAxis type="number" hide />
        <YAxis dataKey="name" type="category" width={100} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }} />
        <Bar dataKey="value" radius={[0, 12, 12, 0]} fill="#38bdf8" />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function CategoryDistributionChart({ data = [] }) {
  if (!data.length) return null
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={70} outerRadius={110} paddingAngle={2}>
          {data.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
        </Pie>
        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function HiringFunnelChart({ data = [] }) {
  if (!data.length) return null
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
        <XAxis type="number" hide />
        <YAxis dataKey="name" type="category" width={110} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }} />
        <Bar dataKey="value" radius={[0, 14, 14, 0]} fill="#10b981" />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function SemanticSimilarityChart({ data = [] }) {
  if (!data.length) return null
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="semanticFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.45} />
            <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }} />
        <Area type="monotone" dataKey="value" stroke="#38bdf8" fill="url(#semanticFill)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ScoreBreakdownChart({ data = [] }) {
  if (!data.length) return null
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="name" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)' }} />
        <Bar dataKey="value" radius={[10, 10, 0, 0]} fill="#a78bfa" />
      </BarChart>
    </ResponsiveContainer>
  )
}
