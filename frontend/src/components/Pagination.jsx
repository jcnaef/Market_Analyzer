export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  const pages = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  for (let i = start; i <= end; i++) pages.push(i);

  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-xs font-medium rounded-md border border-white/10 text-zinc-400 disabled:opacity-40 hover:bg-white/5 transition"
      >
        Prev
      </button>
      {start > 1 && <span className="text-zinc-500">...</span>}
      {pages.map((p) => (
        <button
          key={p}
          onClick={() => onPageChange(p)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md border transition ${
            p === page
              ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
              : "border-white/10 text-zinc-400 hover:bg-white/5"
          }`}
        >
          {p}
        </button>
      ))}
      {end < totalPages && <span className="text-zinc-500">...</span>}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-xs font-medium rounded-md border border-white/10 text-zinc-400 disabled:opacity-40 hover:bg-white/5 transition"
      >
        Next
      </button>
    </div>
  );
}
