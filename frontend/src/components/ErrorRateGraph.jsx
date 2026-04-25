import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export default function ErrorRateGraph({ data = [] }) {
  return (
    <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
        Error Rate - Last 24 Hours
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="errGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis dataKey="hour" tick={{ fill: '#94a3b8', fontSize: 11 }} interval={3} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} allowDecimals={false} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#020617', border: '1px solid rgba(148, 163, 184, 0.2)', borderRadius: 16 }}
            labelStyle={{ color: '#cbd5e1' }}
            itemStyle={{ color: '#67e8f9' }}
          />
          <Area type="monotone" dataKey="count" stroke="#22d3ee" strokeWidth={3} fill="url(#errGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
