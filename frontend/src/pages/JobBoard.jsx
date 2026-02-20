import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { getJobs, getFilterLocations, getSkillAutocomplete, getLocationAutocomplete } from "../api";
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Job Board</h1>
        <span className="text-sm text-gray-500 dark:text-gray-400">{total} jobs found</span>
      </div>

      {/* Filter bar */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <input
            type="text"
            placeholder="Search jobs or companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
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
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-700 text-indigo-600 focus:ring-indigo-500"
            />
            Remote only
          </label>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="ml-auto px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 outline-none"
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
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No jobs match your filters. Try broadening your search.
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div key={job.id} className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">{job.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">{job.company}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {job.locations.map((loc) => (
                      <span key={loc} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        {loc}
                      </span>
                    ))}
                    {job.is_remote && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                        Remote
                      </span>
                    )}
                    {job.level && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
                        {job.level}
                      </span>
                    )}
                  </div>
                  {formatSalary(job.salary_min, job.salary_max) && (
                    <p className="text-sm font-medium text-green-600 dark:text-green-400 mt-2">
                      {formatSalary(job.salary_min, job.salary_max)}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {job.skills.slice(0, 8).map((s) => (
                      <SkillBadge key={s.name} name={s.name} category={s.category} />
                    ))}
                    {job.skills.length > 8 && (
                      <span className="text-xs text-gray-400">+{job.skills.length - 8} more</span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0">
                  <span className="text-xs text-gray-400">{relativeDate(job.publication_date)}</span>
                  {job.job_url && (
                    <a
                      href={job.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition"
                    >
                      Apply
                    </a>
                  )}
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
