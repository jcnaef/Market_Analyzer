import { createContext, useContext, useState, useEffect, useRef } from "react";
import { onAuthStateChanged, signInWithPopup, signOut } from "firebase/auth";
import { useNavigate } from "react-router-dom";
import { auth, googleProvider } from "../config/firebase";
import { getUserMe } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null);
  const [dbUser, setDbUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const isNewLogin = useRef(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user);
      if (user) {
        try {
          const data = await getUserMe();
          setDbUser(data);
          // Redirect after login
          if (isNewLogin.current) {
            if (!data.has_resume) {
              navigate("/account?setup=1");
            } else {
              const pendingJobId = sessionStorage.getItem("pendingTailorJobId");
              if (pendingJobId) {
                sessionStorage.removeItem("pendingTailorJobId");
                navigate(`/tailor?jobId=${pendingJobId}`);
              }
            }
          }
        } catch {
          setDbUser(null);
        }
      } else {
        setDbUser(null);
      }
      isNewLogin.current = false;
      setLoading(false);
    });
    return unsubscribe;
  }, [navigate]);

  async function login() {
    isNewLogin.current = true;
    await signInWithPopup(auth, googleProvider);
  }

  async function logout() {
    await signOut(auth);
    setDbUser(null);
  }

  async function getIdToken() {
    if (!firebaseUser) return null;
    return firebaseUser.getIdToken();
  }

  async function refreshDbUser() {
    try {
      const data = await getUserMe();
      setDbUser(data);
    } catch {
      setDbUser(null);
    }
  }

  return (
    <AuthContext.Provider
      value={{
        firebaseUser,
        dbUser,
        loading,
        login,
        logout,
        getIdToken,
        refreshDbUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
