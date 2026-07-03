import { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Menu, X, Users2, LayoutDashboard, Sparkles, Search, History,
  MessageSquareHeart, LogOut, ListChecks, CalendarDays, ChevronDown, Lightbulb, Target, BarChart3, TrendingUp, Network, Activity, ScrollText, Radar, BrainCircuit, UserCircle2, Settings, Palette, CircleHelp, Bell, AlertCircle, Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useNotifications } from "../hooks/useNotifications";

const navGroups = [
  {
    label: "Command Center",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/follow-ups", label: "Follow-ups", icon: ListChecks },
      { to: "/recommendations", label: "Recommendations", icon: Lightbulb },
      { to: "/opportunities", label: "Opportunities", icon: Target },
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
      { to: "/relationship-scores", label: "Relationship Scores", icon: TrendingUp },
      { to: "/network-graph", label: "Network Graph", icon: Network },
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/history", label: "History", icon: History },
      { to: "/feedback-history", label: "Feedback", icon: MessageSquareHeart },
    ],
  },
];

const developerConsoleItems = [
  { to: "/developer/metrics", label: "Metrics", icon: Activity },
  { to: "/developer/audit-logs", label: "Audit Logs", icon: ScrollText },
  { to: "/developer/retrieval-debug", label: "Retrieval Debug", icon: Radar },
  { to: "/developer/ranker-tools", label: "Ranker Tools", icon: BrainCircuit },
];

const accountItems = [
  { label: "Profile", icon: UserCircle2, to: "/profile" },
  { label: "Settings", icon: Settings, to: "/settings" },
  { label: "Help", icon: CircleHelp, to: "/help" },
];

function notificationTone(type) {
  if (type === "overdue_follow_up") return "border-red-500/15 bg-red-500/10";
  if (type === "high_priority_recommendation" || type === "high_priority_opportunity") {
    return "border-amber-500/15 bg-amber-500/10";
  }
  return "border-white/8 bg-white/[0.04]";
}

function NavDropdown({ group, isActive }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive ? "bg-accent/15 text-accent" : "text-white/60 hover:bg-white/5 hover:text-white"
        }`}
      >
        {group.label}
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full z-50 mt-1 min-w-[180px] rounded-lg glass py-1.5"
          >
            {group.items.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-white/70 transition-colors hover:bg-white/5 hover:text-white"
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function NotificationMenu({ username, mobile = false, onClose }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { loading, error, refresh, notifications, unreadCount, readMap, markAsRead, markAllAsRead, hasNotifications } =
    useNotifications(username);

  useEffect(() => {
    if (mobile) return undefined;
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [mobile]);

  function handleOpen(item) {
    markAsRead(item.id);
    setOpen(false);
    onClose?.();
    navigate(item.href);
  }

  if (mobile) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between px-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-white/40">Notifications</p>
            <p className="mt-1 text-xs text-white/40">Derived from live backend data</p>
          </div>
          {unreadCount > 0 ? (
            <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] font-semibold text-white">{unreadCount}</span>
          ) : null}
        </div>

        <div className="rounded-xl border border-white/8 bg-white/[0.03] px-3 py-3">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-white/50">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading notifications...
            </div>
          ) : error ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-red-300">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
              <button onClick={refresh} className="text-xs text-white/60 hover:text-white">
                Retry
              </button>
            </div>
          ) : !hasNotifications ? (
            <p className="text-sm text-white/45">No notifications right now.</p>
          ) : (
            <div className="space-y-2">
              {notifications.slice(0, 5).map((item) => {
                const isRead = Boolean(readMap[item.id]);
                return (
                  <button
                    key={item.id}
                    onClick={() => handleOpen(item)}
                    className={`w-full rounded-xl border px-3 py-3 text-left transition-colors hover:bg-white/[0.06] ${notificationTone(item.type)}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-white">{item.title}</p>
                        <p className="mt-1 line-clamp-2 text-xs text-white/50">{item.subtitle}</p>
                      </div>
                      {!isRead ? <span className="mt-1 h-2.5 w-2.5 rounded-full bg-accent" /> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className={`relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border transition-all duration-200 ${
          open
            ? "border-white/12 bg-white/10 text-white shadow-[0_12px_30px_rgba(10,14,24,0.28)]"
            : "border-transparent text-white/60 hover:border-white/10 hover:bg-white/5 hover:text-white"
        }`}
        aria-label="Notifications"
      >
        <Bell className="h-4.5 w-4.5" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.985 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="absolute right-0 top-full z-[90] mt-3 w-[380px] overflow-hidden rounded-3xl border border-white/12 bg-[rgba(10,14,24,0.92)] p-2.5 shadow-[0_28px_90px_rgba(2,6,23,0.68)] backdrop-blur-2xl supports-[backdrop-filter]:bg-[rgba(10,14,24,0.8)]"
          >
            <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3.5">
              <div>
                <p className="text-sm font-semibold text-white">Notification Center</p>
                <p className="mt-1 text-xs text-white/45">
                  Live snapshots from existing backend data. No real-time push or WebSockets.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {unreadCount > 0 ? (
                  <button onClick={markAllAsRead} className="text-xs text-white/60 hover:text-white">
                    Mark all read
                  </button>
                ) : null}
                <span className="rounded-full bg-accent/15 px-2.5 py-1 text-xs font-medium text-accent">
                  {unreadCount} unread
                </span>
              </div>
            </div>

            <div className="mt-2 max-h-[420px] overflow-y-auto pr-1">
              {loading ? (
                <div className="flex items-center gap-2 rounded-2xl px-4 py-6 text-sm text-white/50">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading notifications...
                </div>
              ) : error ? (
                <div className="rounded-2xl border border-red-500/15 bg-red-500/10 px-4 py-4">
                  <div className="flex items-center gap-2 text-sm text-red-300">
                    <AlertCircle className="h-4 w-4" />
                    {error}
                  </div>
                  <button onClick={refresh} className="mt-3 text-xs text-white/60 hover:text-white">
                    Retry
                  </button>
                </div>
              ) : !hasNotifications ? (
                <div className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-8 text-center">
                  <p className="text-sm font-medium text-white">No notifications yet</p>
                  <p className="mt-1 text-sm text-white/45">
                    As real follow-ups, events, opportunities, and relationship risks appear, they will surface here.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {notifications.map((item) => {
                    const isRead = Boolean(readMap[item.id]);
                    return (
                      <button
                        key={item.id}
                        onClick={() => handleOpen(item)}
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors hover:bg-white/[0.06] ${notificationTone(item.type)}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-white">{item.title}</p>
                              {!isRead ? <span className="h-2 w-2 rounded-full bg-accent" /> : null}
                            </div>
                            <p className="mt-1 line-clamp-2 text-xs text-white/50">{item.subtitle}</p>
                          </div>
                          <span className="rounded-full bg-white/5 px-2 py-1 text-[11px] text-white/60">
                            {Math.round(item.priority)}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function UserMenu({ username, isAdmin, onLogout, mobile = false, onClose }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { themePreference, setThemePreference, themeOptions } = useTheme();

  useEffect(() => {
    if (mobile) return undefined;
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [mobile]);

  const activeDeveloperRoute = developerConsoleItems.some((item) => window.location.pathname === item.to);

  if (mobile) {
    return (
      <div className="space-y-2">
        <div className="px-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-white/40">Account</p>
          <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
            <p className="text-sm font-medium text-white">{username || "User"}</p>
            <p className="mt-1 text-xs text-white/40">Workspace menu</p>
          </div>
        </div>

        <div className="space-y-1">
          {accountItems.map(({ label, icon: Icon, to }) => (
            <Link
              key={label}
              to={to}
              onClick={onClose}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-white/60 transition-colors hover:bg-white/5 hover:text-white"
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </div>

        <div className="rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3">
          <div className="flex items-center gap-3 text-white/45">
            <Palette className="h-4 w-4" />
            <div className="flex-1">
              <p className="text-sm font-medium text-white/60">Theme</p>
              <p className="mt-1 text-xs text-white/40">Dark palette with saved browser preference</p>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {themeOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setThemePreference(option.value)}
                className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                  themePreference === option.value
                    ? "border-accent/30 bg-accent/15 text-white"
                    : "border-white/10 bg-white/5 text-white/60 hover:bg-white/10 hover:text-white"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {isAdmin ? (
          <div className="border-t border-amber-500/10 pt-2">
            <p className="mb-1 px-3 text-xs font-medium uppercase tracking-wide text-amber-200/70">
              Developer Console
            </p>
            <div className="space-y-1">
              {developerConsoleItems.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  onClick={onClose}
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-amber-100/75 hover:bg-amber-500/10 hover:text-amber-50"
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              ))}
            </div>
          </div>
        ) : null}

        <button
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/10"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition-all duration-200 ${
          open || activeDeveloperRoute
            ? "border-white/12 bg-white/10 text-white shadow-[0_12px_30px_rgba(10,14,24,0.28)]"
            : "border-transparent text-white/60 hover:border-white/10 hover:bg-white/5 hover:text-white"
        }`}
      >
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/12 bg-white/6">
          <UserCircle2 className="h-4 w-4" />
        </span>
        <span className="max-w-[140px] truncate text-left font-medium">{username || "User"}</span>
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.985 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="absolute right-0 top-full z-[90] mt-3 w-[320px] overflow-hidden rounded-3xl border border-white/12 bg-[rgba(10,14,24,0.92)] p-2.5 shadow-[0_28px_90px_rgba(2,6,23,0.68)] backdrop-blur-2xl supports-[backdrop-filter]:bg-[rgba(10,14,24,0.8)]"
          >
            <div className="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3.5">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-white/10 to-white/[0.03]">
                  <UserCircle2 className="h-5 w-5 text-white/75" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">{username || "User"}</p>
                  <p className="mt-1 text-xs text-white/45">Account menu</p>
                </div>
              </div>
            </div>

            <div className="mt-2 space-y-1">
              {accountItems.map(({ label, icon: Icon, to }) => (
                <Link
                  key={label}
                  to={to}
                  onClick={() => setOpen(false)}
                  className="flex w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-sm text-white/60 transition-colors hover:bg-white/[0.06] hover:text-white"
                >
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-white/8 bg-white/[0.04]">
                    <Icon className="h-4 w-4" />
                  </span>
                  {label}
                </Link>
              ))}
            </div>

            <div className="mt-2 rounded-2xl border border-white/8 bg-white/[0.03] px-3.5 py-3">
              <div className="flex items-center gap-3 text-white/60">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-white/8 bg-white/[0.04]">
                  <Palette className="h-4 w-4" />
                </span>
                <div className="flex-1">
                  <p className="text-sm">Theme</p>
                  <p className="mt-1 text-xs text-white/40">Dark palette with saved browser preference</p>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {themeOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setThemePreference(option.value)}
                    className={`rounded-xl border px-3 py-2 text-xs font-medium transition-colors ${
                      themePreference === option.value
                        ? "border-accent/30 bg-accent/15 text-white"
                        : "border-white/10 bg-white/5 text-white/60 hover:bg-white/[0.06] hover:text-white"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {isAdmin ? (
              <div className="mt-2 border-t border-white/8 pt-3">
                <p className="px-3.5 pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-200/70">
                  Developer Console
                </p>
                <div className="space-y-1">
                  {developerConsoleItems.map(({ to, label, icon: Icon }) => (
                    <Link
                      key={to}
                      to={to}
                      onClick={() => setOpen(false)}
                      className="flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm text-amber-100/80 transition-colors hover:bg-amber-500/12 hover:text-amber-50"
                    >
                      <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-amber-500/15 bg-amber-500/10">
                        <Icon className="h-4 w-4" />
                      </span>
                      {label}
                    </Link>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mt-2 border-t border-white/8 pt-3">
              <button
                onClick={() => {
                  setOpen(false);
                  onLogout();
                }}
                className="flex w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-sm text-red-300 transition-colors hover:bg-red-500/10 hover:text-red-200"
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-red-500/15 bg-red-500/10">
                  <LogOut className="h-4 w-4" />
                </span>
                Logout
              </button>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const { username, logout, role } = useAuth();
  const isAdmin = role === "admin";

  return (
    <nav className="sticky top-0 z-50 border-b border-white/5 glass">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-secondary">
              <Users2 className="h-4 w-4 text-white" />
            </div>
            <span className="hidden font-bold text-white sm:block">
              <span className="gradient-text">Nexora</span>
            </span>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {navGroups.map((group) => (
              <NavDropdown
                key={group.label}
                group={group}
                isActive={group.items.some((item) => item.to === location.pathname)}
              />
            ))}
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <NotificationMenu username={username} />
            <UserMenu username={username} isAdmin={isAdmin} onLogout={logout} />
          </div>

          <button className="p-2 text-white/70 md:hidden" onClick={() => setMobileOpen((value) => !value)}>
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {mobileOpen ? (
        <div className="space-y-4 border-t border-white/5 px-4 py-3 glass md:hidden">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="mb-1 px-3 text-xs font-medium uppercase tracking-wide text-white/40">{group.label}</p>
              <div className="space-y-1">
                {group.items.map(({ to, label, icon: Icon }) => (
                  <Link
                    key={to}
                    to={to}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                      location.pathname === to
                        ? "bg-accent/15 text-accent"
                        : "text-white/60 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          ))}

          <NotificationMenu mobile username={username} onClose={() => setMobileOpen(false)} />
          <UserMenu
            mobile
            username={username}
            isAdmin={isAdmin}
            onClose={() => setMobileOpen(false)}
            onLogout={() => {
              setMobileOpen(false);
              logout();
            }}
          />
        </div>
      ) : null}
    </nav>
  );
}
