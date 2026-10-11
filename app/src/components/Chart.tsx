'use client';

import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, ScatterChart, Scatter,
} from 'recharts';

const COLORS = ['#29B5E8', '#FF6B35', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#6366F1', '#EC4899'];

interface ChartProps {
  data: Record<string, any>[];
  type: 'bar' | 'line' | 'area' | 'pie' | 'scatter';
  xKey: string;
  yKeys: { key: string; name: string; color?: string }[];
  title?: string;
  height?: number;
  stacked?: boolean;
  xName?: string;
  yDomain?: [number | 'auto', number | 'auto'];
}

export function Chart({ data, type, xKey, yKeys, title, height = 300, stacked = false, xName = 'x', yDomain = [0, 100] }: ChartProps) {
  const renderChart = () => {
    switch (type) {
      case 'scatter':
        return (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" dataKey={xKey} name={xName} unit="%" domain={[0, 100]} />
            <YAxis type="number" dataKey={yKeys[0].key} name={yKeys[0].name} domain={yDomain} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
            <Scatter name={yKeys[0].name} data={data} fill={COLORS[0]} />
          </ScatterChart>
        );
      case 'bar':
        return (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {yKeys.map((y, i) => (
              <Bar key={y.key} dataKey={y.key} name={y.name} fill={y.color || COLORS[i % COLORS.length]} stackId={stacked ? 'stack' : undefined} />
            ))}
          </BarChart>
        );
      case 'line':
        return (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {yKeys.map((y, i) => (
              <Line key={y.key} type="monotone" dataKey={y.key} name={y.name} stroke={y.color || COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
            ))}
          </LineChart>
        );
      case 'area':
        return (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {yKeys.map((y, i) => (
              <Area key={y.key} type="monotone" dataKey={y.key} name={y.name} fill={y.color || COLORS[i % COLORS.length]} stroke={y.color || COLORS[i % COLORS.length]} fillOpacity={0.3} />
            ))}
          </AreaChart>
        );
      case 'pie':
        return (
          <PieChart>
            <Pie data={data} dataKey={yKeys[0].key} nameKey={xKey} cx="50%" cy="50%" outerRadius={100} label>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        );
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      {title && <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>}
      {data.length === 0 ? <p role="status" className="text-sm text-slate-500">No observations available.</p> : (
        <ResponsiveContainer width="100%" height={height}>
          {renderChart()}
        </ResponsiveContainer>
      )}
    </div>
  );
}
