import { useState } from "react";
import { tailorSection } from "../api";
import SkillSuggestions from "./SkillSuggestions";
import DiffView from "./DiffView";

export default function TailorModal({ experience, jobDescription, userSkills, onApprove, onClose }) {
  const [jobDesc, setJobDesc] = useState(jobDescription || "");
  const [additions, setAdditions] = useState([]);
  const [additionInput, setAdditionInput] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function addSkill(skill) {
    if (!additions.includes(skill)) {
      setAdditions([...additions, skill]);
    }
  }

  function removeSkill(skill) {
    setAdditions(additions.filter((s) => s !== skill));
  }

  function handleAddManual() {
    const skill = additionInput.trim();
    if (skill && !additions.includes(skill)) {
      setAdditions([...additions, skill]);
      setAdditionInput("");
    }
  }

  async function handleTailor() {
    setLoading(true);
    setError(null);
    try {
      const data = await tailorSection({
        original_bullets: experience.bullets,
        job_description: jobDesc,
        allowed_additions: additions,
        experience_company: experience.company,
        experience_title: experience.title,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-white/10 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4 p-6 space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-semibold text-zinc-100">
            Tailor: {experience.title} at {experience.company}
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-sm">
            Close
          </button>
        </div>

        {!result ? (
          <>
            {/* Job description */}
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Job Description</label>
              <textarea
                value={jobDesc}
                onChange={(e) => setJobDesc(e.target.value)}
                rows={5}
                className="w-full bg-zinc-800 border border-white/10 rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500"
                placeholder="Paste the job description here..."
              />
            </div>

            {/* Skill suggestions */}
            <SkillSuggestions
              jobDescription={jobDesc}
              userSkills={userSkills}
              onAdd={addSkill}
            />

            {/* Allowed additions */}
            <div>
              <label className="block text-xs text-zinc-400 mb-1">
                Allowed skill additions ({additions.length})
              </label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {additions.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-500/10 text-indigo-300 text-xs rounded border border-indigo-500/20"
                  >
                    {s}
                    <button onClick={() => removeSkill(s)} className="hover:text-red-400">x</button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={additionInput}
                  onChange={(e) => setAdditionInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddManual())}
                  placeholder="Add skill manually..."
                  className="flex-1 bg-zinc-800 border border-white/10 rounded-md px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={handleAddManual}
                  className="px-3 py-1.5 text-xs font-medium bg-zinc-800 text-zinc-300 rounded-md border border-white/10 hover:bg-zinc-700"
                >
                  Add
                </button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-md p-3">
                {error}
              </p>
            )}

            <button
              onClick={handleTailor}
              disabled={loading || !jobDesc.trim()}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
            >
              {loading ? "Tailoring..." : "Tailor Bullets"}
            </button>
          </>
        ) : (
          <>
            {/* Diff result */}
            {result.warnings?.length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-md p-3">
                {result.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-400">{w}</p>
                ))}
              </div>
            )}

            {result.original.every((b, i) => b === result.tailored[i]) && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3">
                <p className="text-sm font-medium text-green-400">Your bullets are already well optimized for this job description.</p>
                <p className="text-xs text-green-400/70 mt-1">No changes were needed — your experience already aligns well with the role.</p>
              </div>
            )}

            <DiffView original={result.original} tailored={result.tailored} />

            <div className="flex gap-3">
              <button
                onClick={() => {
                  onApprove(result.tailored);
                  onClose();
                }}
                className="flex-1 py-2.5 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition"
              >
                Approve Changes
              </button>
              <button
                onClick={onClose}
                className="flex-1 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm font-medium rounded-lg border border-white/10 transition"
              >
                Reject
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
