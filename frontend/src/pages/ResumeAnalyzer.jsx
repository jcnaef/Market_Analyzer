import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { analyzeResume } from "../api";
import SkillBadge from "../components/SkillBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

export default function ResumeAnalyzer() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFile = (f) => {
    if (!f) return;
    const ext = f.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      setError("Only PDF and DOCX files are supported.");
      return;
    }
    setFile(f);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const upload = () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    analyzeResume(file)
      .then(setResults)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const goToSkillGap = () => {
    if (!results) return;
    const skills = results.extracted_skills
      .filter((s) => s.demand > 0)
      .map((s) => s.name);
    navigate("/skill-gap", { state: { skills } });
  };

  // Group extracted skills by category
  const skillsByCategory = {};
  if (results) {
    for (const s of results.extracted_skills) {
      if (!skillsByCategory[s.category]) skillsByCategory[s.category] = [];
      skillsByCategory[s.category].push(s);
    }
  }

  const demandChartData = results
    ? results.extracted_skills
        .filter((s) => s.demand > 0)
        .sort((a, b) => b.demand - a.demand)
        .slice(0, 15)
        .map((s) => ({ name: s.name, demand: s.demand }))
    : [];

  const missingChartData = results
    ? results.missing_skills.slice(0, 10).map((s) => ({ name: s.name, demand: s.demand }))
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Resume Analyzer</h1>
      <p className="text-gray-500 dark:text-gray-400">
        Upload your resume to see how your skills match market demand.
      </p>

      {/* Upload area */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition ${
            dragActive
              ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950"
              : "border-gray-300 dark:border-gray-700 hover:border-indigo-400 hover:bg-gray-50 dark:hover:bg-gray-800"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          <svg className="mx-auto w-12 h-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          {file ? (
            <p className="text-gray-700 dark:text-gray-300 font-medium">{file.name}</p>
          ) : (
            <>
              <p className="text-gray-600 dark:text-gray-400 font-medium">
                Drag and drop your resume, or click to browse
              </p>
              <p className="text-sm text-gray-400 mt-1">Supports PDF and DOCX</p>
            </>
          )}
        </div>

        {file && (
          <button
            onClick={upload}
            disabled={loading}
            className="mt-4 px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {loading ? "Analyzing..." : "Analyze Resume"}
          </button>
        )}
      </div>

      {loading && <LoadingSpinner message="Parsing and analyzing your resume..." />}
      {error && <ErrorMessage message={error} />}

      {results && !loading && (
        <>
          {/* Readiness score */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-3">Market Readiness Score</h2>
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(results.readiness_score, 100)}%`,
                    backgroundColor: results.readiness_score >= 60 ? "#10b981" : results.readiness_score >= 30 ? "#f59e0b" : "#ef4444",
                  }}
                />
              </div>
              <span className="text-2xl font-bold shrink-0" style={{
                color: results.readiness_score >= 60 ? "#10b981" : results.readiness_score >= 30 ? "#f59e0b" : "#ef4444",
              }}>
                {results.readiness_score}%
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              {results.total_extracted} skills extracted, {results.matched_in_market} matched in market data.
            </p>
          </div>

          {/* Extracted skills by category */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-4">Extracted Skills</h2>
            {Object.keys(skillsByCategory).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(skillsByCategory).map(([category, skills]) => (
                  <div key={category}>
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                      {category.replace(/_/g, " ")}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {skills.map((s) => (
                        <SkillBadge key={s.name} name={s.name} category={category} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">No skills extracted from resume.</p>
            )}
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {demandChartData.length > 0 && (
              <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-lg font-semibold mb-4">Your Skills Demand Ranking</h2>
                <ResponsiveContainer width="100%" height={Math.max(200, demandChartData.length * 30)}>
                  <BarChart data={demandChartData} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 12 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "#6b7280", fontSize: 12 }} width={75} />
                    <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: 8, color: "#f9fafb" }} />
                    <Bar dataKey="demand" fill="#10b981" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {missingChartData.length > 0 && (
              <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-lg font-semibold mb-4">Missing High-Demand Skills</h2>
                <ResponsiveContainer width="100%" height={Math.max(200, missingChartData.length * 30)}>
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

          {/* Skill gap button */}
          <div className="text-center">
            <button
              onClick={goToSkillGap}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition"
            >
              Analyze Skill Gap With These Skills
            </button>
          </div>
        </>
      )}
    </div>
  );
}
