import { createContext, useContext, useState, useMemo } from "react";

const ResumeContext = createContext(null);

const STORAGE_KEY = "resumeResults";

function loadFromStorage() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function ResumeProvider({ children }) {
  const [resumeResults, setResumeResultsRaw] = useState(loadFromStorage);

  const setResumeResults = (data) => {
    setResumeResultsRaw(data);
    if (data) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  };

  const clearResume = () => setResumeResults(null);

  const resumeSkills = useMemo(() => {
    if (!resumeResults?.extracted_skills) return [];
    return resumeResults.extracted_skills
      .filter((s) => s.demand > 0)
      .map((s) => s.name);
  }, [resumeResults]);

  return (
    <ResumeContext.Provider value={{ resumeResults, setResumeResults, clearResume, resumeSkills }}>
      {children}
    </ResumeContext.Provider>
  );
}

export function useResumeContext() {
  const ctx = useContext(ResumeContext);
  if (!ctx) throw new Error("useResumeContext must be used within ResumeProvider");
  return ctx;
}
