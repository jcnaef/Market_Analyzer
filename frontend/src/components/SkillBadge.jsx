const categoryColors = {
  Languages: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  Frameworks_Libs: "bg-zinc-800 text-zinc-300 border-white/5",
  Tools_Infrastructure: "bg-zinc-800 text-zinc-300 border-white/5",
  Concepts: "bg-zinc-800 text-zinc-300 border-white/5",
  Soft_Skills: "bg-zinc-800 text-zinc-300 border-white/5",
};

export default function SkillBadge({ name, category, onRemove }) {
  const colorClass = categoryColors[category] || "bg-zinc-800 text-zinc-300 border-white/5";

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}>
      {name}
      {onRemove && (
        <button onClick={onRemove} className="ml-0.5 hover:opacity-70">
          &times;
        </button>
      )}
    </span>
  );
}
