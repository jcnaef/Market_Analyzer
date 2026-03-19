import { useState, useRef, useEffect, useCallback } from "react";

function TextField({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="block text-xs text-zinc-400 mb-1">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-zinc-800 border border-white/10 rounded-md px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500"
      />
    </div>
  );
}

/**
 * A textarea that maintains its own draft text internally to avoid cursor
 * jumping, only committing structured changes on blur.
 */
function DraftTextarea({ value, onCommit, rows, placeholder, className }) {
  const [draft, setDraft] = useState(value);
  const ref = useRef(null);

  // Sync from parent when the value changes externally (e.g. after upload/save)
  useEffect(() => {
    if (document.activeElement !== ref.current) {
      setDraft(value);
    }
  }, [value]);

  return (
    <textarea
      ref={ref}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => onCommit(draft)}
      rows={rows}
      placeholder={placeholder}
      className={className}
    />
  );
}

function Section({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-zinc-800/50 text-sm font-medium text-zinc-200 hover:bg-zinc-800 transition"
      >
        {title}
        <span className="text-zinc-500 text-xs">{open ? "Collapse" : "Expand"}</span>
      </button>
      {open && <div className="p-4 space-y-3">{children}</div>}
    </div>
  );
}

export default function ResumeForm({ data, onChange, expandAll = false }) {
  function update(path, value) {
    const next = JSON.parse(JSON.stringify(data));
    const keys = path.split(".");
    let obj = next;
    for (let i = 0; i < keys.length - 1; i++) {
      obj = obj[keys[i]];
    }
    obj[keys[keys.length - 1]] = value;
    onChange(next);
  }

  function updateArrayItem(arrayPath, index, field, value) {
    const next = JSON.parse(JSON.stringify(data));
    const arr = arrayPath.split(".").reduce((o, k) => o[k], next);
    arr[index][field] = value;
    onChange(next);
  }

  function addExperience() {
    const next = JSON.parse(JSON.stringify(data));
    next.experience.push({ company: "", title: "", start_date: "", end_date: "", bullets: [] });
    onChange(next);
  }

  function removeExperience(index) {
    const next = JSON.parse(JSON.stringify(data));
    next.experience.splice(index, 1);
    onChange(next);
  }

  function addEducation() {
    const next = JSON.parse(JSON.stringify(data));
    next.education.push({ institution: "", degree: "", field: "", start_date: "", end_date: "", gpa: "" });
    onChange(next);
  }

  function removeEducation(index) {
    const next = JSON.parse(JSON.stringify(data));
    next.education.splice(index, 1);
    onChange(next);
  }

  function commitBullets(expIndex, value) {
    const next = JSON.parse(JSON.stringify(data));
    next.experience[expIndex].bullets = value.split("\n").filter((b) => b.trim());
    onChange(next);
  }

  function commitSkills(value) {
    const next = JSON.parse(JSON.stringify(data));
    next.skills = value.split(",").map((s) => s.trim()).filter(Boolean);
    onChange(next);
  }

  const pi = data.personal_info || {};

  return (
    <div className="space-y-4">
      {/* Personal Info */}
      <Section title="Personal Info" defaultOpen={expandAll || true}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <TextField label="Name" value={pi.name || ""} onChange={(v) => update("personal_info.name", v)} />
          <TextField label="Email" value={pi.email || ""} onChange={(v) => update("personal_info.email", v)} />
          <TextField label="Phone" value={pi.phone || ""} onChange={(v) => update("personal_info.phone", v)} />
          <TextField label="LinkedIn" value={pi.linkedin || ""} onChange={(v) => update("personal_info.linkedin", v)} />
        </div>
      </Section>

      {/* Summary */}
      <Section title="Summary" defaultOpen={expandAll}>
        <DraftTextarea
          value={data.summary || ""}
          onCommit={(v) => update("summary", v)}
          rows={Math.max(4, (data.summary || "").split("\n").length + 1)}
          placeholder="Professional summary..."
          className="w-full bg-zinc-800 border border-white/10 rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500"
        />
      </Section>

      {/* Experience */}
      <Section title={`Experience (${data.experience?.length || 0})`} defaultOpen={expandAll}>
        {(data.experience || []).map((exp, i) => (
          <div key={i} className="border border-white/10 rounded-md p-3 space-y-2 mb-3">
            <div className="flex justify-between items-start">
              <span className="text-xs text-zinc-500">Entry {i + 1}</span>
              <button onClick={() => removeExperience(i)} className="text-xs text-red-400 hover:text-red-300">Remove</button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <TextField label="Company" value={exp.company} onChange={(v) => updateArrayItem("experience", i, "company", v)} />
              <TextField label="Title" value={exp.title} onChange={(v) => updateArrayItem("experience", i, "title", v)} />
              <TextField label="Start Date" value={exp.start_date} onChange={(v) => updateArrayItem("experience", i, "start_date", v)} />
              <TextField label="End Date" value={exp.end_date} onChange={(v) => updateArrayItem("experience", i, "end_date", v)} />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">Bullets (one per line)</label>
              <DraftTextarea
                value={(exp.bullets || []).join("\n")}
                onCommit={(v) => commitBullets(i, v)}
                rows={Math.max(4, (exp.bullets || []).length + 2)}
                className="w-full bg-zinc-800 border border-white/10 rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        ))}
        <button onClick={addExperience} className="text-xs text-indigo-400 hover:text-indigo-300">+ Add Experience</button>
      </Section>

      {/* Education */}
      <Section title={`Education (${data.education?.length || 0})`} defaultOpen={expandAll}>
        {(data.education || []).map((edu, i) => (
          <div key={i} className="border border-white/10 rounded-md p-3 space-y-2 mb-3">
            <div className="flex justify-between items-start">
              <span className="text-xs text-zinc-500">Entry {i + 1}</span>
              <button onClick={() => removeEducation(i)} className="text-xs text-red-400 hover:text-red-300">Remove</button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <TextField label="Institution" value={edu.institution} onChange={(v) => updateArrayItem("education", i, "institution", v)} />
              <TextField label="Degree" value={edu.degree} onChange={(v) => updateArrayItem("education", i, "degree", v)} />
              <TextField label="Field" value={edu.field} onChange={(v) => updateArrayItem("education", i, "field", v)} />
              <TextField label="GPA" value={edu.gpa} onChange={(v) => updateArrayItem("education", i, "gpa", v)} />
              <TextField label="Start Date" value={edu.start_date} onChange={(v) => updateArrayItem("education", i, "start_date", v)} />
              <TextField label="End Date" value={edu.end_date} onChange={(v) => updateArrayItem("education", i, "end_date", v)} />
            </div>
          </div>
        ))}
        <button onClick={addEducation} className="text-xs text-indigo-400 hover:text-indigo-300">+ Add Education</button>
      </Section>

      {/* Skills */}
      <Section title={`Skills (${data.skills?.length || 0})`} defaultOpen={expandAll}>
        <div>
          <label className="block text-xs text-zinc-400 mb-1">Comma-separated list</label>
          <DraftTextarea
            value={(data.skills || []).join(", ")}
            onCommit={(v) => commitSkills(v)}
            rows={Math.max(3, Math.ceil((data.skills || []).length / 5))}
            placeholder="Python, React, Docker..."
            className="w-full bg-zinc-800 border border-white/10 rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </Section>
    </div>
  );
}
