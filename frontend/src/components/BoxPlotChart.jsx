import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function formatSalary(val) {
  if (val == null) return "N/A";
  return `$${Math.round(val / 1000).toLocaleString()}K`;
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="bg-gray-900 text-gray-100 rounded-lg px-4 py-3 shadow-lg text-sm space-y-1">
      <p className="font-semibold text-white">{d.name}</p>
      <p>Max Salary: {formatSalary(d.max_salary)}</p>
      <p>Avg + 1 SD: {formatSalary(d.avg_mid + d.std_dev)}</p>
      <p>Mean: {formatSalary(d.avg_mid)}</p>
      <p>Avg - 1 SD: {formatSalary(d.avg_mid - d.std_dev)}</p>
      <p>Min Salary: {formatSalary(d.min_salary)}</p>
      <p className="text-gray-400 pt-1">{d.job_count} jobs</p>
    </div>
  );
}

function HorizontalBoxPlotShape(props) {
  const { x, y, width, height, payload } = props;
  if (!payload) return null;

  const { min_salary, max_salary, avg_mid, std_dev, _xDomain } = payload;
  if (avg_mid == null) return null;

  const [domainMin, domainMax] = _xDomain;
  const range = domainMax - domainMin;
  if (range === 0) return null;

  // For a horizontal bar layout={vertical} with numeric XAxis:
  // x = left edge of bar (plot area left), width = pixel width of bar value
  // But we set _boxRange to span the full domain, so x = plot left, width = full plot width
  const toX = (val) => {
    const ratio = (val - domainMin) / range;
    return x + ratio * width;
  };

  const boxLeft = toX(avg_mid - std_dev);
  const boxRight = toX(avg_mid + std_dev);
  const boxWidth = boxRight - boxLeft;
  const meanX = toX(avg_mid);
  const whiskerLeft = toX(min_salary);
  const whiskerRight = toX(max_salary);
  const cy = y + height / 2;
  const capH = height * 0.5;

  return (
    <g>
      {/* Left whisker line */}
      <line
        x1={whiskerLeft}
        y1={cy}
        x2={boxLeft}
        y2={cy}
        stroke="#6366f1"
        strokeWidth={2}
      />
      {/* Left whisker cap */}
      <line
        x1={whiskerLeft}
        y1={cy - capH / 2}
        x2={whiskerLeft}
        y2={cy + capH / 2}
        stroke="#6366f1"
        strokeWidth={2}
      />
      {/* Box */}
      <rect
        x={boxLeft}
        y={y + height * 0.1}
        width={Math.max(boxWidth, 1)}
        height={height * 0.8}
        fill="#818cf8"
        fillOpacity={0.6}
        stroke="#6366f1"
        strokeWidth={2}
        rx={3}
      />
      {/* Mean line */}
      <line
        x1={meanX}
        y1={y + height * 0.1}
        x2={meanX}
        y2={y + height * 0.9}
        stroke="#4f46e5"
        strokeWidth={3}
      />
      {/* Right whisker line */}
      <line
        x1={boxRight}
        y1={cy}
        x2={whiskerRight}
        y2={cy}
        stroke="#6366f1"
        strokeWidth={2}
      />
      {/* Right whisker cap */}
      <line
        x1={whiskerRight}
        y1={cy - capH / 2}
        x2={whiskerRight}
        y2={cy + capH / 2}
        stroke="#6366f1"
        strokeWidth={2}
      />
    </g>
  );
}

const ROW_HEIGHT = 50;
const MIN_CHART_HEIGHT = 250;

export default function BoxPlotChart({ data }) {
  if (!data || data.length === 0) return null;

  // Compute X domain (salary axis) from all data points
  const allMin = Math.min(...data.map((d) => d.min_salary ?? Infinity));
  const allMax = Math.max(...data.map((d) => d.max_salary ?? -Infinity));
  const padding = (allMax - allMin) * 0.1 || 10000;
  const domainMin = Math.max(0, allMin - padding);
  const domainMax = allMax + padding;

  // Inject domain info so the custom shape can compute pixel positions
  const chartData = data.map((d) => ({
    ...d,
    _boxRange: domainMax - domainMin,
    _xDomain: [domainMin, domainMax],
  }));

  // Scale height based on number of items so each row is readable
  const chartHeight = Math.max(MIN_CHART_HEIGHT, data.length * ROW_HEIGHT + 60);

  return (
    <div style={{ minWidth: 600 }}>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart
          data={chartData}
          layout="vertical"
          margin={{ left: 20, right: 30, top: 10, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
          <YAxis
            dataKey="name"
            type="category"
            tick={{ fill: "#6b7280", fontSize: 13 }}
            width={140}
            interval={0}
          />
          <XAxis
            type="number"
            domain={[domainMin, domainMax]}
            tick={{ fill: "#6b7280", fontSize: 12 }}
            tickFormatter={(v) => `$${Math.round(v / 1000)}K`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="_boxRange"
            shape={<HorizontalBoxPlotShape />}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
