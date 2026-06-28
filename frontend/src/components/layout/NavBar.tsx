import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { cn } from "../../lib/utils";
import { ThemeToggle } from "./ThemeToggle";

interface NavIconProps {
  className?: string;
}

function DashboardCardsIcon({ className }: NavIconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5.5A1.5 1.5 0 015.5 4h4A1.5 1.5 0 0111 5.5v4A1.5 1.5 0 019.5 11h-4A1.5 1.5 0 014 9.5v-4zM13 5.5A1.5 1.5 0 0114.5 4h4A1.5 1.5 0 0120 5.5v4a1.5 1.5 0 01-1.5 1.5h-4A1.5 1.5 0 0113 9.5v-4zM4 14.5A1.5 1.5 0 015.5 13h4a1.5 1.5 0 011.5 1.5v4A1.5 1.5 0 019.5 20h-4A1.5 1.5 0 014 18.5v-4zM13 14.5a1.5 1.5 0 011.5-1.5h4a1.5 1.5 0 011.5 1.5v4a1.5 1.5 0 01-1.5 1.5h-4a1.5 1.5 0 01-1.5-1.5v-4z" />
    </svg>
  );
}

function ChannelsIcon({ className }: NavIconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function GroupsIcon({ className }: NavIconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  );
}

function PackagesIcon({ className }: NavIconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  );
}

function UsersIcon({ className }: NavIconProps) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

const navLinks = [
  { to: "/", label: "Dashboard", key: "dashboard", icon: DashboardCardsIcon },
  { to: "/channels", label: "Channels", key: "channels", icon: ChannelsIcon },
  { to: "/groups", label: "Groups", key: "groups", icon: GroupsIcon },
  { to: "/packages", label: "Packages & Tariffs", key: "packages", icon: PackagesIcon },
  { to: "/users", label: "Users", key: "users", icon: UsersIcon },
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
      <div className="flex min-h-20 items-center gap-3 border-b border-border px-4">
        <img src="/media/rutv-logo.png" alt="RUTV logo" className="h-12 w-12 shrink-0 object-contain" />
        <div className="flex min-w-0 flex-1 items-center gap-2">
            <div className="truncate text-base font-bold text-card-foreground">Middleware</div>
            <ThemeToggle className="ml-auto hidden md:inline-flex" />
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
                "flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium transition",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className={cn("h-5 w-5", active ? "text-accent-foreground" : "text-muted-foreground")} aria-hidden="true" />
              <span className="truncate">{link.label}</span>
            </RouterLink>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        <div className="flex items-center justify-between gap-2 px-2">
          <div className="min-w-0 truncate text-sm text-muted-foreground">{admin?.username}</div>
          <button
            type="button"
            onClick={() => void logout()}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-destructive transition hover:bg-destructive/10"
            aria-label="Logout"
            title="Logout"
          >
            <LogOut className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
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
          <span className="min-w-0 flex-1 truncate text-base font-bold text-card-foreground">Middleware</span>
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
