import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { getSkillCorrelations, getLocationTrends, getSkillAutocomplete, getLocationAutocomplete } from "../api";
import AutocompleteInput from "../components/AutocompleteInput";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

const DARK_TOOLTIP = {
  contentStyle: { backgroundColor: "#09090b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6 },
  itemStyle: { color: "#e4e4e7" },
  labelStyle: { color: "#e4e4e7" },
};

export default function SkillExplorer() {
  const [skillInput, setSkillInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const [skillResults, setSkillResults] = useState(null);
  const [locationResults, setLocationResults] = useState(null);
  const [skillLoading, setSkillLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [skillError, setSkillError] = useState(null);
  const [locationError, setLocationError] = useState(null);

  const searchSkill = (value) => {
    const q = value || skillInput;
    if (!q.trim()) return;
    setSkillLoading(true);
    setSkillError(null);
    getSkillCorrelations(q)
      .then(setSkillResults)
      .catch((e) => setSkillError(e.message))
      .finally(() => setSkillLoading(false));
  };

  const searchLocation = (value) => {
    const q = value || locationInput;
    if (!q.trim()) return;
    setLocationLoading(true);
    setLocationError(null);
    getLocationTrends(q)
      .then(setLocationResults)
      .catch((e) => setLocationError(e.message))
      .finally(() => setLocationLoading(false));
  };

  const fetchSkillSugg = async (q) => {
    try { const d = await getSkillAutocomplete(q); return d.suggestions; }
    catch { return []; }
  };
  const fetchLocSugg = async (q) => {
    try { const d = await getLocationAutocomplete(q); return d.suggestions; }
    catch { return []; }
  };

  const skillChartData = skillResults
    ? skillResults.related_skills.map((s) => ({
        name: s.skill,
        correlation: Math.round(s.score * 100),
      }))
    : [];

  const locationChartData = locationResults
    ? locationResults.top_skills.map((s) => ({ name: s.skill, count: s.count }))
    : [];

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-medium tracking-tight text-zinc-100">Skill Explorer</h1>

      {/* Skill Correlation Section */}
      <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
        <h2 className="text-sm font-medium text-zinc-100 mb-3">Skill Correlations</h2>
        <p className="text-xs text-zinc-500 mb-4">
          Search for a skill to see which other skills are most commonly found in the same job listings.
        </p>
        <div className="flex gap-3">
          <div className="flex-1">
            <AutocompleteInput
              placeholder="Enter a skill (e.g. Python)..."
              fetchSuggestions={fetchSkillSugg}
              onSelect={searchSkill}
              value={skillInput}
              onChange={setSkillInput}
            />
          </div>
          <button
            onClick={() => searchSkill()}
            disabled={skillLoading}
            className="px-4 py-2 bg-zinc-800 text-zinc-200 text-sm font-medium rounded-md border border-white/10 hover:bg-white/5 disabled:opacity-50 transition"
          >
            {skillLoading ? "Searching..." : "Search"}
          </button>
        </div>

        {skillLoading && <LoadingSpinner message="Analyzing skill correlations..." />}
        {skillError && <ErrorMessage message={skillError} />}
        {skillResults && !skillLoading && (
          <div className="mt-5">
            <h3 className="text-xs font-medium text-zinc-500 mb-3">
              Skills related to "{skillResults.target_skill}"
            </h3>
            {skillChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={skillChartData} layout="vertical" margin={{ left: 80 }}>
                  <XAxis
                    type="number"
                    domain={[0, 100]}
                    tick={{ fill: "#71717a", fontSize: 12 }}
                    tickFormatter={(v) => `${v}%`}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis dataKey="name" type="category" tick={{ fill: "#71717a", fontSize: 12 }} width={75} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(v) => [`${v}%`, "Correlation"]}
                    {...DARK_TOOLTIP}
                  />
                  <Bar dataKey="correlation" fill="#3f3f46" radius={[0, 3, 3, 0]}>
                    {skillChartData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? "#6366f1" : "#3f3f46"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-zinc-500 text-sm text-center py-4">No correlated skills found.</p>
            )}
          </div>
        )}
      </div>

      {/* Location Trends Section */}
      <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
        <h2 className="text-sm font-medium text-zinc-100 mb-3">Location Trends</h2>
        <p className="text-xs text-zinc-500 mb-4">
          See which skills are most in-demand at a specific location.
        </p>
        <div className="flex gap-3">
          <div className="flex-1">
            <AutocompleteInput
              placeholder="Enter a city (e.g. New York)..."
              fetchSuggestions={fetchLocSugg}
              onSelect={searchLocation}
              value={locationInput}
              onChange={setLocationInput}
            />
          </div>
          <button
            onClick={() => searchLocation()}
            disabled={locationLoading}
            className="px-4 py-2 bg-zinc-800 text-zinc-200 text-sm font-medium rounded-md border border-white/10 hover:bg-white/5 disabled:opacity-50 transition"
          >
            {locationLoading ? "Searching..." : "Search"}
          </button>
        </div>

        {locationLoading && <LoadingSpinner message="Loading location data..." />}
        {locationError && <ErrorMessage message={locationError} />}
        {locationResults && !locationLoading && (
          <div className="mt-5">
            <h3 className="text-xs font-medium text-zinc-100 mb-1">
              Top Skills in {locationResults.location}
            </h3>
            <p className="text-xs text-zinc-500 mb-3">
              Based on {locationResults.job_count} jobs analyzed
            </p>
            {locationChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={locationChartData} layout="vertical" margin={{ left: 80 }}>
                  <XAxis type="number" tick={{ fill: "#71717a", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fill: "#71717a", fontSize: 12 }} width={75} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(v) => [v, "Jobs"]}
                    {...DARK_TOOLTIP}
                  />
                  <Bar dataKey="count" fill="#3f3f46" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-zinc-500 text-sm text-center py-4">No skill data found.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
