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
  const [mobileOpen, setMobileOpen] = useState(false);
  const dropdownRef = useRef(null);
  const mobileRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
      if (mobileRef.current && !mobileRef.current.contains(e.target)) {
        setMobileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const linkClass = ({ isActive }) =>
    `px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition ${
      isActive
        ? "bg-indigo-500/10 text-indigo-400"
        : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
    }`;

  const mobileLinkClass = ({ isActive }) =>
    `block px-4 py-3 text-sm font-medium transition ${
      isActive
        ? "bg-indigo-500/10 text-indigo-400"
        : "text-zinc-300 hover:bg-white/5"
    }`;

  return (
    <nav
      ref={mobileRef}
      className="bg-zinc-900 border-b border-white/10 sticky top-0 z-50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-12">
          <NavLink to="/" className="text-sm font-medium text-zinc-100 shrink-0 tracking-tight">
            CareerLogic
          </NavLink>

          {/* Desktop links */}
          <div className="hidden sm:flex items-center gap-0.5">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className={linkClass}
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Auth section */}
            <div className="relative" ref={dropdownRef}>
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

            {/* Hamburger — mobile only */}
            <button
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Toggle navigation menu"
              aria-expanded={mobileOpen}
              className="sm:hidden flex items-center justify-center w-9 h-9 rounded-md text-zinc-300 hover:bg-white/5 transition"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {mobileOpen ? (
                  <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                ) : (
                  <>
                    <path d="M3 6h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    <path d="M3 10h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    <path d="M3 14h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </>
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile slide-down panel */}
      {mobileOpen && (
        <div className="sm:hidden border-t border-white/10 bg-zinc-900">
          <div className="max-w-7xl mx-auto py-1">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                onClick={() => setMobileOpen(false)}
                className={mobileLinkClass}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
