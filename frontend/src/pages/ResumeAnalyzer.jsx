import { useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { analyzeResume, analyzeSkillGap, getSkillAutocomplete } from "../api";
import { useResumeContext } from "../context/ResumeContext";
import AutocompleteInput from "../components/AutocompleteInput";
import SkillBadge from "../components/SkillBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

const DARK_TOOLTIP = {
  contentStyle: { backgroundColor: "#09090b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6 },
  itemStyle: { color: "#e4e4e7" },
  labelStyle: { color: "#e4e4e7" },
};

export default function ResumeAnalyzer() {
  const location = useLocation();
  const { resumeResults, setResumeResults, clearResume, resumeSkills } = useResumeContext();
  const fileInputRef = useRef(null);

  // Upload state
  const [file, setFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Manual skill gap state
  const [knownSkills, setKnownSkills] = useState([]);
  const [skillInput, setSkillInput] = useState("");
  const [gapResults, setGapResults] = useState(null);
  const [gapLoading, setGapLoading] = useState(false);
  const [gapError, setGapError] = useState(null);

  // Pre-fill skills from navigation state or cached resume
  useEffect(() => {
    if (location.state?.skills) {
      setKnownSkills(location.state.skills);
    } else if (resumeSkills.length > 0) {
      setKnownSkills(resumeSkills);
    }
  }, [location.state, resumeSkills]);

  // --- Upload handlers ---
  const handleFile = (f) => {
    if (!f) return;
    const ext = f.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      setUploadError("Only PDF and DOCX files are supported.");
      return;
    }
    setFile(f);
    setUploadError(null);
  };

  const upload = () => {
    if (!file) return;
    setUploadLoading(true);
    setUploadError(null);
    analyzeResume(file)
      .then((data) => {
        setResumeResults(data);
        // Auto-populate skills from resume
        const skills = data.extracted_skills
          .filter((s) => s.demand > 0)
          .map((s) => s.name);
        setKnownSkills(skills);
        setFile(null);
      })
      .catch((e) => setUploadError(e.message))
      .finally(() => setUploadLoading(false));
  };

  // --- Manual skill gap handlers ---
  const addSkill = (skill) => {
    if (skill && !knownSkills.some((s) => s.toLowerCase() === skill.toLowerCase())) {
      setKnownSkills((prev) => [...prev, skill]);
    }
    setSkillInput("");
  };

  const removeSkill = (skill) => {
    setKnownSkills((prev) => prev.filter((s) => s !== skill));
  };

  const analyzeGap = () => {
    if (knownSkills.length === 0) return;
    setGapLoading(true);
    setGapError(null);
    analyzeSkillGap(knownSkills)
      .then(setGapResults)
      .catch((e) => setGapError(e.message))
      .finally(() => setGapLoading(false));
  };

  const fetchSugg = async (q) => {
    try { const d = await getSkillAutocomplete(q); return d.suggestions; }
    catch { return []; }
  };

  // --- Derived chart data ---
  const knownChartData = gapResults
    ? gapResults.known_skills.map((s) => ({ name: s.skill, demand: s.demand }))
    : [];

  const gapMissingData = gapResults
    ? gapResults.missing_skills.slice(0, 10).map((s) => ({ name: s.skill, demand: s.demand }))
    : [];

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-medium tracking-tight text-zinc-100">Resume & Skill Gap</h1>
      <p className="text-xs text-zinc-500">
        Add your skills manually or import them from a resume to analyze market demand.
      </p>

      {/* Skill input + upload */}
      <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
        <h2 className="text-sm font-medium text-zinc-100 mb-3">Your Skills</h2>
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
            className="px-4 py-2 bg-zinc-800 text-zinc-200 text-sm font-medium rounded-md border border-white/10 hover:bg-white/5 transition"
          >
            Add
          </button>
        </div>

        {knownSkills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {knownSkills.map((s) => (
              <SkillBadge key={s} name={s} onRemove={() => removeSkill(s)} />
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-500 mb-4">No skills added yet.</p>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={analyzeGap}
            disabled={gapLoading || knownSkills.length === 0}
            className="px-4 py-2 bg-indigo-500/10 text-indigo-400 text-sm font-medium rounded-md border border-indigo-500/20 hover:bg-indigo-500/20 disabled:opacity-50 transition"
          >
            {gapLoading ? "Analyzing..." : "Analyze Gap"}
          </button>

          <span className="text-xs text-zinc-500">or</span>

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadLoading}
            className="px-4 py-2 bg-zinc-800 text-zinc-300 text-sm font-medium rounded-md border border-white/10 hover:bg-white/5 disabled:opacity-50 transition"
          >
            {uploadLoading ? "Importing..." : file ? file.name : "Import from Resume"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(e) => { handleFile(e.target.files[0]); }}
          />
          {file && !uploadLoading && (
            <button
              onClick={upload}
              className="px-4 py-2 bg-indigo-500/10 text-indigo-400 text-sm font-medium rounded-md border border-indigo-500/20 hover:bg-indigo-500/20 transition"
            >
              Upload
            </button>
          )}
        </div>

        {uploadError && <div className="mt-3"><ErrorMessage message={uploadError} /></div>}
      </div>

      {uploadLoading && <LoadingSpinner message="Parsing resume and extracting skills..." />}
      {gapLoading && <LoadingSpinner message="Analyzing your skill gap..." />}
      {gapError && <ErrorMessage message={gapError} onRetry={analyzeGap} />}

      {gapResults && !gapLoading && (
        <>
          {/* Coverage meter */}
          <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
            <h2 className="text-sm font-medium text-zinc-100 mb-3">Market Coverage</h2>
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-zinc-800 rounded-full h-4 overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(gapResults.coverage_percent, 100)}%` }}
                />
              </div>
              <span className="text-2xl font-medium text-zinc-100 shrink-0">
                {gapResults.coverage_percent}%
              </span>
            </div>
            <p className="text-xs text-zinc-500 mt-2">
              Your skills cover {gapResults.coverage_percent}% of market demand across {gapResults.total_technical_skills} tracked technical skills.
            </p>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {knownChartData.length > 0 && (
              <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
                <h2 className="text-sm font-medium text-zinc-100 mb-4">Your Skills Demand</h2>
                <ResponsiveContainer width="100%" height={Math.max(200, knownChartData.length * 35)}>
                  <BarChart data={knownChartData} layout="vertical" margin={{ left: 80 }}>
                    <XAxis type="number" tick={{ fill: "#71717a", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "#71717a", fontSize: 12 }} width={75} axisLine={false} tickLine={false} />
                    <Tooltip {...DARK_TOOLTIP} />
                    <Bar dataKey="demand" fill="#6366f1" radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {gapMissingData.length > 0 && (
              <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
                <h2 className="text-sm font-medium text-zinc-100 mb-4">Top Missing Skills</h2>
                <ResponsiveContainer width="100%" height={Math.max(200, gapMissingData.length * 35)}>
                  <BarChart data={gapMissingData} layout="vertical" margin={{ left: 80 }}>
                    <XAxis type="number" tick={{ fill: "#71717a", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "#71717a", fontSize: 12 }} width={75} axisLine={false} tickLine={false} />
                    <Tooltip {...DARK_TOOLTIP} />
                    <Bar dataKey="demand" fill="#3f3f46" radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Recommendations */}
          {gapResults.recommendations.length > 0 && (
            <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
              <h2 className="text-sm font-medium text-zinc-100 mb-4">Top 5 Skills to Learn Next</h2>
              <div className="space-y-2">
                {gapResults.recommendations.map((rec, i) => (
                  <div key={rec.skill} className="flex items-center gap-3 p-3 bg-zinc-800/50 rounded-md border border-white/5">
                    <span className="w-7 h-7 flex items-center justify-center rounded-md bg-indigo-500/10 text-indigo-400 text-xs font-medium border border-indigo-500/20">
                      {i + 1}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-zinc-100">{rec.skill}</p>
                      <p className="text-xs text-zinc-500">
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
