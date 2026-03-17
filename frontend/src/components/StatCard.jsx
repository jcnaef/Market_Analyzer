export default function StatCard({ title, value, subtitle, icon }) {
  return (
    <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{title}</p>
          <p className="mt-1 text-2xl font-medium tracking-tight text-zinc-100">{value}</p>
          {subtitle && (
            <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>
          )}
        </div>
        {icon && <div className="text-indigo-400 text-2xl">{icon}</div>}
      </div>
    </div>
  );
}
