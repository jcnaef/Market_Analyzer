import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ResumeProvider } from "./context/ResumeContext";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import JobBoard from "./pages/JobBoard";
import SkillExplorer from "./pages/SkillExplorer";
import SalaryInsights from "./pages/SalaryInsights";
import ResumeAnalyzer from "./pages/ResumeAnalyzer";
import AccountPage from "./pages/AccountPage";
import TailoringPage from "./pages/TailoringPage";

function ProtectedRoute({ children, requireResume = false }) {
  const { firebaseUser, dbUser, loading } = useAuth();
  if (loading) return null;
  if (!firebaseUser) return <Navigate to="/" replace />;
  if (requireResume && dbUser && !dbUser.has_resume) {
    return <Navigate to="/account?setup=1" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <ResumeProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="jobs" element={<JobBoard />} />
            <Route path="skills" element={<SkillExplorer />} />
            <Route path="salary" element={<SalaryInsights />} />
            <Route path="resume" element={<ResumeAnalyzer />} />
            <Route
              path="account"
              element={
                <ProtectedRoute>
                  <AccountPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="tailor"
              element={
                <ProtectedRoute requireResume>
                  <TailoringPage />
                </ProtectedRoute>
              }
            />
          </Route>
        </Routes>
      </ResumeProvider>
    </AuthProvider>
  );
}
