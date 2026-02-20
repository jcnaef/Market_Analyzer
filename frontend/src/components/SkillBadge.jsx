const categoryColors = {
  Languages: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  Frameworks_Libs: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  Tools_Infrastructure: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  Concepts: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  Soft_Skills: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300",
};

export default function SkillBadge({ name, category, onRemove }) {
  const colorClass = categoryColors[category] || "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300";

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {name}
      {onRemove && (
        <button onClick={onRemove} className="ml-0.5 hover:opacity-70">
          &times;
        </button>
      )}
    </span>
  );
}
