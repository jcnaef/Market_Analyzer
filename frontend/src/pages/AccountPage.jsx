import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { uploadResume, saveResume, getResume } from "../api";
import ResumeForm from "../components/ResumeForm";
import PDFDownloadButton from "../components/PDFDownloadButton";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorMessage from "../components/ErrorMessage";

const EMPTY_RESUME = {
  personal_info: { name: "", email: "", phone: "", linkedin: "" },
  summary: "",
  experience: [],
  education: [],
  skills: [],
};

export default function AccountPage() {
  const { dbUser, refreshDbUser } = useAuth();
  const [searchParams] = useSearchParams();
  const isFirstLogin = searchParams.get("setup") === "1";

  const [resumeData, setResumeData] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (dbUser?.has_resume) {
      getResume()
        .then((data) => setResumeData(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [dbUser]);

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const parsed = await uploadResume(file);
      setResumeData(parsed);
      setConfidence(parsed.parse_confidence);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleSave() {
    if (!resumeData) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await saveResume(resumeData);
      await refreshDbUser();
      setSuccess("Resume saved successfully!");
      setConfidence(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  const lowConfidence = confidence !== null && confidence < 0.4;
  const zeroConfidence = confidence !== null && confidence === 0;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-lg font-semibold text-zinc-100">My Account</h1>

      {isFirstLogin && !dbUser?.has_resume && (
        <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-4">
          <p className="text-sm text-indigo-300">
            Upload your resume to get started — you need it to tailor your resume to job listings.
          </p>
        </div>
      )}

      {/* Upload section */}
      <div className="bg-zinc-900 border border-white/10 rounded-lg p-4 space-y-3">
        <h2 className="text-sm font-medium text-zinc-200">
          {resumeData ? "Upload New Resume" : "Upload Resume"}
        </h2>
        <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-md cursor-pointer transition">
          {uploading ? "Uploading..." : "Choose PDF or DOCX"}
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={handleUpload}
            disabled={uploading}
            className="hidden"
          />
        </label>
        <p className="text-xs text-zinc-500">
          For best results, upload your LinkedIn Profile as a PDF.
        </p>
      </div>

      {error && <ErrorMessage message={error} />}
      {success && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
          <p className="text-sm text-green-400">{success}</p>
        </div>
      )}

      {/* Confidence warnings */}
      {zeroConfidence && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <p className="text-sm text-red-400">
            We couldn't parse this file. Please enter your information manually, or try uploading a LinkedIn PDF export.
          </p>
        </div>
      )}
      {lowConfidence && !zeroConfidence && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
          <p className="text-sm text-amber-400">
            We had trouble parsing your resume. Please review and fill in the missing sections.
          </p>
        </div>
      )}

      {/* Resume form */}
      {resumeData && (
        <>
          <ResumeForm
            data={resumeData}
            onChange={setResumeData}
            expandAll={lowConfidence || zeroConfidence}
          />
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
            >
              {saving ? "Saving..." : "Save Resume"}
            </button>
            {dbUser?.has_resume && <PDFDownloadButton data={resumeData} />}
          </div>
        </>
      )}
    </div>
  );
}
