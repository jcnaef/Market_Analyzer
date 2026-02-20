import { useState, useCallback } from "react";
import { getSalaryInsights, getLocationAutocomplete, getSkillAutocomplete } from "../api";
import MultiSelectAutocomplete from "../components/MultiSelectAutocomplete";
import BoxPlotChart from "../components/BoxPlotChart";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

function formatSalary(val) {
  if (val == null) return "N/A";
  return `$${Math.round(val / 1000).toLocaleString()}K`;
}

const tabs = [
  { key: "location", label: "By Location" },
  { key: "skill", label: "By Skill" },
];

export default function SalaryInsights() {
  const [groupBy, setGroupBy] = useState("location");
  const [selected, setSelected] = useState([]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAutocomplete = useCallback(
    async (q) => {
      if (groupBy === "location") {
        const res = await getLocationAutocomplete(q);
        return res.suggestions || [];
      }
      const res = await getSkillAutocomplete(q);
      return res.suggestions || [];
    },
    [groupBy]
  );

  const load = useCallback(
    (names) => {
      if (names.length === 0) {
        setData([]);
        return;
      }
      setLoading(true);
      setError(null);
      getSalaryInsights(groupBy, names)
        .then((d) => setData(d.data))
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    },
    [groupBy]
  );

  const MAX_SELECTED = 8;

  const handleAdd = (item) => {
    let next = [...selected, item];
    // If over the limit, drop the oldest entries to make room
    if (next.length > MAX_SELECTED) {
      next = next.slice(next.length - MAX_SELECTED);
    }
    setSelected(next);
    load(next);
  };

  const handleRemove = (item) => {
    const next = selected.filter((s) => s !== item);
    setSelected(next);
    load(next);
  };

  const switchTab = (key) => {
    setGroupBy(key);
    setSelected([]);
    setData([]);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Salary Insights</h1>

      {/* Toggle tabs */}
      <div className="flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => switchTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              groupBy === t.key
                ? "bg-indigo-600 text-white"
                : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Multi-select search */}
      <div className="max-w-md">
        <MultiSelectAutocomplete
          placeholder={`Search ${groupBy === "location" ? "locations" : "skills"} to compare...`}
          fetchSuggestions={fetchAutocomplete}
          selected={selected}
          onAdd={handleAdd}
          onRemove={handleRemove}
        />
      </div>

      {loading ? (
        <LoadingSpinner message="Loading salary data..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={() => load(selected)} />
      ) : selected.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          Search and select {groupBy === "location" ? "locations" : "skills"} above to compare salary distributions.
        </div>
      ) : data.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No salary data available for the selected {groupBy === "location" ? "locations" : "skills"}.
        </div>
      ) : (
        <>
          {/* Box Plot Chart */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-4">
              Salary Distribution {tabs.find((t) => t.key === groupBy)?.label}
            </h2>
            <BoxPlotChart data={data} />
            <p className="text-xs text-gray-400 mt-3">
              Box = mean &plusmn; 1 std dev &middot; Line = mean &middot; Whiskers = min/max
            </p>
          </div>

          {/* Data table */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800">
                  <th className="text-left px-6 py-3 font-medium text-gray-600 dark:text-gray-400">
                    {groupBy === "location" ? "Location" : "Skill"}
                  </th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Min</th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Avg Min</th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Mean</th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Avg Max</th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Max</th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Std Dev</th>
                  <th className="text-right px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Jobs</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.name} className="border-b border-gray-100 dark:border-gray-800 last:border-0">
                    <td className="px-6 py-3 font-medium text-gray-900 dark:text-white">{row.name}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{formatSalary(row.min_salary)}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{formatSalary(row.avg_min)}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{formatSalary(row.avg_mid)}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{formatSalary(row.avg_max)}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{formatSalary(row.max_salary)}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{formatSalary(row.std_dev)}</td>
                    <td className="px-6 py-3 text-right text-gray-600 dark:text-gray-400">{row.job_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
