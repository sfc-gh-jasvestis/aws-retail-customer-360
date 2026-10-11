import { ReactNode } from 'react';

export interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { direction: 'up' | 'down' | 'flat'; value: string };
  status?: 'success' | 'warning' | 'danger' | 'neutral';
  icon?: ReactNode;
}

export function KPICard({ title, value, subtitle, trend, status = 'neutral', icon }: KPICardProps) {
  const statusColors = {
    success: 'border-l-emerald-500 bg-emerald-50',
    warning: 'border-l-amber-500 bg-amber-50',
    danger: 'border-l-red-500 bg-red-50',
    neutral: 'border-l-slate-300 bg-white',
  };

  const trendColors = {
    up: 'text-emerald-600',
    down: 'text-red-600',
    flat: 'text-slate-500',
  };

  return (
    <div className={`rounded-lg border border-slate-200 border-l-4 p-4 shadow-sm ${statusColors[status]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
          {subtitle && <p className="mt-0.5 text-sm text-slate-600">{subtitle}</p>}
          {trend && (
            <p className={`mt-1 text-xs font-medium ${trendColors[trend.direction]}`}>
              {trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '—'} {trend.value}
            </p>
          )}
        </div>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
    </div>
  );
}
