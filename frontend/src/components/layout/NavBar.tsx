import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { Folder, Gauge, LogOut, Menu, Package, Tv, Users, X } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { cn } from "../../lib/utils";
import { ThemeToggle } from "./ThemeToggle";

const navLinks = [
  { to: "/", label: "Dashboard", key: "dashboard", icon: Gauge },
  { to: "/channels", label: "Channels", key: "channels", icon: Tv },
  { to: "/groups", label: "Groups", key: "groups", icon: Folder },
  { to: "/packages", label: "Packages & Tariffs", key: "packages", icon: Package },
  { to: "/users", label: "Users", key: "users", icon: Users },
];

function isActive(key: string, pathname: string): boolean {
  if (key === "dashboard") return pathname === "/";
  return pathname.startsWith(`/${key}`);
}

function DrawerContent({ onNavigate }: { onNavigate?: () => void }) {
  const { admin, logout } = useAuth();
  const { pathname } = useLocation();

  return (
    <div className="flex min-h-full flex-col bg-card text-card-foreground">
      <div className="flex min-h-16 items-center gap-3 border-b border-border px-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-muted">
          <img src="/media/rutv-logo.png" alt="RUTV logo" className="h-8 w-8 object-contain" />
        </span>
        <div className="min-w-0">
          <div className="truncate text-sm font-bold text-card-foreground">RuTV Middleware</div>
          <div className="truncate text-xs text-muted-foreground">Admin console</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-3" aria-label="Main navigation">
        {navLinks.map((link) => {
          const active = isActive(link.key, pathname);
          const Icon = link.icon;
          return (
            <RouterLink
              key={link.key}
              to={link.to}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className={cn("h-4 w-4", active ? "text-accent-foreground" : "text-muted-foreground")} aria-hidden="true" />
              <span className="truncate">{link.label}</span>
            </RouterLink>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        <div className="mb-2 flex items-center justify-between gap-2 px-2">
          <div className="min-w-0 truncate text-sm text-muted-foreground">{admin?.username}</div>
          <ThemeToggle className="hidden md:inline-flex" />
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold text-destructive transition hover:bg-destructive/10"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          Logout
        </button>
      </div>
    </div>
  );
}

export function NavBar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-border bg-card text-card-foreground md:hidden">
        <div className="flex h-12 items-center gap-2 px-3">
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
          <span className="min-w-0 flex-1 truncate text-sm font-bold text-card-foreground">RuTV Middleware</span>
          <ThemeToggle />
        </div>
      </header>

      <aside
        className="fixed inset-y-0 left-0 z-30 hidden w-[248px] border-r border-border bg-card md:block"
        aria-label="Main navigation"
      >
        <DrawerContent />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/70"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          />
          <aside className="relative h-full w-[248px] shadow-xl">
            <button
              type="button"
              className="absolute right-2 top-2 z-10 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
            <DrawerContent onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}
    </>
  );
}
