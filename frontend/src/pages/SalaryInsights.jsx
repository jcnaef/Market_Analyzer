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
    <div className="space-y-5">
      <h1 className="text-2xl font-medium tracking-tight text-zinc-100">Salary Insights</h1>

      {/* Toggle tabs */}
      <div className="flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => switchTab(t.key)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
              groupBy === t.key
                ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                : "bg-zinc-900 text-zinc-400 border border-white/10 hover:bg-white/5"
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
        <div className="text-center py-12 text-zinc-500 text-sm">
          Search and select {groupBy === "location" ? "locations" : "skills"} above to compare salary distributions.
        </div>
      ) : data.length === 0 ? (
        <div className="text-center py-12 text-zinc-500 text-sm">
          No salary data available for the selected {groupBy === "location" ? "locations" : "skills"}.
        </div>
      ) : (
        <>
          {/* Box Plot Chart */}
          <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
            <h2 className="text-sm font-medium text-zinc-100 mb-4">
              Salary Distribution {tabs.find((t) => t.key === groupBy)?.label}
            </h2>
            <BoxPlotChart data={data} />
            <p className="text-xs text-zinc-500 mt-3">
              Box = mean &plusmn; 1 std dev &middot; Line = mean &middot; Whiskers = min/max
            </p>
          </div>

          {/* Data table */}
          <div className="bg-zinc-900 rounded-md border border-white/10 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">
                    {groupBy === "location" ? "Location" : "Skill"}
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Min</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Avg Min</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Mean</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Avg Max</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Max</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Std Dev</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-zinc-500">Jobs</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.name} className="border-b border-white/5 last:border-0">
                    <td className="px-4 py-3 font-medium text-zinc-100">{row.name}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{formatSalary(row.min_salary)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{formatSalary(row.avg_min)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{formatSalary(row.avg_mid)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{formatSalary(row.avg_max)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{formatSalary(row.max_salary)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{formatSalary(row.std_dev)}</td>
                    <td className="px-4 py-3 text-right text-zinc-400">{row.job_count}</td>
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
