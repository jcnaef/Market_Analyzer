import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, Legend,
} from "recharts";
import { getDashboardStats } from "../api";
import StatCard from "../components/StatCard";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";
import useIsMobile from "../hooks/useIsMobile";

const CATEGORY_COLORS = {
  Languages: "#6366f1",
  Frameworks_Libs: "#3f3f46",
  Tools_Infrastructure: "#3f3f46",
  Concepts: "#3f3f46",
};

const DARK_TOOLTIP = {
  contentStyle: { backgroundColor: "#09090b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6 },
  itemStyle: { color: "#e4e4e7" },
  labelStyle: { color: "#e4e4e7" },
};

function formatSalary(val) {
  if (!val) return "N/A";
  return `$${Math.round(val / 1000)}K`;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    getDashboardStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!stats) return null;

  const skillChartData = stats.top_skills.map((s) => ({
    name: s.skill,
    count: s.count,
    fill: CATEGORY_COLORS[s.category] || "#6366f1",
  }));

  const remoteData = [
    { name: "Remote", value: stats.remote_count, fill: "#6366f1" },
    { name: "Onsite", value: stats.onsite_count, fill: "#3f3f46" },
  ];

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-medium tracking-tight text-zinc-100">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
        <StatCard title="Total Jobs" value={stats.total_jobs.toLocaleString()} />
        <StatCard title="Companies" value={stats.total_companies.toLocaleString()} />
        <StatCard title="Skills Tracked" value={stats.total_skills.toLocaleString()} />
        <StatCard title="Jobs With Salary" value={stats.jobs_with_salary.toLocaleString()} />
      </div>

      {/* Top Skills */}
      <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
        <h2 className="text-sm font-medium text-zinc-100 mb-4">Top Technical Skills</h2>
        {skillChartData.length > 0 ? (
          <>
          <ResponsiveContainer width="100%" height={isMobile ? 320 : 400}>
            <BarChart data={skillChartData} layout="vertical" margin={{ left: isMobile ? 4 : 80, right: isMobile ? 12 : 0 }}>
              <XAxis type="number" tick={{ fill: "#71717a", fontSize: isMobile ? 10 : 12 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" tick={{ fill: "#71717a", fontSize: isMobile ? 10 : 12 }} width={isMobile ? 80 : 75} interval={0} axisLine={false} tickLine={false} />
              <Tooltip {...DARK_TOOLTIP} />
              <Bar
                dataKey="count"
                radius={[0, 3, 3, 0]}
                cursor="pointer"
                onClick={(data) => navigate(`/jobs?skill=${encodeURIComponent(data.name)}`)}
              >
                {skillChartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <details className="sm:hidden mt-3 text-xs">
            <summary className="text-zinc-400 cursor-pointer py-2 select-none">Show details</summary>
            <ul className="mt-2 space-y-1.5">
              {skillChartData.map((s) => (
                <li
                  key={s.name}
                  onClick={() => navigate(`/jobs?skill=${encodeURIComponent(s.name)}`)}
                  className="flex justify-between cursor-pointer py-1"
                >
                  <span className="text-zinc-300">{s.name}</span>
                  <span className="text-zinc-500">{s.count}</span>
                </li>
              ))}
            </ul>
          </details>
          </>
        ) : (
          <p className="text-zinc-500 text-center py-8">No skill data available</p>
        )}
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Remote vs Onsite */}
        <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
          <h2 className="text-sm font-medium text-zinc-100 mb-4">Remote vs Onsite</h2>
          <ResponsiveContainer width="100%" height={isMobile ? 220 : 300}>
            <PieChart>
              <Pie
                data={remoteData}
                cx="50%"
                cy="50%"
                outerRadius={isMobile ? 60 : 100}
                dataKey="value"
                label={isMobile ? false : ({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={isMobile ? false : { stroke: "#71717a" }}
                stroke="rgba(255,255,255,0.1)"
              >
                {remoteData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip {...DARK_TOOLTIP} />
              <Legend wrapperStyle={{ color: "#a1a1aa", fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Avg Salary by Language */}
        <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
          <h2 className="text-sm font-medium text-zinc-100 mb-4">Avg Salary by Language</h2>
          {stats.salary_by_language.length > 0 ? (
            <ResponsiveContainer width="100%" height={isMobile ? 220 : 300}>
              <BarChart data={stats.salary_by_language} margin={{ top: 5, right: isMobile ? 4 : 10, bottom: 5, left: isMobile ? 4 : 10 }}>
                <XAxis dataKey="language" tick={{ fill: "#71717a", fontSize: isMobile ? 10 : 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[150000, "auto"]} tick={{ fill: "#71717a", fontSize: isMobile ? 10 : 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${Math.round(v / 1000)}K`} />
                <Tooltip {...DARK_TOOLTIP} formatter={(value) => [`$${Math.round(value / 1000)}K`, "Avg Salary"]} />
                <Bar dataKey="avg_salary" fill="#6366f1" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-zinc-500 text-center py-8">No salary data available</p>
          )}
        </div>
      </div>

      {/* Salary Overview */}
      {stats.salary_overview.avg_min && (
        <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
          <h2 className="text-sm font-medium text-zinc-100 mb-4">Salary Overview</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Min Salary</p>
              <p className="mt-1 text-2xl font-medium tracking-tight text-zinc-100">{formatSalary(stats.salary_overview.min_salary)}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Avg Min</p>
              <p className="mt-1 text-2xl font-medium tracking-tight text-indigo-400">{formatSalary(stats.salary_overview.avg_min)}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Avg Max</p>
              <p className="mt-1 text-2xl font-medium tracking-tight text-indigo-400">{formatSalary(stats.salary_overview.avg_max)}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Max Salary</p>
              <p className="mt-1 text-2xl font-medium tracking-tight text-zinc-100">{formatSalary(stats.salary_overview.max_salary)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
