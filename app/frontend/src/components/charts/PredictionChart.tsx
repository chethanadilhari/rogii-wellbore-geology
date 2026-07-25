import {
  Brush,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ChartSeriesPoint } from '../../types/well';
import { EmptyState, LoadingBanner } from '../common/StatusBadge';

interface PredictionChartProps {
  data: ChartSeriesPoint[];
  loading?: boolean;
}

export function PredictionChart({ data, loading = false }: PredictionChartProps) {
  if (loading) {
    return <LoadingBanner label="Preparing chart…" />;
  }

  if (data.length === 0) {
    return (
      <EmptyState
        title="Chart unavailable"
        description="Full-well predictions are required to plot TVT versus MD."
      />
    );
  }

  return (
    <div className="chart-container" role="img" aria-label="TVT versus MD chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 20, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d5dbe3" />
          <XAxis
            dataKey="MD"
            type="number"
            domain={['dataMin', 'dataMax']}
            tick={{ fontSize: 12 }}
            label={{ value: 'MD', position: 'insideBottom', offset: -2 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'TVT', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value, name) => [
              value == null ? '—' : Number(value).toFixed(3),
              name === 'knownTvt' ? 'Known TVT' : 'Predicted TVT',
            ]}
            labelFormatter={(label) => `MD: ${label}`}
          />
          <Legend
            formatter={(value) =>
              value === 'knownTvt' ? 'Known TVT' : 'Predicted TVT'
            }
          />
          <Line
            type="monotone"
            dataKey="knownTvt"
            stroke="#1b4f8a"
            dot={false}
            strokeWidth={2}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="predictedTvt"
            stroke="#c9851a"
            dot={false}
            strokeWidth={2}
            connectNulls={false}
            isAnimationActive={false}
          />
          {data.length > 80 ? (
            <Brush dataKey="MD" height={24} stroke="#1b4f8a" />
          ) : null}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
