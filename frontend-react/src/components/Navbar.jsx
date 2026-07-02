import { useState, useRef, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Menu, X, Users2, LayoutDashboard, Sparkles, Search, History,
  MessageSquareHeart, LogOut, ListChecks, CalendarDays, ChevronDown,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";

const navGroups = [
  {
    label: "Command Center",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/follow-ups", label: "Follow-ups", icon: ListChecks },
    ],
  },
  {
    label: "Relationships",
    items: [
      { to: "/contacts", label: "Contacts", icon: Users2 },
      { to: "/events", label: "Events", icon: CalendarDays },
    ],
  },
  {
    label: "Prep",
    items: [
      { to: "/generate", label: "Generate", icon: Sparkles },
      { to: "/fact-check", label: "Fact Check", icon: Search },
    ],
  },
  {
    label: "Insights",
    items: [
      { to: "/history", label: "History", icon: History },
      { to: "/feedback-history", label: "Feedback", icon: MessageSquareHeart },
    ],
  },
];

function NavDropdown({ group, isActive }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive ? "bg-accent/15 text-accent" : "text-white/60 hover:text-white hover:bg-white/5"
        }`}
      >
        {group.label}
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-1 glass rounded-lg py-1.5 min-w-[180px] z-50"
          >
            {group.items.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-white/70 hover:text-white hover:bg-white/5 transition-colors"
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const { username, logout } = useAuth();

  return (
    <>
      <nav className="sticky top-0 z-50 glass border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/dashboard" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-secondary flex items-center justify-center">
                <Users2 className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-white hidden sm:block">
                Networking<span className="gradient-text">Assistant</span>
              </span>
            </Link>

            <div className="hidden md:flex items-center gap-1">
              {navGroups.map((group) => (
                <NavDropdown
                  key={group.label}
                  group={group}
                  isActive={group.items.some((i) => i.to === location.pathname)}
                />
              ))}
            </div>

            <div className="hidden md:flex items-center gap-3">
              <span className="text-sm text-white/50">{username}</span>
              <button
                onClick={logout}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-white/60 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>

            <button
              className="md:hidden p-2 text-white/70"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden glass border-t border-white/5 px-4 py-3 space-y-4">
            {navGroups.map((group) => (
              <div key={group.label}>
                <p className="text-xs font-medium text-white/40 uppercase tracking-wide px-3 mb-1">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {group.items.map(({ to, label, icon: Icon }) => (
                    <Link
                      key={to}
                      to={to}
                      onClick={() => setMobileOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
                        location.pathname === to
                          ? "bg-accent/15 text-accent"
                          : "text-white/60 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      {label}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
            <button
              onClick={() => {
                setMobileOpen(false);
                logout();
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        )}
      </nav>
    </>
  );
}