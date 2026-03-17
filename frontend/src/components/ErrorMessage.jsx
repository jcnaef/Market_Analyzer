export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="bg-red-500/5 border border-red-500/20 rounded-md p-4 text-center">
      <p className="text-red-400 text-sm font-medium">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-3 py-1.5 text-xs font-medium bg-red-500/10 text-red-400 rounded-md border border-red-500/20 hover:bg-red-500/20 transition"
        >
          Retry
        </button>
      )}
    </div>
  );
}
