import { useState, useRef, useEffect } from "react";

export default function AutocompleteInput({ placeholder, fetchSuggestions, onSelect, value, onChange }) {
  const [suggestions, setSuggestions] = useState([]);
  const [show, setShow] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const timerRef = useRef(null);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setShow(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleChange = (e) => {
    const v = e.target.value;
    onChange(v);
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

  const select = (s) => {
    onChange(s);
    setSuggestions([]);
    setShow(false);
    setHighlighted(-1);
    clearTimeout(timerRef.current);
    if (onSelect) onSelect(s);
  };

  const handleKeyDown = (e) => {
    if (!show) {
      if (e.key === "Enter" && onSelect) { e.preventDefault(); onSelect(value); }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((p) => Math.min(p + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((p) => Math.max(p - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlighted >= 0) select(suggestions[highlighted]);
      else { setShow(false); if (onSelect) onSelect(value); }
    } else if (e.key === "Escape") {
      setShow(false);
      setHighlighted(-1);
    }
  };

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        autoComplete="off"
        className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
      />
      {show && suggestions.length > 0 && (
        <ul className="absolute z-50 top-full left-0 right-0 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-b-lg shadow-lg max-h-60 overflow-y-auto">
          {suggestions.map((s, i) => (
            <li
              key={s}
              className={`px-4 py-2 cursor-pointer text-sm ${
                i === highlighted
                  ? "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
              onMouseDown={(e) => { e.preventDefault(); select(s); }}
              onMouseEnter={() => setHighlighted(i)}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
