import { useState, useRef, useEffect } from "react";

export default function MultiSelectAutocomplete({
  placeholder,
  fetchSuggestions,
  selected,
  onAdd,
  onRemove,
}) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [show, setShow] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const timerRef = useRef(null);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target))
        setShow(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleChange = (e) => {
    const v = e.target.value;
    setQuery(v);
    setHighlighted(-1);
    if (!v) {
      setSuggestions([]);
      setShow(false);
      return;
    }
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const results = await fetchSuggestions(v);
      setSuggestions(results);
      setShow(results.length > 0);
    }, 300);
  };

  const add = (item) => {
    if (!selected.includes(item)) onAdd(item);
    setQuery("");
    setSuggestions([]);
    setShow(false);
    setHighlighted(-1);
    clearTimeout(timerRef.current);
  };

  const handleKeyDown = (e) => {
    if (!show) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((p) => Math.min(p + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((p) => Math.max(p - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlighted >= 0) add(suggestions[highlighted]);
    } else if (e.key === "Escape") {
      setShow(false);
      setHighlighted(-1);
    }
  };

  return (
    <div className="space-y-2">
      {/* Chips */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((item) => (
            <span
              key={item}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300"
            >
              {item}
              <button
                onClick={() => onRemove(item)}
                className="ml-0.5 hover:text-indigo-900 dark:hover:text-indigo-100"
                aria-label={`Remove ${item}`}
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input */}
      <div ref={wrapperRef} className="relative">
        <input
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
        />
        {show && suggestions.length > 0 && (
          <ul className="absolute z-50 top-full left-0 right-0 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-b-lg shadow-lg max-h-60 overflow-y-auto">
            {suggestions.map((s, i) => {
              const isSelected = selected.includes(s);
              return (
                <li
                  key={s}
                  className={`px-4 py-2 cursor-pointer text-sm flex items-center justify-between ${
                    i === highlighted
                      ? "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    add(s);
                  }}
                  onMouseEnter={() => setHighlighted(i)}
                >
                  <span>{s}</span>
                  {isSelected && (
                    <span className="text-indigo-500 text-xs font-medium">
                      selected
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
