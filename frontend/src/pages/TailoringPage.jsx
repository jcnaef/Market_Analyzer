import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getResume, saveResume, getJobById } from "../api";
import ResumeForm from "../components/ResumeForm";
import TailorModal from "../components/TailorModal";
import PDFDownloadButton from "../components/PDFDownloadButton";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

export default function TailoringPage() {
  const { dbUser, firebaseUser, refreshDbUser } = useAuth();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("jobId");

  const [resumeData, setResumeData] = useState(null);
  const [jobData, setJobData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(null);
  const [tailorIndex, setTailorIndex] = useState(null);

  useEffect(() => {
    const promises = [];

    if (firebaseUser && dbUser?.has_resume) {
      promises.push(
        getResume().catch((err) => { setError(err.message); return null; })
      );
    } else {
      promises.push(Promise.resolve(null));
    }

    if (jobId) {
      promises.push(
        getJobById(jobId).catch(() => null)
      );
    }

    Promise.all(promises).then(([resume, job]) => {
      setResumeData(resume);
      if (job) setJobData(job);
      setLoading(false);
    });
  }, [jobId, firebaseUser, dbUser]);

  async function handleSave() {
    if (!resumeData) return;
    setSaving(true);
    setError(null);
    try {
      await saveResume(resumeData);
      await refreshDbUser();
      setSuccess("Tailored resume saved!");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function handleApprove(expIndex, tailoredBullets) {
    const next = JSON.parse(JSON.stringify(resumeData));
    next.experience[expIndex].bullets = tailoredBullets;
    setResumeData(next);
    setSuccess(null);
  }

  if (loading) return <LoadingSpinner />;
  if (error && !resumeData) return <ErrorMessage message={error} />;

  const userSkills = resumeData?.skills || [];
  const jobDescription = jobData?.description || "";
  const jobTitle = jobData?.title || "";

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-lg font-semibold text-zinc-100">Tailor Resume</h1>

      {jobTitle && (
        <div className="bg-zinc-900 border border-white/10 rounded-lg p-3">
          <p className="text-xs text-zinc-500">Tailoring for:</p>
          <p className="text-sm font-medium text-zinc-200">{jobTitle}</p>
        </div>
      )}

      {!resumeData ? (
        <p className="text-sm text-zinc-400">
          {!firebaseUser
            ? "Please log in to access your saved resume."
            : !dbUser?.has_resume
              ? "No resume found. Please upload one from your account page first."
              : "Unable to load your resume. Please try again."}
        </p>
      ) : (
        <>
          {/* Experience blocks with tailor buttons */}
          <div className="space-y-3">
            {(resumeData.experience || []).map((exp, i) => (
              <div
                key={i}
                className="bg-zinc-900 border border-white/10 rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-sm font-medium text-zinc-200">
                      {exp.title || "Untitled"}{" "}
                      <span className="text-zinc-500">at</span>{" "}
                      {exp.company || "Unknown"}
                    </h3>
                    <p className="text-xs text-zinc-500">
                      {exp.start_date} - {exp.end_date}
                    </p>
                  </div>
                  <button
                    onClick={() => setTailorIndex(i)}
                    className="px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition"
                  >
                    Tailor to Job
                  </button>
                </div>
                <ul className="space-y-1">
                  {(exp.bullets || []).map((b, j) => (
                    <li key={j} className="text-sm text-zinc-400 flex items-start gap-2">
                      <span className="text-zinc-600 mt-0.5">-</span>
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {success && (
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
              <p className="text-sm text-green-400">{success}</p>
            </div>
          )}

          {/* Full resume form (collapsed by default) */}
          <details className="group">
            <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300">
              View / edit full resume
            </summary>
            <div className="mt-3">
              <ResumeForm data={resumeData} onChange={setResumeData} />
            </div>
          </details>

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
            >
              {saving ? "Saving..." : "Save Tailored Resume"}
            </button>
            <PDFDownloadButton data={resumeData} filename="tailored-resume.pdf" />
          </div>

          {/* Tailor modal */}
          {tailorIndex !== null && resumeData.experience[tailorIndex] && (
            <TailorModal
              experience={resumeData.experience[tailorIndex]}
              jobDescription={jobDescription}
              jobData={jobData}
              userSkills={userSkills}
              onApprove={(bullets) => handleApprove(tailorIndex, bullets)}
              onClose={() => setTailorIndex(null)}
            />
          )}
        </>
      )}
    </div>
  );
}
