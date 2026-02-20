export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-center">
      <p className="text-red-700 dark:text-red-400 font-medium">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-4 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 transition"
        >
          Retry
        </button>
      )}
    </div>
  );
}
