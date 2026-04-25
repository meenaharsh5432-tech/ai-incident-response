import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

function fmtSeconds(seconds) {
  if (seconds == null) return '--'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

export default function MTTRChart({ data = [] }) {
  const chartData = data.map((item) => ({ ...item, label: fmtSeconds(item.avg_mttr) }))

  return (
    <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
        Avg MTTR by Service
      </h3>
      {chartData.length === 0 ? (
        <p className="py-10 text-center text-sm text-slate-400">No resolved incidents yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="service" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(value) => fmtSeconds(value)} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: '#020617', border: '1px solid rgba(148, 163, 184, 0.2)', borderRadius: 16 }}
              labelStyle={{ color: '#cbd5e1' }}
              formatter={(value) => [fmtSeconds(value), 'Avg MTTR']}
              cursor={{ fill: 'rgba(56, 189, 248, 0.08)' }}
            />
            <Bar dataKey="avg_mttr" fill="#38bdf8" radius={[10, 10, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
