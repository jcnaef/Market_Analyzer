import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { analyzeSkillGap, getSkillAutocomplete } from "../api";
import { useResumeContext } from "../context/ResumeContext";
import AutocompleteInput from "../components/AutocompleteInput";
import SkillBadge from "../components/SkillBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

export default function SkillGapAnalyzer() {
  const location = useLocation();
  const { resumeSkills } = useResumeContext();
  const [knownSkills, setKnownSkills] = useState([]);
  const [skillInput, setSkillInput] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Accept pre-filled skills via router state, fall back to cached resume skills
  useEffect(() => {
    if (location.state?.skills) {
      setKnownSkills(location.state.skills);
    } else if (resumeSkills.length > 0) {
      setKnownSkills(resumeSkills);
    }
  }, [location.state, resumeSkills]);

  const addSkill = (skill) => {
    if (skill && !knownSkills.some((s) => s.toLowerCase() === skill.toLowerCase())) {
      setKnownSkills((prev) => [...prev, skill]);
    }
    setSkillInput("");
  };

  const removeSkill = (skill) => {
    setKnownSkills((prev) => prev.filter((s) => s !== skill));
  };

  const analyze = () => {
    if (knownSkills.length === 0) return;
    setLoading(true);
    setError(null);
    analyzeSkillGap(knownSkills)
      .then(setResults)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const fetchSugg = async (q) => {
    try { const d = await getSkillAutocomplete(q); return d.suggestions; }
    catch { return []; }
  };

  const knownChartData = results
    ? results.known_skills.map((s) => ({ name: s.skill, demand: s.demand }))
    : [];

  const missingChartData = results
    ? results.missing_skills.slice(0, 10).map((s) => ({ name: s.skill, demand: s.demand }))
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Skill Gap Analyzer</h1>
      <p className="text-gray-500 dark:text-gray-400">
        Add your known skills and see how they stack up against market demand.
      </p>

      {/* Skill input */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-3">Your Skills</h2>
        <div className="flex gap-3 mb-4">
          <div className="flex-1">
            <AutocompleteInput
              placeholder="Add a skill..."
              fetchSuggestions={fetchSugg}
              onSelect={addSkill}
              value={skillInput}
              onChange={setSkillInput}
            />
          </div>
          <button
            onClick={() => addSkill(skillInput)}
            className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition"
          >
            Add
          </button>
        </div>

        {knownSkills.length > 0 ? (
          <div className="flex flex-wrap gap-2 mb-4">
            {knownSkills.map((s) => (
              <SkillBadge key={s} name={s} onRemove={() => removeSkill(s)} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 mb-4">No skills added yet.</p>
        )}

        <button
          onClick={analyze}
          disabled={loading || knownSkills.length === 0}
          className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
        >
          {loading ? "Analyzing..." : "Analyze Gap"}
        </button>
      </div>

      {loading && <LoadingSpinner message="Analyzing your skill gap..." />}
      {error && <ErrorMessage message={error} onRetry={analyze} />}

      {results && !loading && (
        <>
          {/* Coverage meter */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-3">Market Coverage</h2>
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                <div
                  className="h-full bg-indigo-600 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(results.coverage_percent, 100)}%` }}
                />
              </div>
              <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 shrink-0">
                {results.coverage_percent}%
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Your skills cover {results.coverage_percent}% of market demand across {results.total_technical_skills} tracked technical skills.
            </p>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Known skills demand */}
            {knownChartData.length > 0 && (
              <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-lg font-semibold mb-4">Your Skills Demand</h2>
                <ResponsiveContainer width="100%" height={Math.max(200, knownChartData.length * 35)}>
                  <BarChart data={knownChartData} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 12 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "#6b7280", fontSize: 12 }} width={75} />
                    <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8, color: "#f9fafb" }} />
                    <Bar dataKey="demand" fill="#10b981" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Missing skills */}
            {missingChartData.length > 0 && (
              <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-lg font-semibold mb-4">Top Missing Skills</h2>
                <ResponsiveContainer width="100%" height={Math.max(200, missingChartData.length * 35)}>
                  <BarChart data={missingChartData} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 12 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "#6b7280", fontSize: 12 }} width={75} />
                    <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8, color: "#f9fafb" }} />
                    <Bar dataKey="demand" fill="#ef4444" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Recommendations */}
          {results.recommendations.length > 0 && (
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
              <h2 className="text-lg font-semibold mb-4">Top 5 Skills to Learn Next</h2>
              <div className="space-y-3">
                {results.recommendations.map((rec, i) => (
                  <div key={rec.skill} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <span className="w-8 h-8 flex items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 text-sm font-bold">
                      {i + 1}
                    </span>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{rec.skill}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Found in {rec.demand} job listings
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
