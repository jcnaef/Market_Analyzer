import { useState, useRef, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/jobs", label: "Jobs" },
  { to: "/skills", label: "Skills" },
  { to: "/salary", label: "Salary" },
  { to: "/resume", label: "Resume" },
];

export default function Navbar() {
  const { firebaseUser, loading, login, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <nav className="bg-zinc-900 border-b border-white/10 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-12">
          <NavLink to="/" className="text-sm font-medium text-zinc-100 shrink-0 tracking-tight">
            Market Analyzer
          </NavLink>
          <div className="flex items-center gap-0.5 overflow-x-auto">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition ${
                    isActive
                      ? "bg-indigo-500/10 text-indigo-400"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          {/* Auth section */}
          <div className="relative shrink-0 ml-2" ref={dropdownRef}>
            {loading ? (
              <div className="w-7 h-7 rounded-full bg-zinc-700 animate-pulse" />
            ) : firebaseUser ? (
              <>
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center"
                >
                  <img
                    src={firebaseUser.photoURL || ""}
                    alt=""
                    className="w-7 h-7 rounded-full border border-white/10 hover:border-indigo-400 transition"
                    referrerPolicy="no-referrer"
                  />
                </button>
                {dropdownOpen && (
                  <div className="absolute right-0 mt-1 w-44 bg-zinc-800 border border-white/10 rounded-lg shadow-lg py-1 z-50">
                    <div className="px-3 py-2 border-b border-white/10">
                      <p className="text-xs font-medium text-zinc-200 truncate">
                        {firebaseUser.displayName}
                      </p>
                      <p className="text-xs text-zinc-500 truncate">
                        {firebaseUser.email}
                      </p>
                    </div>
                    <NavLink
                      to="/account"
                      onClick={() => setDropdownOpen(false)}
                      className="block px-3 py-2 text-xs text-zinc-300 hover:bg-white/5 transition"
                    >
                      My Account
                    </NavLink>
                    <button
                      onClick={() => {
                        setDropdownOpen(false);
                        logout();
                      }}
                      className="w-full text-left px-3 py-2 text-xs text-zinc-400 hover:bg-white/5 hover:text-red-400 transition"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </>
            ) : (
              <button
                onClick={login}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-zinc-300 hover:text-zinc-100 hover:bg-white/5 border border-white/10 transition"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
