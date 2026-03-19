import { useState } from "react";
import { pdf } from "@react-pdf/renderer";
import ResumeTemplate from "./ResumeTemplate";

export default function PDFDownloadButton({ data, filename = "resume.pdf" }) {
  const [generating, setGenerating] = useState(false);

  async function handleDownload() {
    setGenerating(true);
    try {
      const blob = await pdf(<ResumeTemplate data={data} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF generation failed:", err);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={generating}
      className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-zinc-200 text-sm font-medium rounded-md border border-white/10 transition"
    >
      {generating ? "Generating PDF..." : "Download PDF"}
    </button>
  );
}
