import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { cn } from "../../utils/cn";
import { Button } from "../ui/Button";

const navLinks = [
  { to: "/", label: "Dashboard", key: "dashboard" },
  { to: "/channels", label: "Channels", key: "channels" },
  { to: "/groups", label: "Groups", key: "groups" },
  { to: "/packages", label: "Packages & Tariffs", key: "packages" },
  { to: "/users", label: "Users", key: "users" },
];

function isActive(key: string, pathname: string): boolean {
  if (key === "dashboard") return pathname === "/";
  return pathname.startsWith(`/${key}`);
}

export function NavBar() {
  const { admin, logout } = useAuth();
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <nav className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur">
      <div className="mx-auto w-full max-w-screen-2xl px-4 md:px-6">
        <div className="flex min-h-16 items-center justify-between gap-4 py-2">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              to="/"
              className="flex min-w-0 items-center gap-2 rounded-md px-1 py-1 text-lg font-semibold text-slate-900"
            >
              <img
                src="/media/rutv-logo.png"
                alt="RUTV logo"
                className="h-8 w-8 flex-shrink-0 object-contain"
              />
              <span className="truncate">Playlist Service</span>
            </Link>
          </div>

          <div className="hidden items-center gap-1 md:flex">
            {navLinks.map((link) => (
              <Link
                key={link.key}
                to={link.to}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-900",
                  isActive(link.key, pathname) && "bg-sky-50 text-sky-800"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden text-sm text-slate-600 md:block">
              {admin?.username}
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="hidden md:inline-flex"
              onClick={() => void logout()}
            >
              Logout
            </Button>
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-300 text-slate-700 md:hidden"
              onClick={() => setMobileOpen((prev) => !prev)}
              aria-expanded={mobileOpen}
              aria-controls="mobile-nav"
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {mobileOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {mobileOpen && (
          <div id="mobile-nav" className="border-t border-slate-200 py-3 md:hidden">
            <div className="mb-3 px-1 text-sm text-slate-600">{admin?.username}</div>
            <div className="grid gap-1">
              {navLinks.map((link) => (
                <Link
                  key={`${link.key}-mobile`}
                  to={link.to}
                  className={cn(
                    "rounded-lg px-3 py-2 text-sm font-medium text-slate-700",
                    isActive(link.key, pathname) && "bg-sky-50 text-sky-800"
                  )}
                >
                  {link.label}
                </Link>
              ))}
              <button
                type="button"
                onClick={() => void logout()}
                className="mt-1 rounded-lg px-3 py-2 text-left text-sm font-medium text-rose-700 hover:bg-rose-50"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
