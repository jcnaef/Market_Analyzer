import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { getSkillCorrelations, getLocationTrends, getSkillAutocomplete, getLocationAutocomplete } from "../api";
import AutocompleteInput from "../components/AutocompleteInput";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

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
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Skill Explorer</h1>

      {/* Skill Correlation Section */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Skill Correlations</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
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
            className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {skillLoading ? "Searching..." : "Search"}
          </button>
        </div>

        {skillLoading && <LoadingSpinner message="Analyzing skill correlations..." />}
        {skillError && <ErrorMessage message={skillError} />}
        {skillResults && !skillLoading && (
          <div className="mt-6">
            <h3 className="text-base font-medium mb-3">
              Skills related to "{skillResults.target_skill}"
            </h3>
            {skillChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={skillChartData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    type="number"
                    domain={[0, 100]}
                    tick={{ fill: "#6b7280", fontSize: 12 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <YAxis dataKey="name" type="category" tick={{ fill: "#6b7280", fontSize: 12 }} width={75} />
                  <Tooltip
                    formatter={(v) => [`${v}%`, "Correlation"]}
                    contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8, color: "#f9fafb" }}
                  />
                  <Bar dataKey="correlation" radius={[0, 4, 4, 0]}>
                    {skillChartData.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? "#6366f1" : "#818cf8"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No correlated skills found.</p>
            )}
          </div>
        )}
      </div>

      {/* Location Trends Section */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Location Trends</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
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
            className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {locationLoading ? "Searching..." : "Search"}
          </button>
        </div>

        {locationLoading && <LoadingSpinner message="Loading location data..." />}
        {locationError && <ErrorMessage message={locationError} />}
        {locationResults && !locationLoading && (
          <div className="mt-6">
            <h3 className="text-base font-medium mb-1">
              Top Skills in {locationResults.location}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              Based on {locationResults.job_count} jobs analyzed
            </p>
            {locationChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={locationChartData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 12 }} />
                  <YAxis dataKey="name" type="category" tick={{ fill: "#6b7280", fontSize: 12 }} width={75} />
                  <Tooltip
                    formatter={(v) => [v, "Jobs"]}
                    contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8, color: "#f9fafb" }}
                  />
                  <Bar dataKey="count" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No skill data found.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
