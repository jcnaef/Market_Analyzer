import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { getJobs, getFilterLocations, getSkillAutocomplete, getLocationAutocomplete } from "../api";
import { useAuth } from "../context/AuthContext";
import AutocompleteInput from "../components/AutocompleteInput";
import SkillBadge from "../components/SkillBadge";
import Pagination from "../components/Pagination";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

function formatSalary(min, max) {
  if (!min && !max) return null;
  const fmt = (v) => `$${Math.round(v / 1000)}K`;
  if (min && max) return `${fmt(min)} - ${fmt(max)}`;
  if (min) return `From ${fmt(min)}`;
  return `Up to ${fmt(max)}`;
}

function relativeDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const days = Math.floor((now - d) / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

export default function JobBoard() {
  const { firebaseUser, login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [skillFilter, setSkillFilter] = useState(() => searchParams.get("skill") || "");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [sort, setSort] = useState("date_desc");

  const load = (p = page) => {
    setLoading(true);
    setError(null);
    getJobs({ page: p, search, location: locationFilter, skill: skillFilter, remote_only: remoteOnly, sort })
      .then((data) => {
        setJobs(data.jobs);
        setTotal(data.total);
        setPage(data.page);
        setTotalPages(data.total_pages);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(1); }, [search, locationFilter, skillFilter, remoteOnly, sort]);

  const fetchSkillSugg = async (q) => {
    try { const d = await getSkillAutocomplete(q); return d.suggestions; }
    catch { return []; }
  };
  const fetchLocSugg = async (q) => {
    try { const d = await getLocationAutocomplete(q); return d.suggestions; }
    catch { return []; }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-medium tracking-tight text-zinc-100">Job Board</h1>
        <span className="text-xs font-medium text-zinc-500">{total} jobs found</span>
      </div>

      {/* Filter bar */}
      <div className="bg-zinc-900 rounded-md border border-white/10 p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <input
            type="text"
            placeholder="Search jobs or companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 rounded-md border border-white/10 bg-zinc-800 text-zinc-100 text-sm placeholder:text-zinc-500 focus:border-indigo-500/50 focus:ring-0 outline-none transition"
          />
          <AutocompleteInput
            placeholder="Filter by location..."
            fetchSuggestions={fetchLocSugg}
            onSelect={(v) => setLocationFilter(v)}
            value={locationFilter}
            onChange={setLocationFilter}
          />
          <AutocompleteInput
            placeholder="Filter by skill..."
            fetchSuggestions={fetchSkillSugg}
            onSelect={(v) => setSkillFilter(v)}
            value={skillFilter}
            onChange={setSkillFilter}
          />
        </div>
        <div className="flex items-center gap-4 mt-3">
          <label className="flex items-center gap-2 text-xs font-medium text-zinc-500 cursor-pointer">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
              className="rounded border-white/10 bg-zinc-800 text-indigo-500 focus:ring-0 focus:ring-offset-0"
            />
            Remote only
          </label>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="ml-auto px-3 py-1.5 text-xs font-medium rounded-md border border-white/10 bg-zinc-800 text-zinc-300 outline-none cursor-pointer"
          >
            <option value="date_desc">Newest first</option>
            <option value="date_asc">Oldest first</option>
            <option value="salary_desc">Highest salary</option>
            <option value="salary_asc">Lowest salary</option>
          </select>
        </div>
      </div>

      {/* Job list */}
      {loading ? (
        <LoadingSpinner message="Loading jobs..." />
      ) : error ? (
        <ErrorMessage message={error} onRetry={() => load(page)} />
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 text-zinc-500 text-sm">
          No jobs match your filters. Try broadening your search.
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div key={job.id} className="bg-zinc-900 rounded-md border border-white/10 p-4">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-zinc-100 truncate">{job.title}</h3>
                  <p className="text-xs text-zinc-500 mt-0.5">{job.company}</p>
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    {job.locations.slice(0, 7).map((loc) => (
                      <span key={loc} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-400 border border-white/5">
                        {loc}
                      </span>
                    ))}
                    {job.locations.length > 7 && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-400 border border-white/5" title={job.locations.slice(7).join(', ')}>
                        +{job.locations.length - 7} more...
                      </span>
                    )}
                    {job.is_remote && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        Remote
                      </span>
                    )}
                    {job.level && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-white/5">
                        {job.level}
                      </span>
                    )}
                  </div>
                  {formatSalary(job.salary_min, job.salary_max) && (
                    <p className="text-xs font-medium text-indigo-400 mt-2">
                      {formatSalary(job.salary_min, job.salary_max)}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {job.skills.slice(0, 8).map((s) => (
                      <SkillBadge key={s.name} name={s.name} category={s.category} />
                    ))}
                    {job.skills.length > 8 && (
                      <span className="text-xs text-zinc-500" title={job.skills.slice(8).map(s => s.name).join(', ')}>+{job.skills.length - 8} more</span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0">
                  <span className="text-xs text-zinc-500">{relativeDate(job.publication_date)}</span>
                  {job.job_url && (
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 bg-zinc-800 text-zinc-200 text-xs font-medium rounded-md border border-white/10 hover:bg-white/5 transition"
                    >
                      Apply
                    </a>
                  )}
                  <button
                    onClick={() => {
                      if (!firebaseUser) {
                        sessionStorage.setItem("pendingTailorJobId", job.id);
                        login();
                      } else {
                        navigate(`/tailor?jobId=${job.id}`);
                      }
                    }}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-md transition"
                  >
                    Tailor Resume
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={(p) => { setPage(p); load(p); }} />
    </div>
  );
}
