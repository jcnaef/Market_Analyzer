import { Routes, Route } from "react-router-dom";
import { ResumeProvider } from "./context/ResumeContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import JobBoard from "./pages/JobBoard";
import SkillExplorer from "./pages/SkillExplorer";
import SalaryInsights from "./pages/SalaryInsights";
import SkillGapAnalyzer from "./pages/SkillGapAnalyzer";
import ResumeAnalyzer from "./pages/ResumeAnalyzer";

export default function App() {
  return (
    <ResumeProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="jobs" element={<JobBoard />} />
          <Route path="skills" element={<SkillExplorer />} />
          <Route path="salary" element={<SalaryInsights />} />
          <Route path="skill-gap" element={<SkillGapAnalyzer />} />
          <Route path="resume" element={<ResumeAnalyzer />} />
        </Route>
      </Routes>
    </ResumeProvider>
  );
}
