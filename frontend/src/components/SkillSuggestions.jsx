import { useState, useEffect } from "react";
import { suggestSkills } from "../api";

export default function SkillSuggestions({ jobDescription, userSkills, onAdd }) {
  const [suggestions, setSuggestions] = useState([]);
  const [highlighted, setHighlighted] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!jobDescription.trim()) {
      setSuggestions([]);
      return;
    }

    setLoading(true);
    suggestSkills(jobDescription, userSkills)
      .then((data) => {
        setSuggestions(data.suggestions || []);
        setHighlighted(data.highlighted || []);
      })
      .catch(() => setSuggestions([]))
      .finally(() => setLoading(false));
  }, [jobDescription, userSkills]);

  if (loading) return <p className="text-xs text-zinc-500">Loading suggestions...</p>;
  if (suggestions.length === 0) return null;

  return (
    <div>
      <p className="text-xs text-zinc-400 mb-2">
        Missing skills (click to add):
      </p>
      <div className="flex flex-wrap gap-1.5">
        {suggestions.map((s) => (
          <button
            key={s.skill}
            onClick={() => onAdd(s.skill)}
            className={`px-2 py-1 rounded text-xs font-medium border transition cursor-pointer ${
              highlighted.includes(s.skill)
                ? "bg-indigo-500/15 text-indigo-300 border-indigo-500/30 hover:bg-indigo-500/25"
                : "bg-zinc-800 text-zinc-400 border-white/5 hover:bg-zinc-700"
            }`}
          >
            {s.skill}
          </button>
        ))}
      </div>
    </div>
  );
}
