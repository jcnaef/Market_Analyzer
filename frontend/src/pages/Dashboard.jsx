import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, Legend,
} from "recharts";
import { getDashboardStats } from "../api";
import StatCard from "../components/StatCard";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

const CATEGORY_COLORS = {
  Languages: "#3b82f6",
  Frameworks_Libs: "#8b5cf6",
  Tools_Infrastructure: "#10b981",
  Concepts: "#f59e0b",
};

function formatSalary(val) {
  if (!val) return "N/A";
  return `$${Math.round(val / 1000)}K`;
}

export default function Dashboard() {
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
    { name: "Onsite", value: stats.onsite_count, fill: "#e5e7eb" },
  ];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Jobs" value={stats.total_jobs.toLocaleString()} />
        <StatCard title="Companies" value={stats.total_companies.toLocaleString()} />
        <StatCard title="Skills Tracked" value={stats.total_skills.toLocaleString()} />
        <StatCard title="Jobs With Salary" value={stats.jobs_with_salary.toLocaleString()} />
      </div>

      {/* Top Skills */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Top Technical Skills</h2>
        {skillChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={skillChartData} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 12 }} />
              <YAxis dataKey="name" type="category" tick={{ fill: "#6b7280", fontSize: 12 }} width={75} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8 }}
                itemStyle={{ color: "#f9fafb" }}
                labelStyle={{ color: "#f9fafb" }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {skillChartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-500 dark:text-gray-400 text-center py-8">No skill data available</p>
        )}
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Remote vs Onsite */}
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Remote vs Onsite</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={remoteData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {remoteData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8 }} itemStyle={{ color: "#f9fafb" }} labelStyle={{ color: "#f9fafb" }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Monthly Trends */}
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Monthly Posting Trends</h2>
          {stats.monthly_trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={stats.monthly_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="month" tick={{ fill: "#6b7280", fontSize: 12 }} />
                <YAxis tick={{ fill: "#6b7280", fontSize: 12 }} />
                <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8 }} itemStyle={{ color: "#f9fafb" }} labelStyle={{ color: "#f9fafb" }} />
                <Area type="monotone" dataKey="count" stroke="#6366f1" fill="#6366f180" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">No trend data available</p>
          )}
        </div>
      </div>

      {/* Salary Overview */}
      {stats.salary_overview.avg_min && (
        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Salary Overview</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Min Salary</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">{formatSalary(stats.salary_overview.min_salary)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Avg Min</p>
              <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400">{formatSalary(stats.salary_overview.avg_min)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Avg Max</p>
              <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400">{formatSalary(stats.salary_overview.avg_max)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Max Salary</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">{formatSalary(stats.salary_overview.max_salary)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
